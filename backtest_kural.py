import csv
import sys
import os
from collections import defaultdict

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

print("=" * 70)
print("BACKTEST - KURAL TABANLI MODEL DOGRULUK TESTI")
print("=" * 70)

# İstatistikleri yükle
jokey_db = {}
antrenor_db = {}
at_db = {}

if os.path.exists("jokey_istatistik.csv"):
    with open("jokey_istatistik.csv", "r", encoding="utf-8-sig") as f:
        for s in csv.DictReader(f, delimiter=";"):
            try:
                jokey_db[s["Jokey"]] = {"toplam": int(s["Toplam"]), "kazanma": float(s["Kazanma_Yuzde"])}
            except: pass

if os.path.exists("antrenor_istatistik.csv"):
    with open("antrenor_istatistik.csv", "r", encoding="utf-8-sig") as f:
        for s in csv.DictReader(f, delimiter=";"):
            try:
                antrenor_db[s["Antrenor"]] = {"toplam": int(s["Toplam"]), "kazanma": float(s["Kazanma_Yuzde"])}
            except: pass

if os.path.exists("at_istatistik.csv"):
    with open("at_istatistik.csv", "r", encoding="utf-8-sig") as f:
        for s in csv.DictReader(f, delimiter=";"):
            try:
                at_db[s["At_Ismi"]] = {"toplam": int(s["Toplam"]), "kazanma": float(s["Kazanma_Yuzde"])}
            except: pass

print(f"[+] {len(jokey_db)} jokey, {len(antrenor_db)} antrenor, {len(at_db)} at yuklendi")

# Geçmiş yarışları grupla
print("\n[1/3] Gecmis yarislar yukleniyor...")
yarislar = defaultdict(list)

with open("gecmis_sonuclar.csv", "r", encoding="utf-8-sig") as f:
    for satir in csv.DictReader(f, delimiter=";"):
        try:
            gelis = satir.get("Gelis_Sirasi", "").strip()
            if not gelis or not gelis.isdigit():
                continue
            anahtar = (satir["Tarih"], satir["Hipodrom"], satir["Kosu_No"])
            yarislar[anahtar].append({
                "gelis": int(gelis),
                "at": satir.get("At_No", "").strip(),
                "jokey": satir.get("Kilo", "").strip(),
                "antrenor": satir.get("Sahip", "").strip(),
                "agf": satir.get("Start_No", "").strip(),
                "ganyan": satir.get("Derece", "").strip(),
                "kilo": satir.get("Orijin_Anne", "").strip(),
            })
        except: pass

print(f"   [+] {len(yarislar)} yaris bulundu")

# Puan fonksiyonları
def parse_sayi(m, v=0.0):
    try: return float(str(m).replace(",", ".").strip())
    except: return v

def agf_puani(agf):
    if not agf or str(agf) == "-": return 0
    import re
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
    if j in jokey_db and jokey_db[j]["toplam"] >= 3:
        return min(jokey_db[j]["kazanma"] * 5, 100)
    return 50

def antrenor_puani(a):
    if a in antrenor_db and antrenor_db[a]["toplam"] >= 3:
        return min(antrenor_db[a]["kazanma"] * 5, 100)
    return 50

def at_puani(at):
    if at in at_db and at_db[at]["toplam"] >= 1:
        return min(at_db[at]["kazanma"] * 5, 100)
    return 50

# Backtest
print("\n[2/3] Backtest yapiliyor...\n")

ganyan_dogru = 0
plase_dogru = 0
ikili_dogru = 0
uclu_dogru = 0
toplam_yaris = 0

for anahtar, atlar in yarislar.items():
    if len(atlar) < 4:
        continue
    
    tum_g = [a["ganyan"] for a in atlar]
    tum_k = [a["kilo"] for a in atlar]
    
    sonuclar = []
    for at in atlar:
        p_agf = agf_puani(at["agf"])
        p_g = ganyan_puani(at["ganyan"], tum_g)
        p_kilo = kilo_puani(at["kilo"], tum_k)
        p_j = jokey_puani(at["jokey"])
        p_a = antrenor_puani(at["antrenor"])
        p_at = at_puani(at["at"])
        
        toplam = p_agf*0.25 + p_g*0.20 + p_j*0.20 + p_at*0.15 + p_a*0.10 + p_kilo*0.10
        sonuclar.append({"at": at, "puan": toplam})
    
    sonuclar.sort(key=lambda x: x["puan"], reverse=True)
    
    if len(sonuclar) < 3:
        continue
    
    tahmin_1 = sonuclar[0]["at"]
    tahmin_2 = sonuclar[1]["at"]
    tahmin_3 = sonuclar[2]["at"]
    
    gercek_top3 = sorted(atlar, key=lambda x: x["gelis"])[:3]
    if len(gercek_top3) < 3:
        continue
    
    gercek_1 = gercek_top3[0]
    gercek_top3_isim = [g["at"] for g in gercek_top3]
    
    toplam_yaris += 1
    
    if tahmin_1["at"] == gercek_1["at"]:
        ganyan_dogru += 1
    
    if tahmin_1["at"] in gercek_top3_isim:
        plase_dogru += 1
    
    gercek_top2_isim = [g["at"] for g in gercek_top3[:2]]
    if {tahmin_1["at"], tahmin_2["at"]} == set(gercek_top2_isim):
        ikili_dogru += 1
    
    if {tahmin_1["at"], tahmin_2["at"], tahmin_3["at"]} == set(gercek_top3_isim):
        uclu_dogru += 1

# Rapor
print("\n[3/3] BACKTEST RAPORU")
print("=" * 70)
print(f"\n   Toplam test edilen yaris: {toplam_yaris}\n")

if toplam_yaris > 0:
    g_oran = ganyan_dogru / toplam_yaris * 100
    p_oran = plase_dogru / toplam_yaris * 100
    i_oran = ikili_dogru / toplam_yaris * 100
    u_oran = uclu_dogru / toplam_yaris * 100
    
    print(f"   GANYAN (1. tahmin 1. gelirse): {ganyan_dogru}/{toplam_yaris} = %{g_oran:.1f}")
    print(f"   PLASE  (1. tahmin ilk 3'te):   {plase_dogru}/{toplam_yaris} = %{p_oran:.1f}")
    print(f"   IKILI  (ilk 2 tahmin dogru):   {ikili_dogru}/{toplam_yaris} = %{i_oran:.1f}")
    print(f"   UCLU   (ilk 3 tahmin dogru):   {uclu_dogru}/{toplam_yaris} = %{u_oran:.1f}")
    
    print("\n   KARSILASTIRMA (8 atli yarista sans):")
    print(f"   Sansla Ganyan: ~%12.5  ->  Bizim: %{g_oran:.1f}")
    print(f"   Sansla Plase:  ~%37.5  ->  Bizim: %{p_oran:.1f}")
    print(f"   Sansla Ikili:  ~%3.6   ->  Bizim: %{i_oran:.1f}")
    print(f"   Sansla Uclu:   ~%1.8   ->  Bizim: %{u_oran:.1f}")
    
    print("\n   YORUM:")
    if g_oran > 25:
        print("   🟢 GANYAN: COK IYI! Sansa gore 2x+")
    elif g_oran > 18:
        print("   🟡 GANYAN: IYI - Sansin 1.5x ustunde")
    elif g_oran > 12.5:
        print("   🟠 GANYAN: ORTA - Sansin biraz ustunde")
    else:
        print("   🔴 GANYAN: GELISTIRMELI - Sansin altinda")
else:
    print("   Yetersiz veri!")

print("\n[+] TAMAMLANDI!")