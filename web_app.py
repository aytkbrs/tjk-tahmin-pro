import streamlit as st
import pandas as pd
import numpy as np
import os, re, sys, csv, glob, subprocess
from collections import defaultdict
import warnings
warnings.filterwarnings('ignore')

st.set_page_config(page_title="TJK Tahmin V4", page_icon="🐎", layout="centered", initial_sidebar_state="collapsed")

# Şifre
def sifre_kontrolu():
    if "sifre_dogru" not in st.session_state: st.session_state["sifre_dogru"] = False
    if not st.session_state["sifre_dogru"]:
        st.markdown("<h1 style='text-align:center;'>🐎 TJK Tahmin V4</h1>", unsafe_allow_html=True)
        with st.form("giris"):
            sifre = st.text_input("🔒 Şifre", type="password")
            if st.form_submit_button("🚪 GİRİŞ", use_container_width=True):
                if sifre == "barisbaba2026":
                    st.session_state["sifre_dogru"] = True
                    st.rerun()
                else: st.error("Hatalı şifre!")
        st.stop()

sifre_kontrolu()

st.markdown("""<style>
#MainMenu, footer, header {visibility:hidden;} .block-container {padding:0.5rem!important; max-width:100%!important;}
.top-card {padding:10px; border-radius:10px; margin:4px 0; font-size:0.85em;}
.gold {background:linear-gradient(135deg,#FFD700,#FFA500); color:#333;}
.silver {background:linear-gradient(135deg,#C0C0C0,#808080); color:white;}
.bronze {background:linear-gradient(135deg,#CD7F32,#8B4513); color:white;}
.surpriz {background:linear-gradient(135deg,#ff6e7f,#bfe9ff); color:white; padding:8px; border-radius:8px; margin:2px 0;}
.stButton > button {width:100%!important; height:50px!important; font-size:1.1em!important; font-weight:bold!important;}
</style>""", unsafe_allow_html=True)

# ==== BUTONLAR (En üstte) ====
col1, col2 = st.columns(2)
with col1:
    if st.button("🔄 VERİLERİ GÜNCELLE", use_container_width=True):
        with st.spinner("Yarış verileri güncelleniyor..."):
            try:
                subprocess.run(["python", "tjk_cekici.py"], capture_output=True, cwd=os.path.dirname(__file__) or ".")
                st.success("✅ Bugünkü yarışlar yeniden çekildi!")
                st.cache_data.clear()
                st.rerun()
            except Exception as e:
                st.error(f"Hata: {e}")

with col2:
    if st.button("📊 SON DAKİKA AGF", use_container_width=True):
        with st.spinner("Güncel AGF oranları çekiliyor..."):
            try:
                subprocess.run(["python", "tjk_cekici.py"], capture_output=True, cwd=os.path.dirname(__file__) or ".")
                st.success("✅ AGF'ler güncellendi! Sayfa yenileniyor...")
                st.cache_data.clear()
                st.rerun()
            except Exception as e:
                st.error(f"Hata: {e}")

st.markdown("<hr style='margin:8px 0'>", unsafe_allow_html=True)

# ==== VERİLERİ YÜKLE ====

def verileri_yukle():
    jokey_db, antrenor_db, at_db = {}, {}, {}
    for dosya, db, anahtar in [("jokey_istatistik.csv", jokey_db, "Jokey"),
                                ("antrenor_istatistik.csv", antrenor_db, "Antrenor"),
                                ("at_istatistik.csv", at_db, "At_Ismi")]:
        if os.path.exists(dosya):
            with open(dosya, "r", encoding="utf-8-sig") as f:
                for s in csv.DictReader(f, delimiter=";"):
                    try:
                        db[s[anahtar]] = {"toplam": int(s["Toplam"]), "kazanma": float(s["Kazanma_Yuzde"]), "ilk3": float(s.get("Ilk3_Yuzde", 0))}
                    except: pass

    at_mesafe = defaultdict(lambda: defaultdict(lambda: {"toplam": 0, "ilk3": 0}))
    at_pist = defaultdict(lambda: defaultdict(lambda: {"toplam": 0, "ilk3": 0}))
    at_hipodrom = defaultdict(lambda: defaultdict(lambda: {"toplam": 0, "ilk3": 0}))
    jokey_at = defaultdict(lambda: {"toplam": 0, "ilk3": 0})
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

    weights = {}
    if os.path.exists("best_weights.csv"):
        with open("best_weights.csv", "r", encoding="utf-8-sig") as f:
            for row in csv.DictReader(f):
                for k, v in row.items(): weights[k] = float(v)
    else:
        weights = {"AGF": 0.18, "G": 0.15, "FORM": 0.14, "TREND": 0.00, "GELIS": 0.00, "VARYANS": 0.00,
                   "JOKEY": 0.12, "AT": 0.10, "MESAFE": 0.08, "KILO": 0.07, "ANTR": 0.05,
                   "PIST": 0.04, "HIP": 0.03, "JAT": 0.03}

    dosyalar = sorted(glob.glob("yarislar_*.csv"))
    df = pd.read_csv(dosyalar[-1], sep=";", encoding="utf-8-sig") if dosyalar else pd.DataFrame()
    return jokey_db, antrenor_db, at_db, at_mesafe, at_pist, at_hipodrom, jokey_at, at_form, weights, df

jokey_db, antrenor_db, at_db, at_mesafe, at_pist, at_hipodrom, jokey_at, at_form, weights, df = verileri_yukle()

# ==== FONKSİYONLAR ====
def parse_sayi(m):
    try: return float(str(m).replace(",", ".").strip())
    except: return 0

def agf_puani(agf):
    if not agf or str(agf) == "-": return 0
    m = re.search(r'(\d+(?:[,.]\d+)?)', str(agf))
    return min(parse_sayi(m.group(1)) * 2.5, 100) if m else 0

def form_detay(at_ismi):
    if at_ismi not in at_form: return 50, 0, 0, 0
    gecmis = [g for _, g in at_form[at_ismi]]
    if len(gecmis) < 2: return 50, 0, 0, 0
    son6 = gecmis[-6:]
    puan, p_map = 0, {1: 100, 2: 80, 3: 65, 4: 50, 5: 35}
    for g in son6: puan += p_map.get(g, max(20 - g * 2, 5))
    ortalama_puan = puan / len(son6)
    ort_gelis = np.mean(son6)
    if len(son6) >= 6: trend = np.mean(son6[:3]) - np.mean(son6[-3:])
    elif len(son6) >= 3: trend = np.mean(son6) - np.mean(son6[-3:])
    else: trend = 0
    varyans = np.var(son6) if len(son6) >= 2 else 0
    return ortalama_puan, ort_gelis, trend, varyans

def surpriz_kontrol(at_ismi, jokey, agf_str, mesafe):
    kriter, nedenler = 0, []
    agf_val = parse_sayi(str(agf_str).replace("%", ""))
    if agf_val < 10: kriter += 1; nedenler.append(f"AGF %{agf_val:.0f}")
    if at_ismi in at_form and len(at_form[at_ismi]) >= 3:
        son3 = [g for _, g in at_form[at_ismi][-3:]]
        if any(g <= 3 for g in son3): kriter += 1; nedenler.append("Form yükseliyor")
    if (jokey, at_ismi) in jokey_at:
        ja = jokey_at[(jokey, at_ismi)]
        if ja["toplam"] >= 2 and (ja["ilk3"] / ja["toplam"]) * 100 >= 50: kriter += 1; nedenler.append("Jokeyle uyumlu")
    return (kriter >= 2, ", ".join(nedenler))

# ==== ANA SAYFA ====
if df.empty:
    st.warning("⚠️ Yarış verisi yok. GÜNCELLE butonuna basın.")
    st.stop()

st.markdown("<h1 style='text-align:center;'>🐎 TJK Tahmin V4</h1>", unsafe_allow_html=True)
st.markdown(f"<p style='text-align:center;color:gray;'>🤖 %45.9 Ganyan | 📱 Mobil | 🔄 Canlı Güncelleme</p>", unsafe_allow_html=True)

hipodrom = st.selectbox("🏟️ Hipodrom Seçin", sorted(df["Hipodrom"].unique()))
df_h = df[df["Hipodrom"] == hipodrom]
kosular = sorted(df_h["Kosu_No"].unique(), key=lambda x: int(x) if str(x).isdigit() else 99)

for kosu in kosular:
    df_k = df_h[df_h["Kosu_No"] == kosu]
    if df_k.empty: continue
    ilk = df_k.iloc[0]

    with st.expander(f"🏁 {kosu}. Koşu | {ilk['Saat']} | {ilk['Mesafe']}m {ilk['Pist']} | {ilk.get('Cins','')}"):
        tum_g = df_k["Ganyan"].tolist()
        tum_k = df_k["Kilo"].tolist()
        mesafe = ilk["Mesafe"]
        pist = ilk["Pist"]
        sonuclar = []

        for _, at in df_k.iterrows():
            agf = at.get("AGF", "")
            ganyan_str = at.get("Ganyan", "")
            kilo_str = at.get("Kilo", "")
            jokey = at.get("Jokey", "")
            antrenor = at.get("Antrenor", "")
            at_ismi = at.get("At_Ismi", "")

            p_agf = agf_puani(agf)
            gv = parse_sayi(ganyan_str)
            gec = [parse_sayi(x) for x in tum_g if parse_sayi(x) > 0]
            p_g = (min(gec) / gv) * 100 if gv > 0 and gec else 20
            kv = parse_sayi(kilo_str)
            gec_k = [parse_sayi(x) for x in tum_k if parse_sayi(x) > 0]
            p_kilo = ((max(gec_k) - kv) / (max(gec_k) - min(gec_k))) * 100 if gec_k and max(gec_k) != min(gec_k) else 70

            form_ort, ort_gelis, trend, varyans = form_detay(at_ismi)
            p_trend = max(0, min(100, 50 + trend * 10))
            p_gelis = max(0, min(100, 100 - ort_gelis * 10))
            p_varyans = max(0, min(100, 100 - varyans * 5))

            p_jokey = min(jokey_db.get(jokey, {}).get("kazanma", 10) * 5, 100) if jokey_db.get(jokey, {}).get("toplam", 0) >= 5 else 50
            p_antr = min(antrenor_db.get(antrenor, {}).get("kazanma", 10) * 5, 100) if antrenor_db.get(antrenor, {}).get("toplam", 0) >= 5 else 50
            p_at = min(at_db.get(at_ismi, {}).get("kazanma", 10) * 5, 100) if at_db.get(at_ismi, {}).get("toplam", 0) >= 2 else 50

            p_mesafe = (at_mesafe[at_ismi][mesafe]["ilk3"] / at_mesafe[at_ismi][mesafe]["toplam"] * 100) if at_mesafe[at_ismi][mesafe]["toplam"] >= 2 else 30
            p_pist = (at_pist[at_ismi][pist]["ilk3"] / at_pist[at_ismi][pist]["toplam"] * 100) if at_pist[at_ismi][pist]["toplam"] >= 2 else 30
            p_hip = (at_hipodrom[at_ismi][hipodrom]["ilk3"] / at_hipodrom[at_ismi][hipodrom]["toplam"] * 100) if at_hipodrom[at_ismi][hipodrom]["toplam"] >= 2 else 30
            p_jat = (jokey_at[(jokey, at_ismi)]["ilk3"] / jokey_at[(jokey, at_ismi)]["toplam"] * 100) if (jokey, at_ismi) in jokey_at and jokey_at[(jokey, at_ismi)]["toplam"] >= 1 else 30

            toplam = (weights["AGF"] * p_agf + weights["G"] * p_g + weights["FORM"] * form_ort +
                      weights["TREND"] * p_trend + weights["GELIS"] * p_gelis + weights["VARYANS"] * p_varyans +
                      weights["JOKEY"] * p_jokey + weights["AT"] * p_at + weights["MESAFE"] * p_mesafe +
                      weights["KILO"] * p_kilo + weights["ANTR"] * p_antr + weights["PIST"] * p_pist +
                      weights["HIP"] * p_hip + weights["JAT"] * p_jat)

            surpriz_mu, surpriz_neden = surpriz_kontrol(at_ismi, jokey, agf, mesafe)
            sonuclar.append({
                "Sıra": at.get("Sira", ""), "At": at_ismi, "Jokey": jokey, "Ganyan": ganyan_str,
                "Puan": round(toplam, 1), "AGF": agf, "Sürpriz": "⚡" if surpriz_mu else ""
            })

        sonuclar.sort(key=lambda x: x["Puan"], reverse=True)

        cols = st.columns(3)
        madalyalar = ["🥇", "🥈", "🥉"]
        renkler = ["gold", "silver", "bronze"]
        for i in range(min(3, len(sonuclar))):
            s = sonuclar[i]
            with cols[i]:
                st.markdown(f"<div class='top-card {renkler[i]}'><b>{madalyalar[i]} #{s['Sıra']} {s['At'][:20]}</b><br>Puan: {s['Puan']}<br>Jokey: {s['Jokey'][:15]}<br>Ganyan: {s['Ganyan']}</div>", unsafe_allow_html=True)

        for s in sonuclar:
            if s["Sürpriz"] == "⚡":
                _, neden = surpriz_kontrol(s["At"], s["Jokey"], s["AGF"], mesafe)
                st.markdown(f"<div class='surpriz'>⚡ Sürpriz Adayı: <b>#{s['Sıra']} {s['At'][:25]}</b> | Puan: {s['Puan']} | {neden}</div>", unsafe_allow_html=True)

        df_sonuc = pd.DataFrame(sonuclar)
        st.dataframe(df_sonuc[["Sıra", "At", "Puan", "Jokey", "Ganyan", "Sürpriz"]], use_container_width=True, hide_index=True)

st.markdown("<p style='text-align:center;color:gray;'>👨‍👦 Aile içi kullanım - Eğitim amaçlıdır</p>", unsafe_allow_html=True)