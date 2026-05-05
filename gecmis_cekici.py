import requests
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
import csv
import re
import sys
import os
import time
from urllib.parse import unquote, quote

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
}

print("=" * 70)
print("GECMIS YARIS SONUCLARI INDIRICI")
print("=" * 70)

GUN_SAYISI = 365
print(f"\nSon {GUN_SAYISI} gunun verisi cekilecek...\n")

TURKIYE_SEHIRLER_MAP = {
    "Ankara": "Ankara", "Istanbul": "İstanbul", "İstanbul": "İstanbul",
    "Izmir": "İzmir", "İzmir": "İzmir", "Bursa": "Bursa",
    "Diyarbakir": "Diyarbakır", "Diyarbakır": "Diyarbakır",
    "Adana": "Adana", "Sanliurfa": "Şanlıurfa", "Şanlıurfa": "Şanlıurfa",
    "Elazig": "Elazığ", "Elazığ": "Elazığ", "Antalya": "Antalya",
    "Kocaeli": "Kocaeli"
}

master_csv = "gecmis_sonuclar.csv"
toplam_satir = 0

with open(master_csv, "w", encoding="utf-8-sig", newline="") as f_master:
    yazici = csv.writer(f_master, delimiter=";")
    yazici.writerow([
        "Tarih", "Hipodrom", "Kosu_No", "Mesafe", "Pist", "Cins",
        "Gelis_Sirasi", "At_No", "At_Ismi", "Yas", "Orijin_Baba", "Orijin_Anne",
        "Kilo", "Jokey", "Sahip", "Antrenor", "Start_No",
        "AGF", "HP", "Derece", "Ganyan", "Fark"
    ])
    
    for gun_geri in range(1, GUN_SAYISI + 1):
        tarih = datetime.now() - timedelta(days=gun_geri)
        tarih_str = tarih.strftime("%d/%m/%Y")
        tarih_kisa = tarih.strftime("%d.%m.%Y")
        tarih_url = tarih.strftime("%Y-%m-%d")
        
        ana_url = f"https://www.tjk.org/TR/YarisSever/Info/Page/GunlukYarisSonuclari?QueryParameter_Tarih={tarih_str}"
        
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
                        if sehir_id in gorulen:
                            continue
                        gorulen.add(sehir_id)
                        raw = href.split("SehirAdi=")[1].split("&")[0]
                        sehir_adi = unquote(raw.replace("+", " "))
                        sehirler.append(sehir_adi)
                    except:
                        pass
            
            tr_sehirler = []
            for s in sehirler:
                for key, val in TURKIYE_SEHIRLER_MAP.items():
                    if key in s:
                        tr_sehirler.append(val)
                        break
            tr_sehirler = list(set(tr_sehirler))
            
            if not tr_sehirler:
                print(f"[{tarih_kisa}] TR yarisi yok")
                continue
            
            print(f"[{tarih_kisa}] {tr_sehirler}: ", end="", flush=True)
            gun_satir = 0
            
            for sehir_adi in tr_sehirler:
                yil = tarih.year
                sehir_url_part = sehir_adi.replace(" ", "")
                csv_url = (f"https://medya-cdn.tjk.org/raporftp/TJKPDF/{yil}/{tarih_url}/CSV/"
                          f"GunlukYarisSonuclari/{tarih_kisa}-{sehir_url_part}-GunlukYarisSonuclari-TR.csv")
                
                try:
                    r_csv = requests.get(csv_url, headers=headers, timeout=15)
                    if r_csv.status_code != 200:
                        continue
                    
                    icerik = r_csv.content.decode("utf-8-sig", errors="replace")
                    satirlar = icerik.split("\n")
                    
                    su_anki_kosu = ""
                    su_anki_mesafe = ""
                    su_anki_pist = ""
                    su_anki_cins = ""
                    headers_bulundu = False
                    
                    for satir in satirlar:
                        if not satir.strip():
                            continue
                        hucreler = satir.split(";")
                        
                        if len(hucreler) > 0 and re.match(r'^\d+\.\s*Kosu', hucreler[0].strip()):
                            kosu_match = re.search(r'(\d+)\.\s*Kosu', hucreler[0])
                            if kosu_match:
                                su_anki_kosu = kosu_match.group(1)
                            for h in hucreler:
                                m = re.search(r'(\d{3,4})m', h)
                                if m:
                                    su_anki_mesafe = m.group(1)
                                if "Çim" in h: su_anki_pist = "Cim"
                                elif "Kum" in h: su_anki_pist = "Kum"
                                elif "Sentetik" in h: su_anki_pist = "Sentetik"
                            headers_bulundu = False
                            continue
                        
                        if "At No" in satir or "At İsmi" in satir or "At Ismi" in satir:
                            headers_bulundu = True
                            continue
                        
                        if not headers_bulundu:
                            continue
                        
                        ilk_hucre = hucreler[0].strip() if hucreler else ""
                        if not re.match(r'^\d+$', ilk_hucre):
                            continue
                        
                        try:
                            gelis = ilk_hucre
                            at_no = hucreler[1].strip() if len(hucreler) > 1 else ""
                            at_ismi_raw = hucreler[2].strip() if len(hucreler) > 2 else ""
                            at_ismi = re.sub(r'\s+(KG|DB|KV|SK|SKG|GKR).*$', '', at_ismi_raw).strip()
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
                            
                            yazici.writerow([
                                tarih_kisa, sehir_adi, su_anki_kosu, su_anki_mesafe, 
                                su_anki_pist, su_anki_cins,
                                gelis, at_no, at_ismi, yas, orijin_baba, orijin_anne,
                                kilo, jokey, sahip, antrenor, start_no,
                                agf, hp, derece, ganyan, fark
                            ])
                            gun_satir += 1
                            toplam_satir += 1
                        except:
                            pass
                    time.sleep(0.1)
                except:
                    pass
            
            print(f"{gun_satir} kayit")
        except Exception as e:
            print(f"[{tarih_kisa}] HATA: {e}")

print(f"\n{'='*70}")
print(f"TAMAMLANDI! Toplam {toplam_satir} at kaydi")
print(f"Dosya: {os.path.abspath(master_csv)}")