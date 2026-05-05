import csv, sys, os, re, glob
from collections import defaultdict
from datetime import datetime

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

print("=" * 70)
print("⚡ SÜRPRİZ ANALİZİ - AYKIRI DEGER TESPITI")
print("=" * 70)

# İstatistikleri yükle
jokey_db, antrenor_db, at_db = {}, {}, {}
for dosya, db, anahtar in [
    ("jokey_istatistik.csv", jokey_db, "Jokey"),
    ("antrenor_istatistik.csv", antrenor_db, "Antrenor"),
    ("at_istatistik.csv", at_db, "At_Ismi")
]:
    if os.path.exists(dosya):
        with open(dosya, "r", encoding="utf-8-sig") as f:
            for s in csv.DictReader(f, delimiter=";"):
                try:
                    db[s[anahtar]] = {
                        "toplam": int(s["Toplam"]),
                        "kazanma": float(s["Kazanma_Yuzde"]),
                        "ilk3": float(s.get("Ilk3_Yuzde", 0)),
                    }
                except: pass

# At detayları
print("[+] At detaylari yukleniyor...")
at_mesafe = defaultdict(lambda: defaultdict(lambda: {"toplam":0,"ilk3":0}))
jokey_at = defaultdict(lambda: {"toplam":0,"ilk3":0,"bir":0})
at_form = defaultdict(list)

with open("gecmis_sonuclar.csv", "r", encoding="utf-8-sig") as f:
    for satir in csv.DictReader(f, delimiter=";"):
        try:
            gelis = int(satir.get("Gelis_Sirasi", "0"))
            if gelis == 0: continue
            at_ismi = satir.get("At_No", "").strip()
            jokey = satir.get("Kilo", "").strip()
            mesafe = satir.get("Mesafe", "").strip()
            tarih = satir["Tarih"]
            ilk3 = 1 if gelis <= 3 else 0
            bir = 1 if gelis == 1 else 0
            if at_ismi and mesafe:
                at_mesafe[at_ismi][mesafe]["toplam"] += 1
                at_mesafe[at_ismi][mesafe]["ilk3"] += ilk3
            if jokey and at_ismi:
                jokey_at[(jokey, at_ismi)]["toplam"] += 1
                jokey_at[(jokey, at_ismi)]["ilk3"] += ilk3
                jokey_at[(jokey, at_ismi)]["bir"] += bir
            at_form[at_ismi].append((tarih, gelis))
        except: pass

for at in at_form:
    at_form[at].sort(key=lambda x: x[0])

# Bugünkü yarışları yükle
dosyalar = sorted(glob.glob("yarislar_*.csv"))
if not dosyalar:
    print("[!] Bugunku yaris dosyasi yok!"); sys.exit()

bugun_csv = dosyalar[-1]
print(f"[+] Veri: {bugun_csv}\n")

yarislar = defaultdict(list)
with open(bugun_csv, "r", encoding="utf-8-sig") as f:
    for satir in csv.DictReader(f, delimiter=";"):
        anahtar = (satir["Hipodrom"], satir["Kosu_No"])
        yarislar[anahtar].append(satir)

def parse_sayi(m):
    try: return float(str(m).replace(",",".").strip())
    except: return 0

# Sürpriz skoru hesapla
print("=" * 70)
print("SÜRPRİZ ADALARI (AGF<%10, Form Yükselen, Jokey-At Uyumu)")
print("=" * 70)

bulunan = 0
for (hipodrom, kosu_no), atlar in yarislar.items():
    for at in atlar:
        at_ismi = at.get("At_Ismi", "")
        jokey = at.get("Jokey", "")
        mesafe = at.get("Mesafe", "")
        agf_str = at.get("AGF", "")
        agf_val = parse_sayi(agf_str.replace("%","")) if agf_str else 0
        
        # Sürpriz kriterleri
        kriter_sayisi = 0
        nedenler = []
        
        # 1) AGF düşük
        if agf_val < 10:
            kriter_sayisi += 1
            nedenler.append(f"AGF:%{agf_val:.0f}")
        
        # 2) Form yükselişi (son 3 yarışta 1-2-3 varsa)
        if at_ismi in at_form and len(at_form[at_ismi]) >= 3:
            son3 = [g for _,g in at_form[at_ismi][-3:]]
            if any(g <= 3 for g in son3):
                kriter_sayisi += 1
                nedenler.append(f"Son 3 formu iyi ({','.join(map(str,son3))})")
        
        # 3) Jokey-at uyumu %50+
        if (jokey, at_ismi) in jokey_at:
            ja = jokey_at[(jokey, at_ismi)]
            if ja["toplam"] >= 2:
                uyum = ja["ilk3"] / ja["toplam"] * 100
                if uyum >= 50:
                    kriter_sayisi += 1
                    nedenler.append(f"Jokey-At uyumu %{uyum:.0f}")
        
        # 4) Mesafe değişikliği ve önceki mesafede başarı
        if at_ismi in at_mesafe and mesafe in at_mesafe[at_ismi]:
            ms = at_mesafe[at_ismi][mesafe]
            if ms["toplam"] == 0 and len(at_mesafe[at_ismi]) > 0:
                kriter_sayisi += 1
                nedenler.append("Yeni mesafe denemesi")
        
        if kriter_sayisi >= 2:
            bulunan += 1
            print(f"⚡ {hipodrom} - {kosu_no}.Koşu | #{at.get('Sira','')} {at_ismi[:25]}")
            print(f"   Jokey: {jokey[:20]} | Ganyan: {at.get('Ganyan','')} | AGF: {agf_str}")
            print(f"   Neden: {' | '.join(nedenler)}")
            print()

if bulunan == 0:
    print("   (Bugün sürpriz adayı tespit edilemedi)")
else:
    print(f"\n[+] Toplam {bulunan} sürpriz adayı bulundu!")

print("\n[+] TAMAMLANDI!")