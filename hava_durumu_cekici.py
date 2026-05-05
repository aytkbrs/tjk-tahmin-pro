import requests
import csv
import sys
import time
import os
from datetime import datetime

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

try:
    from config import OPENWEATHER_API_KEY, HIPODROM_KONUMLARI
except ImportError:
    print("[!] config.py bulunamadi! Once olusturun.")
    sys.exit()

print("=" * 70)
print("HAVA DURUMU CEKICI")
print("=" * 70)

def hava_durumu_al(lat, lon):
    url = "https://api.openweathermap.org/data/2.5/weather"
    params = {
        "lat": lat, "lon": lon,
        "appid": OPENWEATHER_API_KEY,
        "units": "metric", "lang": "tr"
    }
    try:
        r = requests.get(url, params=params, timeout=10)
        if r.status_code == 200:
            data = r.json()
            return {
                "sicaklik": data["main"]["temp"],
                "nem": data["main"]["humidity"],
                "basinc": data["main"]["pressure"],
                "ruzgar_hizi": data.get("wind", {}).get("speed", 0),
                "bulut": data.get("clouds", {}).get("all", 0),
                "yagis": 1 if "rain" in data or "snow" in data else 0,
                "durum": data["weather"][0]["main"],
                "aciklama": data["weather"][0]["description"],
            }
        return None
    except Exception as e:
        print(f"   [!] Hata: {e}")
        return None

hava_verileri = {}
for hipodrom, (lat, lon) in HIPODROM_KONUMLARI.items():
    print(f"   📍 {hipodrom}...", end=" ")
    veri = hava_durumu_al(lat, lon)
    if veri:
        hava_verileri[hipodrom] = veri
        print(f"✓ {veri['sicaklik']:.1f}°C, {veri['durum']}, Nem: %{veri['nem']}")
    else:
        print("✗")
    time.sleep(0.3)

# Kaydet
with open("hava_durumu.csv", "w", encoding="utf-8-sig", newline="") as f:
    yazici = csv.writer(f, delimiter=";")
    yazici.writerow(["Hipodrom", "Tarih", "Sicaklik", "Nem", "Basinc",
                     "Ruzgar", "Bulut", "Yagis", "Durum", "Aciklama"])
    bugun = datetime.now().strftime("%d.%m.%Y")
    for hipodrom, v in hava_verileri.items():
        yazici.writerow([hipodrom, bugun,
            round(v["sicaklik"], 1), v["nem"], v["basinc"],
            round(v["ruzgar_hizi"], 1), v["bulut"], v["yagis"],
            v["durum"], v["aciklama"]])

print(f"\n[+] hava_durumu.csv kaydedildi ({len(hava_verileri)} hipodrom)")