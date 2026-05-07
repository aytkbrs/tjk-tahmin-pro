import requests
from datetime import datetime, timedelta
import csv
import re
import sys
import os
from urllib.parse import unquote

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
}

TURKIYE_SEHIRLER_MAP = {
    "Ankara": "Ankara", "Istanbul": "İstanbul", "İstanbul": "İstanbul",
    "Izmir": "İzmir", "İzmir": "İzmir", "Bursa": "Bursa",
    "Diyarbakir": "Diyarbakır", "Diyarbakır": "Diyarbakır",
    "Adana": "Adana", "Sanliurfa": "Şanlıurfa", "Şanlıurfa": "Şanlıurfa",
    "Elazig": "Elazığ", "Elazığ": "Elazığ", "Antalya": "Antalya",
    "Kocaeli": "Kocaeli"
}

TARIH = (datetime.now() - timedelta(days=1)).strftime("%d/%m/%Y")  # dün
tarih_kisa = (datetime.now() - timedelta(days=1)).strftime("%d.%m.%Y")
tarih_url = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")

CSV_DOSYA = "gecmis_sonuclar.csv"
dosya_yeni_mi = not os.path.exists(CSV_DOSYA)

eklenen = 0
with open(CSV_DOSYA, "a" if not dosya_yeni_mi else "w", encoding="utf-8-sig", newline="") as f:
    yazici = csv.writer(f, delimiter=";")
    if dosya_yeni_mi:
        yazici.writerow(["Tarih","Hipodrom","Kosu_No","Mesafe","Pist","Cins",
                         "Gelis_Sirasi","At_No","At_Ismi","Yas","Orijin_Baba","Orijin_Anne",
                         "Kilo","Jokey","Sahip","Antrenor","Start_No",
                         "AGF","HP","Derece","Ganyan","Fark"])

    ana_url = f"https://www.tjk.org/TR/YarisSever/Info/Page/GunlukYarisSonuclari?QueryParameter_Tarih={TARIH}"
    try:
        r = requests.get(ana_url, headers=headers, timeout=15)
        soup = BeautifulSoup(r.text, "html.parser")

        sehirler = []
        gorulen = set()
        for link in soup.find_all("a", href=True):
            href = link.get("href", "")
            if "SehirId=" in href and "SehirAdi=" in href:
                try:
                    sehir_id = href.split("SehirId=")[1].split("&")[0]
                    if sehir_id in gorulen: continue
                    gorulen.add(sehir_id)
                    raw = href.split("SehirAdi=")[1].split("&")[0]
                    sehir_adi = unquote(raw.replace("+", " "))
                    sehirler.append(sehir_adi)
                except: pass

        tr_sehirler = [val for s in sehirler for key, val in TURKIYE_SEHIRLER_MAP.items() if key in s]
        tr_sehirler = list(set(tr_sehirler))

        if not tr_sehirler:
            print(f"[{tarih_kisa}] Yarış yok")
        else:
            print(f"[{tarih_kisa}] {tr_sehirler}: ", end="", flush=True)

            for sehir_adi in tr_sehirler:
                sehir_url_part = sehir_adi.replace(" ", "")
                csv_url = (f"https://medya-cdn.tjk.org/raporftp/TJKPDF/{tarih_url[:4]}/{tarih_url}/CSV/"
                           f"GunlukYarisSonuclari/{tarih_kisa}-{sehir_url_part}-GunlukYarisSonuclari-TR.csv")
                try:
                    r_csv = requests.get(csv_url, headers=headers, timeout=15)
                    if r_csv.status_code != 200: continue
                    icerik = r_csv.content.decode("utf-8-sig", errors="replace")
                    satirlar = icerik.split("\n")

                    su_anki_kosu, su_anki_mesafe, su_anki_pist, su_anki_cins = "", "", "", ""
                    headers_bulundu = False

                    for satir in satirlar:
                        if not satir.strip(): continue
                        hucreler = satir.split(";")

                        if len(hucreler) > 0 and re.match(r'^\d+\.\s*Kosu', hucreler[0].strip()):
                            kosu_match = re.search(r'(\d+)\.\s*Kosu', hucreler[0])
                            if kosu_match: su_anki_kosu = kosu_match.group(1)
                            for h in hucreler:
                                if re.search(r'(\d{3,4})m', h): su_anki_mesafe = re.search(r'(\d{3,4})m', h).group(1)
                                if "Çim" in h: su_anki_pist = "Cim"
                                elif "Kum" in h: su_anki_pist = "Kum"
                                elif "Sentetik" in h: su_anki_pist = "Sentetik"
                            headers_bulundu = False
                            continue

                        if "At No" in satir or "At İsmi" in satir or "At Ismi" in satir:
                            headers_bulundu = True
                            continue

                        if not headers_bulundu: continue
                        ilk_hucre = hucreler[0].strip() if hucreler else ""
                        if not re.match(r'^\d+$', ilk_hucre): continue

                        try:
                            gelis = ilk_hucre
                            at_no = hucreler[1].strip() if len(hucreler) > 1 else ""
                            at_ismi = re.sub(r'\s+(KG|DB|KV|SK|SKG|GKR).*$', '', hucreler[2].strip() if len(hucreler) > 2 else "").strip()
                            yas = hucreler[3].strip() if len(hucreler) > 3 else ""
                            orijin_baba = hucreler[4].strip() if len(hucreler) > 4 else ""
                            orijin_anne = hucreler[5].strip() if len(hucreler) > 5 else ""
                            kilo = hucreler[6].strip() if len(hucreler) > 6 else ""
                            jokey = hucreler[7].strip() if len(hucreler) > 7 else ""
                            sahip = hucreler[8].strip() if len(hucreler) > 8 else ""
                            antrenor = hucreler[9].strip() if len(hucreler) > 9 else ""
                            start_no = hucreler[10].strip() if len(hucreler) > 10 else ""
                            agf = hucreler[11].strip() if len(hucreler) > 11 else ""
                            hp = hucreler[12].strip() if len(hucreler) > 12 else ""
                            derece = hucreler[13].strip() if len(hucreler) > 13 else ""
                            ganyan = hucreler[14].strip() if len(hucreler) > 14 else ""
                            fark = hucreler[15].strip() if len(hucreler) > 15 else ""

                            yazici.writerow([tarih_kisa, sehir_adi, su_anki_kosu, su_anki_mesafe,
                                             su_anki_pist, su_anki_cins, gelis, at_no, at_ismi, yas,
                                             orijin_baba, orijin_anne, kilo, jokey, sahip, antrenor,
                                             start_no, agf, hp, derece, ganyan, fark])
                            eklenen += 1
                        except: pass
                except: pass
        print(f"{eklenen} kayit")
    except Exception as e:
        print(f"Hata: {e}")

print(f"\nToplam {eklenen} yeni kayit eklendi.")