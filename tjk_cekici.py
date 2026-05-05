import requests
from bs4 import BeautifulSoup
from datetime import datetime
import csv
import os
import re
import sys
import pandas as pd
from urllib.parse import unquote, quote

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

# ============================================
# TJK YARIS VERI CEKICI v5 - ALTILI GANYAN DESTEKLİ
# ============================================

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "X-Requested-With": "XMLHttpRequest",
    "Referer": "https://www.tjk.org/TR/YarisSever/Info/Page/GunlukYarisProgrami"
}

bugun = datetime.now().strftime("%d/%m/%Y")
print("=" * 70)
print(f"TJK YARIS LISTESI CEKICI v5")
print(f"Tarih: {bugun}")
print("=" * 70)

TURKIYE_SEHIRLER = ["Ankara", "Izmir", "İzmir", "Bursa", "Diyarbakir", "Diyarbakır",
                    "Istanbul", "İstanbul", "Adana", "Sanliurfa", "Şanlıurfa",
                    "Elazig", "Elazığ", "Antalya", "Kocaeli"]

ALTILI_GANYAN_KOSULARI = []

# ADIM 1: Şehirleri bul
print("\n[1/3] Hipodromlar tespit ediliyor...")
ana_url = "https://www.tjk.org/TR/YarisSever/Info/Page/GunlukYarisProgrami"
response = requests.get(ana_url, headers=headers, timeout=15)
soup = BeautifulSoup(response.text, "html.parser")

sehirler = []
gorulen = set()
for link in soup.find_all("a", href=True):
    href = link.get("href", "")
    if "SehirId=" in href:
        try:
            sehir_id = href.split("SehirId=")[1].split("&")[0]
            if sehir_id in gorulen:
                continue
            gorulen.add(sehir_id)
            if "SehirAdi=" in href:
                raw = href.split("SehirAdi=")[1].split("&")[0]
                sehir_adi = unquote(raw.replace("+", " "))
            else:
                sehir_adi = link.text.strip()
            sehirler.append((sehir_id, sehir_adi))
        except:
            pass

turkiye = [(sid, sad) for sid, sad in sehirler
          if any(t in sad for t in TURKIYE_SEHIRLER)]

if not turkiye:
    print("\n[!] Bugun Turkiye'de yaris yok!")
    sys.exit()

for sid, sad in turkiye:
    print(f"   [+] {sad}")
print(f"\n   {len(turkiye)} hipodrom bulundu")

# ADIM 2: Veri çek
print(f"\n[2/3] Yaris verileri cekiliyor...")
tarih_dosya = datetime.now().strftime("%Y%m%d")
csv_dosya = f"yarislar_{tarih_dosya}.csv"

with open(csv_dosya, "w", encoding="utf-8-sig", newline="") as f:
    yazici = csv.writer(f, delimiter=";")
    yazici.writerow([
        "Hipodrom", "Kosu_No", "Saat", "Mesafe", "Pist", "Cins",
        "Sira", "At_Ismi", "Yas_Cinsiyet", "Orijin", "Kilo",
        "Jokey", "Sahip", "Antrenor", "Start_No", "HP",
        "Son_6_Yaris", "KGS", "S20", "Ganyan", "AGF", "Tarih"
    ])

    for sehir_id, sehir_adi in turkiye:
        print(f"\n   [{sehir_adi}] isleniyor...")
        sehir_adi_url = quote(sehir_adi.replace(" ", "+"), safe="+")
        sehir_url = (f"https://www.tjk.org/TR/YarisSever/Info/Sehir/GunlukYarisProgrami"
                     f"?SehirId={sehir_id}&QueryParameter_Tarih={bugun}"
                     f"&SehirAdi={sehir_adi_url}&Era=today")

        try:
            r = requests.get(sehir_url, headers=headers, timeout=20)
            ssoup = BeautifulSoup(r.text, "html.parser")

            # Saatleri bul
            kosu_saatleri = {}
            for tab in ssoup.find_all("a", id=re.compile(r"^anc-?\d+")):
                tab_text = tab.get_text(" ", strip=True)
                match = re.search(r'(\d+)\.\s*Ko[şs]u\s+(\d{1,2}[:\.]\d{2})', tab_text)
                if match:
                    kosu_no = match.group(1)
                    saat = match.group(2).replace(".", ":")
                    kosu_saatleri[kosu_no] = saat

            kosu_tablolari = ssoup.find_all("div", id=re.compile(r"^kosubilgisi-"))
            print(f"      [{len(kosu_tablolari)} kosu tablosu]")

            kosu_index = 0
            for kosu_div in kosu_tablolari:
                kosu_index += 1
                parent = kosu_div.find_parent("div", id=re.compile(r"^-?\d+"))

                # Altılı Ganyan kontrolü
                altili_var = False
                if parent:
                    parent_text = parent.get_text(" ", strip=True)
                    if "Altılı Ganyan" in parent_text or "ALTILI GANYAN" in parent_text:
                        altili_var = True

                kosu_no = str(kosu_index)
                if parent:
                    h3 = parent.find("h3", class_="race-no")
                    if h3:
                        h3_text = h3.get_text(" ", strip=True)
                        no_match = re.search(r'(\d+)\.\s*Ko[şs]u', h3_text)
                        if no_match:
                            kosu_no = no_match.group(1)

                if altili_var:
                    ALTILI_GANYAN_KOSULARI.append((sehir_adi, kosu_no))

                saat = kosu_saatleri.get(kosu_no, "")

                mesafe, pist, cins = "", "", ""
                if parent:
                    config = parent.find("h3", class_="race-config")
                    if config:
                        ctext = config.get_text(" ", strip=True)
                        m = re.search(r'\b(\d{3,4})\b', ctext)
                        if m: mesafe = m.group(1)
                        if "Çim" in ctext or "Cim" in ctext:
                            pist = "Cim"
                        elif "Kum" in ctext:
                            pist = "Kum"
                        for c in ["Maiden", "Handikap", "Şartlı", "Sartli", "Satış", "Satis", "KV", "A1", "A2", "A3"]:
                            if c in ctext:
                                cins = c
                                break

                tablo = kosu_div.find("table", class_="tablesorter")
                if not tablo: continue
                tbody = tablo.find("tbody")
                if not tbody: continue

                for tr in tbody.find_all("tr"):
                    try:
                        td_sira = tr.find("td", class_="gunluk-GunlukYarisProgrami-SiraId")
                        td_at = tr.find("td", class_="gunluk-GunlukYarisProgrami-AtAdi")
                        td_yas = tr.find("td", class_="gunluk-GunlukYarisProgrami-Yas")
                        td_orijin = tr.find("td", class_="gunluk-GunlukYarisProgrami-Baba")
                        td_kilo = tr.find("td", class_="gunluk-GunlukYarisProgrami-Kilo")
                        td_jokey = tr.find("td", class_="gunluk-GunlukYarisProgrami-JokeAdi")
                        td_sahip = tr.find("td", class_="gunluk-GunlukYarisProgrami-SahipAdi")
                        td_antrenor = tr.find("td", class_="gunluk-GunlukYarisProgrami-AntronorAdi")
                        td_start = tr.find("td", class_="gunluk-GunlukYarisProgrami-StartId")
                        td_hp = tr.find("td", class_="gunluk-GunlukYarisProgrami-Hc")
                        td_son6 = tr.find("td", class_="gunluk-GunlukYarisProgrami-Son6Yaris")
                        td_kgs = tr.find("td", class_="gunluk-GunlukYarisProgrami-KGS")
                        td_s20 = tr.find("td", class_="gunluk-GunlukYarisProgrami-s20")
                        td_gny = tr.find("td", class_="gunluk-GunlukYarisProgrami-Gny")
                        td_agf = tr.find("td", class_="gunluk-GunlukYarisProgrami-AGFORAN")

                        if not td_at or not td_sira: continue

                        sira = td_sira.get_text(strip=True)
                        at_text = td_at.get_text(" ", strip=True)
                        match_at = re.match(r"^([A-ZÇĞİÖŞÜ' ]+?)(?:\s+(?:KG|DB|KV|SK|SKG)|\s+\([^)]*\)|\s+[a-z]|$)", at_text)
                        at_ismi = match_at.group(1).strip() if match_at else at_text.split()[0]
                        if "(Koşmaz)" in at_text or "Kosmaz" in at_text: continue

                        yas = td_yas.get_text(strip=True) if td_yas else ""
                        orijin = td_orijin.get_text(strip=True) if td_orijin else ""
                        kilo = td_kilo.get_text(strip=True) if td_kilo else ""

                        jokey = ""
                        if td_jokey:
                            j_link = td_jokey.find("a")
                            if j_link: jokey = j_link.get_text(strip=True)
                            else: jokey = td_jokey.get_text(strip=True)

                        sahip = td_sahip.get_text(strip=True) if td_sahip else ""
                        antrenor = td_antrenor.get_text(strip=True) if td_antrenor else ""
                        start_no = td_start.get_text(strip=True) if td_start else ""
                        hp = td_hp.get_text(strip=True) if td_hp else ""
                        son6 = td_son6.get_text(strip=True) if td_son6 else ""
                        kgs = td_kgs.get_text(strip=True) if td_kgs else ""
                        s20 = td_s20.get_text(strip=True) if td_s20 else ""

                        ganyan = ""
                        if td_gny:
                            g_text = td_gny.get_text(strip=True)
                            g_match = re.search(r'(\d+[,.]?\d*)', g_text)
                            if g_match: ganyan = g_match.group(1)

                        agf = ""
                        if td_agf:
                            agf_text = td_agf.get_text(strip=True)
                            agf_match = re.search(r'%(\d+(?:[,.]\d+)?)', agf_text)
                            if agf_match: agf = "%" + agf_match.group(1)

                        yazici.writerow([
                            sehir_adi, kosu_no, saat, mesafe, pist, cins,
                            sira, at_ismi, yas, orijin, kilo,
                            jokey, sahip, antrenor, start_no, hp,
                            son6, kgs, s20, ganyan, agf, bugun
                        ])
                    except Exception as e:
                        pass
        except Exception as e:
            print(f"      [!] Hata: {e}")

# ADIM 3: Altılı Ganyan sütunu ekle
print(f"\n[3/3] Altili Ganyan kontrolu ve kayit...")
if ALTILI_GANYAN_KOSULARI:
    print(f"\n[+] Altılı Ganyan başlangıç koşuları: {ALTILI_GANYAN_KOSULARI}")
    df = pd.read_csv(csv_dosya, sep=";", encoding="utf-8-sig")
    df["Altili_Ganyan"] = 0
    for hip, kno in ALTILI_GANYAN_KOSULARI:
        df.loc[(df["Hipodrom"] == hip) & (df["Kosu_No"] == str(kno)), "Altili_Ganyan"] = 1
    df.to_csv(csv_dosya, sep=";", encoding="utf-8-sig", index=False)
    print("[+] Altili_Ganyan sutunu eklendi")
else:
    print("[i] Altılı Ganyan başlangıcı tespit edilemedi")

print("\n" + "=" * 70)
print("TAMAMLANDI!")
print(f"   Dosya: {os.path.abspath(csv_dosya)}")
print("=" * 70)