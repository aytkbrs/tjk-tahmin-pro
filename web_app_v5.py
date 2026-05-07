import streamlit as st
import pandas as pd
import numpy as np
import os, re, csv, glob, datetime
from collections import defaultdict
import warnings
warnings.filterwarnings('ignore')

st.set_page_config(page_title="TJK Pro v5", page_icon="🐎", layout="wide")

if "dark" not in st.session_state: st.session_state.dark = False
if "auth" not in st.session_state: st.session_state.auth = False

if not st.session_state.auth:
    with st.form("login"):
        st.title("🐎 TJK Pro v5")
        pwd = st.text_input("Şifre", type="password")
        if st.form_submit_button("Giriş"):
            if pwd == "barisbaba2026":
                st.session_state.auth = True
                st.rerun()
            else:
                st.error("Yanlış şifre!")
    st.stop()

col1, col2, col3 = st.columns([0.5, 0.5, 9])
with col1:
    if st.button("🌙" if not st.session_state.dark else "☀️"):
        st.session_state.dark = not st.session_state.dark
if st.session_state.dark:
    st.markdown("""
    <style>
    body, .stApp { background: #1a1a2e; color: #eee; }
    .st-bw, .st-cb { color: #eee !important; }
    .st-expander { background: #16213e; border-radius: 12px; padding: 8px; margin-bottom: 8px; }
    </style>
    """, unsafe_allow_html=True)

@st.cache_resource
def load_data():
    jokey_db, antrenor_db, at_db = {}, {}, {}
    for file, db, key in [("jokey_istatistik.csv", jokey_db, "Jokey"),
                          ("antrenor_istatistik.csv", antrenor_db, "Antrenor"),
                          ("at_istatistik.csv", at_db, "At_Ismi")]:
        if os.path.exists(file):
            with open(file, "r", encoding="utf-8-sig") as f:
                for s in csv.DictReader(f, delimiter=";"):
                    try:
                        db[s[key]] = {"toplam": int(s["Toplam"]), "kazanma": float(s["Kazanma_Yuzde"]), "ilk3": float(s.get("Ilk3_Yuzde", 0))}
                    except: pass
    at_mesafe = defaultdict(lambda: defaultdict(lambda: {"toplam":0,"ilk3":0}))
    jokey_at = defaultdict(lambda: {"toplam":0,"ilk3":0})
    at_form = defaultdict(list)
    if os.path.exists("gecmis_sonuclar.csv"):
        with open("gecmis_sonuclar.csv", "r", encoding="utf-8-sig") as f:
            for s in csv.DictReader(f, delimiter=";"):
                try:
                    gelis = int(s["Gelis_Sirasi"])
                    if gelis==0: continue
                    at_ismi = s.get("At_No","").strip()
                    jokey = s.get("Kilo","").strip()
                    mesafe = s.get("Mesafe","").strip()
                    ilk3 = 1 if gelis<=3 else 0
                    if at_ismi and mesafe:
                        at_mesafe[at_ismi][mesafe]["toplam"]+=1
                        at_mesafe[at_ismi][mesafe]["ilk3"]+=ilk3
                    if jokey and at_ismi:
                        jokey_at[(jokey,at_ismi)]["toplam"]+=1
                        jokey_at[(jokey,at_ismi)]["ilk3"]+=ilk3
                    at_form[at_ismi].append((s["Tarih"],gelis))
                except: pass
    for at in at_form: at_form[at].sort(key=lambda x:x[0])
    weights = {}
    if os.path.exists("best_weights.csv"):
        with open("best_weights.csv","r",encoding="utf-8-sig") as f:
            for row in csv.DictReader(f):
                for k,v in row.items(): weights[k]=float(v)
    else:
        weights = dict(AGF=0.18,G=0.15,FORM=0.14,TREND=0.0,GELIS=0.0,VARYANS=0.0,
                       JOKEY=0.12,AT=0.10,MESAFE=0.08,KILO=0.07,ANTR=0.05,PIST=0.04,HIP=0.03,JAT=0.03)
    dosyalar = sorted(glob.glob("yarislar_*.csv"))
    df = pd.read_csv(dosyalar[-1], sep=";", encoding="utf-8-sig") if dosyalar else pd.DataFrame()
    return jokey_db, antrenor_db, at_db, at_mesafe, jokey_at, at_form, weights, df

jokey_db, antrenor_db, at_db, at_mesafe, jokey_at, at_form, weights, df = load_data()

def p(s):
    try: return float(str(s).replace(",","."))
    except: return 0

def agf_puan(agf):
    if not agf or str(agf)=="-": return 0
    m = re.search(r'(\d+(?:[,.]\d+)?)',str(agf))
    return min(p(m.group(1))*2.5,100) if m else 0

def form_detay(at):
    if at not in at_form: return 50,0,0,0
    gecmis = [g for _,g in at_form[at]]
    if len(gecmis)<2: return 50,0,0,0
    son6 = gecmis[-6:]
    puan = sum({1:100,2:80,3:65,4:50,5:35}.get(g,max(20-g*2,5)) for g in son6)/len(son6)
    ort = np.mean(son6)
    trend = (np.mean(son6[:3])-np.mean(son6[-3:])) if len(son6)>=6 else 0
    varyans = np.var(son6) if len(son6)>=2 else 0
    return puan, ort, trend, varyans

st.title("🐎 TJK Tahmin Pro v5")
st.caption("Ganyan %45.9 | Plase %77.7 | Akıllı Sürpriz | Yeni Tasarım")

if os.path.exists("gecmis_sonuclar.csv"):
    mod_time = os.path.getmtime("gecmis_sonuclar.csv")
    son_tarih = datetime.datetime.fromtimestamp(mod_time).strftime("%d.%m.%Y %H:%M")
    st.info(f"📅 Son güncelleme: {son_tarih} (Her gece otomatik)")

if df.empty:
    st.warning("Henüz yarış verisi yok.")
    st.stop()

# --- HİPODROM SEÇİMİ (Buton Grubu) ---
hipodrom_listesi = sorted(df["Hipodrom"].unique())
hipodrom = st.radio("🏟️ Hipodrom", hipodrom_listesi, horizontal=True)

kosular = sorted(df[df["Hipodrom"]==hipodrom]["Kosu_No"].unique(), key=lambda x: int(x) if str(x).isdigit() else 99)

for k_no in kosular:
    k_df = df[(df["Hipodrom"]==hipodrom) & (df["Kosu_No"]==k_no)]
    if k_df.empty: continue
    row = k_df.iloc[0]
    pist_goster = str(row["Pist"]) if not pd.isna(row["Pist"]) else "?"
    cins_goster = str(row["Cins"]) if not pd.isna(row["Cins"]) else ""
    with st.expander(f"🏁 {k_no}. Koşu | {row['Saat']} | {row['Mesafe']}m {pist_goster} | {cins_goster}", expanded=(k_no==kosular[0])):
        pist_str = str(row["Pist"]) if not pd.isna(row["Pist"]) else ""
        if "Cim" in pist_str or "Çim" in pist_str: st.caption("🌧️ Çim pist, yağışta ağırlaşır")
        elif "Kum" in pist_str: st.caption("🏜️ Kum pist, stabil")

        puanlar = []
        for _, at in k_df.iterrows():
            p_agf = agf_puan(at.get("AGF",""))
            ganyanlar = [p(x) for x in k_df["Ganyan"] if p(x)>0]
            gv = p(at["Ganyan"])
            p_g = (min(ganyanlar)/gv*100) if gv>0 and ganyanlar else 20
            kilolar = [p(x) for x in k_df["Kilo"] if p(x)>0]
            kv = p(at["Kilo"])
            if kilolar and max(kilolar)!=min(kilolar):
                p_kilo = ((max(kilolar)-kv)/(max(kilolar)-min(kilolar)))*100
            else: p_kilo = 70
            form_ort, ort, trend, varyans = form_detay(at["At_Ismi"])
            p_trend = max(0, min(100, 50 + trend*10))
            p_gelis = max(0, min(100, 100 - ort*10))
            p_var = max(0, min(100, 100 - varyans*5))
            p_jokey = min(jokey_db.get(at["Jokey"],{}).get("kazanma",10)*5,100) if jokey_db.get(at["Jokey"],{}).get("toplam",0)>=5 else 50
            p_antr = min(antrenor_db.get(at["Antrenor"],{}).get("kazanma",10)*5,100) if antrenor_db.get(at["Antrenor"],{}).get("toplam",0)>=5 else 50
            p_at = min(at_db.get(at["At_Ismi"],{}).get("kazanma",10)*5,100) if at_db.get(at["At_Ismi"],{}).get("toplam",0)>=2 else 50
            p_mesafe = (at_mesafe[at["At_Ismi"]][str(row["Mesafe"])]["ilk3"]/at_mesafe[at["At_Ismi"]][str(row["Mesafe"])]["toplam"]*100) if at_mesafe[at["At_Ismi"]][str(row["Mesafe"])]["toplam"]>=2 else 30
            p_uyum = (jokey_at.get((at["Jokey"],at["At_Ismi"]),{}).get("ilk3",0)/max(1,jokey_at.get((at["Jokey"],at["At_Ismi"]),{}).get("toplam",1)))*100

            toplam = (weights["AGF"]*p_agf + weights["G"]*p_g + weights["FORM"]*form_ort +
                      weights["TREND"]*p_trend + weights["GELIS"]*p_gelis + weights["VARYANS"]*p_var +
                      weights["JOKEY"]*p_jokey + weights["AT"]*p_at + weights["MESAFE"]*p_mesafe)

            # --- DENGELİ SÜRPRİZ ---
            agf_val = p(str(at.get("AGF","")).replace("%",""))
            son3_list = [g for _,g in at_form.get(at["At_Ismi"],[])[-3:]]
            son3_var = len(son3_list)==3 and any(g<=3 for g in son3_list)
            uyum_var = p_uyum >= 50
            kriterler = sum([agf_val<5, son3_var, uyum_var])
            surpriz = "⚡" if kriterler >= 2 else ""

            puanlar.append({
                "Sıra": at["Sira"], "At": at["At_Ismi"], "Jokey": at["Jokey"],
                "Puan": round(toplam,1), "Ganyan": at["Ganyan"], "Sürpriz": surpriz
            })

        puanlar.sort(key=lambda x: x["Puan"], reverse=True)

        if len(puanlar)>=3:
            fark = puanlar[0]["Puan"] - puanlar[1]["Puan"]
            if fark>15: st.info(f"🎯 **Tek geç:** {puanlar[0]['At']}")
            elif fark>8: st.info(f"🔒 **İkili:** {puanlar[0]['At']} - {puanlar[1]['At']}")
            else: st.info(f"🌐 **Geniş:** {puanlar[0]['At']}, {puanlar[1]['At']}, {puanlar[2]['At']}")

        cols = st.columns(3)
        for i, c in enumerate(["#FFD700","#C0C0C0","#CD7F32"]):
            if i < len(puanlar):
                s = puanlar[i]
                with cols[i]:
                    st.markdown(f"<div style='background:{c};padding:10px;border-radius:12px;font-weight:bold;'>{['🥇','🥈','🥉'][i]} #{s['Sıra']} {s['At'][:20]}<br>Puan: {s['Puan']}</div>", unsafe_allow_html=True)

        # SÜRPRİZ SATIRLARI
        for s in puanlar:
            if s["Sürpriz"]=="⚡":
                st.markdown(f"""
                <div style="background:#ff4757; color:white; padding:6px 12px; border-radius:8px; margin:2px 0; animation:blink 1.5s infinite;">
                ⚡ SÜRPRİZ ADAYI: #{s['Sıra']} {s['At']} | Puan: {s['Puan']}
                </div>
                <style>@keyframes blink {{ 50% {{ opacity:0.6; }} }}</style>
                """, unsafe_allow_html=True)

        st.dataframe(pd.DataFrame(puanlar)[["Sıra","At","Puan","Jokey","Ganyan","Sürpriz"]], use_container_width=True)