import csv
import sys
import os
import re
import glob

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

print("=" * 70)
print("🏆 CMD TAHMIN MOTORU")
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
                        "bir": int(s.get("Birinci", 0))
                    }
                except: pass

print(f"[+] {len(jokey_db)} jokey, {len(antrenor_db)} antrenor, {len(at_db)} at yuklendi\n")

# Bugünkü yarış dosyasını bul
dosyalar = sorted(glob.glob("yarislar_*.csv"))
if not dosyalar:
    print("[!] Bugunku yaris dosyasi bulunamadi!")
    sys.exit()

bugun_csv = dosyalar[-1]
print(f"[+] Veri: {bugun_csv}\n")

# Yarışları oku ve grupla
from collections import defaultdict
yarislar = defaultdict(list)

with open(bugun_csv, "r", encoding="utf-8-sig") as f:
    for satir in csv.DictReader(f, delimiter=";"):
        anahtar = (satir["Hipodrom"], satir["Kosu_No"])
        yarislar[anahtar].append(satir)

# Puan fonksiyonları
def parse_sayi(m, v=0.0):
    try: return float(str(m).replace(",", ".").strip())
    except: return v

def agf_puani(agf):
    if not agf or str(agf) == "-": return 0
    m = re.search(r'(\d+(?:[,.]\d+)?)', str(agf))
    return min(parse_sayi(m.group(1)) * 2.5, 100) if m else 0

def ganyan_puani(g, tum):
    gv = parse_sayi(g)
    if gv <= 0: return 20
    gec = [parse_sayi(x) for x in tum if parse_sayi(x) > 0]
    if not gec: return 20
    return (min(gec) / gv) * 100

def kilo_puani(k, tum):
    kv = parse_sayi(k)
    if kv <= 0: return 50
    gec = [parse_sayi(x) for x in tum if parse_sayi(x) > 0]
    if not gec: return 50
    mn, mx = min(gec), max(gec)
    if mx == mn: return 70
    return ((mx - kv) / (mx - mn)) * 100

def jokey_puani(j):
    if j in jokey_db and jokey_db[j]["toplam"] >= 5:
        return min(jokey_db[j]["kazanma"] * 5, 100)
    return 50

def antrenor_puani(a):
    if a in antrenor_db and antrenor_db[a]["toplam"] >= 5:
        return min(antrenor_db[a]["kazanma"] * 5, 100)
    return 50

def at_puani(at):
    if at in at_db and at_db[at]["toplam"] >= 2:
        return min(at_db[at]["kazanma"] * 5, 100)
    return 50

# Tahmin yap
for (hipodrom, kosu_no), atlar in sorted(yarislar.items()):
    if len(atlar) < 3:
        continue
    
    tum_g = [a.get("Ganyan", "") for a in atlar]
    tum_k = [a.get("Kilo", "") for a in atlar]
    
    sonuclar = []
    for at in atlar:
        p_agf = agf_puani(at.get("AGF", ""))
        p_g = ganyan_puani(at.get("Ganyan", ""), tum_g)
        p_kilo = kilo_puani(at.get("Kilo", ""), tum_k)
        p_j = jokey_puani(at.get("Jokey", ""))
        p_a = antrenor_puani(at.get("Antrenor", ""))
        p_at = at_puani(at.get("At_Ismi", ""))
        
        toplam = p_agf*0.25 + p_g*0.20 + p_j*0.20 + p_at*0.15 + p_a*0.10 + p_kilo*0.10
        sonuclar.append({
            "sira": at.get("Sira", ""),
            "at": at.get("At_Ismi", ""),
            "jokey": at.get("Jokey", ""),
            "kilo": at.get("Kilo", ""),
            "ganyan": at.get("Ganyan", ""),
            "agf": at.get("AGF", ""),
            "puan": round(toplam, 1)
        })
    
    sonuclar.sort(key=lambda x: x["puan"], reverse=True)
    
    # Başlık
    ilk_at = atlar[0]
    print("=" * 70)
    print(f"🏁 {hipodrom} - {kosu_no}. Koşu")
    print(f"   ⏰ {ilk_at.get('Saat','')} | 📏 {ilk_at.get('Mesafe','')}m | 🌱 {ilk_at.get('Pist','')} | 🏷️ {ilk_at.get('Cins','')}")
    print("-" * 70)
    
    # Top 3
    madalyalar = ["🥇", "🥈", "🥉"]
    for i in range(min(3, len(sonuclar))):
        s = sonuclar[i]
        print(f"{madalyalar[i]} #{s['sira']} {s['at'][:28]:<28} | Puan: {s['puan']:>5.1f} | Jokey: {s['jokey'][:18]:<18} | Ganyan: {s['ganyan']}")
    
    # Tablo (opsiyonel tüm atlar)
    print("-" * 70)
    print(f"{'Sira':<5}{'At':<30}{'Puan':<8}{'Jokey':<20}{'Ganyan':<8}{'AGF':<8}")
    for s in sonuclar:
        print(f"#{s['sira']:<4}{s['at'][:29]:<30}{s['puan']:<8}{s['jokey'][:19]:<20}{s['ganyan']:<8}{s['agf']:<8}")
    print()

print("=" * 70)
print("[+] TUM TAHMINLER YAPILDI")