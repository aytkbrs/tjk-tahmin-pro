import csv, sys, os, re
from collections import defaultdict
import numpy as np

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

print("=" * 70)
print("BACKTEST V3 - FORM DETAY + AGIRLIK OPTIMIZASYONU")
print("=" * 70)

# 1) İstatistikleri yükle
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
print(f"[+] {len(jokey_db)} jokey, {len(antrenor_db)} antrenor, {len(at_db)} at yuklendi")

# 2) At detayları
print("[+] At detaylari hesaplaniyor...")
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

print(f"   [+] {len(tum_kayitlar)} kayit")

# 3) GELİŞMİŞ FORM FONKSİYONLARI
def form_detay(at_ismi, hedef_tarih):
    """Son 6 yarıştan: ortalama geliş, trend, dalgalanma döndürür."""
    if at_ismi not in at_form: return 50, 0, 0, 0
    gecmis = [g for t,g in at_form[at_ismi] if t < hedef_tarih]
    if len(gecmis) < 2: return 50, 0, 0, 0
    son6 = gecmis[-6:]
    # Temel puan (ağırlıklı)
    puan, p_map = 0, {1:100,2:80,3:65,4:50,5:35}
    for g in son6:
        puan += p_map.get(g, max(20-g*2,5))
    ortalama_puan = puan/len(son6)
    
    # Ortalama geliş sırası (düşük = iyi)
    ort_gelis = np.mean(son6)
    
    # Trend: son 3 ort - önceki 3 ort (negatif = iyileşme)
    if len(son6) >= 6:
        son3_ort = np.mean(son6[-3:])
        once3_ort = np.mean(son6[:3])
        trend = once3_ort - son3_ort   # pozitif = yükseliş
    elif len(son6) >= 3:
        son3_ort = np.mean(son6[-3:])
        once3_ort = np.mean(son6)
        trend = once3_ort - son3_ort
    else:
        trend = 0
    
    # Dalgalanma (varyans, düşük = istikrarlı)
    varyans = np.var(son6) if len(son6)>=2 else 0
    
    return ortalama_puan, ort_gelis, trend, varyans

# 4) Diğer puan fonksiyonları
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

# 5) AĞIRLIKLAR (varsayılan)
A_AGF, A_G, A_FORM, A_TREND, A_GELIS, A_VARYANS = 0.16, 0.13, 0.12, 0.05, 0.04, 0.02
A_JOKEY, A_AT, A_MESAFE, A_KILO, A_ANTR, A_PIST, A_HIP, A_JAT = 0.11, 0.09, 0.07, 0.06, 0.04, 0.04, 0.03, 0.03
# YEDEK (best_weights.csv varsa onu kullan)
if os.path.exists("best_weights.csv"):
    with open("best_weights.csv","r") as f:
        reader = csv.DictReader(f)
        for row in reader:
            A_AGF=float(row["AGF"]); A_G=float(row["G"]); A_FORM=float(row["FORM"])
            A_TREND=float(row["TREND"]); A_GELIS=float(row["GELIS"]); A_VARYANS=float(row["VARYANS"])
            A_JOKEY=float(row["JOKEY"]); A_AT=float(row["AT"]); A_MESAFE=float(row["MESAFE"])
            A_KILO=float(row["KILO"]); A_ANTR=float(row["ANTR"]); A_PIST=float(row["PIST"])
            A_HIP=float(row["HIP"]); A_JAT=float(row["JAT"])
    print("[+] best_weights.csv yuklendi, varsayilan agirliklar guncellendi")

# 6) Yarışları grupla
yarislar = defaultdict(list)
for k in tum_kayitlar:
    anahtar = (k["tarih"], k["hipodrom"], k["kosu_no"])
    yarislar[anahtar].append(k)

print(f"\n[2/3] Backtest yapiliyor ({len(yarislar)} yaris)...")
ganyan_d, plase_d, ikili_d, uclu_d = 0,0,0,0
toplam = 0

for (tarih, hip, kosu_no), atlar in yarislar.items():
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
        # trend pozitifse iyileşme var demek => puan arttır
        p_trend = max(0, min(100, 50 + trend*10))  # trend -5..+5 arası olabilir
        p_gelis = max(0, min(100, 100 - ort_gelis*10))  # düşük geliş = yüksek puan
        p_varyans = max(0, min(100, 100 - varyans*5))   # az dalgalanma = yüksek
        
        p_jokey = jokey_puani(at["jokey"])
        p_antr = antrenor_puani(at["antrenor"])
        p_at = at_puani(at["at"])
        p_mesafe = at_mesafe_puani(at["at"], mesafe)
        p_pist = at_pist_puani(at["at"], pist)
        p_hip = at_hipodrom_puani(at["at"], hip)
        p_jat = jokey_at_puani(at["jokey"], at["at"])
        
        toplam_puan = (A_AGF*p_agf + A_G*p_g + A_FORM*form_ort + A_TREND*p_trend + 
                       A_GELIS*p_gelis + A_VARYANS*p_varyans +
                       A_JOKEY*p_jokey + A_AT*p_at + A_MESAFE*p_mesafe + A_KILO*p_kilo +
                       A_ANTR*p_antr + A_PIST*p_pist + A_HIP*p_hip + A_JAT*p_jat)
        sonuclar.append({"at": at, "puan": toplam_puan})
    
    sonuclar.sort(key=lambda x: x["puan"], reverse=True)
    if len(sonuclar) < 3: continue
    
    tahmin_1, tahmin_2, tahmin_3 = sonuclar[0]["at"], sonuclar[1]["at"], sonuclar[2]["at"]
    gercek_top3 = sorted(atlar, key=lambda x: x["gelis"])[:3]
    gercek_isimler = [g["at"] for g in gercek_top3]
    
    toplam += 1
    if tahmin_1["at"] == gercek_top3[0]["at"]: ganyan_d += 1
    if tahmin_1["at"] in gercek_isimler: plase_d += 1
    if {tahmin_1["at"], tahmin_2["at"]} == set([g["at"] for g in gercek_top3[:2]]): ikili_d += 1
    if {tahmin_1["at"], tahmin_2["at"], tahmin_3["at"]} == set(gercek_isimler): uclu_d += 1

print("\n[3/3] SONUCLAR")
print("=" * 70)
print(f"\n   Test edilen yaris: {toplam}")
if toplam > 0:
    print(f"   GANYAN: {ganyan_d}/{toplam} = %{ganyan_d/toplam*100:.1f}")
    print(f"   PLASE:  {plase_d}/{toplam} = %{plase_d/toplam*100:.1f}")
    print(f"   IKILI:  {ikili_d}/{toplam} = %{ikili_d/toplam*100:.1f}")
    print(f"   UCLU:   {uclu_d}/{toplam} = %{uclu_d/toplam*100:.1f}")
print("\n[+] TAMAMLANDI!")