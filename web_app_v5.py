import streamlit as st
import pandas as pd
import numpy as np
import os, re, csv, glob, datetime, pickle, requests
from bs4 import BeautifulSoup
from collections import defaultdict
from urllib.parse import unquote, quote
import warnings
warnings.filterwarnings('ignore')

st.set_page_config(page_title="TJK Pro Final", page_icon="🐎", layout="wide")

# ---------- Karanlık mod ----------
if "dark" not in st.session_state: st.session_state.dark = False
if "auth" not in st.session_state: st.session_state.auth = False

if not st.session_state.auth:
    with st.form("login"):
        st.title("🐎 TJK Pro Final")
        pwd = st.text_input("Şifre", type="password")
        if st.form_submit_button("Giriş"):
            if pwd == "barisbaba2026":
                st.session_state.auth = True
                st.rerun()
            else:
                st.error("Yanlış şifre!")
    st.stop()

# ---------- SİDEBAR ----------
with st.sidebar:
    st.markdown("### ⚙️ Kontroller")
    if st.button("🌙 Karanlık Mod" if not st.session_state.dark else "☀️ Aydınlık Mod"):
        st.session_state.dark = not st.session_state.dark
        st.rerun()
    
    st.markdown("---")
    use_ml = st.checkbox("🤖 ML Destekli Hibrit Tahmin", value=True)
    
    st.markdown("---")
    if st.button("🔄 Yarışları Canlı Çek"):
        with st.spinner("⏳ TJK'dan güncel yarışlar alınıyor..."):
            basarili, dosya = canli_yaris_cek()
            if basarili:
                st.success(f"✅ {dosya} oluşturuldu! Sayfa yenileniyor...")
                st.cache_resource.clear()
                st.cache_data.clear()
                st.rerun()
            else:
                st.warning("⚠️ Bugün yarış bulunamadı veya bağlantı hatası.")
    
    if st.button("🗑️ Cache Temizle & Yenile"):
        st.cache_resource.clear()
        st.cache_data.clear()
        st.success("✅ Cache temizlendi, sayfa yenileniyor...")
        st.rerun()
    
    st.markdown("---")
    if os.path.exists("gecmis_sonuclar.csv"):
        mod_time = os.path.getmtime("gecmis_sonuclar.csv")
        son_tarih = datetime.datetime.fromtimestamp(mod_time).strftime("%d.%m.%Y %H:%M")
        st.caption(f"📅 Son güncelleme: {son_tarih}")
    
    st.markdown("---")
    st.caption("👨‍👦 Aile içi kullanım")

# ---------- CSS ----------
if st.session_state.dark:
    st.markdown("""<style>
    body, .stApp {background:#1a1a2e;color:#eee}
    .st-expander {background:#16213e;border-radius:12px;padding:8px;margin-bottom:8px;border:1px solid #0f3460}
    .top-card {padding:12px;border-radius:12px;color:white;margin:4px 0;box-shadow:0 4px 8px rgba(0,0,0,0.3)}
    .kupon-box {background:#2c3e50;border-radius:8px;padding:10px;margin:8px 0}
    </style>""", unsafe_allow_html=True)
else:
    st.markdown("""<style>
    .top-card {padding:12px;border-radius:12px;color:white;margin:4px 0;box-shadow:0 2px 6px rgba(0,0,0,0.15)}
    .kupon-box {background:#f8f9fa;border-radius:8px;padding:10px;margin:8px 0;border:1px solid #dee2e6}
    </style>""", unsafe_allow_html=True)

# ---------- CANLI YARIŞ ÇEKME FONKSİYONU ----------
def canli_yaris_cek():
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "X-Requested-With": "XMLHttpRequest",
        "Referer": "https://www.tjk.org/TR/YarisSever/Info/Page/GunlukYarisProgrami"
    }
    bugun = datetime.datetime.now().strftime("%d/%m/%Y")
    tarih_dosya = datetime.datetime.now().strftime("%Y%m%d")
    csv_dosya = f"yarislar_{tarih_dosya}.csv"

    TURKIYE_SEHIRLER = ["Ankara", "Izmir", "İzmir", "Bursa", "Diyarbakir", "Diyarbakır",
                        "Istanbul", "İstanbul", "Adana", "Sanliurfa", "Şanlıurfa",
                        "Elazig", "Elazığ", "Antalya", "Kocaeli"]

    ana_url = "https://www.tjk.org/TR/YarisSever/Info/Page/GunlukYarisProgrami"
    response = requests.get(ana_url, headers=headers, timeout=15)
    soup = BeautifulSoup(response.text, "html.parser")

    sehirler = []
    gorulen = set()
    for link in soup.find_all("a", href=True):
        href = link.get("href", "")
        if "SehirId=" in href:
            try:
                sehir_id = href.split("SehirId=")[1].split("&")[0]
                if sehir_id in gorulen: continue
                gorulen.add(sehir_id)
                if "SehirAdi=" in href:
                    raw = href.split("SehirAdi=")[1].split("&")[0]
                    sehir_adi = unquote(raw.replace("+", " "))
                else:
                    sehir_adi = link.text.strip()
                sehirler.append((sehir_id, sehir_adi))
            except: pass
    turkiye = [(sid, sad) for sid, sad in sehirler if any(t in sad for t in TURKIYE_SEHIRLER)]
    if not turkiye: return False, csv_dosya

    with open(csv_dosya, "w", encoding="utf-8-sig", newline="") as f:
        yazici = csv.writer(f, delimiter=";")
        yazici.writerow(["Hipodrom","Kosu_No","Saat","Mesafe","Pist","Cins","Sira","At_Ismi",
                         "Yas_Cinsiyet","Orijin","Kilo","Jokey","Sahip","Antrenor","Start_No",
                         "HP","Son_6_Yaris","KGS","S20","Ganyan","AGF","Tarih"])
        for sehir_id, sehir_adi in turkiye:
            sehir_adi_url = quote(sehir_adi.replace(" ", "+"), safe="+")
            sehir_url = (f"https://www.tjk.org/TR/YarisSever/Info/Sehir/GunlukYarisProgrami"
                         f"?SehirId={sehir_id}&QueryParameter_Tarih={bugun}&SehirAdi={sehir_adi_url}&Era=today")
            try:
                r = requests.get(sehir_url, headers=headers, timeout=20)
                ssoup = BeautifulSoup(r.text, "html.parser")
                kosu_saatleri = {}
                for tab in ssoup.find_all("a", id=re.compile(r"^anc-?\d+")):
                    tab_text = tab.get_text(" ", strip=True)
                    match = re.search(r'(\d+)\.\s*Ko[şs]u\s+(\d{1,2}[:\.]\d{2})', tab_text)
                    if match: kosu_saatleri[match.group(1)] = match.group(2).replace(".", ":")
                kosu_tablolari = ssoup.find_all("div", id=re.compile(r"^kosubilgisi-"))
                kosu_index = 0
                for kosu_div in kosu_tablolari:
                    kosu_index += 1
                    parent = kosu_div.find_parent("div", id=re.compile(r"^-?\d+"))
                    kosu_no = str(kosu_index)
                    if parent:
                        h3 = parent.find("h3", class_="race-no")
                        if h3:
                            no_match = re.search(r'(\d+)\.\s*Ko[şs]u', h3.get_text(" ", strip=True))
                            if no_match: kosu_no = no_match.group(1)
                    saat = kosu_saatleri.get(kosu_no, "")
                    mesafe, pist, cins = "", "", ""
                    if parent:
                        config = parent.find("h3", class_="race-config")
                        if config:
                            ctext = config.get_text(" ", strip=True)
                            m = re.search(r'\b(\d{3,4})\b', ctext)
                            if m: mesafe = m.group(1)
                            if "Çim" in ctext or "Cim" in ctext: pist = "Cim"
                            elif "Kum" in ctext: pist = "Kum"
                            for c in ["Maiden","Handikap","Şartlı","Sartli","Satış","Satis","KV","A1","A2","A3"]:
                                if c in ctext: cins = c; break
                    tablo = kosu_div.find("table", class_="tablesorter")
                    if not tablo: continue
                    tbody = tablo.find("tbody")
                    if not tbody: continue
                    for tr in tbody.find_all("tr"):
                        try:
                            td_sira = tr.find("td", class_="gunluk-GunlukYarisProgrami-SiraId")
                            td_at = tr.find("td", class_="gunluk-GunlukYarisProgrami-AtAdi")
                            if not td_at or not td_sira: continue
                            sira = td_sira.get_text(strip=True)
                            at_text = td_at.get_text(" ", strip=True)
                            match_at = re.match(r"^([A-ZÇĞİÖŞÜ' ]+?)(?:\s+(?:KG|DB|KV|SK|SKG)|\s+\([^)]*\)|\s+[a-z]|$)", at_text)
                            at_ismi = match_at.group(1).strip() if match_at else at_text.split()[0]
                            if "(Koşmaz)" in at_text or "Kosmaz" in at_text: continue

                            td_yas = tr.find("td", class_="gunluk-GunlukYarisProgrami-Yas")
                            td_orijin = tr.find("td", class_="gunluk-GunlukYarisProgrami-Baba")
                            td_kilo = tr.find("td", class_="gunluk-GunlukYarisProgrami-Kilo")
                            td_jokey = tr.find("td", class_="gunluk-GunlukYarisProgrami-JokeAdi")
                            td_sahip = tr.find("td", class_="gunluk-GunlukYarisProgrami-SahipAdi")
                            td_antrenor = tr.find("td", class_="gunluk-GunlukYarisProgrami-AntronorAdi")
                            td_start = tr.find("td", class_="gunluk-GunlukYarisProgrami-StartId")
                            td_hp = tr.find("td", class_="gunluk-GunlukYarisProgrami-Hc")
                            td_son6 = tr.find("td", class_="gunluk-GunlukYarisProgrami-Son6Yaris")
                            td_kgs = tr.find("td", class_="gunluk-GunlukYarisProgrami-KGS")
                            td_s20 = tr.find("td", class_="gunluk-GunlukYarisProgrami-s20")
                            td_gny = tr.find("td", class_="gunluk-GunlukYarisProgrami-Gny")
                            td_agf = tr.find("td", class_="gunluk-GunlukYarisProgrami-AGFORAN")

                            yas = td_yas.get_text(strip=True) if td_yas else ""
                            orijin = td_orijin.get_text(strip=True) if td_orijin else ""
                            kilo = td_kilo.get_text(strip=True) if td_kilo else ""
                            jokey = td_jokey.find("a").get_text(strip=True) if td_jokey and td_jokey.find("a") else (td_jokey.get_text(strip=True) if td_jokey else "")
                            sahip = td_sahip.get_text(strip=True) if td_sahip else ""
                            antrenor = td_antrenor.get_text(strip=True) if td_antrenor else ""
                            start_no = td_start.get_text(strip=True) if td_start else ""
                            hp = td_hp.get_text(strip=True) if td_hp else ""
                            son6 = td_son6.get_text(strip=True) if td_son6 else ""
                            kgs = td_kgs.get_text(strip=True) if td_kgs else ""
                            s20 = td_s20.get_text(strip=True) if td_s20 else ""
                            ganyan = ""
                            if td_gny:
                                g_text = td_gny.get_text(strip=True)
                                g_match = re.search(r'(\d+[,.]?\d*)', g_text)
                                if g_match: ganyan = g_match.group(1)
                            agf = ""
                            if td_agf:
                                agf_text = td_agf.get_text(strip=True)
                                agf_match = re.search(r'%(\d+(?:[,.]\d+)?)', agf_text)
                                if agf_match: agf = "%" + agf_match.group(1)

                            yazici.writerow([sehir_adi, kosu_no, saat, mesafe, pist, cins,
                                             sira, at_ismi, yas, orijin, kilo,
                                             jokey, sahip, antrenor, start_no, hp,
                                             son6, kgs, s20, ganyan, agf, bugun])
                        except: pass
            except: pass
    return True, csv_dosya

# ---------- VERİ YÜKLEME ----------
@st.cache_resource(ttl=3600)
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
    at_gecmis_detay = defaultdict(list)

    if os.path.exists("gecmis_sonuclar.csv"):
        with open("gecmis_sonuclar.csv", "r", encoding="utf-8-sig") as f:
            for s in csv.DictReader(f, delimiter=";"):
                try:
                    gelis = int(s["Gelis_Sirasi"])
                    if gelis == 0: continue
                    at_ismi = re.sub(r'\s+(KG|DB|KV|SK|SKG|GKR).*$', '', s.get("At_No", "").strip()).strip()
                    jokey = s.get("Kilo", "").strip()
                    mesafe = s.get("Mesafe", "").strip()
                    pist = s.get("Pist", "").strip()
                    hipodrom = s.get("Hipodrom", "").strip()
                    tarih = s.get("Tarih", "").strip()
                    kilo = s.get("Orijin_Anne", "").strip()
                    ganyan = s.get("Derece", "").strip()
                    ilk3 = 1 if gelis <= 3 else 0
                    if at_ismi and mesafe:
                        at_mesafe[at_ismi][mesafe]["toplam"] += 1
                        at_mesafe[at_ismi][mesafe]["ilk3"] += ilk3
                    if jokey and at_ismi:
                        jokey_at[(jokey, at_ismi)]["toplam"] += 1
                        jokey_at[(jokey, at_ismi)]["ilk3"] += ilk3
                    at_form[at_ismi].append((tarih, gelis))
                    at_gecmis_detay[at_ismi].append({"tarih":tarih,"hipodrom":hipodrom,"mesafe":mesafe,"pist":pist,"jokey":jokey,"kilo":kilo,"ganyan":ganyan,"gelis":gelis})
                except: pass
    for at in at_form: at_form[at].sort(key=lambda x: x[0])

    weights = {}
    if os.path.exists("best_weights.csv"):
        with open("best_weights.csv", "r", encoding="utf-8-sig") as f:
            for row in csv.DictReader(f):
                for k, v in row.items(): weights[k] = float(v)
    else:
        weights = dict(AGF=0.18, G=0.15, FORM=0.14, TREND=0.0, GELIS=0.0, VARYANS=0.0,
                       JOKEY=0.12, AT=0.10, MESAFE=0.08, KILO=0.07, ANTR=0.05, PIST=0.04, HIP=0.03, JAT=0.03)

    dosyalar = sorted(glob.glob("yarislar_*.csv"))
    df = pd.read_csv(dosyalar[-1], sep=";", encoding="utf-8-sig") if dosyalar else pd.DataFrame()
    return jokey_db, antrenor_db, at_db, at_mesafe, jokey_at, at_form, weights, df, at_gecmis_detay

jokey_db, antrenor_db, at_db, at_mesafe, jokey_at, at_form, weights, df, at_gecmis_detay = load_data()

# ---------- ML Modeli Yükle ----------
ml_model = None
ml_features = []
if os.path.exists("ml_model.pkl"):
    with open("ml_model.pkl", "rb") as f:
        ml_data = pickle.load(f)
        ml_model = ml_data["model"]
        ml_features = ml_data["features"]

# ---------- Yardımcılar ----------
def p(s):
    try: return float(str(s).replace(",", "."))
    except: return 0

def agf_sayisal(agf):
    if not agf or str(agf) == "-": return 0.0
    m = re.search(r'(\d+(?:[,.]\d+)?)', str(agf))
    return p(m.group(1)) if m else 0.0

def agf_puan(agf):
    if not agf or str(agf) == "-": return 0
    m = re.search(r'(\d+(?:[,.]\d+)?)', str(agf))
    return min(p(m.group(1)) * 2.5, 100) if m else 0

def form_detay(at):
    if at not in at_form: return 50, 0, 0, 0
    gecmis = [g for _, g in at_form[at]]
    if len(gecmis) < 2: return 50, 0, 0, 0
    son6 = gecmis[-6:]
    puan = sum({1:100,2:80,3:65,4:50,5:35}.get(g, max(20 - g * 2, 5)) for g in son6) / len(son6)
    ort = np.mean(son6)
    trend = (np.mean(son6[:3]) - np.mean(son6[-3:])) if len(son6) >= 6 else 0
    varyans = np.var(son6) if len(son6) >= 2 else 0
    return puan, ort, trend, varyans

# ---------- ANA EKRAN ----------
st.title("🐎 TJK Tahmin Pro")
st.caption("Kural Tabanlı + ML Hibrit | Akıllı Kupon | Güven Skoru")

if df.empty:
    st.warning("Henüz yarış verisi yok. Lütfen sol menüden 'Yarışları Canlı Çek' butonuna basın.")
    st.stop()

hipodrom = st.radio("🏟️ Hipodrom", sorted(df["Hipodrom"].unique()), horizontal=True)
kosular = sorted(df[df["Hipodrom"] == hipodrom]["Kosu_No"].unique(), key=lambda x: int(x) if str(x).isdigit() else 99)

for k_no in kosular:
    k_df = df[(df["Hipodrom"] == hipodrom) & (df["Kosu_No"] == k_no)]
    if k_df.empty: continue
    row = k_df.iloc[0]
    pist_str = str(row["Pist"]) if not pd.isna(row["Pist"]) else ""
    cins_str = str(row.get("Cins", "")) if not pd.isna(row.get("Cins", "")) else ""
    with st.expander(f"🏁 {k_no}. Koşu | {row['Saat']} | {row['Mesafe']}m {pist_str} | {cins_str}", expanded=(k_no == kosular[0])):
        if "Cim" in pist_str or "Çim" in pist_str: st.caption("🌧️ Çim pist, yağışta ağırlaşır")
        elif "Kum" in pist_str: st.caption("🏜️ Kum pist, stabil")

        kilolar = [p(x) for x in k_df["Kilo"] if p(x) > 0]
        min_kilo, max_kilo = (min(kilolar), max(kilolar)) if kilolar else (0, 0)
        ganyanlar = [p(x) for x in k_df["Ganyan"] if p(x) > 0]
        min_ganyan = min(ganyanlar) if ganyanlar else 0
        max_agf = max([agf_sayisal(x) for x in k_df["AGF"]]) if len(k_df) > 0 else 1

        puanlar = []
        for _, at in k_df.iterrows():
            p_agf = agf_puan(at.get("AGF", ""))
            gv, kv = p(at["Ganyan"]), p(at["Kilo"])
            p_g = (min_ganyan / gv * 100) if gv > 0 and ganyanlar else 20
            p_kilo = ((max_kilo - kv) / (max_kilo - min_kilo)) * 100 if max_kilo != min_kilo else 70
            form_ort, ort, trend, varyans = form_detay(at["At_Ismi"])
            p_trend = max(0, min(100, 50 + trend * 10))
            p_gelis = max(0, min(100, 100 - ort * 10))
            p_var = max(0, min(100, 100 - varyans * 5))
            p_jokey = min(jokey_db.get(at["Jokey"], {}).get("kazanma", 10) * 5, 100) if jokey_db.get(at["Jokey"], {}).get("toplam", 0) >= 5 else 50
            p_antr = min(antrenor_db.get(at["Antrenor"], {}).get("kazanma", 10) * 5, 100) if antrenor_db.get(at["Antrenor"], {}).get("toplam", 0) >= 5 else 50
            p_at = min(at_db.get(at["At_Ismi"], {}).get("kazanma", 10) * 5, 100) if at_db.get(at["At_Ismi"], {}).get("toplam", 0) >= 2 else 50
            p_mesafe = (at_mesafe[at["At_Ismi"]][str(row["Mesafe"])]["ilk3"] / max(1, at_mesafe[at["At_Ismi"]][str(row["Mesafe"])]["toplam"]) * 100) if at_mesafe[at["At_Ismi"]][str(row["Mesafe"])]["toplam"] >= 2 else 30
            p_uyum = (jokey_at.get((at["Jokey"], at["At_Ismi"]), {}).get("ilk3", 0) / max(1, jokey_at.get((at["Jokey"], at["At_Ismi"]), {}).get("toplam", 1))) * 100

            toplam = (weights["AGF"] * p_agf + weights["G"] * p_g + weights["FORM"] * form_ort +
                      weights["TREND"] * p_trend + weights["GELIS"] * p_gelis + weights["VARYANS"] * p_var +
                      weights["JOKEY"] * p_jokey + weights["AT"] * p_at + weights["MESAFE"] * p_mesafe)

            ml_prob = 0.0
            if use_ml and ml_model is not None:
                try:
                    ml_row = {
                        "kilo": kv, "ganyan": gv, "agf": agf_sayisal(at.get("AGF", "")),
                        "hp": p(at.get("HP", "0")), "mesafe": p(row["Mesafe"]),
                        "pist_cim": 1 if "Cim" in pist_str else 0,
                        "pist_kum": 1 if "Kum" in pist_str else 0,
                        "pist_sentetik": 1 if "Sentetik" in pist_str else 0,
                        "cins_handikap": 1 if "Handikap" in cins_str else 0,
                        "cins_maiden": 1 if "Maiden" in cins_str else 0,
                        "cins_sartli": 1 if ("Şartlı" in cins_str or "Sartli" in cins_str) else 0,
                        "kilo_avantaji": (max_kilo - kv) / (max_kilo - min_kilo + 0.01) if max_kilo > min_kilo else 0.5,
                        "ganyan_avantaji": (min_ganyan / gv) if gv > 0 else 0,
                        "agf_yuzde": (agf_sayisal(at.get("AGF", "")) / max_agf * 100) if max_agf > 0 else 0,
                        "jokey_kazanma": jokey_db.get(at["Jokey"], {}).get("kazanma", 10.0),
                        "jokey_ilk3": jokey_db.get(at["Jokey"], {}).get("ilk3", 30.0),
                        "jokey_toplam": jokey_db.get(at["Jokey"], {}).get("toplam", 0),
                        "antrenor_kazanma": antrenor_db.get(at["Antrenor"], {}).get("kazanma", 10.0),
                        "antrenor_ilk3": antrenor_db.get(at["Antrenor"], {}).get("ilk3", 30.0),
                        "antrenor_toplam": antrenor_db.get(at["Antrenor"], {}).get("toplam", 0),
                        "at_kazanma": at_db.get(at["At_Ismi"], {}).get("kazanma", 10.0),
                        "at_ilk3": at_db.get(at["At_Ismi"], {}).get("ilk3", 30.0),
                        "at_toplam": at_db.get(at["At_Ismi"], {}).get("toplam", 0),
                        "yaris_at_sayisi": len(k_df)
                    }
                    ml_input = pd.DataFrame([ml_row])[ml_features].fillna(0)
                    ml_prob = ml_model.predict_proba(ml_input)[0, 1] * 100
                    toplam = toplam * 0.7 + ml_prob * 0.3
                except: pass

            agf_val = agf_sayisal(at.get("AGF", ""))
            puanlar.append({
                "Sıra": at["Sira"], "At": at["At_Ismi"], "Jokey": at["Jokey"],
                "Puan": round(toplam, 1), "Ganyan": at["Ganyan"],
                "ml_prob": ml_prob, "agf_val": agf_val
            })

        puanlar.sort(key=lambda x: x["Puan"], reverse=True)

        # -- Akıllı Kupon Stratejisi --
        if len(puanlar) >= 3:
            fark1 = puanlar[0]["Puan"] - puanlar[1]["Puan"]
            fark2 = puanlar[1]["Puan"] - puanlar[2]["Puan"]

            guven_skoru = min(100, max(20, 100 - (fark2 * 5)))
            if fark1 > 25: guven_skoru = 90
            elif fark1 > 15: guven_skoru = 75

            stratejiler = []
            if fark1 > 20:
                stratejiler.append(f"🏆 **Banko:** {puanlar[0]['At']} (çok baskın)")
                stratejiler.append(f"💡 Tavsiye: Tekli #{puanlar[0]['Sıra']} oyna")
            elif fark1 > 10:
                stratejiler.append(f"⭐ **Güçlü Favori:** {puanlar[0]['At']} – {puanlar[1]['At']}")
                stratejiler.append(f"💡 Tavsiye: İkili oyna, banko olarak ilk atı seç")
            else:
                stratejiler.append(f"⚖️ **Dengeli Yarış:** İlk 3 at birbirine yakın")
                stratejiler.append(f"💡 Tavsiye: Üçlü veya 4 atla geniş kupon")

            stratejiler.append(f"📊 En düşük ganyan: {puanlar[0]['Ganyan']}")
            stratejiler.append(f"🛡️ Güven Skoru: %{guven_skoru}")

            with st.container():
                st.markdown("<div class='kupon-box'>", unsafe_allow_html=True)
                for s in stratejiler:
                    st.markdown(s)
                st.markdown("</div>", unsafe_allow_html=True)

        # Madalya kartları
        cols = st.columns(3)
        madalya_renk = ["#FFD700", "#C0C0C0", "#CD7F32"]
        for i in range(3):
            if i < len(puanlar):
                s = puanlar[i]
                with cols[i]:
                    st.markdown(f"<div class='top-card' style='background:{madalya_renk[i]};'>{['🥇','🥈','🥉'][i]} #{s['Sıra']} {s['At'][:20]}<br><small>Puan: {s['Puan']}</small></div>", unsafe_allow_html=True)

        # At detay
        at_secenekleri = [f"#{s['Sıra']} {s['At']}" for s in puanlar]
        secilen_at = st.selectbox("🔍 At detayı", ["Seçiniz"] + at_secenekleri, key=f"detay_{hipodrom}_{k_no}")
        if secilen_at != "Seçiniz":
            at_adi = secilen_at.split(" ", 1)[1] if " " in secilen_at else secilen_at
            detay_listesi = at_gecmis_detay.get(at_adi, [])
            if not detay_listesi:
                for key in at_gecmis_detay:
                    if at_adi in key or key in at_adi:
                        detay_listesi = at_gecmis_detay[key]
                        break
            if detay_listesi:
                st.dataframe(pd.DataFrame(detay_listesi).sort_values("tarih", ascending=False).head(20), use_container_width=True)
            else:
                st.warning("Detaylı geçmiş bulunamadı.")

        st.dataframe(pd.DataFrame(puanlar)[["Sıra","At","Puan","Jokey","Ganyan"]], use_container_width=True)