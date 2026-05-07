import requests
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
import csv, re, sys, os
from urllib.parse import unquote

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}

TURKIYE_SEHIRLER_MAP = {
    "Ankara":"Ankara","Istanbul":"İstanbul","İstanbul":"İstanbul","Izmir":"İzmir","İzmir":"İzmir",
    "Bursa":"Bursa","Diyarbakir":"Diyarbakır","Diyarbakır":"Diyarbakır","Adana":"Adana",
    "Sanliurfa":"Şanlıurfa","Şanlıurfa":"Şanlıurfa","Elazig":"Elazığ","Elazığ":"Elazığ",
    "Antalya":"Antalya","Kocaeli":"Kocaeli"
}

# SADECE DÜN
tarih = datetime.now() - timedelta(days=1)
tarih_str = tarih.strftime("%d/%m/%Y")
tarih_kisa = tarih.strftime("%d.%m.%Y")
tarih_url = tarih.strftime("%Y-%m-%d")

CSV = "gecmis_sonuclar.csv"
yeni_dosya = not os.path.exists(CSV)

eklenen = 0
with open(CSV, "a" if not yeni_dosya else "w", encoding="utf-8-sig", newline="") as f:
    yazici = csv.writer(f, delimiter=";")
    if yeni_dosya:
        yazici.writerow(["Tarih","Hipodrom","Kosu_No","Mesafe","Pist","Cins",
                         "Gelis_Sirasi","At_No","At_Ismi","Yas","Orijin_Baba","Orijin_Anne",
                         "Kilo","Jokey","Sahip","Antrenor","Start_No",
                         "AGF","HP","Derece","Ganyan","Fark"])

    ana_url = f"https://www.tjk.org/TR/YarisSever/Info/Page/GunlukYarisSonuclari?QueryParameter_Tarih={tarih_str}"
    try:
        r = requests.get(ana_url, headers=headers, timeout=15)
        soup = BeautifulSoup(r.text, "html.parser")
        sehirler, gorulen = [], set()
        for link in soup.find_all("a", href=True):
            href = link.get("href","")
            if "SehirId=" in href and "SehirAdi=" in href:
                try:
                    sid = href.split("SehirId=")[1].split("&")[0]
                    if sid in gorulen: continue
                    gorulen.add(sid)
                    raw = href.split("SehirAdi=")[1].split("&")[0]
                    sehirler.append(unquote(raw.replace("+"," ")))
                except: pass
        tr_sehirler = [val for s in sehirler for key,val in TURKIYE_SEHIRLER_MAP.items() if key in s]
        tr_sehirler = list(set(tr_sehirler))

        if not tr_sehirler:
            print(f"[{tarih_kisa}] Yarış yok")
        else:
            print(f"[{tarih_kisa}] {tr_sehirler}: ", end="", flush=True)
            for sehir_adi in tr_sehirler:
                sehir_url_part = sehir_adi.replace(" ", "")
                csv_url = (f"https://medya-cdn.tjk.org/raporftp/TJKPDF/{tarih.year}/{tarih_url}/CSV/"
                           f"GunlukYarisSonuclari/{tarih_kisa}-{sehir_url_part}-GunlukYarisSonuclari-TR.csv")
                try:
                    r_csv = requests.get(csv_url, headers=headers, timeout=15)
                    if r_csv.status_code != 200: continue
                    icerik = r_csv.content.decode("utf-8-sig", errors="replace")
                    satirlar = icerik.split("\n")
                    kosu_no, mesafe, pist, cins = "", "", "", ""
                    headers_bulundu = False
                    for satir in satirlar:
                        if not satir.strip(): continue
                        hucreler = satir.split(";")
                        if re.match(r'^\d+\.\s*Ko[sş]u', hucreler[0].strip()):
                            kosu_no = re.search(r'(\d+)\.', hucreler[0]).group(1)
                            for h in hucreler:
                                m = re.search(r'(\d{3,4})m', h)
                                if m: mesafe = m.group(1)
                                if "Çim" in h: pist = "Cim"
                                elif "Kum" in h: pist = "Kum"
                                elif "Sentetik" in h: pist = "Sentetik"
                            headers_bulundu = False
                            continue
                        if "At No" in satir or "At İsmi" in satir:
                            headers_bulundu = True
                            continue
                        if not headers_bulundu: continue
                        ilk = hucreler[0].strip()
                        if not re.match(r'^\d+$', ilk): continue
                        try:
                            gelis = ilk
                            at_no = hucreler[1].strip() if len(hucreler)>1 else ""
                            at_ismi = re.sub(r'\s+(KG|DB|KV|SK|SKG|GKR).*$', '', hucreler[2].strip() if len(hucreler)>2 else "").strip()
                            yas = hucreler[3].strip() if len(hucreler)>3 else ""
                            baba = hucreler[4].strip() if len(hucreler)>4 else ""
                            anne = hucreler[5].strip() if len(hucreler)>5 else ""
                            kilo = hucreler[6].strip() if len(hucreler)>6 else ""
                            jokey = hucreler[7].strip() if len(hucreler)>7 else ""
                            sahip = hucreler[8].strip() if len(hucreler)>8 else ""
                            antrenor = hucreler[9].strip() if len(hucreler)>9 else ""
                            start = hucreler[10].strip() if len(hucreler)>10 else ""
                            agf = hucreler[11].strip() if len(hucreler)>11 else ""
                            hp = hucreler[12].strip() if len(hucreler)>12 else ""
                            derece = hucreler[13].strip() if len(hucreler)>13 else ""
                            ganyan = hucreler[14].strip() if len(hucreler)>14 else ""
                            fark = hucreler[15].strip() if len(hucreler)>15 else ""

                            yazici.writerow([tarih_kisa, sehir_adi, kosu_no, mesafe, pist, cins,
                                             gelis, at_no, at_ismi, yas, baba, anne,
                                             kilo, jokey, sahip, antrenor, start,
                                             agf, hp, derece, ganyan, fark])
                            eklenen += 1
                        except: pass
                except: pass
        print(f"{eklenen} kayıt")
    except Exception as e:
        print(f"Hata: {e}")

print(f"\nToplam {eklenen} yeni kayıt eklendi.")