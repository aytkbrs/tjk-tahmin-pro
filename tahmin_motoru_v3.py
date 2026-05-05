import csv, sys, os, re, glob, numpy as np
from collections import defaultdict
from datetime import datetime

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

print("=" * 70)
print("🏆 TAHMIN MOTORU V3 - OPTIMIZE EDILMIS")
print("=" * 70)

# 1) VERILERI YUKLE
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

print(f"[+] {len(jokey_db)} jokey, {len(antrenor_db)} antrenor, {len(at_db)} at")

# At detayları
print("[+] At detaylari hesaplaniyor...")
at_mesafe = defaultdict(lambda: defaultdict(lambda: {"toplam":0,"ilk3":0}))
at_pist = defaultdict(lambda: defaultdict(lambda: {"toplam":0,"ilk3":0}))
at_hipodrom = defaultdict(lambda: defaultdict(lambda: {"toplam":0,"ilk3":0}))
jokey_at = defaultdict(lambda: {"toplam":0,"ilk3":0})
at_form = defaultdict(list)

with open("gecmis_sonuclar.csv", "r", encoding="utf-8-sig") as f:
    for satir in csv.DictReader(f, delimiter=";"):
        try:
            gelis = int(satir.get("Gelis_Sirasi", "0"))
            if gelis == 0: continue
            at_ismi = satir.get("At_No", "").strip()
            jokey = satir.get("Kilo", "").strip()
            mesafe = satir.get("Mesafe", "").strip()
            pist = satir.get("Pist", "").strip()
            hip = satir.get("Hipodrom", "").strip()
            tarih = satir["Tarih"]
            ilk3 = 1 if gelis <= 3 else 0
            if at_ismi:
                if mesafe:
                    at_mesafe[at_ismi][mesafe]["toplam"] += 1
                    at_mesafe[at_ismi][mesafe]["ilk3"] += ilk3
                if pist:
                    at_pist[at_ismi][pist]["toplam"] += 1
                    at_pist[at_ismi][pist]["ilk3"] += ilk3
                if hip:
                    at_hipodrom[at_ismi][hip]["toplam"] += 1
                    at_hipodrom[at_ismi][hip]["ilk3"] += ilk3
                at_form[at_ismi].append((tarih, gelis))
            if jokey and at_ismi:
                jokey_at[(jokey, at_ismi)]["toplam"] += 1
                jokey_at[(jokey, at_ismi)]["ilk3"] += ilk3
        except: pass

for at in at_form: at_form[at].sort(key=lambda x: x[0])
print(f"   [+] {len(at_form)} at detaylandi")

# 2) AGIRLIKLARI YUKLE
weights = {}
if os.path.exists("best_weights.csv"):
    with open("best_weights.csv", "r", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        for row in reader:
            for k, v in row.items():
                weights[k] = float(v)
    print("[+] Optimize agirliklar yuklendi")
else:
    weights = {"AGF":0.18,"G":0.15,"FORM":0.14,"TREND":0.00,"GELIS":0.00,"VARYANS":0.00,
               "JOKEY":0.12,"AT":0.10,"MESAFE":0.08,"KILO":0.07,"ANTR":0.05,
               "PIST":0.04,"HIP":0.03,"JAT":0.03}
    print("[!] best_weights.csv bulunamadi, varsayilan agirliklar kullaniliyor")

# 3) PUAN FONKSIYONLARI
def parse_sayi(m):
    try: return float(str(m).replace(",",".").strip())
    except: return 0

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
    return ((mx-kv)/(mx-mn))*100 if mx!=mn else 70

def form_detay(at_ismi):
    if at_ismi not in at_form: return 50,0,0,0
    gecmis = [g for _,g in at_form[at_ismi]]
    if len(gecmis) < 2: return 50,0,0,0
    son6 = gecmis[-6:]
    puan, p_map = 0, {1:100,2:80,3:65,4:50,5:35}
    for g in son6: puan += p_map.get(g, max(20-g*2,5))
    ortalama_puan = puan/len(son6)
    ort_gelis = np.mean(son6)
    if len(son6)>=6: trend = np.mean(son6[:3]) - np.mean(son6[-3:])
    elif len(son6)>=3: trend = np.mean(son6) - np.mean(son6[-3:])
    else: trend = 0
    varyans = np.var(son6) if len(son6)>=2 else 0
    return ortalama_puan, ort_gelis, trend, varyans

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

# 4) BUGUNKU YARISLAR
dosyalar = sorted(glob.glob("yarislar_*.csv"))
if not dosyalar: print("[!] Yaris dosyasi yok!"); sys.exit()
bugun_csv = dosyalar[-1]

yarislar = defaultdict(list)
with open(bugun_csv, "r", encoding="utf-8-sig") as f:
    for satir in csv.DictReader(f, delimiter=";"):
        anahtar = (satir["Hipodrom"], satir["Kosu_No"])
        yarislar[anahtar].append(satir)

print(f"\n[+] Veri: {bugun_csv}\n")

# 5) TAHMIN
for (hipodrom, kosu_no), atlar in sorted(yarislar.items()):
    if len(atlar) < 3: continue
    tum_g = [a.get("Ganyan","") for a in atlar]
    tum_k = [a.get("Kilo","") for a in atlar]
    mesafe = atlar[0].get("Mesafe","")
    pist = atlar[0].get("Pist","")
    
    sonuclar = []
    for at in atlar:
        agf = at.get("AGF","")
        jokey = at.get("Jokey","")
        antrenor = at.get("Antrenor","")
        at_ismi = at.get("At_Ismi","")
        
        p_agf = agf_puani(agf)
        p_g = ganyan_puani(at.get("Ganyan",""), tum_g)
        p_kilo = kilo_puani(at.get("Kilo",""), tum_k)
        form_ort, ort_gelis, trend, varyans = form_detay(at_ismi)
        p_trend = max(0, min(100, 50 + trend*10))
        p_gelis = max(0, min(100, 100 - ort_gelis*10))
        p_varyans = max(0, min(100, 100 - varyans*5))
        p_jokey = jokey_puani(jokey)
        p_antr = antrenor_puani(antrenor)
        p_at = at_puani(at_ismi)
        p_mesafe = at_mesafe_puani(at_ismi, mesafe)
        p_pist = at_pist_puani(at_ismi, pist)
        p_hip = at_hipodrom_puani(at_ismi, hipodrom)
        p_jat = jokey_at_puani(jokey, at_ismi)
        
        toplam = (weights["AGF"]*p_agf + weights["G"]*p_g + weights["FORM"]*form_ort + 
                  weights["TREND"]*p_trend + weights["GELIS"]*p_gelis + weights["VARYANS"]*p_varyans +
                  weights["JOKEY"]*p_jokey + weights["AT"]*p_at + weights["MESAFE"]*p_mesafe +
                  weights["KILO"]*p_kilo + weights["ANTR"]*p_antr + weights["PIST"]*p_pist +
                  weights["HIP"]*p_hip + weights["JAT"]*p_jat)
        
        sonuclar.append({
            "sira": at.get("Sira",""), "at": at_ismi, "jokey": jokey,
            "puan": round(toplam,1), "ganyan": at.get("Ganyan",""), "agf": agf
        })
    
    sonuclar.sort(key=lambda x: x["puan"], reverse=True)
    
    print("="*70)
    print(f"🏁 {hipodrom} - {kosu_no}. Koşu")
    print(f"   ⏰ {atlar[0].get('Saat','')} | 📏 {mesafe}m | 🌱 {pist} | 🏷️ {atlar[0].get('Cins','')}")
    print("-"*70)
    for i in range(min(3, len(sonuclar))):
        s = sonuclar[i]
        madalya = ["🥇","🥈","🥉"][i]
        print(f"{madalya} #{s['sira']} {s['at'][:28]:<28} | Puan:{s['puan']:>5.1f} | Jokey:{s['jokey'][:18]:<18} | Ganyan:{s['ganyan']}")
    print("-"*70)
    print(f"{'Sira':<5}{'At':<30}{'Puan':<8}{'Jokey':<20}{'Ganyan':<8}{'AGF':<8}")
    for s in sonuclar:
        print(f"#{s['sira']:<4}{s['at'][:29]:<30}{s['puan']:<8}{s['jokey'][:19]:<20}{s['ganyan']:<8}{s['agf']:<8}")
    print()

print("="*70)
print("[+] TUM TAHMINLER YAPILDI")