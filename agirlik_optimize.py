import csv, sys, os, re, itertools, warnings
from collections import defaultdict
import numpy as np
warnings.filterwarnings('ignore')

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

print("=" * 70)
print("AGIRLIK OPTIMIZASYONU - GRID SEARCH")
print("=" * 70)

# 1) Veriyi yükle (backtest_v3.py ile aynı)
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

at_mesafe = defaultdict(lambda: defaultdict(lambda: {"toplam":0,"ilk3":0,"bir":0}))
at_pist = defaultdict(lambda: defaultdict(lambda: {"toplam":0,"ilk3":0,"bir":0}))
at_hipodrom = defaultdict(lambda: defaultdict(lambda: {"toplam":0,"ilk3":0,"bir":0}))
jokey_at = defaultdict(lambda: {"toplam":0,"ilk3":0,"bir":0})
at_form = defaultdict(list)

tum_kayitlar = []
with open("gecmis_sonuclar.csv", "r", encoding="utf-8-sig") as f:
    for satir in csv.DictReader(f, delimiter=";"):
        try:
            gelis = int(satir.get("Gelis_Sirasi", "0"))
            if gelis == 0: continue
            kayit = {
                "tarih": satir["Tarih"],
                "hipodrom": satir["Hipodrom"],
                "kosu_no": satir["Kosu_No"],
                "gelis": gelis,
                "at": satir.get("At_No", "").strip(),
                "jokey": satir.get("Kilo", "").strip(),
                "antrenor": satir.get("Sahip", "").strip(),
                "agf": satir.get("Start_No", "").strip(),
                "ganyan": satir.get("Derece", "").strip(),
                "kilo": satir.get("Orijin_Anne", "").strip(),
                "mesafe": satir.get("Mesafe", "").strip(),
                "pist": satir.get("Pist", "").strip(),
            }
            tum_kayitlar.append(kayit)
            at_ismi = kayit["at"]
            jokey = kayit["jokey"]
            mesafe = kayit["mesafe"]
            pist = kayit["pist"]
            hip = kayit["hipodrom"]
            ilk3 = 1 if gelis <= 3 else 0
            bir = 1 if gelis == 1 else 0
            if at_ismi:
                if mesafe: 
                    at_mesafe[at_ismi][mesafe]["toplam"] += 1
                    at_mesafe[at_ismi][mesafe]["ilk3"] += ilk3
                    at_mesafe[at_ismi][mesafe]["bir"] += bir
                if pist:
                    at_pist[at_ismi][pist]["toplam"] += 1
                    at_pist[at_ismi][pist]["ilk3"] += ilk3
                if hip:
                    at_hipodrom[at_ismi][hip]["toplam"] += 1
                    at_hipodrom[at_ismi][hip]["ilk3"] += ilk3
                at_form[at_ismi].append((kayit["tarih"], gelis))
            if jokey and at_ismi:
                jokey_at[(jokey, at_ismi)]["toplam"] += 1
                jokey_at[(jokey, at_ismi)]["ilk3"] += ilk3
                jokey_at[(jokey, at_ismi)]["bir"] += bir
        except: pass

for at in at_form:
    at_form[at].sort(key=lambda x: x[0])

print(f"[+] Veri yuklendi ({len(tum_kayitlar)} kayit)")

# 2) Puan fonksiyonları (backtest_v3 ile aynı)
def form_detay(at_ismi, hedef_tarih):
    if at_ismi not in at_form: return 50, 0, 0, 0
    gecmis = [g for t,g in at_form[at_ismi] if t < hedef_tarih]
    if len(gecmis) < 2: return 50, 0, 0, 0
    son6 = gecmis[-6:]
    puan, p_map = 0, {1:100,2:80,3:65,4:50,5:35}
    for g in son6: puan += p_map.get(g, max(20-g*2,5))
    ortalama_puan = puan/len(son6)
    ort_gelis = np.mean(son6)
    if len(son6) >= 6:
        trend = np.mean(son6[:3]) - np.mean(son6[-3:])
    elif len(son6) >= 3:
        trend = np.mean(son6) - np.mean(son6[-3:])
    else: trend = 0
    varyans = np.var(son6) if len(son6)>=2 else 0
    return ortalama_puan, ort_gelis, trend, varyans

def parse_sayi(m, v=0.0):
    try: return float(str(m).replace(",", ".").strip())
    except: return v

def agf_puani(agf):
    if not agf or str(agf)=="-": return 0
    m = re.search(r'(\d+(?:[,.]\d+)?)', str(agf))
    return min(parse_sayi(m.group(1))*2.5, 100) if m else 0

def ganyan_puani(g, tum):
    gv = parse_sayi(g)
    if gv <= 0: return 20
    gec = [parse_sayi(x) for x in tum if parse_sayi(x)>0]
    if not gec: return 20
    return (min(gec)/gv)*100

def kilo_puani(k, tum):
    kv = parse_sayi(k)
    if kv <= 0: return 50
    gec = [parse_sayi(x) for x in tum if parse_sayi(x)>0]
    if not gec: return 50
    mn, mx = min(gec), max(gec)
    if mx==mn: return 70
    return ((mx-kv)/(mx-mn))*100

def jokey_puani(j):
    if j in jokey_db and jokey_db[j]["toplam"]>=5:
        return min(jokey_db[j]["kazanma"]*5,100)
    return 50

def antrenor_puani(a):
    if a in antrenor_db and antrenor_db[a]["toplam"]>=5:
        return min(antrenor_db[a]["kazanma"]*5,100)
    return 50

def at_puani(at):
    if at in at_db and at_db[at]["toplam"]>=2:
        return min(at_db[at]["kazanma"]*5,100)
    return 50

def at_mesafe_puani(at, mesafe):
    if at in at_mesafe and mesafe in at_mesafe[at]:
        s = at_mesafe[at][mesafe]
        if s["toplam"]>=2: return (s["ilk3"]/s["toplam"])*100
    return 30

def at_pist_puani(at, pist):
    if at in at_pist and pist in at_pist[at]:
        s = at_pist[at][pist]
        if s["toplam"]>=2: return (s["ilk3"]/s["toplam"])*100
    return 30

def at_hipodrom_puani(at, hip):
    if at in at_hipodrom and hip in at_hipodrom[at]:
        s = at_hipodrom[at][hip]
        if s["toplam"]>=2: return (s["ilk3"]/s["toplam"])*100
    return 30

def jokey_at_puani(j, at):
    if (j,at) in jokey_at and jokey_at[(j,at)]["toplam"]>=1:
        s = jokey_at[(j,at)]
        return (s["ilk3"]/s["toplam"])*100
    return 30

# Yarışları grupla (optimizasyon için örnekle: 2000 yarış)
yarislar = defaultdict(list)
for k in tum_kayitlar:
    anahtar = (k["tarih"], k["hipodrom"], k["kosu_no"])
    yarislar[anahtar].append(k)

yaris_listesi = list(yarislar.items())
if len(yaris_listesi) > 2000:
    yaris_listesi = yaris_listesi[-2000:]  # Son 2000 yarışla optimize et (hızlı)
print(f"[+] Optimizasyon {len(yaris_listesi)} yaris uzerinde yapilacak")

# 3) Optimizasyon döngüsü
print("\n[2/3] Agirlik optimizasyonu basliyor...")
print("      (Bu islem 15-30 dakika surebilir, bilgisayari kapatmayin)")
print("-" * 60)

# Ağırlık aralıkları (her parametre için denenebilecek değerler)
agirlik_aralik = {
    "AGF": [0.14, 0.16, 0.18, 0.20],
    "G": [0.12, 0.14, 0.16],
    "FORM": [0.10, 0.12, 0.14],
    "TREND": [0.04, 0.06, 0.08],
    "GELIS": [0.03, 0.05, 0.07],
    "VARYANS": [0.01, 0.02, 0.03],
    "JOKEY": [0.10, 0.12, 0.14],
    "AT": [0.08, 0.10, 0.12],
    "MESAFE": [0.06, 0.08, 0.10],
    "KILO": [0.04, 0.06, 0.08],
    "ANTR": [0.03, 0.05, 0.07],
    "PIST": [0.02, 0.03, 0.04],
    "HIP": [0.02, 0.03, 0.04],
    "JAT": [0.02, 0.03, 0.04],
}

# En iyi sonucu tut
en_iyi_ganyan = 0
en_iyi_agirlik = None

# Rastgele 500 kombinasyon dene (greedy)
import random
random.seed(42)
deneme = 0
max_deneme = 500

for _ in range(max_deneme):
    # Rastgele ağırlıklar seç
    w = {}
    for k, v in agirlik_aralik.items():
        w[k] = random.choice(v)
    # Toplamı 1'e normalize et
    toplam_w = sum(w.values())
    for k in w: w[k] /= toplam_w
    
    # Backtest
    ganyan_d, toplam = 0, 0
    for (tarih, hip, kosu_no), atlar in yaris_listesi:
        if len(atlar) < 4: continue
        tum_g = [a["ganyan"] for a in atlar]
        tum_kilo = [a["kilo"] for a in atlar]
        mesafe = atlar[0]["mesafe"]
        pist = atlar[0]["pist"]
        
        sonuclar = []
        for at in atlar:
            p_agf = agf_puani(at["agf"])
            p_g = ganyan_puani(at["ganyan"], tum_g)
            p_kilo = kilo_puani(at["kilo"], tum_kilo)
            form_ort, ort_gelis, trend, varyans = form_detay(at["at"], tarih)
            p_trend = max(0, min(100, 50 + trend*10))
            p_gelis = max(0, min(100, 100 - ort_gelis*10))
            p_varyans = max(0, min(100, 100 - varyans*5))
            p_jokey = jokey_puani(at["jokey"])
            p_antr = antrenor_puani(at["antrenor"])
            p_at = at_puani(at["at"])
            p_mesafe = at_mesafe_puani(at["at"], mesafe)
            p_pist = at_pist_puani(at["at"], pist)
            p_hip = at_hipodrom_puani(at["at"], hip)
            p_jat = jokey_at_puani(at["jokey"], at["at"])
            
            toplam_puan = (w["AGF"]*p_agf + w["G"]*p_g + w["FORM"]*form_ort + 
                           w["TREND"]*p_trend + w["GELIS"]*p_gelis + w["VARYANS"]*p_varyans +
                           w["JOKEY"]*p_jokey + w["AT"]*p_at + w["MESAFE"]*p_mesafe +
                           w["KILO"]*p_kilo + w["ANTR"]*p_antr + w["PIST"]*p_pist +
                           w["HIP"]*p_hip + w["JAT"]*p_jat)
            sonuclar.append({"at": at, "puan": toplam_puan})
        
        sonuclar.sort(key=lambda x: x["puan"], reverse=True)
        if len(sonuclar) < 3: continue
        tahmin_1 = sonuclar[0]["at"]
        gercek_top3 = sorted(atlar, key=lambda x: x["gelis"])[:3]
        if tahmin_1["at"] == gercek_top3[0]["at"]:
            ganyan_d += 1
        toplam += 1
    
    if toplam > 0:
        ganyan_oran = ganyan_d/toplam*100
    else:
        ganyan_oran = 0
    
    if ganyan_oran > en_iyi_ganyan:
        en_iyi_ganyan = ganyan_oran
        en_iyi_agirlik = w.copy()
        print(f"   [{deneme+1}/{max_deneme}] Yeni en iyi: %{ganyan_oran:.2f} | AGF:{w['AGF']:.2f} G:{w['G']:.2f} FORM:{w['FORM']:.2f} TREND:{w['TREND']:.2f} JOKEY:{w['JOKEY']:.2f}")
    
    deneme += 1
    if deneme % 100 == 0:
        print(f"   ...{deneme}/{max_deneme} (en iyi: %{en_iyi_ganyan:.2f})")

# 4) Kaydet
print("\n[3/3] EN IYI AGIRLIKLAR")
print("=" * 70)
if en_iyi_agirlik:
    print(f"\n   Ganyan basarisi: %{en_iyi_ganyan:.2f}")
    print(f"\n   Agirliklar:")
    for k, v in en_iyi_agirlik.items():
        print(f"   {k:<10}: {v:.4f}")
    
    with open("best_weights.csv", "w", newline="", encoding="utf-8-sig") as f:
        yazici = csv.writer(f)
        yazici.writerow(en_iyi_agirlik.keys())
        yazici.writerow([f"{v:.4f}" for v in en_iyi_agirlik.values()])
    print(f"\n[+] best_weights.csv kaydedildi")
else:
    print("   [!] Optimizasyon basarisiz")

print("\n[+] TAMAMLANDI!")