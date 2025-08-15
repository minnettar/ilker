import streamlit as st
import pandas as pd
import numpy as np
import io, os, re, time, tempfile, datetime
from email.message import EmailMessage
import smtplib

from pydrive2.auth import GoogleAuth
from pydrive2.drive import GoogleDrive

from google.oauth2 import service_account
from googleapiclient.discovery import build

from googleapiclient.http import MediaIoBaseDownload  # kullanılmıyor ama dursun

# ===========================
# ==== GENEL AYARLAR
# ===========================
st.set_page_config(page_title="ŞEKEROĞLU İHRACAT CRM", layout="wide")

# Sabitler (Kullanacağımız Drive klasörleri ve Sheets)
SHEET_ID = "1A_gL11UL6JFAoZrMrg92K8bAegeCn_KzwUyU8AWzE_0"
MUSTERI_SHEET_NAME = "Sayfa1"

LOGO_FILE_ID = "1DCxtSsAeR7Zfk2IQU0UMGmD0uTdNO1B3"
LOGO_LOCAL_NAME = "logo1.png"

FIYAT_TEKLIFI_ID = "1TNjwx-xhmlxNRI3ggCJA7jaCAu9Lt_65"   # Teklif PDF klasörü
EVRAK_KLASOR_ID   = "14FTE1oSeIeJ6Y_7C0oQyZPKC8dK8hr1J"   # Evrak ana klasör

# (Proforma için kullanıcı verdiği klasörler)
PROFORMA_PDF_FOLDER_ID    = "17lPkdYcC4BdowLdCsiWxiq0H_6oVGXLs"
SIPARIS_FORMU_FOLDER_ID   = "1xeTdhOE1Cc6ohJsRzPVlCMMraBIXWO9w"

# ===========================
# ==== KULLANICI GİRİŞİ
# ===========================
USERS = {"export1":"Seker12345!", "admin":"Seker12345!", "Boss":"Seker12345!"}
if "user" not in st.session_state: st.session_state.user = None

def login_screen():
    st.title("ŞEKEROĞLU CRM - Giriş Ekranı")
    u = st.text_input("Kullanıcı Adı")
    p = st.text_input("Şifre", type="password")
    if st.button("Giriş Yap"):
        if u in USERS and p == USERS[u]:
            st.session_state.user = u
            st.success("Giriş başarılı!")
            st.rerun()
        else:
            st.error("Kullanıcı adı veya şifre hatalı.")

if not st.session_state.user:
    login_screen()
    st.stop()

if st.sidebar.button("Çıkış Yap"):
    st.session_state.user = None
    st.rerun()

# ===========================
# ==== REFERANS LİSTELER
# ===========================
ulke_listesi = sorted([
    "Afganistan","Almanya","Amerika Birleşik Devletleri","Andorra","Angola","Antigua ve Barbuda","Arjantin",
    "Arnavutluk","Avustralya","Avusturya","Azerbaycan","Bahamalar","Bahreyn","Bangladeş","Barbados","Belçika",
    "Belize","Benin","Beyaz Rusya","Bhutan","Birleşik Arap Emirlikleri","Birleşik Krallık","Bolivya",
    "Bosna-Hersek","Botsvana","Brezilya","Brunei","Bulgaristan","Burkina Faso","Burundi","Butan",
    "Cezayir","Çad","Çekya","Çin","Danimarka","Doğu Timor","Dominik Cumhuriyeti","Dominika","Ekvador",
    "Ekvator Ginesi","El Salvador","Endonezya","Eritre","Ermenistan","Estonya","Etiyopya","Fas",
    "Fiji","Fildişi Sahili","Filipinler","Filistin","Finlandiya","Fransa","Gabon","Gambia",
    "Gana","Gine","Gine-Bissau","Grenada","Guatemala","Guyana","Güney Afrika","Güney Kore",
    "Güney Sudan","Gürcistan","Haiti","Hindistan","Hırvatistan","Hollanda","Honduras","Hong Kong",
    "Irak","İran","İrlanda","İspanya","İsrail","İsveç","İsviçre","İtalya","İzlanda","Jamaika",
    "Japonya","Kamboçya","Kamerun","Kanada","Karadağ","Katar","Kazakistan","Kenya","Kırgızistan",
    "Kiribati","Kolombiya","Komorlar","Kongo","Kongo Demokratik Cumhuriyeti","Kostarika","Küba",
    "Kuveyt","Kuzey Kore","Kuzey Makedonya","Laos","Lesotho","Letonya","Liberya","Libya",
    "Liechtenstein","Litvanya","Lübnan","Lüksemburg","Macaristan","Madagaskar","Malavi","Maldivler",
    "Malezya","Mali","Malta","Marshall Adaları","Meksika","Mısır","Mikronezya","Moğolistan","Moldova",
    "Monako","Morityus","Mozambik","Myanmar","Namibya","Nauru","Nepal","Nijer","Nijerya",
    "Nikaragua","Norveç","Orta Afrika Cumhuriyeti","Özbekistan","Pakistan","Palau","Panama","Papua Yeni Gine",
    "Paraguay","Peru","Polonya","Portekiz","Romanya","Ruanda","Rusya","Saint Kitts ve Nevis",
    "Saint Lucia","Saint Vincent ve Grenadinler","Samoa","San Marino","Sao Tome ve Principe","Senegal",
    "Seyşeller","Sırbistan","Sierra Leone","Singapur","Slovakya","Slovenya","Solomon Adaları","Somali",
    "Sri Lanka","Sudan","Surinam","Suriye","Suudi Arabistan","Svaziland","Şili","Tacikistan","Tanzanya",
    "Tayland","Tayvan","Togo","Tonga","Trinidad ve Tobago","Tunus","Tuvalu","Türkiye","Türkmenistan",
    "Uganda","Ukrayna","Umman","Uruguay","Ürdün","Vanuatu","Vatikan","Venezuela","Vietnam",
    "Yemen","Yeni Zelanda","Yunanistan","Zambiya","Zimbabve"
]) + ["Diğer"]

temsilci_listesi = ["KEMAL İLKER ÇELİKKALKAN", "HÜSEYİN POLAT", "EFE YILDIRIM", "FERHAT ŞEKEROĞLU"]

# ===========================
# ==== DRIVE
# ===========================
@st.cache_resource
def get_drive():
    gauth = GoogleAuth()
    gauth.LocalWebserverAuth()
    return GoogleDrive(gauth)

drive = get_drive()

# Logo indir (yoksa)
if not os.path.exists(LOGO_LOCAL_NAME):
    try:
        f = drive.CreateFile({'id': LOGO_FILE_ID})
        f.GetContentFile(LOGO_LOCAL_NAME)
    except Exception as e:
        st.warning(f"Logo indirilemedi: {e}")

# Üst başlık
c1, c2 = st.columns([3,7])
with c1:
    if os.path.exists(LOGO_LOCAL_NAME):
        st.image(LOGO_LOCAL_NAME, width=300)
with c2:
    st.markdown("""
    <style>.block-container{padding-top:.2rem!important}</style>
    <div style="display:flex;flex-direction:column;align-items:flex-start;width:100%;margin-bottom:10px;">
      <h1 style="color:#219A41;font-weight:bold;font-size:2.8em;letter-spacing:2px;margin:0;margin-top:-8px;">
        ŞEKEROĞLU İHRACAT CRM
      </h1>
    </div>
    """, unsafe_allow_html=True)

# ===========================
# ==== VERİ YÜKLEME (Lokal temp.xlsx)
# ===========================
def _empty_frames():
    return (
        pd.DataFrame(columns=["Müşteri Adı","Telefon","E-posta","Adres","Ülke","Satış Temsilcisi","Kategori","Durum","Vade (Gün)","Ödeme Şekli","Para Birimi","DT Seçimi"]),
        pd.DataFrame(columns=["Müşteri Adı","Tarih","Tip","Açıklama"]),
        pd.DataFrame(columns=["Müşteri Adı","Tarih","Teklif No","Tutar","Ürün/Hizmet","Açıklama","Durum","PDF"]),
        pd.DataFrame(columns=["Müşteri Adı","Tarih","Proforma No","Tutar","Açıklama","Durum","PDF","Sipariş Formu","Vade (gün)","Sevk Durumu","Termin Tarihi","Sevk Tarihi","Ulaşma Tarihi","Ülke","Satış Temsilcisi","Ödeme Şekli"]),
        pd.DataFrame(columns=["Müşteri Adı","Proforma No","Fatura No","Fatura Tarihi","Vade (gün)","Vade Tarihi","Tutar","Ülke","Satış Temsilcisi","Ödeme Şekli",
                              "Commercial Invoice","Sağlık Sertifikası","Packing List","Konşimento","İhracat Beyannamesi","Fatura PDF","Sipariş Formu","Yük Resimleri","EK Belgeler","Ödendi","Ödeme Kanıtı"]),
        pd.DataFrame(columns=["Müşteri Adı","Proforma No","ETA Tarihi","Açıklama"]),
        pd.DataFrame(columns=["Fuar Adı","Müşteri Adı","Ülke","Telefon","E-mail","Satış Temsilcisi","Açıklamalar","Görüşme Kalitesi","Tarih"])
    )

def load_frames_from_local():
    if os.path.exists("temp.xlsx"):
        try: df_m = pd.read_excel("temp.xlsx", sheet_name="Sayfa1")
        except: df_m = pd.DataFrame()
        try: df_k = pd.read_excel("temp.xlsx", sheet_name="Kayıtlar")
        except: df_k = pd.DataFrame(columns=["Müşteri Adı","Tarih","Tip","Açıklama"])
        try: df_t = pd.read_excel("temp.xlsx", sheet_name="Teklifler")
        except: df_t = pd.DataFrame(columns=["Müşteri Adı","Tarih","Teklif No","Tutar","Ürün/Hizmet","Açıklama","Durum","PDF"])
        try: df_p = pd.read_excel("temp.xlsx", sheet_name="Proformalar")
        except: df_p = pd.DataFrame()
        try: df_e = pd.read_excel("temp.xlsx", sheet_name="Evraklar")
        except: df_e = pd.DataFrame()
        try: df_eta = pd.read_excel("temp.xlsx", sheet_name="ETA")
        except: df_eta = pd.DataFrame(columns=["Müşteri Adı","Proforma No","ETA Tarihi","Açıklama"])
        try: df_fuar = pd.read_excel("temp.xlsx", sheet_name="FuarMusteri")
        except: df_fuar = pd.DataFrame(columns=["Fuar Adı","Müşteri Adı","Ülke","Telefon","E-mail","Satış Temsilcisi","Açıklamalar","Görüşme Kalitesi","Tarih"])

        # eksik kolonları ekle
        if df_m.empty:
            df_m, df_k, df_t, df_p, df_e, df_eta, df_fuar = _empty_frames()
        else:
            for col in ["Para Birimi","DT Seçimi"]:
                if col not in df_m.columns: df_m[col] = ""
            if df_p.empty:
                df_p = pd.DataFrame(columns=["Müşteri Adı","Tarih","Proforma No","Tutar","Açıklama","Durum","PDF","Sipariş Formu","Vade (gün)","Sevk Durumu","Termin Tarihi","Sevk Tarihi","Ulaşma Tarihi","Ülke","Satış Temsilcisi","Ödeme Şekli"])
            for c in ["Ülke","Satış Temsilcisi","Ödeme Şekli","Sevk Durumu","Termin Tarihi","Sevk Tarihi","Ulaşma Tarihi","Vade (gün)"]:
                if c not in df_p.columns: df_p[c] = ""
            if df_e.empty:
                df_e = pd.DataFrame(columns=["Müşteri Adı","Proforma No","Fatura No","Fatura Tarihi","Vade (gün)","Vade Tarihi","Tutar","Ülke","Satış Temsilcisi","Ödeme Şekli",
                                             "Commercial Invoice","Sağlık Sertifikası","Packing List","Konşimento","İhracat Beyannamesi","Fatura PDF","Sipariş Formu","Yük Resimleri","EK Belgeler","Ödendi","Ödeme Kanıtı"])
            for c in ["Ödendi","Ödeme Kanıtı"]:
                if c not in df_e.columns: df_e[c] = False if c=="Ödendi" else ""
        return df_m, df_k, df_t, df_p, df_e, df_eta, df_fuar
    else:
        return _empty_frames()

df_musteri, df_kayit, df_teklif, df_proforma, df_evrak, df_eta, df_fuar_musteri = load_frames_from_local()

def update_excel():
    """Lokal temp.xlsx günceller (Drive'a yükleme YOK)."""
    buffer = io.BytesIO()
    with pd.ExcelWriter(buffer, engine='openpyxl') as w:
        df_musteri.to_excel(w, sheet_name="Sayfa1", index=False)
        df_kayit.to_excel(w, sheet_name="Kayıtlar", index=False)
        df_teklif.to_excel(w, sheet_name="Teklifler", index=False)
        df_proforma.to_excel(w, sheet_name="Proformalar", index=False)
        df_evrak.to_excel(w, sheet_name="Evraklar", index=False)
        df_eta.to_excel(w, sheet_name="ETA", index=False)
        df_fuar_musteri.to_excel(w, sheet_name="FuarMusteri", index=False)
    buffer.seek(0)
    with open("temp.xlsx", "wb") as f:
        f.write(buffer.read())

# ===========================
# ==== GOOGLE SHEETS (MÜŞTERİ) SENKRON
# ===========================
def _build_sheets():
    creds = service_account.Credentials.from_service_account_info(
        st.secrets["gcp_service_account"],
        scopes=["https://www.googleapis.com/auth/spreadsheets"]
    )
    return build("sheets", "v4", credentials=creds, cache_discovery=False)

def _df_to_values(df: pd.DataFrame):
    def _cell(v):
        if pd.isna(v): return ""
        if isinstance(v, (pd.Timestamp, datetime.date, datetime.datetime)):
            try: return pd.to_datetime(v).date().isoformat()
            except: return str(v)
        if isinstance(v, (np.bool_, bool)): return bool(v)
        return v
    header = list(df.columns)
    rows = df.applymap(_cell).values.tolist()
    return [header] + rows

def write_customers_to_gsheet(df_customers: pd.DataFrame) -> bool:
    try:
        if df_customers is None or df_customers.empty:
            st.warning("Müşteri tablosu boş, Sheets’e yazılacak bir şey yok.")
            return False
        service = _build_sheets()
        sheet = service.spreadsheets()
        # clear
        sheet.values().batchClear(
            spreadsheetId=SHEET_ID,
            body={"ranges":[f"{MUSTERI_SHEET_NAME}!A:ZZ"]}
        ).execute()
        # write
        values = _df_to_values(df_customers)
        sheet.values().update(
            spreadsheetId=SHEET_ID,
            range=f"{MUSTERI_SHEET_NAME}!A1",
            valueInputOption="RAW",
            body={"values": values}
        ).execute()
        st.info(f"{MUSTERI_SHEET_NAME} sayfasına {len(df_customers)} satır yazıldı.")
        return True
    except Exception as e:
        st.error(f"Sheets yazma hatası: {e}")
        return False

def push_customers_throttled():
    now = datetime.datetime.utcnow().timestamp()
    last = st.session_state.get("_last_sheet_write_ts", 0)
    if now - last < 10:  # 10 sn içinde tekrar yazma (429 riski azalt)
        return False
    ok = write_customers_to_gsheet(df_musteri)
    if ok:
        st.session_state["_last_sheet_write_ts"] = now
    return ok

# ===========================
# ==== ŞIK SIDEBAR MENÜ
# ===========================
menuler = [
    ("Özet Ekran","📊"),
    ("Cari Ekleme","🧑‍💼"),
    ("Müşteri Listesi","📒"),
    ("Görüşme / Arama / Ziyaret Kayıtları","☎️"),
    ("Fiyat Teklifleri","💰"),
    ("Proforma Takibi","📄"),
    ("Güncel Sipariş Durumu","🚚"),
    ("Fatura & İhracat Evrakları","📑"),
    ("Vade Takibi","⏰"),
    ("ETA Takibi","🛳️"),
    ("Fuar Müşteri Kayıtları","🎫"),
    ("Medya Çekmecesi","🗂️"),
    ("Satış Performansı","📈"),
]

if st.session_state.user == "Boss":
    allowed_menus = [("Özet Ekran","📊")]
else:
    allowed_menus = menuler

labels = [f"{i} {n}" for (n,i) in allowed_menus]
name_by_label = {f"{i} {n}": n for (n,i) in allowed_menus}
label_by_name = {n: f"{i} {n}" for (n,i) in allowed_menus}

if "menu_state" not in st.session_state:
    st.session_state.menu_state = allowed_menus[0][0]

st.sidebar.markdown("""
<style>
section[data-testid="stSidebar"] { padding-top:.5rem; }
div[data-testid="stSidebar"] .stRadio > div { gap:10px!important; }
div[data-testid="stSidebar"] .stRadio label {
  border-radius:12px; padding:12px 14px; margin-bottom:6px;
  border:1px solid rgba(255,255,255,.12); display:flex; align-items:center;
  transition:transform .06s ease, filter .15s ease;
  box-shadow:0 1px 4px rgba(0,0,0,.08);
}
div[data-testid="stSidebar"] .stRadio label span { font-weight:700; color:#fff; }
div[data-testid="stSidebar"] .stRadio label:hover { filter:brightness(1.08); transform:translateY(-1px); }
div[data-testid="stSidebar"] .stRadio [aria-checked="true"] { outline:2px solid rgba(255,255,255,.25); }
div[data-testid="stSidebar"] .stRadio label:nth-child(1)  { background:linear-gradient(90deg,#1D976C,#93F9B9); }
div[data-testid="stSidebar"] .stRadio label:nth-child(2)  { background:linear-gradient(90deg,#43cea2,#185a9d); }
div[data-testid="stSidebar"] .stRadio label:nth-child(3)  { background:linear-gradient(90deg,#ffb347,#ffcc33); }
div[data-testid="stSidebar"] .stRadio label:nth-child(4)  { background:linear-gradient(90deg,#ff5e62,#ff9966); }
div[data-testid="stSidebar"] .stRadio label:nth-child(5)  { background:linear-gradient(90deg,#8e54e9,#4776e6); }
div[data-testid="stSidebar"] .stRadio label:nth-child(6)  { background:linear-gradient(90deg,#11998e,#38ef7d); }
div[data-testid="stSidebar"] .stRadio label:nth-child(7)  { background:linear-gradient(90deg,#f7971e,#ffd200); }
div[data-testid="stSidebar"] .stRadio label:nth-child(8)  { background:linear-gradient(90deg,#f953c6,#b91d73); }
div[data-testid="stSidebar"] .stRadio label:nth-child(9)  { background:linear-gradient(90deg,#43e97b,#38f9d7); }
div[data-testid="stSidebar"] .stRadio label:nth-child(10) { background:linear-gradient(90deg,#f857a6,#ff5858); }
div[data-testid="stSidebar"] .stRadio label:nth-child(11) { background:linear-gradient(90deg,#8e54e9,#bd4de6); }
div[data-testid="stSidebar"] .stRadio label:nth-child(12) { background:linear-gradient(90deg,#4b79a1,#283e51); }
div[data-testid="stSidebar"] .stRadio label:nth-child(13) { background:linear-gradient(90deg,#2b5876,#4e4376); }
</style>
""", unsafe_allow_html=True)

def _on_menu_change():
    sel_label = st.session_state.menu_radio_label
    st.session_state.menu_state = name_by_label.get(sel_label, allowed_menus[0][0])

current_label = label_by_name.get(st.session_state.menu_state, labels[0])
current_index = labels.index(current_label) if current_label in labels else 0
st.sidebar.radio("Menü", labels, index=current_index, label_visibility="collapsed",
                 key="menu_radio_label", on_change=_on_menu_change)

menu = st.session_state.menu_state

# Sidebar: manuel senkron
with st.sidebar.expander("🔄 Sheets Senkron"):
    if st.button("Müşterileri Sheets’e Yaz"):
        push_customers_throttled()

# ===========================
# ==== E-POSTA (Cari açılış)
# ===========================
def yeni_cari_txt_olustur(cari_dict, file_path="yeni_cari.txt"):
    with open(file_path, "w", encoding="utf-8") as f:
        f.write(
            f"Müşteri Adı: {cari_dict.get('Müşteri Adı','')}\n"
            f"Telefon: {cari_dict.get('Telefon','')}\n"
            f"E-posta: {cari_dict.get('E-posta','')}\n"
            f"Adres: {cari_dict.get('Adres','')}\n"
            f"Ülke: {cari_dict.get('Ülke','')}\n"
            f"Satış Temsilcisi: {cari_dict.get('Satış Temsilcisi','')}\n"
            f"Kategori: {cari_dict.get('Kategori','')}\n"
            f"Durum: {cari_dict.get('Durum','')}\n"
            f"Vade (Gün): {cari_dict.get('Vade (Gün)','')}\n"
            f"Ödeme Şekli: {cari_dict.get('Ödeme Şekli','')}\n"
            f"Para Birimi: {cari_dict.get('Para Birimi','')}\n"
            f"DT Seçimi: {cari_dict.get('DT Seçimi','')}\n"
        )

def send_email_with_txt(to_email, subject, body, file_path):
    from_email = "todo@sekeroglugroup.com"
    password   = "vbgvforwwbcpzhxf"
    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = from_email
    msg["To"] = ", ".join(to_email)
    msg.set_content(body)
    with open(file_path, "rb") as f:
        msg.add_attachment(f.read(), maintype="text", subtype="plain", filename="yeni_cari.txt")
    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as smtp:
        smtp.login(from_email, password)
        smtp.send_message(msg)

# ===========================
# ==== MENÜLER
# ===========================

# --- ÖZET EKRAN ---
if menu == "Özet Ekran":
    st.markdown("<h2 style='color:#219A41; font-weight:bold;'>📊 Özet Ekran</h2>", unsafe_allow_html=True)
    def smart_to_num(x):
        if pd.isna(x): return 0.0
        s = str(x).strip()
        for sym in ["USD","$","€","EUR","₺","TL","tl","Tl"]: s = s.replace(sym,"")
        s = s.replace("\u00A0","").replace(" ","")
        try: return float(s)
        except: pass
        if "," in s:
            try: return float(s.replace(".","").replace(",","."))
            except: pass
        return 0.0

    toplam_fatura_tutar = 0.0
    if "Tutar" in df_evrak.columns and not df_evrak.empty:
        _ev = df_evrak.copy()
        _ev["Tutar_num"] = _ev["Tutar"].apply(smart_to_num).fillna(0.0)
        toplam_fatura_tutar = float(_ev["Tutar_num"].sum())
    st.markdown(f"<div style='font-size:1.4em;color:#B22222;font-weight:bold;'>💰 Toplam Fatura Tutarı: {toplam_fatura_tutar:,.2f} USD</div>", unsafe_allow_html=True)

    st.markdown("---")
    for col in ["Vade Tarihi","Ödendi","Tutar"]:
        if col not in df_evrak.columns: df_evrak[col] = "" if col!="Ödendi" else False
    v = df_evrak.copy()
    v["Ödendi"] = v["Ödendi"].fillna(False).astype(bool)
    v["Vade Tarihi"] = pd.to_datetime(v["Vade Tarihi"], errors="coerce")
    v["Tutar_num"] = v["Tutar"].apply(smart_to_num).fillna(0.0)
    today_norm = pd.Timestamp.today().normalize()
    od_me = ~v["Ödendi"]
    m_gelmemis = (v["Vade Tarihi"] > today_norm) & od_me
    m_bugun    = (v["Vade Tarihi"].dt.date == today_norm.date()) & od_me
    m_gecikmis = (v["Vade Tarihi"] < today_norm) & od_me
    c1,c2,c3 = st.columns(3)
    c1.metric("📅 Vadesi Gelmemiş", f"{float(v.loc[m_gelmemis,'Tutar_num'].sum()):,.2f} USD", f"{int(m_gelmemis.sum())} Fatura")
    c2.metric("⚠️ Bugün Vadesi Dolan", f"{float(v.loc[m_bugun,'Tutar_num'].sum()):,.2f} USD", f"{int(m_bugun.sum())} Fatura")
    c3.metric("⛔ Gecikmiş", f"{float(v.loc[m_gecikmis,'Tutar_num'].sum()):,.2f} USD", f"{int(m_gecikmis.sum())} Fatura")

    acik = v[v["Vade Tarihi"].notna() & (~v["Ödendi"])].copy()
    if not acik.empty:
        acik["Kalan Gün"] = (acik["Vade Tarihi"] - today_norm).dt.days
        st.markdown("#### 💸 Açık Vade Kayıtları")
        cols = ["Müşteri Adı","Ülke","Fatura No","Vade Tarihi","Tutar","Kalan Gün"]
        cols = [c for c in cols if c in acik.columns]
        if "Vade Tarihi" in cols:
            acik["Vade Tarihi"] = pd.to_datetime(acik["Vade Tarihi"], errors="coerce").dt.strftime("%d/%m/%Y")
        st.dataframe(acik[cols].sort_values("Kalan Gün"), use_container_width=True)
    else:
        st.info("Açık vade kaydı yok.")

    st.markdown("---")
    st.markdown("### 💰 Bekleyen Teklifler")
    bek_teklif = df_teklif[df_teklif.get("Durum","") == "Açık"] if len(df_teklif)>0 else pd.DataFrame()
    try: toplam_teklif = pd.to_numeric(bek_teklif["Tutar"], errors="coerce").sum()
    except: toplam_teklif = 0
    st.markdown(f"<div style='font-size:1.1em;color:#11998e;font-weight:bold;'>Toplam: {toplam_teklif:,.2f} $</div>", unsafe_allow_html=True)
    if bek_teklif.empty: st.info("Bekleyen teklif yok.")
    else:
        st.dataframe(bek_teklif[["Müşteri Adı","Tarih","Teklif No","Tutar","Ürün/Hizmet","Açıklama"]], use_container_width=True)

    st.markdown("### 📄 Bekleyen Proformalar")
    bek_prof = df_proforma[df_proforma.get("Durum","") == "Beklemede"] if len(df_proforma)>0 else pd.DataFrame()
    try: toplam_p = pd.to_numeric(bek_prof["Tutar"], errors="coerce").sum()
    except: toplam_p = 0
    st.markdown(f"<div style='font-size:1.1em;color:#f7971e;font-weight:bold;'>Toplam: {toplam_p:,.2f} $</div>", unsafe_allow_html=True)
    if bek_prof.empty: st.info("Bekleyen proforma yok.")
    else:
        st.dataframe(bek_prof[["Müşteri Adı","Proforma No","Tarih","Tutar","Vade (gün)","Açıklama"]], use_container_width=True)

    st.markdown("### 🚚 Siparişe Dönüşen (Sevk Bekleyen) Siparişler")
    for c in ["Sevk Durumu","Ülke","Termin Tarihi"]:
        if c not in df_proforma.columns: df_proforma[c]=""
    sevk_bekleyen = df_proforma[(df_proforma.get("Durum","")=="Siparişe Dönüştü") & (~df_proforma["Sevk Durumu"].isin(["Sevkedildi","Ulaşıldı"]))] if len(df_proforma)>0 else pd.DataFrame()
    try: toplam_s = pd.to_numeric(sevk_bekleyen["Tutar"], errors="coerce").sum()
    except: toplam_s = 0
    st.markdown(f"<div style='font-size:1.1em;color:#185a9d;font-weight:bold;'>Toplam: {toplam_s:,.2f} $</div>", unsafe_allow_html=True)
    if sevk_bekleyen.empty: st.info("Sevk bekleyen sipariş yok.")
    else:
        disp = sevk_bekleyen.copy()
        disp["Tarih"] = pd.to_datetime(disp["Tarih"], errors="coerce").dt.strftime("%d/%m/%Y")
        disp["Termin Tarihi"] = pd.to_datetime(disp["Termin Tarihi"], errors="coerce").dt.strftime("%d/%m/%Y")
        st.dataframe(disp[["Müşteri Adı","Ülke","Proforma No","Tarih","Termin Tarihi","Tutar","Vade (gün)","Açıklama"]], use_container_width=True)

    st.markdown("### ⏳ Yolda Olan (ETA Takibi) Siparişler")
    eta_yolda = df_proforma[(df_proforma.get("Sevk Durumu","")== "Sevkedildi")] if len(df_proforma)>0 else pd.DataFrame()
    try: toplam_eta = pd.to_numeric(eta_yolda["Tutar"], errors="coerce").sum()
    except: toplam_eta = 0
    st.markdown(f"<div style='font-size:1.1em;color:#c471f5;font-weight:bold;'>Toplam: {toplam_eta:,.2f} $</div>", unsafe_allow_html=True)
    if eta_yolda.empty: st.info("Yolda olan (sevk edilmiş) sipariş yok.")
    else:
        eta_disp = eta_yolda.copy()
        eta_disp["Tarih"] = pd.to_datetime(eta_disp["Tarih"], errors="coerce").dt.strftime("%d/%m/%Y")
        st.dataframe(eta_disp[["Müşteri Adı","Ülke","Proforma No","Tarih","Tutar","Vade (gün)","Açıklama"]], use_container_width=True)

    st.markdown("### ✅ Son Teslim Edilen 5 Sipariş")
    if "Sevk Durumu" in df_proforma.columns:
        teslim = df_proforma[df_proforma["Sevk Durumu"]=="Ulaşıldı"]
        if not teslim.empty:
            teslim = teslim.sort_values(by="Tarih", ascending=False).head(5).copy()
            teslim["Tarih"] = pd.to_datetime(teslim["Tarih"], errors="coerce").dt.strftime("%d/%m/%Y")
            st.dataframe(teslim[["Müşteri Adı","Ülke","Proforma No","Tarih","Tutar","Vade (gün)","Açıklama"]], use_container_width=True)
        else:
            st.info("Teslim edilmiş sipariş yok.")
    st.markdown("<hr>", unsafe_allow_html=True)
    st.info("Detaylar için soldaki menülerden ilgili bölümlere geçebilirsiniz.")

# --- CARİ EKLEME ---
elif menu == "Cari Ekleme":
    st.markdown("<h2 style='color:#219A41; font-weight:bold;'>Yeni Müşteri Ekle</h2>", unsafe_allow_html=True)
    with st.form("add_customer"):
        name = st.text_input("Müşteri Adı")
        phone = st.text_input("Telefon")
        email = st.text_input("E-posta")
        address = st.text_area("Adres")
        ulke = st.selectbox("Ülke", ulke_listesi)
        temsilci = st.selectbox("Satış Temsilcisi", temsilci_listesi)
        kategori = st.selectbox("Kategori", ["Avrupa bayi","bayi","müşteri","yeni müşteri"])
        aktif_pasif = st.selectbox("Durum", ["Aktif","Pasif"])
        vade_gun = st.number_input("Vade (Gün Sayısı)", min_value=0, max_value=365, value=0, step=1)
        odeme_sekli = st.selectbox("Ödeme Şekli", ["Peşin","Mal Mukabili","Vesaik Mukabili","Akreditif","Diğer"])
        para_birimi = st.selectbox("Para Birimi", ["EURO","USD","TL","RUBLE"])
        dt_secim    = st.selectbox("DT Seçin", ["DT-1","DT-2","DT-3","DT-4"])
        submitted = st.form_submit_button("Kaydet")

        if submitted:
            if not name.strip():
                st.error("Müşteri adı boş olamaz!")
            else:
                new_row = {
                    "Müşteri Adı": name, "Telefon": phone, "E-posta": email, "Adres": address,
                    "Ülke": ulke, "Satış Temsilcisi": temsilci, "Kategori": kategori, "Durum": aktif_pasif,
                    "Vade (Gün)": vade_gun, "Ödeme Şekli": odeme_sekli, "Para Birimi": para_birimi, "DT Seçimi": dt_secim
                }
                df_musteri = pd.concat([df_musteri, pd.DataFrame([new_row])], ignore_index=True)
                update_excel()
                # e-posta
                yeni_cari_txt_olustur(new_row)
                try:
                    send_email_with_txt(
                        to_email=["muhasebe@sekeroglugroup.com","h.boy@sekeroglugroup.com"],
                        subject="Yeni Cari Açılışı",
                        body="Muhasebe için yeni cari açılışı ekte gönderilmiştir.",
                        file_path="yeni_cari.txt"
                    )
                    st.success("Müşteri eklendi ve e-posta gönderildi!")
                except Exception as e:
                    st.warning(f"Müşteri eklendi ama e-posta gönderilemedi: {e}")
                # Sheets
                push_customers_throttled()
                st.rerun()

# --- MÜŞTERİ LİSTESİ ---
elif menu == "Müşteri Listesi":
    st.markdown("<h2 style='color:#219A41; font-weight:bold;'>Müşteri Listesi</h2>", unsafe_allow_html=True)
    for c in ["Vade (Gün)","Ülke","Satış Temsilcisi","Ödeme Şekli"]:
        if c not in df_musteri.columns: df_musteri[c]=""

    if not df_musteri.empty:
        aktif_df = df_musteri[df_musteri["Durum"]=="Aktif"].sort_values("Müşteri Adı").reset_index(drop=True)
        aktif_df = aktif_df.replace({np.nan:"Eksik bilgi, lütfen tamamlayın","":"Eksik bilgi, lütfen tamamlayın"})
        if aktif_df.shape[0]==0:
            st.markdown("<div style='color:#b00020;font-weight:bold;font-size:1.2em;'>Aktif müşteri kaydı yok.</div>", unsafe_allow_html=True)
        else:
            st.dataframe(aktif_df, use_container_width=True)

        st.markdown("<h4 style='margin-top:32px;'>Müşteri Düzenle</h4>", unsafe_allow_html=True)
        df_m_sorted = df_musteri.sort_values("Müşteri Adı").reset_index(drop=True)
        musteri_options = df_m_sorted.index.tolist()
        sec_index = st.selectbox("Düzenlenecek Müşteriyi Seçin", options=musteri_options,
                                 format_func=lambda i: f"{df_m_sorted.at[i,'Müşteri Adı']} ({df_m_sorted.at[i,'Kategori']})")

        with st.form("edit_existing_customer"):
            name = st.text_input("Müşteri Adı", value=df_m_sorted.at[sec_index,"Müşteri Adı"])
            phone = st.text_input("Telefon", value=df_m_sorted.at[sec_index,"Telefon"])
            email = st.text_input("E-posta", value=df_m_sorted.at[sec_index,"E-posta"])
            address = st.text_area("Adres", value=df_m_sorted.at[sec_index,"Adres"])
            ulke = st.selectbox("Ülke", ulke_listesi,
                                index=ulke_listesi.index(df_m_sorted.at[sec_index,"Ülke"]) if df_m_sorted.at[sec_index,"Ülke"] in ulke_listesi else 0)
            temsilci = st.selectbox("Satış Temsilcisi", temsilci_listesi,
                                    index=temsilci_listesi.index(df_m_sorted.at[sec_index,"Satış Temsilcisi"]) if df_m_sorted.at[sec_index,"Satış Temsilcisi"] in temsilci_listesi else 0)
            kategoriler = sorted(["Avrupa bayi","bayi","müşteri","yeni müşteri"])
            kategori = st.selectbox("Kategori", kategoriler,
                                    index=kategoriler.index(df_m_sorted.at[sec_index,"Kategori"]) if df_m_sorted.at[sec_index,"Kategori"] in kategoriler else 0)
            aktif_pasif = st.selectbox("Durum", ["Aktif","Pasif"], index=0 if df_m_sorted.at[sec_index,"Durum"]=="Aktif" else 1)
            vade = st.text_input("Vade (Gün)", value=str(df_m_sorted.at[sec_index,"Vade (Gün)"]) if "Vade (Gün)" in df_m_sorted.columns else "")
            odeme_sekli = st.selectbox("Ödeme Şekli", ["Peşin","Mal Mukabili","Vesaik Mukabili","Akreditif","Diğer"],
                                       index=["Peşin","Mal Mukabili","Vesaik Mukabili","Akreditif","Diğer"].index(df_m_sorted.at[sec_index,"Ödeme Şekli"]) if df_m_sorted.at[sec_index,"Ödeme Şekli"] in ["Peşin","Mal Mukabili","Vesaik Mukabili","Akreditif","Diğer"] else 0)
            guncelle = st.form_submit_button("Güncelle")

            if guncelle:
                flt = (df_musteri["Müşteri Adı"] == df_m_sorted.at[sec_index,"Müşteri Adı"])
                if flt.any():
                    orj_idx = df_musteri[flt].index[0]
                    df_musteri.at[orj_idx,"Müşteri Adı"] = name
                    df_musteri.at[orj_idx,"Telefon"] = phone
                    df_musteri.at[orj_idx,"E-posta"] = email
                    df_musteri.at[orj_idx,"Adres"] = address
                    df_musteri.at[orj_idx,"Ülke"] = ulke
                    df_musteri.at[orj_idx,"Satış Temsilcisi"] = temsilci
                    df_musteri.at[orj_idx,"Kategori"] = kategori
                    df_musteri.at[orj_idx,"Durum"] = aktif_pasif
                    df_musteri.at[orj_idx,"Vade (Gün)"] = vade
                    df_musteri.at[orj_idx,"Ödeme Şekli"] = odeme_sekli
                    update_excel()
                    push_customers_throttled()
                    st.success("Müşteri bilgisi güncellendi!")
                    st.rerun()
                else:
                    st.warning("Beklenmeyen hata: Kayıt bulunamadı.")

        st.markdown("<h4 style='margin-top:32px;'>Müşteri Sil</h4>", unsafe_allow_html=True)
        if st.button("Seçili Müşteriyi Sil"):
            flt = (df_musteri["Müşteri Adı"] == df_m_sorted.at[sec_index,"Müşteri Adı"])
            if flt.any():
                orj_idx = df_musteri[flt].index[0]
                df_musteri = df_musteri.drop(orj_idx).reset_index(drop=True)
                update_excel()
                push_customers_throttled()
                st.success("Müşteri kaydı silindi!")
                st.rerun()
            else:
                st.warning("Beklenmeyen hata: Silinecek kayıt bulunamadı.")
    else:
        st.markdown("<div style='color:#b00020;font-weight:bold;font-size:1.2em;'>Henüz müşteri kaydı yok.</div>", unsafe_allow_html=True)

# --- GÖRÜŞME / ARAMA / ZİYARET ---
elif menu == "Görüşme / Arama / Ziyaret Kayıtları":
    st.markdown("<h2 style='color:#219A41; font-weight:bold;'>Görüşme / Arama / Ziyaret Kayıtları</h2>", unsafe_allow_html=True)
    musteri_listesi = [m for m in df_musteri["Müşteri Adı"].dropna().unique() if isinstance(m,str) and m.strip()!=""]
    musteri_options = [""] + sorted(musteri_listesi)

    st.subheader("Kayıt Ekranı")
    secim = st.radio("Lütfen işlem seçin:", ["Yeni Kayıt","Eski Kayıt","Tarih Aralığı ile Kayıtlar"])

    if secim == "Yeni Kayıt":
        with st.form("add_kayit"):
            musteri_sec = st.selectbox("Müşteri Seç", musteri_options, index=0)
            tarih = st.date_input("Tarih", value=datetime.date.today(), format="DD/MM/YYYY")
            tip = st.selectbox("Tip", ["Arama","Görüşme","Ziyaret"])
            aciklama = st.text_area("Açıklama")
            if st.form_submit_button("Kaydet"):
                if not musteri_sec:
                    st.error("Lütfen bir müşteri seçiniz.")
                else:
                    new_row = {"Müşteri Adı":musteri_sec,"Tarih":tarih,"Tip":tip,"Açıklama":aciklama}
                    df_kayit = pd.concat([df_kayit, pd.DataFrame([new_row])], ignore_index=True)
                    update_excel()
                    st.success("Kayıt eklendi!")
                    st.rerun()

    elif secim == "Eski Kayıt":
        musteri_sec = st.selectbox("Müşteri Seç", musteri_options, index=0, key="eski_musteri")
        if musteri_sec:
            mk = df_kayit[df_kayit["Müşteri Adı"]==musteri_sec].sort_values("Tarih", ascending=False)
            if not mk.empty:
                tg = mk.copy()
                if "Tarih" in tg.columns:
                    tg["Tarih"] = pd.to_datetime(tg["Tarih"], errors="coerce").dt.strftime('%d/%m/%Y')
                st.dataframe(tg, use_container_width=True)
            else:
                st.info("Seçili müşteri için kayıt yok.")
        else:
            st.info("Lütfen müşteri seçin.")

    else:
        col1,col2 = st.columns(2)
        with col1:
            bas = st.date_input("Başlangıç Tarihi", value=datetime.date.today()-datetime.timedelta(days=7), format="DD/MM/YYYY")
        with col2:
            bit = st.date_input("Bitiş Tarihi", value=datetime.date.today(), format="DD/MM/YYYY")
        tarih_arasi = df_kayit[
            (pd.to_datetime(df_kayit["Tarih"], errors="coerce") >= pd.to_datetime(bas)) &
            (pd.to_datetime(df_kayit["Tarih"], errors="coerce") <= pd.to_datetime(bit))
        ]
        if not tarih_arasi.empty:
            tg = tarih_arasi.copy()
            if "Tarih" in tg.columns:
                tg["Tarih"] = pd.to_datetime(tg["Tarih"], errors="coerce").dt.strftime('%d/%m/%Y')
            st.dataframe(tg.sort_values("Tarih", ascending=False), use_container_width=True)
        else:
            st.info("Bu tarihler arasında kayıt yok.")

# --- FİYAT TEKLİFLERİ ---
elif menu == "Fiyat Teklifleri":
    st.markdown("<h2 style='color:#219A41; font-weight:bold;'>Fiyat Teklifleri</h2>", unsafe_allow_html=True)

    def otomatik_teklif_no():
        if df_teklif.empty or "Teklif No" not in df_teklif.columns:
            return "TKF-0001"
        mevcut = pd.to_numeric(df_teklif["Teklif No"].astype(str).str.extract(r'(\d+)$')[0], errors='coerce').dropna().astype(int)
        if mevcut.empty:
            return "TKF-0001"
        return f"TKF-{(max(mevcut)+1):04d}"

    def güvenli_sil(path, tekrar=5, bekle=1):
        for _ in range(tekrar):
            try:
                os.remove(path)
                return True
            except PermissionError:
                time.sleep(bekle)
        return False

    st.subheader("Açık Pozisyondaki Teklifler")
    teklif_goster = df_teklif.copy()
    if not teklif_goster.empty and "Tarih" in teklif_goster.columns:
        teklif_goster["Tarih"] = pd.to_datetime(teklif_goster["Tarih"]).dt.strftime("%d/%m/%Y")
    acik_teklifler = teklif_goster[teklif_goster["Durum"]=="Açık"].sort_values(by=["Müşteri Adı","Teklif No"])
    try:
        toplam_teklif = pd.to_numeric(acik_teklifler["Tutar"], errors="coerce").sum()
    except:
        toplam_teklif = 0
    st.markdown(f"<div style='font-size:1.1em;color:#11998e;font-weight:bold;'>Toplam: {toplam_teklif:,.2f} $ | Toplam Açık Teklif: {len(acik_teklifler)} adet</div>", unsafe_allow_html=True)
    st.dataframe(acik_teklifler[["Müşteri Adı","Tarih","Teklif No","Tutar","Ürün/Hizmet","Açıklama"]], use_container_width=True)

    st.markdown("##### Lütfen bir işlem seçin")
    c1,c2 = st.columns(2)
    with c1: yeni_teklif_buton = st.button("Yeni Teklif")
    with c2: eski_teklif_buton = st.button("Eski Teklif")

    if "teklif_view" not in st.session_state:
        st.session_state['teklif_view'] = None
    if yeni_teklif_buton:
        st.session_state['teklif_view']="yeni"
    if eski_teklif_buton:
        st.session_state['teklif_view']="eski"

    if st.session_state['teklif_view']=="yeni":
        musteri_list = [""] + sorted(df_musteri["Müşteri Adı"].dropna().unique().tolist())
        st.subheader("Yeni Teklif Ekle")
        with st.form("add_teklif"):
            musteri_sec = st.selectbox("Müşteri Seç", musteri_list, key="yeni_teklif_musteri")
            tarih = st.date_input("Tarih", value=datetime.date.today(), format="DD/MM/YYYY")
            teklif_no = st.text_input("Teklif No", value=otomatik_teklif_no())
            tutar = st.text_input("Tutar ($)")
            urun = st.text_input("Ürün/Hizmet")
            aciklama = st.text_area("Açıklama")
            durum = st.selectbox("Durum", ["Açık","Sonuçlandı","Beklemede"])
            pdf_file = st.file_uploader("Teklif PDF", type="pdf")
            if st.form_submit_button("Kaydet"):
                if not teklif_no.strip():
                    st.error("Teklif No boş olamaz!")
                elif not musteri_sec:
                    st.error("Lütfen müşteri seçiniz!")
                else:
                    pdf_link = ""
                    if pdf_file:
                        temiz_m = "".join(x if x.isalnum() else "_" for x in str(musteri_sec))
                        temiz_t = str(tarih).replace("-","")
                        pdf_filename = f"{temiz_m}__{temiz_t}__{teklif_no}.pdf"
                        temp_path = os.path.join(".", pdf_filename)
                        with open(temp_path, "wb") as f:
                            f.write(pdf_file.read())
                        gfile = drive.CreateFile({'title': pdf_filename, 'parents': [{'id': FIYAT_TEKLIFI_ID}]})
                        gfile.SetContentFile(temp_path)
                        gfile.Upload(param={'supportsAllDrives': True})
                        pdf_link = f"https://drive.google.com/file/d/{gfile['id']}/view?usp=sharing"
                        güvenli_sil(temp_path)
                    new_row = {
                        "Müşteri Adı":musteri_sec,"Tarih":tarih,"Teklif No":teklif_no,"Tutar":tutar,
                        "Ürün/Hizmet":urun,"Açıklama":aciklama,"Durum":durum,"PDF":pdf_link
                    }
                    df_teklif = pd.concat([df_teklif, pd.DataFrame([new_row])], ignore_index=True)
                    update_excel()
                    st.success("Teklif eklendi!")
                    st.session_state['teklif_view']=None
                    st.rerun()

    if st.session_state['teklif_view']=="eski":
        st.subheader("Eski Teklifler")
        musteriler = [""] + sorted(df_teklif["Müşteri Adı"].dropna().unique().tolist())
        sec_m = st.selectbox("Müşteri Seçiniz", musteriler, key="eski_teklif_musteri_sec")
        if sec_m:
            tler = df_teklif[df_teklif["Müşteri Adı"]==sec_m].sort_values(by="Tarih", ascending=False)
            if tler.empty:
                st.info("Bu müşteriye ait teklif yok.")
            else:
                teklif_index = st.selectbox("Teklif Seçiniz", tler.index,
                                            format_func=lambda i: f"{tler.at[i,'Teklif No']} | {tler.at[i,'Tarih']}")
                secilen = tler.loc[teklif_index]
                if secilen.get("PDF",""):
                    st.markdown(f"**Teklif PDF:** [{secilen['Teklif No']}]({secilen['PDF']})", unsafe_allow_html=True)
                st.write("**Teklif Detayları:**")
                st.table({
                    "Müşteri Adı":[secilen["Müşteri Adı"]],
                    "Tarih":[secilen["Tarih"]],
                    "Teklif No":[secilen["Teklif No"]],
                    "Tutar":[secilen["Tutar"]],
                    "Ürün/Hizmet":[secilen["Ürün/Hizmet"]],
                    "Açıklama":[secilen["Açıklama"]],
                    "Durum":[secilen["Durum"]],
                })

# --- PROFORMA TAKİBİ ---
elif menu == "Proforma Takibi":
    st.markdown("<h2 style='color:#219A41; font-weight:bold;'>Proforma Takibi</h2>", unsafe_allow_html=True)
    for col in ["Vade (gün)","Sipariş Formu","Durum","PDF","Sevk Durumu","Ülke","Satış Temsilcisi","Ödeme Şekli"]:
        if col not in df_proforma.columns:
            df_proforma[col]=""

    beklemede = df_proforma[df_proforma["Durum"]=="Beklemede"]
    if not beklemede.empty:
        st.subheader("Bekleyen Proformalar")
        st.dataframe(beklemede[["Müşteri Adı","Proforma No","Tarih","Tutar","Durum","Vade (gün)","Sevk Durumu"]], use_container_width=True)

    musteri_list = sorted([x for x in df_musteri["Müşteri Adı"].dropna().unique() if isinstance(x,str) and x.strip()!=""]) if not df_musteri.empty else []
    musteri_sec = st.selectbox("Müşteri Seç", [""]+musteri_list)

    if musteri_sec:
        st.write("Proforma işlemi seçin:")
        islem = st.radio("", ["Yeni Kayıt","Eski Kayıt"], horizontal=True)

        if islem=="Yeni Kayıt":
            info = df_musteri[df_musteri["Müşteri Adı"]==musteri_sec]
            default_ulke = info["Ülke"].values[0] if not info.empty else ""
            default_tems = info["Satış Temsilcisi"].values[0] if not info.empty else ""
            default_odeme = info["Ödeme Şekli"].values[0] if not info.empty else ""
            with st.form("add_proforma"):
                tarih = st.date_input("Tarih", value=datetime.date.today())
                proforma_no = st.text_input("Proforma No")
                tutar = st.text_input("Tutar ($)")
                vade_gun = st.text_input("Vade (gün)")
                ulke = st.text_input("Ülke", value=default_ulke, disabled=True)
                temsilci = st.text_input("Satış Temsilcisi", value=default_tems, disabled=True)
                odeme = st.text_input("Ödeme Şekli", value=default_odeme, disabled=True)
                aciklama = st.text_area("Açıklama")
                durum = st.selectbox("Durum", ["Beklemede","İptal","Faturası Kesildi","Siparişe Dönüştü"])
                pdf_file = st.file_uploader("Proforma PDF", type="pdf")
                if st.form_submit_button("Kaydet"):
                    if not proforma_no.strip() or not vade_gun.strip():
                        st.error("Proforma No ve Vade (gün) boş olamaz!")
                    else:
                        pdf_link = ""
                        if pdf_file:
                            pdf_filename = f"{musteri_sec}_{tarih}_{proforma_no}.pdf"
                            temp_path = os.path.join(".", pdf_filename)
                            with open(temp_path, "wb") as f:
                                f.write(pdf_file.read())
                            gfile = drive.CreateFile({'title': pdf_filename, 'parents':[{'id': PROFORMA_PDF_FOLDER_ID}]})
                            gfile.SetContentFile(temp_path)
                            gfile.Upload(param={'supportsAllDrives': True})
                            pdf_link = f"https://drive.google.com/file/d/{gfile['id']}/view?usp=sharing"
                            try:
                                os.remove(temp_path)
                            except:
                                pass
                        new_row = {
                            "Müşteri Adı":musteri_sec,"Tarih":tarih,"Proforma No":proforma_no,"Tutar":tutar,"Vade (gün)":vade_gun,
                            "Ülke":default_ulke,"Satış Temsilcisi":default_tems,"Ödeme Şekli":default_odeme,
                            "Açıklama":aciklama,"Durum":"Beklemede","PDF":pdf_link,"Sipariş Formu":"","Sevk Durumu":""
                        }
                        df_proforma = pd.concat([df_proforma, pd.DataFrame([new_row])], ignore_index=True)
                        update_excel()
                        st.success("Proforma eklendi!")
                        st.rerun()

        else:  # Eski Kayıt
            eski = df_proforma[(df_proforma["Müşteri Adı"]==musteri_sec) & (df_proforma["Durum"]=="Beklemede")]
            if eski.empty:
                st.info("Bu müşteriye ait siparişe dönüşmemiş proforma kaydı yok.")
            else:
                st.dataframe(eski[["Müşteri Adı","Proforma No","Tarih","Tutar","Durum","Vade (gün)","Sevk Durumu"]], use_container_width=True)
                sec_index = st.selectbox("Proforma Seç", eski.index,
                                         format_func=lambda i: f"{eski.at[i,'Proforma No']} | {eski.at[i,'Tarih']}") if not eski.empty else None
                if sec_index is not None:
                    kayit = eski.loc[sec_index]
                    if kayit.get("PDF",""):
                        st.markdown(f"**Proforma PDF:** [{kayit['Proforma No']}]({kayit['PDF']})", unsafe_allow_html=True)

                    with st.form("edit_proforma"):
                        tarih_ = st.date_input("Tarih", value=pd.to_datetime(kayit["Tarih"]).date())
                        proforma_no_ = st.text_input("Proforma No", value=kayit["Proforma No"])
                        tutar_ = st.text_input("Tutar ($)", value=kayit["Tutar"])
                        vade_gun_ = st.text_input("Vade (gün)", value=str(kayit["Vade (gün)"]))
                        aciklama_ = st.text_area("Açıklama", value=kayit["Açıklama"])
                        durum_ = st.selectbox(
                            "Durum",
                            ["Beklemede","Siparişe Dönüştü","İptal","Faturası Kesildi"],
                            index=["Beklemede","Siparişe Dönüştü","İptal","Faturası Kesildi"].index(kayit["Durum"]) if kayit["Durum"] in ["Beklemede","Siparişe Dönüştü","İptal","Faturası Kesildi"] else 0
                        )
                        guncelle = st.form_submit_button("Güncelle")
                        sil = st.form_submit_button("Sil")

                    # Siparişe dönüşüyorsa sipariş formu yüklet
                    if durum_=="Siparişe Dönüştü":
                        st.info("Lütfen sipariş formunu yükleyin ve ardından 'Sipariş Formunu Kaydet' butonuna basın.")
                        with st.form(f"siparis_formu_upload_{sec_index}"):
                            siparis_formu_file = st.file_uploader("Sipariş Formu PDF", type="pdf")
                            siparis_kaydet = st.form_submit_button("Sipariş Formunu Kaydet")
                        if siparis_kaydet:
                            if siparis_formu_file is None:
                                st.error("Sipariş formu yüklemelisiniz.")
                            else:
                                sf_name = f"{musteri_sec}_{proforma_no_}_SiparisFormu_{datetime.datetime.now().strftime('%Y%m%d%H%M%S')}.pdf"
                                temp_path = os.path.join(".", sf_name)
                                with open(temp_path, "wb") as f:
                                    f.write(siparis_formu_file.read())
                                gfile = drive.CreateFile({'title': sf_name, 'parents':[{'id': SIPARIS_FORMU_FOLDER_ID}]})
                                gfile.SetContentFile(temp_path)
                                gfile.Upload(param={'supportsAllDrives': True})
                                sf_url = f"https://drive.google.com/file/d/{gfile['id']}/view?usp=sharing"
                                try:
                                    os.remove(temp_path)
                                except:
                                    pass
                                df_proforma.at[sec_index,"Sipariş Formu"] = sf_url
                                df_proforma.at[sec_index,"Durum"] = "Siparişe Dönüştü"
                                update_excel()
                                st.success("Sipariş formu kaydedildi ve durum güncellendi!")
                                st.rerun()

                    if guncelle:
                        df_proforma.at[sec_index,"Tarih"] = tarih_
                        df_proforma.at[sec_index,"Proforma No"] = proforma_no_
                        df_proforma.at[sec_index,"Tutar"] = tutar_
                        df_proforma.at[sec_index,"Vade (gün)"] = vade_gun_
                        df_proforma.at[sec_index,"Açıklama"] = aciklama_
                        if durum_ != "Siparişe Dönüştü":
                            df_proforma.at[sec_index,"Durum"] = durum_
                        update_excel()
                        st.success("Proforma güncellendi!")
                        st.rerun()

                    if sil:
                        df_proforma = df_proforma.drop(sec_index).reset_index(drop=True)
                        update_excel()
                        st.success("Kayıt silindi!")
                        st.rerun()

# --- GÜNCEL SİPARİŞ DURUMU ---
elif menu == "Güncel Sipariş Durumu":
    st.header("Güncel Sipariş Durumu")

    if "Sevk Durumu" not in df_proforma.columns:
        df_proforma["Sevk Durumu"] = ""
    if "Termin Tarihi" not in df_proforma.columns:
        df_proforma["Termin Tarihi"] = ""

    siparisler = df_proforma[
        (df_proforma["Durum"]=="Siparişe Dönüştü") & (~df_proforma["Sevk Durumu"].isin(["Sevkedildi","Ulaşıldı"]))
    ].copy()

    for c in ["Termin Tarihi","Sipariş Formu","Ülke","Satış Temsilcisi","Ödeme Şekli"]:
        if c not in siparisler.columns:
            siparisler[c] = ""

    siparisler["Termin Tarihi Order"] = pd.to_datetime(siparisler["Termin Tarihi"], errors="coerce")
    siparisler = siparisler.sort_values("Termin Tarihi Order", ascending=True)

    if siparisler.empty:
        st.info("Henüz sevk edilmeyi bekleyen sipariş yok.")
    else:
        siparisler["Tarih"] = pd.to_datetime(siparisler["Tarih"], errors="coerce").dt.strftime("%d/%m/%Y")
        siparisler["Termin Tarihi"] = pd.to_datetime(siparisler["Termin Tarihi"], errors="coerce").dt.strftime("%d/%m/%Y")
        tablo = siparisler[["Tarih","Müşteri Adı","Termin Tarihi","Ülke","Satış Temsilcisi","Ödeme Şekli","Proforma No","Tutar","Açıklama"]]
        st.markdown("<h4 style='color:#219A41;font-weight:bold;'>Tüm Siparişe Dönüşenler</h4>", unsafe_allow_html=True)
        st.dataframe(tablo, use_container_width=True)

        st.markdown("#### Termin Tarihi Güncelle")
        sec_index = st.selectbox(
            "Termin Tarihi Girilecek Siparişi Seçin",
            options=siparisler.index,
            format_func=lambda i: f"{siparisler.at[i,'Müşteri Adı']} - {siparisler.at[i,'Proforma No']}"
        )
        mevcut_termin = df_proforma.at[sec_index,"Termin Tarihi"] if "Termin Tarihi" in df_proforma.columns else ""
        try:
            default_termin = pd.to_datetime(mevcut_termin, errors="coerce")
            default_termin = datetime.date.today() if pd.isnull(default_termin) else default_termin.date()
        except:
            default_termin = datetime.date.today()
        yeni_termin = st.date_input("Termin Tarihi", value=default_termin, key="termin_input")
        if st.button("Termin Tarihini Kaydet"):
            df_proforma.at[sec_index,"Termin Tarihi"] = yeni_termin
            update_excel()
            st.success("Termin tarihi kaydedildi!")
            st.rerun()

        st.markdown("#### Sipariş Sevk Et")
        sevk_sec_index = st.selectbox(
            "Sevk Edilecek Siparişi Seçin",
            options=siparisler.index,
            format_func=lambda i: f"{siparisler.at[i,'Müşteri Adı']} - {siparisler.at[i,'Proforma No']}",
            key="sevk_sec"
        )
        if st.button("Sipariş Sevkedildi (ETA Takibine Gönder)"):
            for c in ["Müşteri Adı","Proforma No","ETA Tarihi","Açıklama"]:
                if c not in df_eta.columns:
                    df_eta[c] = ""
            yeni_eta = {
                "Müşteri Adı": siparisler.at[sevk_sec_index,"Müşteri Adı"],
                "Proforma No": siparisler.at[sevk_sec_index,"Proforma No"],
                "ETA Tarihi": "",
                "Açıklama": siparisler.at[sevk_sec_index,"Açıklama"]
            }
            df_eta = pd.concat([df_eta, pd.DataFrame([yeni_eta])], ignore_index=True)
            df_proforma.at[sevk_sec_index,"Sevk Durumu"] = "Sevkedildi"
            update_excel()
            st.success("Sipariş sevkedildi ve ETA takibine gönderildi!")
            st.rerun()

        st.markdown("#### Siparişi Beklemeye Al (Geri Çağır)")
        geri_index = st.selectbox(
            "Beklemeye Alınacak Siparişi Seçin",
            options=siparisler.index,
            format_func=lambda i: f"{siparisler.at[i,'Müşteri Adı']} - {siparisler.at[i,'Proforma No']}",
            key="geri_sec"
        )
        if st.button("Siparişi Beklemeye Al / Geri Çağır"):
            df_proforma.at[geri_index,"Durum"]="Beklemede"
            df_proforma.at[geri_index,"Sevk Durumu"]=""
            df_proforma.at[geri_index,"Termin Tarihi"]=""
            update_excel()
            st.success("Sipariş tekrar bekleyen proformalar listesine alındı!")
            st.rerun()

        st.markdown("#### Tıklanabilir Proforma ve Sipariş Formu Linkleri")
        for i,row in siparisler.iterrows():
            links=[]
            if pd.notnull(row.get("PDF","")) and row.get("PDF",""):
                links.append(f"[Proforma PDF: {row['Proforma No']}]({row['PDF']})")
            if pd.notnull(row.get("Sipariş Formu","")) and row.get("Sipariş Formu",""):
                fname=f"{row['Müşteri Adı']}__{row['Proforma No']}__SiparisFormu"
                links.append(f"[Sipariş Formu: {fname}]({row['Sipariş Formu']})")
            if links:
                st.markdown(" - " + " | ".join(links), unsafe_allow_html=True)

        try:
            toplam = pd.to_numeric(siparisler["Tutar"], errors="coerce").sum()
        except:
            toplam = 0
        st.markdown(f"<div style='color:#219A41;font-weight:bold;'>*Toplam Bekleyen Sevk: {toplam:,.2f} $*</div>", unsafe_allow_html=True)

# --- FATURA & İHRACAT EVRAKLARI ---
elif menu == "Fatura & İhracat Evrakları":
    st.markdown("<h2 style='color:#219A41; font-weight:bold;'>Fatura & İhracat Evrakları</h2>", unsafe_allow_html=True)
    for c in ["Proforma No","Vade (gün)","Vade Tarihi","Ülke","Satış Temsilcisi","Ödeme Şekli",
              "Commercial Invoice","Sağlık Sertifikası","Packing List","Konşimento","İhracat Beyannamesi",
              "Fatura PDF","Sipariş Formu","Yük Resimleri","EK Belgeler","Ödendi","Ödeme Kanıtı"]:
        if c not in df_evrak.columns:
            df_evrak[c] = False if c=="Ödendi" else ""

    musteri_secenek = sorted(df_proforma["Müşteri Adı"].dropna().unique().tolist())
    secilen_musteri = st.selectbox("Müşteri Seç", [""]+musteri_secenek)

    if secilen_musteri:
        pnos = df_proforma[df_proforma["Müşteri Adı"]==secilen_musteri]["Proforma No"].astype(str).tolist()
    else:
        pnos=[]
    proforma_no_sec = st.selectbox("Proforma No Seç", [""]+pnos)

    info = df_musteri[df_musteri["Müşteri Adı"]==secilen_musteri]
    ulke = info["Ülke"].values[0] if not info.empty else ""
    temsilci = info["Satış Temsilcisi"].values[0] if not info.empty else ""
    odeme = info["Ödeme Şekli"].values[0] if not info.empty else ""

    onceki_evrak = df_evrak[(df_evrak["Müşteri Adı"]==secilen_musteri) & (df_evrak["Proforma No"]==proforma_no_sec)]

    def file_link_html(label, url):
        return (f'<div style="margin-top:-6px;"><a href="{url}" target="_blank" style="color:#219A41;">[Daha önce yüklenmiş {label}]</a></div>'
                if url else '<div style="margin-top:-6px;color:#b00020;font-size:.95em;">(Daha önce yüklenmemiş)</div>')

    evrak_tipleri = [
        ("Commercial Invoice","Commercial Invoice PDF"),
        ("Sağlık Sertifikası","Sağlık Sertifikası PDF"),
        ("Packing List","Packing List PDF"),
        ("Konşimento","Konşimento PDF"),
        ("İhracat Beyannamesi","İhracat Beyannamesi PDF"),
    ]

    with st.form("add_evrak"):
        fatura_no = st.text_input("Fatura No")
        fatura_tarih = st.date_input("Fatura Tarihi", value=datetime.date.today())
        tutar = st.text_input("Fatura Tutarı ($)")
        vade_gun = ""; vade_tarihi = ""
        if secilen_musteri and proforma_no_sec:
            prof = df_proforma[(df_proforma["Müşteri Adı"]==secilen_musteri) & (df_proforma["Proforma No"]==proforma_no_sec)]
            if not prof.empty:
                vade_gun = prof.iloc[0].get("Vade (gün)","")
                try:
                    vg = int(vade_gun)
                    vade_tarihi = fatura_tarih + datetime.timedelta(days=vg)
                except:
                    vade_tarihi = ""
        st.text_input("Vade (gün)", value=vade_gun, key="vade_gun", disabled=True)
        st.date_input("Vade Tarihi", value=vade_tarihi if vade_tarihi else fatura_tarih, key="vade_tarihi", disabled=True)
        st.text_input("Ülke", value=ulke, disabled=True)
        st.text_input("Satış Temsilcisi", value=temsilci, disabled=True)
        st.text_input("Ödeme Şekli", value=odeme, disabled=True)

        uploaded_files = {}
        for col,label in evrak_tipleri:
            uploaded_files[col] = st.file_uploader(label, type="pdf", key=f"{col}_upload")
            prev_url = onceki_evrak.iloc[0][col] if not onceki_evrak.empty else ""
            st.markdown(file_link_html(label, prev_url), unsafe_allow_html=True)

        if st.form_submit_button("Kaydet"):
            if not fatura_no.strip() or not tutar.strip():
                st.error("Fatura No ve Tutar boş olamaz!")
            else:
                file_urls = {}
                for col,label in evrak_tipleri:
                    up = uploaded_files[col]
                    if up:
                        file_name = f"{col}_{datetime.datetime.now().strftime('%Y%m%d%H%M%S')}.pdf"
                        temp_path = os.path.join(".", file_name)
                        with open(temp_path, "wb") as f:
                            f.write(up.read())
                        gfile = drive.CreateFile({'title': file_name, 'parents':[{'id': EVRAK_KLASOR_ID}]})
                        gfile.SetContentFile(temp_path)
                        gfile.Upload(param={'supportsAllDrives': True})
                        file_urls[col] = f"https://drive.google.com/file/d/{gfile['id']}/view?usp=sharing"
                        try:
                            os.remove(temp_path)
                        except:
                            pass
                    else:
                        file_urls[col] = onceki_evrak.iloc[0][col] if not onceki_evrak.empty else ""
                new_row = {
                    "Müşteri Adı": secilen_musteri, "Proforma No": proforma_no_sec,
                    "Fatura No": fatura_no, "Fatura Tarihi": fatura_tarih, "Tutar": tutar,
                    "Vade (gün)": vade_gun, "Vade Tarihi": vade_tarihi,
                    "Ülke": ulke, "Satış Temsilcisi": temsilci, "Ödeme Şekli": odeme,
                    "Commercial Invoice": file_urls.get("Commercial Invoice",""),
                    "Sağlık Sertifikası": file_urls.get("Sağlık Sertifikası",""),
                    "Packing List": file_urls.get("Packing List",""),
                    "Konşimento": file_urls.get("Konşimento",""),
                    "İhracat Beyannamesi": file_urls.get("İhracat Beyannamesi",""),
                    "Fatura PDF":"", "Sipariş Formu":"", "Yük Resimleri":"", "EK Belgeler":"",
                    "Ödendi": False
                }
                df_evrak = pd.concat([df_evrak, pd.DataFrame([new_row])], ignore_index=True)
                update_excel()
                st.success("Evrak eklendi!")
                st.rerun()

# --- VADE TAKİBİ ---
elif menu == "Vade Takibi":
    st.markdown("<h2 style='color:#219A41; font-weight:bold;'>Vade Takibi</h2>", unsafe_allow_html=True)

    ROOT_EXPORT_FOLDER_ID = EVRAK_KLASOR_ID

    def safe_name(text, maxlen=120):
        s = str(text or "").strip().replace(" ","_")
        s = re.sub(r'[\\/*?:"<>|]+',"_",s)
        return s[:maxlen]

    def get_or_create_folder_by_name(name, parent_id):
        q = (f"title = '{name}' and mimeType = 'application/vnd.google-apps.folder' "
             f"and '{parent_id}' in parents and trashed = false")
        try:
            lst = drive.ListFile({'q':q,'supportsAllDrives':True,'includeItemsFromAllDrives':True}).GetList()
            if lst:
                return lst[0]['id']
            meta = {'title':name,'mimeType':'application/vnd.google-apps.folder','parents':[{'id':parent_id}]}
            f = drive.CreateFile(meta)
            f.Upload(param={'supportsAllDrives':True})
            return f['id']
        except Exception as e:
            st.error(f"Klasör oluşturma/arama hatası: {e}")
            return ""

    def get_or_create_customer_folder(customer_name, parent_folder_id):
        return get_or_create_folder_by_name(safe_name(customer_name,100), parent_folder_id)

    for c in ["Proforma No","Vade (gün)","Ödendi","Ülke","Satış Temsilcisi","Ödeme Şekli","Vade Tarihi","Fatura No","Müşteri Adı","Ödeme Kanıtı"]:
        if c not in df_evrak.columns:
            df_evrak[c] = "" if c!="Ödendi" else False

    df_evrak["Ödendi"] = df_evrak["Ödendi"].fillna(False).astype(bool)
    df_evrak["Vade Tarihi"] = pd.to_datetime(df_evrak["Vade Tarihi"], errors="coerce")

    today = pd.to_datetime(datetime.date.today())
    vade_df = df_evrak[df_evrak["Vade Tarihi"].notna() & (~df_evrak["Ödendi"])].reset_index()

    if vade_df.empty:
        st.info("Açık vade kaydı yok.")
    else:
        for i,row in vade_df.iterrows():
            kalan = (row["Vade Tarihi"] - today).days
            mesaj = (f"{row['Müşteri Adı']} | {row.get('Ülke','')} | {row.get('Satış Temsilcisi','')} "
                     f"| Proforma No: {row.get('Proforma No','')} | Fatura No: {row['Fatura No']} "
                     f"| Vade Tarihi: {row['Vade Tarihi'].date()} | Ödeme: {row.get('Ödeme Şekli','')}")
            box = st.container(border=True)
            with box:
                if kalan == 1:
                    st.error(f"{mesaj} | **YARIN VADE DOLUYOR!**")
                elif kalan < 0:
                    st.warning(f"{mesaj} | **{abs(kalan)} gün GECİKTİ!**")
                else:
                    st.info(f"{mesaj} | {kalan} gün kaldı.")

                kanit_file = st.file_uploader(
                    "Ödeme Kanıtı (PDF/JPG/PNG/JPEG/WEBP)",
                    type=["pdf","jpg","jpeg","png","webp"],
                    key=f"kanit_{i}"
                )

                prev_link = row.get("Ödeme Kanıtı","")
                if prev_link:
                    st.markdown(f"[Önceden yüklenmiş ödeme kanıtı]({prev_link})", unsafe_allow_html=True)

                tick = st.checkbox(
                    f"Ödendi olarak işaretle → {row['Müşteri Adı']} - Proforma: {row.get('Proforma No','')} - Fatura: {row['Fatura No']}",
                    key=f"odendi_{i}"
                )

                if tick:
                    if kanit_file is None and not prev_link:
                        st.error("Lütfen önce **Ödeme Kanıtı** yükleyin.")
                    else:
                        odeme_kaniti_url = prev_link
                        if kanit_file is not None:
                            if not ROOT_EXPORT_FOLDER_ID:
                                st.error("Ana klasör ID tanımlı değil.")
                                st.stop()
                            cust_folder_id = get_or_create_customer_folder(row["Müşteri Adı"], ROOT_EXPORT_FOLDER_ID)
                            if not cust_folder_id:
                                st.error("Müşteri klasörü oluşturulamadı.")
                                st.stop()
                            kanit_folder_id = get_or_create_folder_by_name("Odeme_Kanitlari", cust_folder_id)
                            if not kanit_folder_id:
                                st.error("Ödeme kanıtı klasörü oluşturulamadı.")
                                st.stop()
                            suffix = os.path.splitext(kanit_file.name)[1].lower() or ".pdf"
                            ts = datetime.datetime.now().strftime('%Y%m%d%H%M%S')
                            fname = safe_name(f"OdemeKaniti__{row['Müşteri Adı']}__{row.get('Proforma No','')}__{row['Fatura No']}__{ts}") + suffix
                            with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as fp:
                                fp.write(kanit_file.read())
                                temp_path = fp.name
                            meta = {'title': fname, 'parents':[{'id': kanit_folder_id}]}
                            gfile = drive.CreateFile(meta)
                            gfile.SetContentFile(temp_path)
                            try:
                                gfile.Upload(param={'supportsAllDrives': True})
                                odeme_kaniti_url = f"https://drive.google.com/file/d/{gfile['id']}/view?usp=sharing"
                            except Exception as e:
                                st.error(f"Ödeme kanıtı yüklenirken hata: {e}")
                            finally:
                                try:
                                    os.remove(temp_path)
                                except:
                                    pass

                        df_evrak.at[row['index'],"Ödeme Kanıtı"] = odeme_kaniti_url
                        df_evrak.at[row['index'],"Ödendi"] = True
                        update_excel()
                        st.success("Kayıt 'Ödendi' olarak işaretlendi.")
                        st.rerun()

        st.markdown("#### Açık Vade Kayıtları")
        st.dataframe(
            df_evrak[
                df_evrak["Vade Tarihi"].notna() & (~df_evrak["Ödendi"])
            ][["Müşteri Adı","Ülke","Satış Temsilcisi","Ödeme Şekli","Proforma No","Fatura No","Fatura Tarihi","Vade (gün)","Vade Tarihi","Tutar"]]
        )

# --- ETA TAKİBİ ---
elif menu == "ETA Takibi":
    st.markdown("<h2 style='color:#219A41; font-weight:bold;'>ETA Takibi</h2>", unsafe_allow_html=True)

    import re as _re
    ROOT_EXPORT_FOLDER_ID = EVRAK_KLASOR_ID

    for c in ["Sevk Durumu","Proforma No","Sevk Tarihi","Ulaşma Tarihi"]:
        if c not in df_proforma.columns:
            df_proforma[c]=""
    for c in ["Müşteri Adı","Proforma No","ETA Tarihi","Açıklama"]:
        if c not in df_eta.columns:
            df_eta[c]=""

    def safe_name(text, maxlen=120):
        s = str(text or "").strip().replace(" ","_")
        s = _re.sub(r'[\\/*?:"<>|]+',"_",s)
        return s[:maxlen]

    def get_or_create_folder_by_name(name, parent_id):
        q=(f"title = '{name}' and mimeType='application/vnd.google-apps.folder' "
           f"and '{parent_id}' in parents and trashed=false")
        try:
            lst = drive.ListFile({'q':q,'supportsAllDrives':True,'includeItemsFromAllDrives':True}).GetList()
            if lst:
                return lst[0]['id']
            meta={'title':name,'mimeType':'application/vnd.google-apps.folder','parents':[{'id':parent_id}]}
            f = drive.CreateFile(meta)
            f.Upload(param={'supportsAllDrives':True})
            return f['id']
        except Exception as e:
            st.error(f"Klasör oluşturma/arama hatası: {e}")
            return ""

    def get_proforma_yukleme_folder(proforma_no):
        if not ROOT_EXPORT_FOLDER_ID:
            return ""
        p = get_or_create_folder_by_name(safe_name(proforma_no,100), ROOT_EXPORT_FOLDER_ID)
        if not p:
            return ""
        y = get_or_create_folder_by_name("Yükleme Resimleri", p)
        return y

    sevkedilenler = df_proforma[df_proforma["Sevk Durumu"]=="Sevkedildi"].copy()
    if sevkedilenler.empty:
        st.info("Sevkedilmiş sipariş bulunmuyor.")
    else:
        secenekler = sevkedilenler[["Müşteri Adı","Proforma No"]].drop_duplicates()
        secenekler["sec_text"] = secenekler["Müşteri Adı"] + " - " + secenekler["Proforma No"]
        selected = st.selectbox("Sevkedilen Sipariş Seç", secenekler["sec_text"])
        row_sel = secenekler[secenekler["sec_text"]==selected].iloc[0]
        sec_musteri = row_sel["Müşteri Adı"]
        sec_proforma = row_sel["Proforma No"]

        st.markdown("#### 🖼️ Yükleme Fotoğrafları (Proforma bazlı)")
        hedef_klasor = get_proforma_yukleme_folder(sec_proforma)
        if not hedef_klasor:
            st.error("Proforma klasörü / 'Yükleme Resimleri' klasörü oluşturulamadı.")
        else:
            drive_link = f"https://drive.google.com/drive/folders/{hedef_klasor}?usp=sharing"
            st.markdown(f"[🔗 Klasörü yeni sekmede aç]({drive_link})")
            with st.expander("📂 Panelde klasörü görüntüle"):
                embed = f"https://drive.google.com/embeddedfolderview?id={hedef_klasor}#grid"
                st.markdown(
                    f'<iframe src="{embed}" width="100%" height="520" frameborder="0" style="border:1px solid #eee;border-radius:12px;"></iframe>',
                    unsafe_allow_html=True
                )
            try:
                mevcut_dosyalar = drive.ListFile({
                    'q':f"'{hedef_klasor}' in parents and trashed=false",
                    'supportsAllDrives':True,'includeItemsFromAllDrives':True
                }).GetList()
            except Exception as e:
                mevcut_dosyalar=[]; st.warning(f"Dosyalar listelenemedi: {e}")

            if mevcut_dosyalar:
                st.caption(f"Bu klasörde {len(mevcut_dosyalar)} dosya var.")
                names = [f"- {f['title']}" for f in mevcut_dosyalar[:10]]
                st.write("\n".join(names) if names else "")
                if len(mevcut_dosyalar)>10:
                    st.write("…")

            with st.expander("➕ Dosya Ekle (opsiyonel, duplike önleme)"):
                files = st.file_uploader(
                    "Yüklenecek dosyaları seçin",
                    type=["pdf","jpg","jpeg","png","webp"],
                    accept_multiple_files=True,
                    key=f"yuk_res_{sec_proforma}"
                )
                if files:
                    var_isimler = set(f["title"] for f in mevcut_dosyalar)
                    yuklenen, atlanan = 0, 0
                    for up in files:
                        suffix = os.path.splitext(up.name)[1].lower()
                        base = os.path.splitext(up.name)[0]
                        fname = safe_name(base) + (suffix if suffix else "")
                        if fname in var_isimler:
                            atlanan += 1
                            continue
                        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as fp:
                            fp.write(up.read())
                            temp_path = fp.name
                        meta = {'title': fname, 'parents':[{'id': hedef_klasor}]}
                        gfile = drive.CreateFile(meta)
                        gfile.SetContentFile(temp_path)
                        try:
                            gfile.Upload(param={'supportsAllDrives': True})
                            yuklenen += 1
                            var_isimler.add(fname)
                        except Exception as e:
                            st.error(f"{up.name} yüklenemedi: {e}")
                        finally:
                            try:
                                os.remove(temp_path)
                            except:
                                pass
                    if yuklenen:
                        update_excel()
                        st.success(f"{yuklenen} dosya yüklendi.")
                        if atlanan:
                            st.info(f"{atlanan} dosya isim aynı olduğu için atlandı.")
                        st.rerun()
                    else:
                        if atlanan and not yuklenen:
                            st.warning("Tüm dosyalar klasörde zaten mevcut (isim aynı).")

        st.markdown("---")
        filtre = (df_eta["Müşteri Adı"]==sec_musteri) & (df_eta["Proforma No"]==sec_proforma)
        mevcut_eta = df_eta.loc[filtre,"ETA Tarihi"].values[0] if filtre.any() else ""
        mevcut_aciklama = df_eta.loc[filtre,"Açıklama"].values[0] if filtre.any() else ""
        with st.form("edit_eta"):
            try:
                varsayilan_eta = pd.to_datetime(mevcut_eta).date() if mevcut_eta and pd.notnull(mevcut_eta) and str(mevcut_eta)!="NaT" else datetime.date.today()
            except:
                varsayilan_eta = datetime.date.today()
            eta_tarih = st.date_input("ETA Tarihi", value=varsayilan_eta)
            aciklama = st.text_area("Açıklama", value=mevcut_aciklama)
            guncelle = st.form_submit_button("ETA'yı Kaydet/Güncelle")
            ulasti = st.form_submit_button("Ulaştı")
            geri_al= st.form_submit_button("Sevki Geri Al")

            if guncelle:
                if filtre.any():
                    df_eta.loc[filtre,"ETA Tarihi"]=eta_tarih
                    df_eta.loc[filtre,"Açıklama"]=aciklama
                else:
                    df_eta = pd.concat([df_eta, pd.DataFrame([{
                        "Müşteri Adı":sec_musteri,"Proforma No":sec_proforma,"ETA Tarihi":eta_tarih,"Açıklama":aciklama
                    }])], ignore_index=True)
                update_excel()
                st.success("ETA kaydedildi/güncellendi!")
                st.rerun()

            if ulasti:
                df_eta = df_eta[~((df_eta["Müşteri Adı"]==sec_musteri) & (df_eta["Proforma No"]==sec_proforma))]
                idx = df_proforma[(df_proforma["Müşteri Adı"]==sec_musteri) & (df_proforma["Proforma No"]==sec_proforma)].index
                if len(idx)>0:
                    df_proforma.at[idx[0],"Sevk Durumu"]="Ulaşıldı"
                    df_proforma.at[idx[0],"Ulaşma Tarihi"]=datetime.date.today()
                update_excel()
                st.success("Sipariş 'Ulaşıldı' ve ETA’dan çıkarıldı!")
                st.rerun()

            if geri_al:
                df_eta = df_eta[~((df_eta["Müşteri Adı"]==sec_musteri) & (df_eta["Proforma No"]==sec_proforma))]
                idx = df_proforma[(df_proforma["Müşteri Adı"]==sec_musteri) & (df_proforma["Proforma No"]==sec_proforma)].index
                if len(idx)>0:
                    df_proforma.at[idx[0],"Sevk Durumu"]=""
                update_excel()
                st.success("Sevkiyat geri alındı; Güncel Sipariş Durumu'na döndü.")
                st.rerun()

    st.markdown("#### ETA Takip Listesi")
    for c in ["Proforma No","ETA Tarihi"]:
        if c not in df_eta.columns:
            df_eta[c]=""
    if not df_eta.empty:
        df_eta["ETA Tarihi"] = pd.to_datetime(df_eta["ETA Tarihi"], errors="coerce")
        today = pd.to_datetime(datetime.date.today())
        df_eta["Kalan Gün"] = (df_eta["ETA Tarihi"] - today).dt.days
        tablo = df_eta[["Müşteri Adı","Proforma No","ETA Tarihi","Kalan Gün","Açıklama"]].copy()
        tablo = tablo.sort_values(["ETA Tarihi","Müşteri Adı","Proforma No"], ascending=[True,True,True])
        st.dataframe(tablo, use_container_width=True)

        st.markdown("##### ETA Kaydı Sil")
        silinecekler = df_eta.index.tolist()
        sil_sec = st.selectbox(
            "Silinecek Kaydı Seçin", options=silinecekler,
            format_func=lambda i: f"{df_eta.at[i,'Müşteri Adı']} - {df_eta.at[i,'Proforma No']}"
        )
        if st.button("KAYDI SİL"):
            df_eta = df_eta.drop(sil_sec).reset_index(drop=True)
            update_excel()
            st.success("Seçilen ETA kaydı silindi!")
            st.rerun()
    else:
        st.info("Henüz ETA kaydı yok.")

    ulasanlar = df_proforma[df_proforma["Sevk Durumu"]=="Ulaşıldı"].copy()
    if not ulasanlar.empty:
        ulasanlar["sec_text"] = ulasanlar["Müşteri Adı"] + " - " + ulasanlar["Proforma No"]
        st.markdown("#### Teslim Edilen Siparişlerde İşlemler")
        selected_ulasan = st.selectbox("Sipariş Seçiniz", ulasanlar["sec_text"])
        row = ulasanlar[ulasanlar["sec_text"]==selected_ulasan].iloc[0]

        try:
            current_ulasma = pd.to_datetime(row.get("Ulaşma Tarihi",None)).date()
            if pd.isnull(current_ulasma) or str(current_ulasma)=="NaT":
                current_ulasma = datetime.date.today()
        except:
            current_ulasma = datetime.date.today()
        new_ulasma_tarih = st.date_input("Ulaşma Tarihi", value=current_ulasma, key="ulasan_guncelle")
        if st.button("Ulaşma Tarihini Kaydet"):
            idx = df_proforma[
                (df_proforma["Müşteri Adı"]==row["Müşteri Adı"]) &
                (df_proforma["Proforma No"]==row["Proforma No"])
            ].index
            if len(idx)>0:
                df_proforma.at[idx[0],"Ulaşma Tarihi"]=new_ulasma_tarih
                update_excel()
                st.success("Ulaşma Tarihi güncellendi!")
                st.rerun()

        with st.form("ulasan_geri_al_form"):
            st.markdown("##### 🔄 Ulaşan siparişi yeniden **Yolda Olanlar (ETA)** listesine al")
            yeni_eta = st.date_input("Yeni ETA (opsiyonel)", value=datetime.date.today()+datetime.timedelta(days=7))
            aciklama_geri = st.text_input("Açıklama (opsiyonel)", value="Geri alındı - tekrar yolda")
            onay = st.form_submit_button("Yola Geri Al")

        if onay:
            musteri = row["Müşteri Adı"]; pno = row["Proforma No"]
            idx = df_proforma[(df_proforma["Müşteri Adı"]==musteri) & (df_proforma["Proforma No"]==pno)].index
            if len(idx)>0:
                df_proforma.at[idx[0],"Sevk Durumu"]="Sevkedildi"
                df_proforma.at[idx[0],"Ulaşma Tarihi"]=""
            filtre_eta = (df_eta["Müşteri Adı"]==musteri) & (df_eta["Proforma No"]==pno)
            eta_deger = pd.to_datetime(yeni_eta) if yeni_eta else ""
            if filtre_eta.any():
                if yeni_eta:
                    df_eta.loc[filtre_eta,"ETA Tarihi"]=eta_deger
                if aciklama_geri:
                    df_eta.loc[filtre_eta,"Açıklama"]=aciklama_geri
            else:
                df_eta = pd.concat([df_eta, pd.DataFrame([{
                    "Müşteri Adı":musteri,"Proforma No":pno,"ETA Tarihi":eta_deger if yeni_eta else "","Açıklama":aciklama_geri
                }])], ignore_index=True)
            update_excel()
            st.success("Sipariş geri alındı ve ETA listesine taşındı.")
            st.rerun()

        st.markdown("#### Ulaşan (Teslim Edilmiş) Siparişler")
        if "Sevk Tarihi" in ulasanlar.columns:
            ulasanlar["Sevk Tarihi"] = pd.to_datetime(ulasanlar["Sevk Tarihi"], errors="coerce")
        else:
            ulasanlar["Sevk Tarihi"] = pd.NaT
        if "Termin Tarihi" in ulasanlar.columns:
            ulasanlar["Termin Tarihi"] = pd.to_datetime(ulasanlar["Termin Tarihi"], errors="coerce")
        else:
            ulasanlar["Termin Tarihi"] = pd.NaT
        ulasanlar["Ulaşma Tarihi"] = pd.to_datetime(ulasanlar["Ulaşma Tarihi"], errors="coerce")
        ulasanlar["Gün Farkı"] = (ulasanlar["Ulaşma Tarihi"] - ulasanlar["Termin Tarihi"]).dt.days
        ulasanlar["Sevk Tarihi"] = ulasanlar["Sevk Tarihi"].dt.strftime("%d/%m/%Y")
        ulasanlar["Termin Tarihi"] = ulasanlar["Termin Tarihi"].dt.strftime("%d/%m/%Y")
        ulasanlar["Ulaşma Tarihi"] = ulasanlar["Ulaşma Tarihi"].dt.strftime("%d/%m/%Y")
        tablo = ulasanlar[["Müşteri Adı","Proforma No","Termin Tarihi","Sevk Tarihi","Ulaşma Tarihi","Gün Farkı","Tutar","Açıklama"]]
        st.dataframe(tablo, use_container_width=True)
    else:
        st.info("Henüz ulaşan sipariş yok.")

# --- FUAR MÜŞTERİ KAYITLARI ---
elif menu == "Fuar Müşteri Kayıtları":
    st.markdown("<h2 style='color:#8e54e9; font-weight:bold; text-align:center;'>🎫 FUAR MÜŞTERİ KAYITLARI</h2>", unsafe_allow_html=True)
    st.info("Fuarlarda müşteri görüşmelerinizi buraya ekleyin.")

    fuar_isimleri = list(df_fuar_musteri["Fuar Adı"].dropna().unique())
    yeni_fuar = st.text_input("Yeni Fuar Adı Ekleyin (Eklemek istemiyorsanız boş bırakın):")
    if yeni_fuar and yeni_fuar not in fuar_isimleri:
        fuar_isimleri.append(yeni_fuar)
        fuar_adi=yeni_fuar
    else:
        fuar_adi = st.selectbox("Fuar Seçiniz", ["- Fuar Seçiniz -"]+sorted(fuar_isimleri), index=0)
        if fuar_adi == "- Fuar Seçiniz -":
            fuar_adi=""

    secim = st.radio("İşlem Seçiniz:", ["Yeni Kayıt","Eski Kayıt"])

    if secim=="Yeni Kayıt":
        st.markdown("#### Yeni Fuar Müşteri Kaydı Ekle")
        with st.form("fuar_musteri_ekle"):
            musteri_adi = st.text_input("Müşteri Adı")
            ulke = st.selectbox("Ülke Seçin", ulke_listesi)
            tel = st.text_input("Telefon")
            email = st.text_input("E-mail")
            temsilci = st.selectbox("Satış Temsilcisi", ["Hüseyin POLAT","Kemal İlker Çelikkalkan","Efe Yıldırım"])
            aciklama = st.text_area("Açıklamalar")
            gorusme_kalitesi = st.slider("Görüşme Kalitesi (1=Kötü, 5=Çok İyi)", 1, 5, 3)
            tarih = st.date_input("Tarih", value=datetime.date.today())
            if st.form_submit_button("Kaydet"):
                if not musteri_adi.strip() or not fuar_adi:
                    st.warning("Lütfen fuar seçin ve müşteri adı girin.")
                else:
                    new_row = {
                        "Fuar Adı":fuar_adi,"Müşteri Adı":musteri_adi,"Ülke":ulke,"Telefon":tel,"E-mail":email,
                        "Satış Temsilcisi":temsilci,"Açıklamalar":aciklama,"Görüşme Kalitesi":gorusme_kalitesi,"Tarih":tarih
                    }
                    df_fuar_musteri = pd.concat([df_fuar_musteri, pd.DataFrame([new_row])], ignore_index=True)
                    update_excel()
                    st.success("Fuar müşterisi eklendi!")
                    st.rerun()
    else:
        kolonlar = ["Müşteri Adı","Ülke","Telefon","E-mail","Satış Temsilcisi","Açıklamalar","Görüşme Kalitesi","Tarih"]
        musteri_df = df_fuar_musteri[df_fuar_musteri["Fuar Adı"]==fuar_adi].copy()
        if musteri_df.empty:
            st.info("Bu fuara ait müşteri kaydı bulunamadı.")
        else:
            st.markdown(f"<h4 style='color:#4776e6;'>{fuar_adi} Fuarındaki Müşteri Görüşme Kayıtları</h4>", unsafe_allow_html=True)
            secili_index = st.selectbox(
                "Düzenlemek/Silmek istediğiniz kaydı seçin:",
                musteri_df.index,
                format_func=lambda i: f"{musteri_df.at[i,'Müşteri Adı']} ({musteri_df.at[i,'Tarih']})"
            )
            with st.form("kayit_duzenle"):
                musteri_adi = st.text_input("Müşteri Adı", value=musteri_df.at[secili_index,"Müşteri Adı"])
                ulke = st.selectbox("Ülke", ulke_listesi, index=ulke_listesi.index(musteri_df.at[secili_index,"Ülke"]))
                temsilci = st.selectbox(
                    "Satış Temsilcisi",
                    ["Hüseyin POLAT","Kemal İlker Çelikkalkan","Efe Yıldırım"],
                    index=["Hüseyin POLAT","Kemal İlker Çelikkalkan","Efe Yıldırım"].index(musteri_df.at[secili_index,"Satış Temsilcisi"]) if musteri_df.at[secili_index,"Satış Temsilcisi"] in ["Hüseyin POLAT","Kemal İlker Çelikkalkan","Efe Yıldırım"] else 0
                )
                tel = st.text_input("Telefon", value=musteri_df.at[secili_index,"Telefon"])
                email = st.text_input("E-mail", value=musteri_df.at[secili_index,"E-mail"])
                aciklama = st.text_area("Açıklamalar", value=musteri_df.at[secili_index,"Açıklamalar"])
                gk = st.slider(
                    "Görüşme Kalitesi (1=Kötü, 5=Çok İyi)", 1, 5,
                    int(musteri_df.at[secili_index,"Görüşme Kalitesi"]) if musteri_df.at[secili_index,"Görüşme Kalitesi"] else 3
                )
                tarih = st.date_input(
                    "Tarih",
                    value=pd.to_datetime(musteri_df.at[secili_index,"Tarih"]).date()
                    if musteri_df.at[secili_index,"Tarih"] else datetime.date.today()
                )
                guncelle = st.form_submit_button("Kaydı Güncelle")
                sil      = st.form_submit_button("Kaydı Sil")

            if guncelle:
                for key,val in zip(kolonlar,[musteri_adi,ulke,tel,email,temsilci,aciklama,gk,tarih]):
                    df_fuar_musteri.at[secili_index,key]=val
                update_excel()
                st.success("Kayıt güncellendi!")
                st.rerun()

            if sil:
                df_fuar_musteri = df_fuar_musteri.drop(secili_index).reset_index(drop=True)
                update_excel()
                st.success("Kayıt silindi!")
                st.rerun()

            st.dataframe(musteri_df[kolonlar], use_container_width=True)

# --- MEDYA ÇEKMECESİ ---
elif menu == "Medya Çekmecesi":
    st.markdown("<h2 style='color:#8e54e9; font-weight:bold;'>Medya Çekmecesi</h2>", unsafe_allow_html=True)
    st.info("Google Drive’daki medya, ürün görselleri ve kalite evraklarına aşağıdaki sekmelerden ulaşabilirsiniz.")
    drive_folders = {
        "Genel Medya Klasörü": "https://drive.google.com/embeddedfolderview?id=1gFAaK-6v1e3346e-W0TsizOqSq43vHLY#list",
        "Ürün Görselleri": "https://drive.google.com/embeddedfolderview?id=18NNlmadm5NNFkI1Amzt_YMwB53j6AmbD#list",
        "Kalite Evrakları": "https://drive.google.com/embeddedfolderview?id=1pbArzYfA4Tp50zvdyTzSPF2ThrMWrGJc#list"
    }
    tab1,tab2,tab3 = st.tabs(list(drive_folders.keys()))
    with tab1:
        st.markdown(f"""<iframe src="{drive_folders['Genel Medya Klasörü']}" width="100%" height="600" frameborder="0" style="border:1px solid #eee;border-radius:12px;margin-top:10px;"></iframe>""", unsafe_allow_html=True)
        st.info("Dosyayı çift tıklayarak yeni sekmede açabilirsiniz.")
    with tab2:
        st.markdown(f"""<iframe src="{drive_folders['Ürün Görselleri']}" width="100%" height="600" frameborder="0" style="border:1px solid #eee;border-radius:12px;margin-top:10px;"></iframe>""", unsafe_allow_html=True)
        st.info("Dosyayı çift tıklayarak yeni sekmede açabilirsiniz.")
    with tab3:
        st.markdown(f"""<iframe src="{drive_folders['Kalite Evrakları']}" width="100%" height="600" frameborder="0" style="border:1px solid #eee;border-radius:12px;margin-top:10px;"></iframe>""", unsafe_allow_html=True)
        st.info("Sertifikaları bu klasörden inceleyebilirsiniz.")
    st.warning("Not: Klasör paylaşımı 'Bağlantıya sahip olan herkes görüntüleyebilir' olmalı.")

# --- SATIŞ PERFORMANSI ---
elif menu == "Satış Performansı":
    st.markdown("<h2 style='color:#219A41; font-weight:bold;'>Satış Performansı</h2>", unsafe_allow_html=True)

    def smart_to_num(x):
        if pd.isna(x):
            return 0.0
        s = str(x).strip()
        for sym in ["USD","$","€","EUR","₺","TL","tl","Tl"]:
            s = s.replace(sym,"")
        s = s.replace("\u00A0","").replace(" ","")
        try:
            return float(s)
        except:
            pass
        if "," in s:
            try:
                return float(s.replace(".","").replace(",","."))
            except:
                pass
        return 0.0

    if "Tutar" not in df_evrak.columns:
        df_evrak["Tutar"]=0
    date_col = "Fatura Tarihi" if "Fatura Tarihi" in df_evrak.columns else "Tarih"
    if date_col not in df_evrak.columns:
        df_evrak[date_col]=pd.NaT

    df_ev = df_evrak.copy()
    df_ev["Tutar_num"] = df_ev["Tutar"].apply(smart_to_num).fillna(0.0)
    df_ev[date_col] = pd.to_datetime(df_ev[date_col], errors="coerce")
    df_ev = df_ev[df_ev[date_col].notna()]

    toplam_fatura = float(df_ev["Tutar_num"].sum())
    st.markdown(f"<div style='font-size:1.3em;color:#185a9d;font-weight:bold;'>💵 Toplam Fatura Tutarı: {toplam_fatura:,.2f} USD</div>", unsafe_allow_html=True)

    if not df_ev.empty:
        min_ts = df_ev[date_col].min()
        max_ts = df_ev[date_col].max()
        d1,d2 = st.date_input("📅 Tarih Aralığı", value=(min_ts.date(), max_ts.date()))
        start_ts = pd.to_datetime(d1)
        end_ts = pd.to_datetime(d2) + pd.Timedelta(days=1) - pd.Timedelta(milliseconds=1)
        mask = df_ev[date_col].between(start_ts, end_ts, inclusive="both")
        df_range = df_ev[mask]
        aralik_toplam = float(df_range["Tutar_num"].sum())
        st.markdown(f"<div style='font-size:1.2em;color:#f7971e;font-weight:bold;'>📊 {d1} - {d2} Arası Toplam: {aralik_toplam:,.2f} USD</div>", unsafe_allow_html=True)
        show_cols = ["Müşteri Adı","Fatura No",date_col,"Tutar"]
        show_cols = [c for c in show_cols if c in df_range.columns]
        st.dataframe(df_range[show_cols].sort_values(by=date_col, ascending=False), use_container_width=True)
    else:
        st.info("Fatura verisi bulunamadı.")
