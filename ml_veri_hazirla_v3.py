import csv
import re
import os
import sys
import pandas as pd
import numpy as np
from collections import defaultdict
from datetime import datetime, timedelta

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

# ============================================
# ML VERI HAZIRLAMA v3.0 - HAVA DURUMU + EKSTRA FEATURES
# 35+ feature ile profesyonel hazirlık
# ============================================

print("=" * 70)
print("ML VERI HAZIRLAMA v3.0 - HAVA + GELISMIS FEATURES")
print("=" * 70)

# ====== HAVA DURUMU YUKLE ======
print("\n[1/6] Hava durumu yukleniyor...")
hava_db = {}

if os.path.exists("hava_durumu.csv"):
    with open("hava_durumu.csv", "r", encoding="utf-8-sig") as f:
        for s in csv.DictReader(f, delimiter=";"):
            try:
                hipodrom = s["Hipodrom"]
                hava_db[hipodrom] = {
                    "sicaklik": float(s["Sicaklik"]),
                    "nem": float(s["Nem"]),
                    "ruzgar": float(s["Ruzgar"]),
                    "yagis": int(s["Yagis"]),
                    "bulut": float(s["Bulut"]),
                }
            except: pass
    print(f"   [+] {len(hava_db)} hipodrom hava verisi")
else:
    print("   [!] hava_durumu.csv yok, varsayilan deger kullanilacak")

# Mevsim ortalamasi (yazin sicak, kisin soguk)
def mevsim_havasi(tarih_str, hipodrom):
    """Geçmiş yarışlar için tahmini hava"""
    try:
        # Tarih: "01.05.2025"
        gun, ay, yil = tarih_str.split(".")
        ay = int(ay)
        
        # Mevsime göre tahmini sıcaklık
        if ay in [12, 1, 2]:  # Kış
            sicaklik = 5.0 + np.random.uniform(-3, 3)
            nem = 75.0
            yagis_olasilik = 0.4
        elif ay in [3, 4, 5]:  # İlkbahar
            sicaklik = 15.0 + np.random.uniform(-3, 3)
            nem = 65.0
            yagis_olasilik = 0.3
        elif ay in [6, 7, 8]:  # Yaz
            sicaklik = 28.0 + np.random.uniform(-3, 3)
            nem = 55.0
            yagis_olasilik = 0.1
        else:  # Sonbahar
            sicaklik = 18.0 + np.random.uniform(-3, 3)
            nem = 70.0
            yagis_olasilik = 0.3
        
        # Şehir bazlı ayarlama (kabaca)
        if "Antalya" in hipodrom or "İzmir" in hipodrom or "Adana" in hipodrom:
            sicaklik += 4  # Sıcak şehirler
        elif "Erzurum" in hipodrom or "Elazığ" in hipodrom:
            sicaklik -= 4  # Soğuk şehirler
        
        return {
            "sicaklik": sicaklik,
            "nem": nem,
            "ruzgar": 5.0,
            "yagis": 1 if np.random.random() < yagis_olasilik else 0,
            "bulut": 50.0,
        }
    except:
        return {"sicaklik": 18.0, "nem": 65.0, "ruzgar": 5.0, "yagis": 0, "bulut": 50.0}

# ====== ISTATISTIKLER YUKLE ======
print("\n[2/6] Istatistikler yukleniyor...")

jokey_db, antrenor_db, at_db = {}, {}, {}

if os.path.exists("jokey_istatistik.csv"):
    with open("jokey_istatistik.csv", "r", encoding="utf-8-sig") as f:
        for s in csv.DictReader(f, delimiter=";"):
            try:
                jokey_db[s["Jokey"]] = {
                    "toplam": int(s["Toplam"]),
                    "kazanma": float(s["Kazanma_Yuzde"]),
                    "ilk3": float(s["Ilk3_Yuzde"])
                }
            except: pass

if os.path.exists("antrenor_istatistik.csv"):
    with open("antrenor_istatistik.csv", "r", encoding="utf-8-sig") as f:
        for s in csv.DictReader(f, delimiter=";"):
            try:
                antrenor_db[s["Antrenor"]] = {
                    "toplam": int(s["Toplam"]),
                    "kazanma": float(s["Kazanma_Yuzde"]),
                    "ilk3": float(s["Ilk3_Yuzde"])
                }
            except: pass

if os.path.exists("at_istatistik.csv"):
    with open("at_istatistik.csv", "r", encoding="utf-8-sig") as f:
        for s in csv.DictReader(f, delimiter=";"):
            try:
                at_temiz = re.sub(r'\s+(KG|DB|KV|SK|SKG|GKR).*$', '', s["At_Ismi"]).strip()
                at_db[at_temiz] = {
                    "toplam": int(s["Toplam"]),
                    "kazanma": float(s["Kazanma_Yuzde"]),
                    "ilk3": float(s["Ilk3_Yuzde"])
                }
            except: pass

print(f"   [+] {len(jokey_db)} jokey, {len(antrenor_db)} antrenor, {len(at_db)} at")

def parse_sayi(m, v=0.0):
    if not m: return v
    try: return float(str(m).replace(",", ".").strip())
    except: return v

def agf_sayisal(agf):
    if not agf or str(agf) == "-": return 0.0
    m = re.search(r'(\d+(?:[,.]\d+)?)', str(agf))
    return parse_sayi(m.group(1)) if m else 0.0

# ====== GECMIS VERILERI YUKLE ======
print("\n[3/6] Gecmis veriler okunuyor...")

CSV_DOSYA = "gecmis_sonuclar.csv"
if not os.path.exists(CSV_DOSYA):
    print(f"[!] {CSV_DOSYA} bulunamadi!")
    sys.exit()

yarislar = defaultdict(list)
tum_kayitlar = []

with open(CSV_DOSYA, "r", encoding="utf-8-sig") as f:
    for s in csv.DictReader(f, delimiter=";"):
        try:
            gelis = s.get("Gelis_Sirasi", "").strip()
            if not gelis or not gelis.isdigit():
                continue
            
            kayit = {
                "tarih": s["Tarih"],
                "hipodrom": s["Hipodrom"],
                "kosu_no": s["Kosu_No"],
                "gelis": int(gelis),
                "at_ismi": s.get("At_No", "").strip(),
                "yas": s.get("At_Ismi", "").strip(),
                "orijin": s.get("Yas", "").strip(),
                "kilo": s.get("Orijin_Anne", "").strip(),
                "jokey": s.get("Kilo", "").strip(),
                "sahip": s.get("Jokey", "").strip(),
                "antrenor": s.get("Sahip", "").strip(),
                "agf": s.get("Start_No", "").strip(),
                "hp": s.get("AGF", "").strip(),
                "derece": s.get("HP", "").strip(),
                "ganyan": s.get("Derece", "").strip(),
                "mesafe": s.get("Mesafe", "").strip(),
                "pist": s.get("Pist", "").strip(),
                "cins": s.get("Cins", "").strip(),
            }
            
            anahtar = (kayit["tarih"], kayit["hipodrom"], kayit["kosu_no"])
            yarislar[anahtar].append(kayit)
            tum_kayitlar.append(kayit)
        except: pass

print(f"   [+] {len(yarislar)} yaris, {len(tum_kayitlar)} at kaydi")

# ====== DETAYLI ISTATISTIKLER ======
print("\n[4/6] Detayli istatistikler hesaplaniyor...")

at_mesafe = defaultdict(lambda: defaultdict(lambda: {"toplam": 0, "ilk3": 0, "bir": 0}))
at_pist = defaultdict(lambda: defaultdict(lambda: {"toplam": 0, "ilk3": 0, "bir": 0}))
at_hipodrom = defaultdict(lambda: defaultdict(lambda: {"toplam": 0, "ilk3": 0, "bir": 0}))
jokey_at = defaultdict(lambda: {"toplam": 0, "ilk3": 0, "bir": 0})
jokey_mesafe = defaultdict(lambda: defaultdict(lambda: {"toplam": 0, "ilk3": 0, "bir": 0}))
jokey_hipodrom = defaultdict(lambda: defaultdict(lambda: {"toplam": 0, "ilk3": 0, "bir": 0}))
antrenor_mesafe = defaultdict(lambda: defaultdict(lambda: {"toplam": 0, "ilk3": 0, "bir": 0}))

for k in tum_kayitlar:
    at = k["at_ismi"]
    j = k["jokey"]
    a = k["antrenor"]
    mesafe = k["mesafe"]
    pist = k["pist"]
    hip = k["hipodrom"]
    gelis = k["gelis"]
    ilk3 = 1 if gelis <= 3 else 0
    bir = 1 if gelis == 1 else 0
    
    if at:
        at_mesafe[at][mesafe]["toplam"] += 1
        at_mesafe[at][mesafe]["ilk3"] += ilk3
        at_mesafe[at][mesafe]["bir"] += bir
        at_pist[at][pist]["toplam"] += 1
        at_pist[at][pist]["ilk3"] += ilk3
        at_hipodrom[at][hip]["toplam"] += 1
        at_hipodrom[at][hip]["ilk3"] += ilk3
    
    if j and at:
        jokey_at[(j, at)]["toplam"] += 1
        jokey_at[(j, at)]["ilk3"] += ilk3
        jokey_at[(j, at)]["bir"] += bir
    
    if j:
        jokey_mesafe[j][mesafe]["toplam"] += 1
        jokey_mesafe[j][mesafe]["ilk3"] += ilk3
        jokey_hipodrom[j][hip]["toplam"] += 1
        jokey_hipodrom[j][hip]["ilk3"] += ilk3
    
    if a:
        antrenor_mesafe[a][mesafe]["toplam"] += 1
        antrenor_mesafe[a][mesafe]["ilk3"] += ilk3

print(f"   [+] At-Mesafe: {len(at_mesafe)} at")
print(f"   [+] Jokey-At kombinasyon: {len(jokey_at)}")

# ====== FEATURE'LAR OLUSTUR ======
print("\n[5/6] Feature'lar olusturuluyor (35+ feature)...")

ml_data = []

for anahtar, atlar in yarislar.items():
    if len(atlar) < 4:
        continue
    
    tarih_str, hipodrom_str, kosu_no_str = anahtar
    
    # HAVA DURUMU (mevsim tahminli)
    hava = mevsim_havasi(tarih_str, hipodrom_str)
    
    # Yaris istatistikleri
    tum_kilolar = [parse_sayi(a["kilo"]) for a in atlar]
    tum_kilolar = [k for k in tum_kilolar if k > 0]
    tum_ganyanlar = [parse_sayi(a["ganyan"]) for a in atlar]
    tum_ganyanlar = [g for g in tum_ganyanlar if g > 0]
    tum_agf = [agf_sayisal(a["agf"]) for a in atlar]
    
    min_kilo = min(tum_kilolar) if tum_kilolar else 0
    max_kilo = max(tum_kilolar) if tum_kilolar else 0
    min_ganyan = min(tum_ganyanlar) if tum_ganyanlar else 0
    max_agf = max(tum_agf) if tum_agf else 1
    at_sayisi = len(atlar)
    
    if len(tum_ganyanlar) >= 2:
        sirali_g = sorted(tum_ganyanlar)
        rekabet_seviyesi = (sirali_g[1] - sirali_g[0]) / (sirali_g[0] + 0.01)
    else:
        rekabet_seviyesi = 1.0
    
    # AY (mevsim için)
    try:
        ay = int(tarih_str.split(".")[1])
    except:
        ay = 6
    
    for at in atlar:
        kilo = parse_sayi(at["kilo"])
        ganyan = parse_sayi(at["ganyan"])
        agf = agf_sayisal(at["agf"])
        hp = parse_sayi(at["hp"])
        mesafe = parse_sayi(at["mesafe"])
        pist = at["pist"]
        cins = at["cins"]
        hip = at["hipodrom"]
        
        yas = 0
        yas_match = re.search(r'(\d+)y', at["yas"])
        if yas_match:
            yas = int(yas_match.group(1))
        
        pist_cim = 1 if "Cim" in pist or "Çim" in pist else 0
        pist_kum = 1 if "Kum" in pist else 0
        pist_sentetik = 1 if "Sentetik" in pist else 0
        
        cins_handikap = 1 if "Handikap" in cins else 0
        cins_maiden = 1 if "Maiden" in cins else 0
        cins_sartli = 1 if "Şartlı" in cins or "Sartli" in cins else 0
        cins_kv = 1 if "KV" in cins else 0
        
        kilo_avantaji = (max_kilo - kilo) / (max_kilo - min_kilo + 0.01) if max_kilo > min_kilo else 0.5
        ganyan_avantaji = (min_ganyan / ganyan) if ganyan > 0 else 0
        agf_yuzde = (agf / max_agf * 100) if max_agf > 0 else 0
        
        j = at["jokey"]
        jokey_kazanma = jokey_db.get(j, {}).get("kazanma", 10.0)
        jokey_ilk3 = jokey_db.get(j, {}).get("ilk3", 30.0)
        jokey_toplam = jokey_db.get(j, {}).get("toplam", 0)
        
        a = at["antrenor"]
        antrenor_kazanma = antrenor_db.get(a, {}).get("kazanma", 10.0)
        antrenor_ilk3 = antrenor_db.get(a, {}).get("ilk3", 30.0)
        antrenor_toplam = antrenor_db.get(a, {}).get("toplam", 0)
        
        at_ismi = at["at_ismi"]
        at_kazanma = at_db.get(at_ismi, {}).get("kazanma", 10.0)
        at_ilk3 = at_db.get(at_ismi, {}).get("ilk3", 30.0)
        at_toplam = at_db.get(at_ismi, {}).get("toplam", 0)
        
        am = at_mesafe[at_ismi].get(at["mesafe"], {"toplam": 0, "ilk3": 0, "bir": 0})
        at_mesafe_ilk3 = (am["ilk3"] / am["toplam"] * 100) if am["toplam"] >= 2 else 30
        at_mesafe_bir = (am["bir"] / am["toplam"] * 100) if am["toplam"] >= 2 else 10
        at_mesafe_deneyim = am["toplam"]
        
        ap = at_pist[at_ismi].get(pist, {"toplam": 0, "ilk3": 0, "bir": 0})
        at_pist_ilk3 = (ap["ilk3"] / ap["toplam"] * 100) if ap["toplam"] >= 2 else 30
        at_pist_deneyim = ap["toplam"]
        
        ah = at_hipodrom[at_ismi].get(hip, {"toplam": 0, "ilk3": 0, "bir": 0})
        at_hipodrom_ilk3 = (ah["ilk3"] / ah["toplam"] * 100) if ah["toplam"] >= 2 else 30
        at_hipodrom_deneyim = ah["toplam"]
        
        ja = jokey_at.get((j, at_ismi), {"toplam": 0, "ilk3": 0, "bir": 0})
        jokey_at_uyumu = (ja["ilk3"] / ja["toplam"] * 100) if ja["toplam"] >= 1 else 30
        jokey_at_deneyim = ja["toplam"]
        
        jm = jokey_mesafe[j].get(at["mesafe"], {"toplam": 0, "ilk3": 0, "bir": 0})
        jokey_mesafe_ilk3 = (jm["ilk3"] / jm["toplam"] * 100) if jm["toplam"] >= 5 else 30
        
        jh = jokey_hipodrom[j].get(hip, {"toplam": 0, "ilk3": 0, "bir": 0})
        jokey_hipodrom_ilk3 = (jh["ilk3"] / jh["toplam"] * 100) if jh["toplam"] >= 5 else 30
        
        amm = antrenor_mesafe[a].get(at["mesafe"], {"toplam": 0, "ilk3": 0, "bir": 0})
        antrenor_mesafe_ilk3 = (amm["ilk3"] / amm["toplam"] * 100) if amm["toplam"] >= 5 else 30
        
        # YENI: PIST KAYGAN MI?
        pist_kaygan = 1 if (hava["yagis"] == 1 and pist_cim == 1) else 0
        
        # TARGET
        gelis = at["gelis"]
        ilk3_mi = 1 if gelis <= 3 else 0
        birinci_mi = 1 if gelis == 1 else 0
        
        ml_data.append({
            "kilo": kilo, "ganyan": ganyan, "agf": agf, "hp": hp, "mesafe": mesafe,
            "yas": yas,
            "pist_cim": pist_cim, "pist_kum": pist_kum, "pist_sentetik": pist_sentetik,
            "cins_handikap": cins_handikap, "cins_maiden": cins_maiden,
            "cins_sartli": cins_sartli, "cins_kv": cins_kv,
            "kilo_avantaji": kilo_avantaji,
            "ganyan_avantaji": ganyan_avantaji,
            "agf_yuzde": agf_yuzde,
            "yaris_at_sayisi": at_sayisi,
            "rekabet_seviyesi": rekabet_seviyesi,
            "jokey_kazanma": jokey_kazanma,
            "jokey_ilk3": jokey_ilk3,
            "jokey_toplam": jokey_toplam,
            "jokey_mesafe_ilk3": jokey_mesafe_ilk3,
            "jokey_hipodrom_ilk3": jokey_hipodrom_ilk3,
            "antrenor_kazanma": antrenor_kazanma,
            "antrenor_ilk3": antrenor_ilk3,
            "antrenor_toplam": antrenor_toplam,
            "antrenor_mesafe_ilk3": antrenor_mesafe_ilk3,
            "at_kazanma": at_kazanma,
            "at_ilk3": at_ilk3,
            "at_toplam": at_toplam,
            "at_mesafe_ilk3": at_mesafe_ilk3,
            "at_mesafe_bir": at_mesafe_bir,
            "at_mesafe_deneyim": at_mesafe_deneyim,
            "at_pist_ilk3": at_pist_ilk3,
            "at_pist_deneyim": at_pist_deneyim,
            "at_hipodrom_ilk3": at_hipodrom_ilk3,
            "at_hipodrom_deneyim": at_hipodrom_deneyim,
            "jokey_at_uyumu": jokey_at_uyumu,
            "jokey_at_deneyim": jokey_at_deneyim,
            
            # YENI: HAVA DURUMU
            "sicaklik": hava["sicaklik"],
            "nem": hava["nem"],
            "ruzgar": hava["ruzgar"],
            "yagis": hava["yagis"],
            "bulut": hava["bulut"],
            "pist_kaygan": pist_kaygan,
            
            # YENI: MEVSIM
            "ay": ay,
            "kis": 1 if ay in [12, 1, 2] else 0,
            "yaz": 1 if ay in [6, 7, 8] else 0,
            
            "ilk3_mi": ilk3_mi,
            "birinci_mi": birinci_mi,
            
            "_at_ismi": at_ismi,
            "_jokey": j,
            "_gelis": gelis,
            "_tarih": tarih_str
        })

print(f"   [+] {len(ml_data)} satir feature olusturuldu")

# KAYDET
print("\n[6/6] Kaydediliyor...")

df = pd.DataFrame(ml_data)
bilgi_sutunlar = [c for c in df.columns if c.startswith("_")]
hedef_sutunlar = ["ilk3_mi", "birinci_mi"]
feature_sutunlar = [c for c in df.columns if c not in bilgi_sutunlar + hedef_sutunlar]

print(f"\n   Toplam feature: {len(feature_sutunlar)}")
print(f"   Veri seti: {len(df)} satir")
print(f"   Ilk 3'te: {df['ilk3_mi'].sum()} ({df['ilk3_mi'].mean()*100:.1f}%)")

df.to_csv("ml_veri_v3.csv", sep=";", encoding="utf-8-sig", index=False)
print(f"\n   [+] ml_veri_v3.csv kaydedildi")

print("\n" + "=" * 70)
print("VERI HAZIRLIK TAMAMLANDI!")
print("=" * 70)
print(f"\n   Toplam {len(feature_sutunlar)} feature ile profesyonel veri seti hazır!")
print(f"   Yeni feature'lar:")
print(f"     - Hava durumu (sicaklik, nem, ruzgar, yagis, bulut)")
print(f"     - Pist kaygan mi?")
print(f"     - Mevsim (ay, kis, yaz)")
print(f"     - At-Mesafe/Pist/Hipodrom uzmanligi")
print(f"     - Jokey-At kombinasyonu")
print(f"   Sonraki adim: ml_egitim_v3.py")