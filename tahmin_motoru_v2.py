import csv, sys, os, re, glob, random
from collections import defaultdict
from datetime import datetime

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

print("=" * 70)
print("🏆 GELISMIS TAHMIN MOTORU (Hava + Form + Detay)")
print("=" * 70)

# ====== 1) İSTATİSTİKLERİ YÜKLE ======
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
                        "bir": int(s.get("Birinci", 0))
                    }
                except: pass
print(f"[+] {len(jokey_db)} jokey, {len(antrenor_db)} antrenor, {len(at_db)} at yuklendi")

# ====== 2) GEÇMİŞ VERİDEN AT DETAYLARI ÇIKAR ======
print("[+] At detaylari hesaplaniyor...")
at_mesafe = defaultdict(lambda: defaultdict(lambda: {"toplam":0,"ilk3":0,"bir":0}))
at_pist = defaultdict(lambda: defaultdict(lambda: {"toplam":0,"ilk3":0,"bir":0}))
at_hipodrom = defaultdict(lambda: defaultdict(lambda: {"toplam":0,"ilk3":0,"bir":0}))
jokey_at = defaultdict(lambda: {"toplam":0,"ilk3":0,"bir":0})
at_form = defaultdict(list)

if os.path.exists("gecmis_sonuclar.csv"):
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
                tarih = satir.get("Tarih", "").strip()
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
                    at_form[at_ismi].append((tarih, gelis))
                if jokey and at_ismi:
                    jokey_at[(jokey, at_ismi)]["toplam"] += 1
                    jokey_at[(jokey, at_ismi)]["ilk3"] += ilk3
                    jokey_at[(jokey, at_ismi)]["bir"] += bir
            except: pass
    # Form sırala
    for at in at_form:
        at_form[at].sort(key=lambda x: x[0])
print(f"   [+] {len(at_mesafe)} at detaylandi")

# ====== 3) MEVSİMSEL HAVA ======
def mevsim_havasi(ay, hipodrom):
    if ay in [12,1,2]: sicaklik, nem, yagis_oran = 5.0, 75.0, 0.4
    elif ay in [3,4,5]: sicaklik, nem, yagis_oran = 15.0, 65.0, 0.3
    elif ay in [6,7,8]: sicaklik, nem, yagis_oran = 28.0, 55.0, 0.1
    else: sicaklik, nem, yagis_oran = 18.0, 70.0, 0.3
    sicak_sehir = ["Antalya","İzmir","Adana","Şanlıurfa","Diyarbakır"]
    soguk_sehir = ["Elazığ"]
    if any(s in hipodrom for s in sicak_sehir): sicaklik += 4
    if any(s in hipodrom for s in soguk_sehir): sicaklik -= 4
    yagis = 1 if random.random() < yagis_oran else 0
    return {"sicaklik": sicaklik, "nem": nem, "ruzgar": 5.0, "yagis": yagis, "bulut": 50.0}

# ====== 4) PUAN FONKSİYONLARI ======
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

def form_puani(at_ismi):
    if at_ismi not in at_form or len(at_form[at_ismi])<2: return 50
    son6 = [g for _,g in at_form[at_ismi][-6:]]
    puan = 0
    puan_map = {1:100, 2:80, 3:65, 4:50, 5:35}
    for g in son6:
        puan += puan_map.get(g, max(20-g*2, 5))
    return puan/len(son6)

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

def pist_kaygan_puani(pist, yagis):
    if yagis==1 and ("Cim" in pist or "Çim" in pist): return 1
    return 0

# ====== 5) BUGÜNKÜ YARIŞLARI YÜKLE ======
dosyalar = sorted(glob.glob("yarislar_*.csv"))
if not dosyalar:
    print("[!] Yarış dosyası yok!"); sys.exit()

bugun_csv = dosyalar[-1]
print(f"\n[+] Veri: {bugun_csv}\n")

yarislar = defaultdict(list)
with open(bugun_csv, "r", encoding="utf-8-sig") as f:
    for satir in csv.DictReader(f, delimiter=";"):
        anahtar = (satir["Hipodrom"], satir["Kosu_No"])
        yarislar[anahtar].append(satir)

# ====== 6) TAHMİN ======
bugun = datetime.now()
ay = bugun.month

for (hipodrom, kosu_no), atlar in sorted(yarislar.items()):
    if len(atlar) < 3: continue
    
    tum_g = [a.get("Ganyan","") for a in atlar]
    tum_k = [a.get("Kilo","") for a in atlar]
    mesafe = atlar[0].get("Mesafe","")
    pist = atlar[0].get("Pist","")
    
    hava = mevsim_havasi(ay, hipodrom)
    
    sonuclar = []
    for at in atlar:
        agf = at.get("AGF","")
        jokey = at.get("Jokey","")
        antrenor = at.get("Antrenor","")
        at_ismi = at.get("At_Ismi","")
        
        p_agf = agf_puani(agf)
        p_g = ganyan_puani(at.get("Ganyan",""), tum_g)
        p_kilo = kilo_puani(at.get("Kilo",""), tum_k)
        p_form = form_puani(at_ismi)
        p_jokey = jokey_puani(jokey)
        p_antr = antrenor_puani(antrenor)
        p_at = at_puani(at_ismi)
        p_mesafe = at_mesafe_puani(at_ismi, mesafe)
        p_pist = at_pist_puani(at_ismi, pist)
        p_hip = at_hipodrom_puani(at_ismi, hipodrom)
        p_jat = jokey_at_puani(jokey, at_ismi)
        p_kaygan = pist_kaygan_puani(pist, hava["yagis"])
        
        # AĞIRLIKLANDIRILMIŞ TOPLAM PUAN (Backtest optimize)
        toplam = (p_agf*0.18 + p_g*0.15 + p_form*0.14 + p_jokey*0.12 + 
                  p_at*0.10 + p_mesafe*0.08 + p_kilo*0.07 + p_antr*0.05 + 
                  p_pist*0.04 + p_hip*0.03 + p_jat*0.03)
        if p_kaygan:
            toplam *= 0.95  # kaygan pist cezası
        
        sonuclar.append({
            "sira": at.get("Sira",""), "at": at_ismi, "jokey": jokey,
            "kilo": at.get("Kilo",""), "ganyan": at.get("Ganyan",""),
            "agf": agf, "puan": round(toplam,1)
        })
    
    sonuclar.sort(key=lambda x: x["puan"], reverse=True)
    
    print("="*70)
    print(f"🏁 {hipodrom} - {kosu_no}. Koşu")
    print(f"   ⏰ {atlar[0].get('Saat','')} | 📏 {mesafe}m | 🌱 {pist} | 🏷️ {atlar[0].get('Cins','')}")
    print(f"   🌡️ Hava: {hava['sicaklik']:.0f}°C | Nem:%{hava['nem']:.0f} | Yağış:{'Var' if hava['yagis'] else 'Yok'} | Rüzgar:{hava['ruzgar']:.0f}m/s")
    print("-"*70)
    
    madalyalar = ["🥇","🥈","🥉"]
    for i in range(min(3, len(sonuclar))):
        s = sonuclar[i]
        print(f"{madalyalar[i]} #{s['sira']} {s['at'][:28]:<28} | Puan:{s['puan']:>5.1f} | Jokey:{s['jokey'][:18]:<18} | Ganyan:{s['ganyan']}")
    
    print("-"*70)
    print(f"{'Sira':<5}{'At':<30}{'Puan':<8}{'Jokey':<20}{'Ganyan':<8}{'AGF':<8}")
    for s in sonuclar:
        print(f"#{s['sira']:<4}{s['at'][:29]:<30}{s['puan']:<8}{s['jokey'][:19]:<20}{s['ganyan']:<8}{s['agf']:<8}")
    print()

print("="*70)
print("[+] TUM TAHMINLER YAPILDI")