import csv
import sys
import os
from collections import defaultdict

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

print("=" * 70)
print("ISTATISTIK MOTORU v2 - SUTUN KAYMASI DUZELTILDI")
print("=" * 70)

CSV_DOSYA = "gecmis_sonuclar.csv"

if not os.path.exists(CSV_DOSYA):
    print(f"[!] {CSV_DOSYA} bulunamadi!")
    sys.exit()

jokey_stats = defaultdict(lambda: {"toplam": 0, "bir": 0, "iki": 0, "uc": 0})
antrenor_stats = defaultdict(lambda: {"toplam": 0, "bir": 0, "iki": 0, "uc": 0})
at_stats = defaultdict(lambda: {"toplam": 0, "bir": 0, "iki": 0, "uc": 0})

print(f"\n[1/3] {CSV_DOSYA} okunuyor...")
toplam_kayit = 0
hatali = 0

with open(CSV_DOSYA, "r", encoding="utf-8-sig") as f:
    okuyucu = csv.DictReader(f, delimiter=";")
    
    for satir in okuyucu:
        try:
            gelis = satir.get("Gelis_Sirasi", "").strip()
            if not gelis or not gelis.isdigit():
                continue
            gelis_int = int(gelis)
            
            # DÜZELTME: CSV'de sütunlar 1 kaymış.
            # Gerçek At_Ismi  -> "At_No" sütununda
            # Gerçek Jokey    -> "Kilo" sütununda
            # Gerçek Antrenor -> "Sahip" sütununda
            
            at_ismi = satir.get("At_No", "").strip()
            jokey = satir.get("Kilo", "").strip()
            antrenor = satir.get("Sahip", "").strip()
            
            if jokey and len(jokey) > 1 and not jokey.replace('.','').replace(',','').isdigit():
                jokey_stats[jokey]["toplam"] += 1
                if gelis_int == 1: jokey_stats[jokey]["bir"] += 1
                elif gelis_int == 2: jokey_stats[jokey]["iki"] += 1
                elif gelis_int == 3: jokey_stats[jokey]["uc"] += 1
            
            if antrenor and len(antrenor) > 1 and not antrenor.isdigit():
                antrenor_stats[antrenor]["toplam"] += 1
                if gelis_int == 1: antrenor_stats[antrenor]["bir"] += 1
                elif gelis_int == 2: antrenor_stats[antrenor]["iki"] += 1
                elif gelis_int == 3: antrenor_stats[antrenor]["uc"] += 1
            
            if at_ismi and len(at_ismi) > 1:
                at_stats[at_ismi]["toplam"] += 1
                if gelis_int == 1: at_stats[at_ismi]["bir"] += 1
                elif gelis_int == 2: at_stats[at_ismi]["iki"] += 1
                elif gelis_int == 3: at_stats[at_ismi]["uc"] += 1
            
            toplam_kayit += 1
        except Exception as e:
            hatali += 1

print(f"   [+] {toplam_kayit} kayit islendi ({hatali} hatali)")
print(f"   [+] {len(jokey_stats)} jokey, {len(antrenor_stats)} antrenor, {len(at_stats)} at")

# Kaydet
print(f"\n[2/3] Kaydediliyor...")

with open("jokey_istatistik.csv", "w", encoding="utf-8-sig", newline="") as f:
    yazici = csv.writer(f, delimiter=";")
    yazici.writerow(["Jokey", "Toplam", "Birinci", "Ikinci", "Ucuncu", "Kazanma_Yuzde", "Ilk3_Yuzde"])
    for jokey, s in sorted(jokey_stats.items(), key=lambda x: -x[1]["toplam"]):
        if s["toplam"] >= 3:
            kazanma = round(s["bir"] / s["toplam"] * 100, 2)
            ilk3 = round((s["bir"] + s["iki"] + s["uc"]) / s["toplam"] * 100, 2)
            yazici.writerow([jokey, s["toplam"], s["bir"], s["iki"], s["uc"], kazanma, ilk3])

with open("antrenor_istatistik.csv", "w", encoding="utf-8-sig", newline="") as f:
    yazici = csv.writer(f, delimiter=";")
    yazici.writerow(["Antrenor", "Toplam", "Birinci", "Ikinci", "Ucuncu", "Kazanma_Yuzde", "Ilk3_Yuzde"])
    for antr, s in sorted(antrenor_stats.items(), key=lambda x: -x[1]["toplam"]):
        if s["toplam"] >= 3:
            kazanma = round(s["bir"] / s["toplam"] * 100, 2)
            ilk3 = round((s["bir"] + s["iki"] + s["uc"]) / s["toplam"] * 100, 2)
            yazici.writerow([antr, s["toplam"], s["bir"], s["iki"], s["uc"], kazanma, ilk3])

with open("at_istatistik.csv", "w", encoding="utf-8-sig", newline="") as f:
    yazici = csv.writer(f, delimiter=";")
    yazici.writerow(["At_Ismi", "Toplam", "Birinci", "Ikinci", "Ucuncu", "Kazanma_Yuzde", "Ilk3_Yuzde"])
    for at, s in sorted(at_stats.items(), key=lambda x: -x[1]["toplam"]):
        if s["toplam"] >= 1:
            kazanma = round(s["bir"] / s["toplam"] * 100, 2) if s["toplam"] else 0
            ilk3 = round((s["bir"] + s["iki"] + s["uc"]) / s["toplam"] * 100, 2) if s["toplam"] else 0
            yazici.writerow([at, s["toplam"], s["bir"], s["iki"], s["uc"], kazanma, ilk3])

print(f"   [+] jokey_istatistik.csv")
print(f"   [+] antrenor_istatistik.csv")
print(f"   [+] at_istatistik.csv")

# Özet
print(f"\n[3/3] OZET (En iyi 10)")
print("=" * 70)

print("\n🏆 En basarili 10 jokey:")
for j, s in sorted(jokey_stats.items(), key=lambda x: -x[1]["bir"])[:10]:
    if s["toplam"] >= 5:
        k = round(s["bir"]/s["toplam"]*100, 1)
        print(f"   {j[:28]:<28} {s['toplam']:>4} yaris, {s['bir']} birincilik (%{k})")

print("\n🏆 En basarili 10 antrenor:")
for a, s in sorted(antrenor_stats.items(), key=lambda x: -x[1]["bir"])[:10]:
    if s["toplam"] >= 5:
        k = round(s["bir"]/s["toplam"]*100, 1)
        print(f"   {a[:28]:<28} {s['toplam']:>4} yaris, {s['bir']} birincilik (%{k})")

print("\n🏆 En basarili 10 at:")
for at, s in sorted(at_stats.items(), key=lambda x: -x[1]["bir"])[:10]:
    if s["toplam"] >= 2:
        k = round(s["bir"]/s["toplam"]*100, 1)
        print(f"   {at[:28]:<28} {s['toplam']:>4} yaris, {s['bir']} birincilik (%{k})")

print("\n[+] TAMAMLANDI!")