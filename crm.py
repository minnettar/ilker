import streamlit as st
import pandas as pd
import numpy as np
import io, os, time, datetime, re, tempfile
from email.message import EmailMessage
import smtplib

# Google API (Service Account ile)
import gspread
from google.oauth2.service_account import Credentials
from gspread_dataframe import set_with_dataframe
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload

st.set_page_config(page_title="ŞEKEROĞLU İHRACAT CRM", layout="wide")

# ==== KULLANICI GİRİŞİ SİSTEMİ ====
USERS = {
    "export1": "Seker12345!",
    "admin": "Seker12345!",
    "Boss": "Seker12345!",
}

if "user" not in st.session_state:
    st.session_state.user = None

def login_screen():
    st.title("ŞEKEROĞLU CRM - Giriş Ekranı")
    username = st.text_input("Kullanıcı Adı")
    password = st.text_input("Şifre", type="password")
    login_btn = st.button("Giriş Yap")
    if login_btn:
        if username in USERS and password == USERS[username]:
            st.session_state.user = username
            st.success("Giriş başarılı!")
            st.rerun()
        else:
            st.error("Kullanıcı adı veya şifre hatalı.")

if not st.session_state.user:
    login_screen()
    st.stop()

# Sol menüde çıkış butonu
if st.sidebar.button("Çıkış Yap"):
    st.session_state.user = None
    st.rerun()

# --- Ülke ve Temsilci Listeleri ---
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

# ===== Sabit ID'ler =====
SHEET_ID = "1A_gL11UL6JFAoZrMrg92K8bAegeCn_KzwUyU8AWzE_0"
LOGO_FILE_ID = "1DCxtSsAeR7Zfk2IQU0UMGmD0uTdNO1B3"
LOGO_LOCAL_NAME = "logo1.png"
EVRAK_KLASOR_ID = "14FTE1oSeIeJ6Y_7C0oQyZPKC8dK8hr1J"
FIYAT_TEKLIFI_ID = "1TNjwx-xhmlxNRI3ggCJA7jaCAu9Lt_65"

LOCAL_EXCEL = "temp.xlsx"
SYNC_INTERVAL = 30  # yazma debounce (saniye) → 429'a düşmemek için

EXPECTED_SHEETS = [
    "Sayfa1", "Kayıtlar", "Teklifler", "Proformalar", "Evraklar", "ETA", "FuarMusteri"
]

# ===== Google Auth (st.secrets ile) =====
_SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]

@st.cache_resource(show_spinner=False)
def get_gspread_client():
    creds = Credentials.from_service_account_info(st.secrets["gcp_service_account"], scopes=_SCOPES)
    return gspread.authorize(creds)

@st.cache_resource(show_spinner=False)
def get_drive_service():
    creds = Credentials.from_service_account_info(st.secrets["gcp_service_account"], scopes=_SCOPES)
    return build("drive", "v3", credentials=creds, cache_discovery=False)

GC = get_gspread_client()
DRIVE = get_drive_service()

def ensure_logo():
    if os.path.exists(LOGO_LOCAL_NAME):
        return
    try:
        req = DRIVE.files().get_media(fileId=LOGO_FILE_ID)
        with open(LOGO_LOCAL_NAME, "wb") as fh:
            downloader = MediaIoBaseDownload(fh, req)
            done = False
            while not done:
                status, done = downloader.next_chunk()
    except Exception as e:
        st.warning(f"Logo indirilemedi: {e}")

def ensure_worksheets():
    sh = GC.open_by_key(SHEET_ID)
    have = {ws.title for ws in sh.worksheets()}
    for name in EXPECTED_SHEETS:
        if name not in have:
            sh.add_worksheet(title=name, rows=1000, cols=26)

# ===== Sheets / Local I/O =====
_last_sync_time = 0.0

def _debounce_ok() -> bool:
    global _last_sync_time
    now = time.time()
    if (now - _last_sync_time) < SYNC_INTERVAL:
        return False
    _last_sync_time = now
    return True

def read_all_from_sheet() -> dict:
    sh = GC.open_by_key(SHEET_ID)
    dfs = {}
    for name in EXPECTED_SHEETS:
        ws = sh.worksheet(name)
        dfs[name] = pd.DataFrame(ws.get_all_records())
    return dfs

def write_all_to_sheet(dfs: dict):
    if not _debounce_ok():
        return
    sh = GC.open_by_key(SHEET_ID)
    for name in EXPECTED_SHEETS:
        df = dfs.get(name, pd.DataFrame())
        ws = sh.worksheet(name)
        ws.clear()
        if not df.empty:
            set_with_dataframe(ws, df)

def read_all_from_local(path: str = LOCAL_EXCEL) -> dict:
    dfs = {}
    if not os.path.exists(path):
        return dfs
    for name in EXPECTED_SHEETS:
        try:
            dfs[name] = pd.read_excel(path, sheet_name=name)
        except Exception:
            dfs[name] = pd.DataFrame()
    return dfs

def write_all_to_local(dfs: dict, path: str = LOCAL_EXCEL):
    with pd.ExcelWriter(path, engine="openpyxl") as writer:
        for name in EXPECTED_SHEETS:
            (dfs.get(name, pd.DataFrame())).to_excel(writer, sheet_name=name, index=False)

# ===== Global DF seti & aliaslar =====
_dfs = {name: pd.DataFrame() for name in EXPECTED_SHEETS}

def _alias_bind():
    globals()["df_musteri"]      = _dfs["Sayfa1"]
    globals()["df_kayit"]        = _dfs["Kayıtlar"]
    globals()["df_teklif"]       = _dfs["Teklifler"]
    globals()["df_proforma"]     = _dfs["Proformalar"]
    globals()["df_evrak"]        = _dfs["Evraklar"]
    globals()["df_eta"]          = _dfs["ETA"]
    globals()["df_fuar_musteri"] = _dfs["FuarMusteri"]

def _init_dataframes():
    ensure_worksheets()
    if not os.path.exists(LOCAL_EXCEL):
        # temp.xlsx yoksa Sheets'ten indir
        with st.spinner("İlk veri indiriliyor..."):
            sheet_dfs = read_all_from_sheet()
            # Boş sayfalar minimum kolonlarla başlasın
            if sheet_dfs.get("Sayfa1", pd.DataFrame()).empty:
                sheet_dfs["Sayfa1"] = pd.DataFrame(columns=[
                    "Müşteri Adı","Telefon","E-posta","Adres","Ülke",
                    "Satış Temsilcisi","Kategori","Durum","Vade (Gün)","Ödeme Şekli",
                    "Para Birimi","DT Seçimi"
                ])
            if sheet_dfs.get("Kayıtlar", pd.DataFrame()).empty:
                sheet_dfs["Kayıtlar"] = pd.DataFrame(columns=["Müşteri Adı","Tarih","Tip","Açıklama"])
            if sheet_dfs.get("Teklifler", pd.DataFrame()).empty:
                sheet_dfs["Teklifler"] = pd.DataFrame(columns=[
                    "Müşteri Adı","Tarih","Teklif No","Tutar","Ürün/Hizmet","Açıklama","Durum","PDF"
                ])
            if sheet_dfs.get("Proformalar", pd.DataFrame()).empty:
                sheet_dfs["Proformalar"] = pd.DataFrame(columns=[
                    "Müşteri Adı","Tarih","Proforma No","Tutar","Açıklama","Durum","PDF",
                    "Sipariş Formu","Vade (gün)","Sevk Durumu","Termin Tarihi","Ulaşma Tarihi",
                    "Ülke","Satış Temsilcisi","Ödeme Şekli"
                ])
            if sheet_dfs.get("Evraklar", pd.DataFrame()).empty:
                sheet_dfs["Evraklar"] = pd.DataFrame(columns=[
                    "Müşteri Adı","Proforma No","Fatura No","Fatura Tarihi","Vade (gün)","Vade Tarihi","Tutar",
                    "Ülke","Satış Temsilcisi","Ödeme Şekli",
                    "Commercial Invoice","Sağlık Sertifikası","Packing List","Konşimento","İhracat Beyannamesi",
                    "Fatura PDF","Sipariş Formu","Yük Resimleri","EK Belgeler","Ödendi","Ödeme Kanıtı"
                ])
            if sheet_dfs.get("ETA", pd.DataFrame()).empty:
                sheet_dfs["ETA"] = pd.DataFrame(columns=["Müşteri Adı","Proforma No","ETA Tarihi","Açıklama"])
            if sheet_dfs.get("FuarMusteri", pd.DataFrame()).empty:
                sheet_dfs["FuarMusteri"] = pd.DataFrame(columns=[
                    "Fuar Adı","Müşteri Adı","Ülke","Telefon","E-mail",
                    "Satış Temsilcisi","Açıklamalar","Görüşme Kalitesi","Tarih"
                ])

            write_all_to_local(sheet_dfs, LOCAL_EXCEL)
            _dfs.update(sheet_dfs)
    else:
        # temp.xlsx varsa ordan oku
        _dfs_local = read_all_from_local(LOCAL_EXCEL)
        _dfs.update(_dfs_local)

    _alias_bind()

# ===== Tek nokta kayıt API =====
def set_df(sheet_name: str, df: pd.DataFrame, autosave: bool = True):
    _dfs[sheet_name] = df if isinstance(df, pd.DataFrame) else pd.DataFrame()
    _alias_bind()
    if autosave:
        # önce lokali güncelle, sonra Sheets'e yaz (debounce)
        write_all_to_local(_dfs, LOCAL_EXCEL)
        write_all_to_sheet(_dfs)

def save_all():
    write_all_to_local(_dfs, LOCAL_EXCEL)
    write_all_to_sheet(_dfs)

# ===== Başlatma =====
with st.spinner("Veri seti hazırlanıyor..."):
    _init_dataframes()

# ===== Logo & Header =====
ensure_logo()
col1, col2 = st.columns([3, 7])
with col1:
    if os.path.exists(LOGO_LOCAL_NAME):
        st.image(LOGO_LOCAL_NAME, width=300)
with col2:
    st.markdown("""
        <style>.block-container { padding-top: 0.2rem !important; }</style>
        <div style="display:flex; flex-direction:column; align-items:flex-start; width:100%; margin-bottom:10px;">
            <h1 style="color: #219A41; font-weight: bold; font-size: 2.8em; letter-spacing:2px; margin:0; margin-top:-8px;">
                ŞEKEROĞLU İHRACAT CRM
            </h1>
        </div>
    """, unsafe_allow_html=True)

# ===== Geriye dönük uyumluluk (eski çağrılar kırılmasın) =====
def update_excel():
    """ESKİ API: İçeride yeni save_all()'ı çağırır."""
    save_all()

# ========= ŞIK SIDEBAR MENÜ (RADIO TABANLI) =========
# (Not: Boss kullanıcıda menü kısıtlı olduğu için CSS nth-child arka plan renkleri
# allowed_menus sırasına göre uygulanır; fonksiyonellikte sorun yok.)

# 1) Menü tanımı (ikonlar)
menuler = [
    ("Özet Ekran", "📊"),
    ("Cari Ekleme", "🧑‍💼"),
    ("Müşteri Listesi", "📒"),
    ("Görüşme / Arama / Ziyaret Kayıtları", "☎️"),
    ("Fiyat Teklifleri", "💰"),
    ("Proforma Takibi", "📄"),
    ("Güncel Sipariş Durumu", "🚚"),
    ("Fatura & İhracat Evrakları", "📑"),
    ("Vade Takibi", "⏰"),
    ("ETA Takibi", "🛳️"),
    ("Fuar Müşteri Kayıtları", "🎫"),
    ("Medya Çekmecesi", "🗂️"),
    ("Satış Performansı", "📈"),
]

# 2) Kullanıcıya göre izinli menüler
if st.session_state.user == "Boss":
    allowed_menus = [("Özet Ekran", "📊")]
else:
    allowed_menus = menuler

# 3) Etiketler ve haritalar
labels = [f"{ikon} {isim}" for (isim, ikon) in allowed_menus]
name_by_label = {f"{ikon} {isim}": isim for (isim, ikon) in allowed_menus}
label_by_name = {isim: f"{ikon} {isim}" for (isim, ikon) in allowed_menus}

# 4) Varsayılan state
if "menu_state" not in st.session_state:
    st.session_state.menu_state = allowed_menus[0][0]

# 5) CSS (radio’yu kart gibi; input’u gizlemiyoruz)
st.sidebar.markdown("""
<style>
section[data-testid="stSidebar"] { padding-top: 0.5rem; }
div[data-testid="stSidebar"] .stRadio > div { gap: 10px !important; }
div[data-testid="stSidebar"] .stRadio label {
    border-radius: 12px;
    padding: 12px 14px;
    margin-bottom: 6px;
    border: 1px solid rgba(255,255,255,0.12);
    display: flex; align-items: center;
    transition: transform .06s ease, filter .15s ease;
    box-shadow: 0 1px 4px rgba(0,0,0,.08);
}
div[data-testid="stSidebar"] .stRadio label span { font-weight: 700; color: #fff; }
div[data-testid="stSidebar"] .stRadio label:hover { filter: brightness(1.08); transform: translateY(-1px); }
div[data-testid="stSidebar"] .stRadio [aria-checked="true"] { outline: 2px solid rgba(255,255,255,0.25); }

/* Kart arka planları (sıra) */
div[data-testid="stSidebar"] .stRadio label:nth-child(1)  { background: linear-gradient(90deg,#1D976C,#93F9B9); }  /* Özet */
div[data-testid="stSidebar"] .stRadio label:nth-child(2)  { background: linear-gradient(90deg,#43cea2,#185a9d); }  /* Cari */
div[data-testid="stSidebar"] .stRadio label:nth-child(3)  { background: linear-gradient(90deg,#ffb347,#ffcc33); }  /* Müşteri */
div[data-testid="stSidebar"] .stRadio label:nth-child(4)  { background: linear-gradient(90deg,#ff5e62,#ff9966); }  /* Görüşme */
div[data-testid="stSidebar"] .stRadio label:nth-child(5)  { background: linear-gradient(90deg,#8e54e9,#4776e6); }  /* Teklif */
div[data-testid="stSidebar"] .stRadio label:nth-child(6)  { background: linear-gradient(90deg,#11998e,#38ef7d); }  /* Proforma */
div[data-testid="stSidebar"] .stRadio label:nth-child(7)  { background: linear-gradient(90deg,#f7971e,#ffd200); }  /* Sipariş */
div[data-testid="stSidebar"] .stRadio label:nth-child(8)  { background: linear-gradient(90deg,#f953c6,#b91d73); }  /* Evrak */
div[data-testid="stSidebar"] .stRadio label:nth-child(9)  { background: linear-gradient(90deg,#43e97b,#38f9d7); }  /* Vade */
div[data-testid="stSidebar"] .stRadio label:nth-child(10) { background: linear-gradient(90deg,#f857a6,#ff5858); }  /* ETA */
div[data-testid="stSidebar"] .stRadio label:nth-child(11) { background: linear-gradient(90deg,#8e54e9,#bd4de6); }  /* Fuar */
div[data-testid="stSidebar"] .stRadio label:nth-child(12) { background: linear-gradient(90deg,#4b79a1,#283e51); }  /* Medya */
div[data-testid="stSidebar"] .stRadio label:nth-child(13) { background: linear-gradient(90deg,#2b5876,#4e4376); }  /* Satış Perf. */
div[data-testid="stSidebar"] .stRadio label:nth-child(14) { background: linear-gradient(90deg,#667eea,#764ba2); }  /* Veritabanı */
</style>
""", unsafe_allow_html=True)

# 6) Callback: seçilince anında state yaz
def _on_menu_change():
    sel_label = st.session_state.get("menu_radio_label")
    st.session_state.menu_state = name_by_label.get(sel_label, allowed_menus[0][0])

# 7) Radio’yu mevcut state’e göre başlat
current_label = label_by_name.get(st.session_state.menu_state, labels[0])
current_index = labels.index(current_label) if current_label in labels else 0

st.sidebar.radio(
    "Menü",
    labels,
    index=current_index,
    label_visibility="collapsed",
    key="menu_radio_label",
    on_change=_on_menu_change
)

# 8) Kullanım: seçili menü adı
menu = st.session_state.menu_state
# ========= /ŞIK MENÜ =========


# ========== E-Posta Yardımcıları ==========
import smtplib
from email.message import EmailMessage

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
    password = "vbgvforwwbcpzhxf"

    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = from_email
    msg["To"] = ", ".join(to_email) if isinstance(to_email, (list, tuple)) else str(to_email)
    msg.set_content(body)

    with open(file_path, "rb") as f:
        msg.add_attachment(f.read(), maintype="text", subtype="plain", filename="yeni_cari.txt")

    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as smtp:
        smtp.login(from_email, password)
        smtp.send_message(msg)

### ===========================
### === CARİ EKLEME MENÜSÜ ===
### ===========================

# Google Sheets'e (SHEET_ID) yazan yardımcı (429 backoff'lu)
def _write_customers_to_gsheet(df_customers: pd.DataFrame) -> bool:
    try:
        import time
        import gspread
        from google.oauth2.service_account import Credentials as _SA_Credentials
        from gspread_dataframe import set_with_dataframe

        # Service Account bilgisi secrets'tan okunur
        sa_info = dict(st.secrets.get("gcp_service_account", {}))
        if not sa_info:
            return False

        scopes = [
            "https://www.googleapis.com/auth/spreadsheets",
            "https://www.googleapis.com/auth/drive",
        ]
        creds = _SA_Credentials.from_service_account_info(sa_info, scopes=scopes)
        gc = gspread.authorize(creds)
        sh = gc.open_by_key(SHEET_ID)

        try:
            ws = sh.worksheet("Sayfa1")
        except Exception:
            ws = sh.add_worksheet(title="Sayfa1", rows=1000, cols=26)

        # 429 kotasına karşı 3 deneme (0.8s, 1.6s, 3.2s)
        delay = 0.8
        for attempt in range(3):
            try:
                ws.clear()
                set_with_dataframe(ws, df_customers.fillna(""))
                return True
            except Exception as e:
                msg = str(e)
                if "429" in msg or "Quota exceeded" in msg:
                    time.sleep(delay)
                    delay *= 2
                    continue
                else:
                    # 429 dışı hata → fallback
                    return False
        # 3 deneme de 429 ile sonuçlanırsa False
        return False

    except Exception:
        return False


# Cari Ekleme Formu
if menu == "Cari Ekleme":
    st.markdown("<h2 style='color:#219A41; font-weight:bold;'>Yeni Müşteri Ekle</h2>", unsafe_allow_html=True)
    with st.form("add_customer"):
        name = st.text_input("Müşteri Adı")
        phone = st.text_input("Telefon")
        email = st.text_input("E-posta")
        address = st.text_area("Adres")
        ulke = st.selectbox("Ülke", ulke_listesi)
        temsilci = st.selectbox("Satış Temsilcisi", temsilci_listesi)
        kategori = st.selectbox("Kategori", ["Avrupa bayi", "bayi", "müşteri", "yeni müşteri"])
        aktif_pasif = st.selectbox("Durum", ["Aktif", "Pasif"])
        vade_gun = st.number_input("Vade (Gün Sayısı)", min_value=0, max_value=365, value=0, step=1)
        odeme_sekli = st.selectbox("Ödeme Şekli", ["Peşin", "Mal Mukabili", "Vesaik Mukabili", "Akreditif", "Diğer"])
        para_birimi = st.selectbox("Para Birimi", ["EURO", "USD", "TL", "RUBLE"])
        dt_secim = st.selectbox("DT Seçin", ["DT-1", "DT-2", "DT-3", "DT-4"])

        submitted = st.form_submit_button("Kaydet")

    if submitted:
        if name.strip() == "":
            st.error("Müşteri adı boş olamaz!")
        else:
            new_row = {
                "Müşteri Adı": name,
                "Telefon": phone,
                "E-posta": email,
                "Adres": address,
                "Ülke": ulke,
                "Satış Temsilcisi": temsilci,
                "Kategori": kategori,
                "Durum": aktif_pasif,
                "Vade (Gün)": vade_gun,
                "Ödeme Şekli": odeme_sekli,
                "Para Birimi": para_birimi,
                "DT Seçimi": dt_secim,
            }
            # DataFrame'e ekle
            df_musteri = pd.concat([df_musteri, pd.DataFrame([new_row])], ignore_index=True)

            # Önce Google Sheets'e yazmayı dene (429 backoff'lu)
            wrote_sheet = _write_customers_to_gsheet(df_musteri)

            # Her durumda lokal temp.xlsx'i güncelle (senin mevcut fonksiyonun)
            try:
                update_excel()
            except Exception as e:
                st.warning(f"Yerel temp.xlsx güncellenemedi: {e}")

            # Mail + TXT
            try:
                yeni_cari_txt_olustur(new_row)
                send_email_with_txt(
                    to_email=["muhasebe@sekeroglugroup.com", "h.boy@sekeroglugroup.com"],
                    subject="Yeni Cari Açılışı",
                    body="Muhasebe için yeni cari açılışı ekte gönderilmiştir.",
                    file_path="yeni_cari.txt"
                )
                st.success("Müşteri eklendi ve e-posta ile muhasebeye gönderildi!")
            except Exception as e:
                st.warning(f"Müşteri eklendi ama e-posta gönderilemedi: {e}")

            # Kullanıcıya senkron özeti
            if wrote_sheet:
                st.toast("Google Sheets güncellendi.")
            else:
                st.toast("Sheets yazımı atlandı (quota/hata). Lokal dosya güncellendi.", icon="⚠️")

            st.rerun()

### ===========================
### === MÜŞTERİ LİSTESİ MENÜSÜ ===
### ===========================

import numpy as np  # Eksik bilgi mesajı için gerekli

# Eğer önceki blokta tanımlı değilse, NameError olmaması için basit bir fallback tanımı
try:
    _write_customers_to_gsheet
except NameError:
    def _write_customers_to_gsheet(df_customers: pd.DataFrame) -> bool:
        return False

# Kolon güvenliği
if "Vade (Gün)" not in df_musteri.columns:
    df_musteri["Vade (Gün)"] = ""
if "Ülke" not in df_musteri.columns:
    df_musteri["Ülke"] = ""
if "Satış Temsilcisi" not in df_musteri.columns:
    df_musteri["Satış Temsilcisi"] = ""
if "Ödeme Şekli" not in df_musteri.columns:
    df_musteri["Ödeme Şekli"] = ""

if menu == "Müşteri Listesi":
    st.markdown("<h2 style='color:#219A41; font-weight:bold;'>Müşteri Listesi</h2>", unsafe_allow_html=True)
    
    # Sadece Aktif müşterileri göster
    if not df_musteri.empty:
        aktif_df = df_musteri[df_musteri["Durum"] == "Aktif"].sort_values("Müşteri Adı").reset_index(drop=True)
        # Eksik (NaN veya boş) alanlara uyarı metni ekle
        aktif_df = aktif_df.replace({np.nan: "Eksik bilgi, lütfen tamamlayın", "": "Eksik bilgi, lütfen tamamlayın"})
        if aktif_df.shape[0] == 0:
            st.markdown("<div style='color:#b00020; font-weight:bold; font-size:1.2em;'>Aktif müşteri kaydı yok.</div>", unsafe_allow_html=True)
        else:
            st.dataframe(aktif_df, use_container_width=True)

        st.markdown("<h4 style='margin-top: 32px;'>Müşteri Düzenle</h4>", unsafe_allow_html=True)

        # Kombo box seçenekleri yine tüm müşterilerden, alfabetik
        df_musteri_sorted = df_musteri.sort_values("Müşteri Adı").reset_index(drop=True)
        musteri_options = df_musteri_sorted.index.tolist()

        sec_index = st.selectbox(
            "Düzenlenecek Müşteriyi Seçin",
            options=musteri_options,
            format_func=lambda i: f"{df_musteri_sorted.at[i,'Müşteri Adı']} ({df_musteri_sorted.at[i,'Kategori']})"
        )

        with st.form("edit_existing_customer"):
            name = st.text_input("Müşteri Adı", value=df_musteri_sorted.at[sec_index, "Müşteri Adı"])
            phone = st.text_input("Telefon", value=df_musteri_sorted.at[sec_index, "Telefon"])
            email = st.text_input("E-posta", value=df_musteri_sorted.at[sec_index, "E-posta"])
            address = st.text_area("Adres", value=df_musteri_sorted.at[sec_index, "Adres"])
            ulke = st.selectbox(
                "Ülke", ulke_listesi,
                index=ulke_listesi.index(df_musteri_sorted.at[sec_index, "Ülke"])
                      if df_musteri_sorted.at[sec_index, "Ülke"] in ulke_listesi else 0
            )
            temsilci = st.selectbox(
                "Satış Temsilcisi", temsilci_listesi,
                index=temsilci_listesi.index(df_musteri_sorted.at[sec_index, "Satış Temsilcisi"])
                      if df_musteri_sorted.at[sec_index, "Satış Temsilcisi"] in temsilci_listesi else 0
            )
            kategori_sec = ["Avrupa bayi", "bayi", "müşteri", "yeni müşteri"]
            kategori = st.selectbox(
                "Kategori", sorted(kategori_sec),
                index=sorted(kategori_sec).index(df_musteri_sorted.at[sec_index, "Kategori"])
                      if df_musteri_sorted.at[sec_index, "Kategori"] in kategori_sec else 0
            )
            aktif_pasif = st.selectbox(
                "Durum", ["Aktif", "Pasif"],
                index=0 if df_musteri_sorted.at[sec_index, "Durum"] == "Aktif" else 1
            )
            vade = st.text_input("Vade (Gün)", value=str(df_musteri_sorted.at[sec_index, "Vade (Gün)"]) if "Vade (Gün)" in df_musteri_sorted.columns else "")
            odeme_list = ["Peşin", "Mal Mukabili", "Vesaik Mukabili", "Akreditif", "Diğer"]
            odeme_sekli = st.selectbox(
                "Ödeme Şekli", odeme_list,
                index=odeme_list.index(df_musteri_sorted.at[sec_index, "Ödeme Şekli"])
                      if df_musteri_sorted.at[sec_index, "Ödeme Şekli"] in odeme_list else 0
            )

            guncelle = st.form_submit_button("Güncelle")

        if guncelle:
            # Eski indexi bulup güncelle (çünkü sorted kopyada çalışıyoruz)
            filtre = (df_musteri["Müşteri Adı"] == df_musteri_sorted.at[sec_index, "Müşteri Adı"])
            if filtre.any():
                orj_idx = df_musteri[filtre].index[0]
                df_musteri.at[orj_idx, "Müşteri Adı"] = name
                df_musteri.at[orj_idx, "Telefon"] = phone
                df_musteri.at[orj_idx, "E-posta"] = email
                df_musteri.at[orj_idx, "Adres"] = address
                df_musteri.at[orj_idx, "Ülke"] = ulke
                df_musteri.at[orj_idx, "Satış Temsilcisi"] = temsilci
                df_musteri.at[orj_idx, "Kategori"] = kategori
                df_musteri.at[orj_idx, "Durum"] = aktif_pasif
                df_musteri.at[orj_idx, "Vade (Gün)"] = vade
                df_musteri.at[orj_idx, "Ödeme Şekli"] = odeme_sekli

                # Önce Sheets'e yaz (429 için backoff'lu helper)
                wrote_sheet = _write_customers_to_gsheet(df_musteri)

                # Lokal dosyayı da güncelle (her durumda)
                try:
                    update_excel()
                except Exception as e:
                    st.warning(f"Yerel temp.xlsx güncellenemedi: {e}")

                if wrote_sheet:
                    st.toast("Google Sheets güncellendi.")
                else:
                    st.toast("Sheets yazımı atlandı (quota/hata). Lokal dosya güncellendi.", icon="⚠️")

                st.success("Müşteri bilgisi güncellendi!")
                st.rerun()
            else:
                st.warning("Beklenmeyen hata: Kayıt bulunamadı.")

        # Silme butonu
        st.markdown("<h4 style='margin-top: 32px;'>Müşteri Sil</h4>", unsafe_allow_html=True)
        sil_btn = st.button("Seçili Müşteriyi Sil")
        if sil_btn:
            filtre = (df_musteri["Müşteri Adı"] == df_musteri_sorted.at[sec_index, "Müşteri Adı"])
            if filtre.any():
                orj_idx = df_musteri[filtre].index[0]
                df_musteri = df_musteri.drop(orj_idx).reset_index(drop=True)

                # Önce Sheets'e yaz
                wrote_sheet = _write_customers_to_gsheet(df_musteri)

                # Lokal dosyayı da güncelle
                try:
                    update_excel()
                except Exception as e:
                    st.warning(f"Yerel temp.xlsx güncellenemedi: {e}")

                if wrote_sheet:
                    st.toast("Google Sheets güncellendi.")
                else:
                    st.toast("Sheets yazımı atlandı (quota/hata). Lokal dosya güncellendi.", icon="⚠️")

                st.success("Müşteri kaydı silindi!")
                st.rerun()
            else:
                st.warning("Beklenmeyen hata: Silinecek kayıt bulunamadı.")
    else:
        st.markdown("<div style='color:#b00020; font-weight:bold; font-size:1.2em;'>Henüz müşteri kaydı yok.</div>", unsafe_allow_html=True)

### ===========================
### === GÖRÜŞME / ARAMA / ZİYARET KAYITLARI MENÜSÜ ===
### ===========================

# 429 için backoff’lu, sadece "Kayıtlar" sayfasını yazan yardımcı
try:
    _write_kayit_to_gsheet
except NameError:
    def _write_kayit_to_gsheet(df_kayit: pd.DataFrame) -> bool:
        """SHEET_ID içindeki 'Kayıtlar' sayfasını komple yazar.
        429 için basit exponential backoff uygular. Başarılıysa True."""
        try:
            get_gspread_client  # globalde var mı?
            SHEET_ID            # globalde var mı?
        except NameError:
            return False

        gc = get_gspread_client()
        if gc is None:
            return False

        import time
        try:
            from gspread_dataframe import set_with_dataframe
        except Exception:
            # kütüphane yoksa sessizce atla (requirements’a eklenmeli)
            return False

        sh = gc.open_by_key(SHEET_ID)
        try:
            ws = sh.worksheet("Kayıtlar")
        except Exception:
            ws = sh.add_worksheet(title="Kayıtlar", rows=1000, cols=26)

        # Basit backoff: 1s, 2s, 4s, 8s (maks 4 deneme)
        wait = 1.0
        for _ in range(4):
            try:
                ws.clear()
                set_with_dataframe(ws, df_kayit if isinstance(df_kayit, pd.DataFrame) else pd.DataFrame())
                return True
            except Exception as e:
                msg = str(e)
                if "429" in msg or "Quota exceeded" in msg or "quota" in msg.lower():
                    time.sleep(wait)
                    wait *= 2
                    continue
                # 429 dışı hata → bırak
                break
        return False

elif menu == "Görüşme / Arama / Ziyaret Kayıtları":
    # --- Her menüye geçişte dataframe’leri tekrar yükle ---
    if os.path.exists("temp.xlsx"):
        df_musteri = pd.read_excel("temp.xlsx", sheet_name=0)
        try:
            df_kayit = pd.read_excel("temp.xlsx", sheet_name="Kayıtlar")
        except Exception:
            df_kayit = pd.DataFrame(columns=["Müşteri Adı", "Tarih", "Tip", "Açıklama"])
    else:
        df_musteri = pd.DataFrame(columns=["Müşteri Adı", "Telefon", "E-posta", "Adres", "Ek Bilgi"])
        df_kayit = pd.DataFrame(columns=["Müşteri Adı", "Tarih", "Tip", "Açıklama"])

    st.markdown("<h2 style='color:#219A41; font-weight:bold;'>Görüşme / Arama / Ziyaret Kayıtları</h2>", unsafe_allow_html=True)

    # --- Müşterileri alfabetik sırala ve başa boş ekle ---
    musteri_listesi = [
        m for m in df_musteri["Müşteri Adı"].dropna().unique() if isinstance(m, str) and m.strip() != ""
    ]
    musteri_options = [""] + sorted(musteri_listesi)

    st.subheader("Kayıt Ekranı")

    secim = st.radio(
        "Lütfen işlem seçin:",
        ["Yeni Kayıt", "Eski Kayıt", "Tarih Aralığı ile Kayıtlar"]
    )

    # === YENİ KAYIT ===
    if secim == "Yeni Kayıt":
        with st.form("add_kayit"):
            musteri_sec = st.selectbox("Müşteri Seç", musteri_options, index=0)
            tarih = st.date_input("Tarih", value=datetime.date.today(), format="DD/MM/YYYY")
            tip = st.selectbox("Tip", ["Arama", "Görüşme", "Ziyaret"])
            aciklama = st.text_area("Açıklama")
            submitted = st.form_submit_button("Kaydet")
            if submitted:
                if not musteri_sec:
                    st.error("Lütfen bir müşteri seçiniz.")
                else:
                    new_row = {
                        "Müşteri Adı": musteri_sec,
                        "Tarih": tarih,
                        "Tip": tip,
                        "Açıklama": aciklama
                    }
                    df_kayit = pd.concat([df_kayit, pd.DataFrame([new_row])], ignore_index=True)

                    # Önce Sheets'e yazmayı dene (429 backoff’lu)
                    wrote_sheet = _write_kayit_to_gsheet(df_kayit)

                    # Lokal temp.xlsx’i her durumda güncelle
                    try:
                        update_excel()
                    except Exception as e:
                        st.warning(f"Yerel temp.xlsx güncellenemedi: {e}")

                    if wrote_sheet:
                        st.toast("Google Sheets güncellendi.")
                    else:
                        st.toast("Sheets yazımı atlandı (quota/hata). Lokal dosya güncellendi.", icon="⚠️")

                    st.success("Kayıt eklendi!")
                    st.rerun()

    # === ESKİ KAYIT ===
    elif secim == "Eski Kayıt":
        musteri_sec = st.selectbox("Müşteri Seç", musteri_options, index=0, key="eski_musteri")
        if musteri_sec:
            musteri_kayitlar = df_kayit[df_kayit["Müşteri Adı"] == musteri_sec].sort_values("Tarih", ascending=False)
            if not musteri_kayitlar.empty:
                tablo_goster = musteri_kayitlar.copy()
                if "Tarih" in tablo_goster.columns:
                    tablo_goster["Tarih"] = pd.to_datetime(tablo_goster["Tarih"], errors="coerce").dt.strftime('%d/%m/%Y')
                st.dataframe(tablo_goster, use_container_width=True)
            else:
                st.info("Seçili müşteri için kayıt yok.")
        else:
            st.info("Lütfen müşteri seçin.")

    # === TARİH ARALIĞI İLE KAYITLAR ===
    elif secim == "Tarih Aralığı ile Kayıtlar":
        col1, col2 = st.columns(2)
        with col1:
            baslangic = st.date_input("Başlangıç Tarihi", value=datetime.date.today() - datetime.timedelta(days=7), format="DD/MM/YYYY")
        with col2:
            bitis = st.date_input("Bitiş Tarihi", value=datetime.date.today(), format="DD/MM/YYYY")
        tarih_arasi = df_kayit[
            (pd.to_datetime(df_kayit["Tarih"], errors="coerce") >= pd.to_datetime(baslangic)) &
            (pd.to_datetime(df_kayit["Tarih"], errors="coerce") <= pd.to_datetime(bitis))
        ]
        if not tarih_arasi.empty:
            tablo_goster = tarih_arasi.copy()
            if "Tarih" in tablo_goster.columns:
                tablo_goster["Tarih"] = pd.to_datetime(tablo_goster["Tarih"], errors="coerce").dt.strftime('%d/%m/%Y')
            st.dataframe(tablo_goster.sort_values("Tarih", ascending=False), use_container_width=True)
        else:
            st.info("Bu tarihler arasında kayıt yok.")

### ===========================
### --- FİYAT TEKLİFLERİ MENÜSÜ ---
### ===========================

elif menu == "Fiyat Teklifleri":
    st.markdown("<h2 style='color:#219A41; font-weight:bold;'>Fiyat Teklifleri</h2>", unsafe_allow_html=True)

    # Teklif No Otomatik Üretici
    def otomatik_teklif_no():
        if df_teklif.empty or "Teklif No" not in df_teklif.columns:
            return "TKF-0001"
        mevcut_nolar = pd.to_numeric(
            df_teklif["Teklif No"].astype(str).str.extract(r'(\d+)$')[0], errors='coerce'
        ).dropna().astype(int)
        if mevcut_nolar.empty:
            return "TKF-0001"
        yeni_no = max(mevcut_nolar) + 1
        return f"TKF-{yeni_no:04d}"

    # Dosya güvenli silme fonksiyonu
    import time
    def güvenli_sil(dosya_adı, tekrar=5, bekle=1):
        for _ in range(tekrar):
            try:
                os.remove(dosya_adı)
                return True
            except PermissionError:
                time.sleep(bekle)
        return False

    # Açık teklifleri göster
    st.subheader("Açık Pozisyondaki Teklifler Listesi")
    teklif_goster = df_teklif.copy()
    if "Tarih" in teklif_goster.columns:
        teklif_goster["Tarih"] = pd.to_datetime(teklif_goster["Tarih"], errors="coerce").dt.strftime("%d/%m/%Y")
    acik_teklifler = teklif_goster[teklif_goster["Durum"] == "Açık"].sort_values(by=["Müşteri Adı", "Teklif No"])
    acik_teklif_sayi = len(acik_teklifler)
    try:
        toplam_teklif = pd.to_numeric(acik_teklifler["Tutar"], errors="coerce").sum()
    except Exception:
        toplam_teklif = 0
    st.markdown(
        f"<div style='font-size:1.1em; color:#11998e; font-weight:bold;'>"
        f"Toplam: {toplam_teklif:,.2f} $ | Toplam Açık Teklif: {acik_teklif_sayi} adet</div>",
        unsafe_allow_html=True
    )
    st.dataframe(acik_teklifler[[
        "Müşteri Adı", "Tarih", "Teklif No", "Tutar", "Ürün/Hizmet", "Açıklama"
    ]], use_container_width=True)

    # İşlem seçimi
    st.markdown("##### Lütfen bir işlem seçin")
    col1, col2 = st.columns(2)
    with col1:
        yeni_teklif_buton = st.button("Yeni Teklif")
    with col2:
        eski_teklif_buton = st.button("Eski Teklif")

    if "teklif_view" not in st.session_state:
        st.session_state['teklif_view'] = None
    if yeni_teklif_buton:
        st.session_state['teklif_view'] = "yeni"
    if eski_teklif_buton:
        st.session_state['teklif_view'] = "eski"

    # === YENİ TEKLİF EKLEME ===
    if st.session_state['teklif_view'] == "yeni":
        musteri_list = [""] + sorted(df_musteri["Müşteri Adı"].dropna().unique().tolist())
        st.subheader("Yeni Teklif Ekle")
        with st.form("add_teklif"):
            musteri_sec = st.selectbox("Müşteri Seç", musteri_list, key="yeni_teklif_musteri")
            tarih = st.date_input("Tarih", value=datetime.date.today(), format="DD/MM/YYYY")
            teklif_no = st.text_input("Teklif No", value=otomatik_teklif_no())
            tutar = st.text_input("Tutar ($)")
            urun = st.text_input("Ürün/Hizmet")
            aciklama = st.text_area("Açıklama")
            durum = st.selectbox("Durum", ["Açık", "Sonuçlandı", "Beklemede"])
            pdf_file = st.file_uploader("Teklif PDF", type="pdf")
            submitted = st.form_submit_button("Kaydet")
            pdf_link = ""
            if submitted:
                if not teklif_no.strip():
                    st.error("Teklif No boş olamaz!")
                elif not musteri_sec:
                    st.error("Lütfen müşteri seçiniz!")
                else:
                    # PDF varsa Drive'a yükle
                    if pdf_file:
                        temiz_musteri = "".join(x if x.isalnum() else "_" for x in str(musteri_sec))
                        temiz_tarih = str(tarih).replace("-", "")
                        pdf_filename = f"{temiz_musteri}__{temiz_tarih}__{teklif_no}.pdf"
                        temp_path = os.path.join(".", pdf_filename)
                        with open(temp_path, "wb") as f:
                            f.write(pdf_file.read())
                        gfile = drive.CreateFile({'title': pdf_filename, 'parents': [{'id': FIYAT_TEKLIFI_ID}]})
                        gfile.SetContentFile(temp_path)
                        gfile.Upload()
                        pdf_link = f"https://drive.google.com/file/d/{gfile['id']}/view?usp=sharing"
                        güvenli_sil(temp_path)
                    # Yeni satır ekle
                    new_row = {
                        "Müşteri Adı": musteri_sec,
                        "Tarih": tarih,
                        "Teklif No": teklif_no,
                        "Tutar": tutar,
                        "Ürün/Hizmet": urun,
                        "Açıklama": aciklama,
                        "Durum": durum,
                        "PDF": pdf_link
                    }
                    df_teklif = pd.concat([df_teklif, pd.DataFrame([new_row])], ignore_index=True)
                    update_excel()
                    st.success("Teklif eklendi!")
                    st.session_state['teklif_view'] = None
                    st.rerun()

    # === ESKİ TEKLİFLER ===
    if st.session_state['teklif_view'] == "eski":
        st.subheader("Eski Teklifler Listesi")
        eski_teklif_musteriler = [""] + sorted(df_teklif["Müşteri Adı"].dropna().unique().tolist())
        secili_musteri = st.selectbox("Müşteri Seçiniz", eski_teklif_musteriler, key="eski_teklif_musteri_sec")
        if secili_musteri:
            teklifler_bu_musteri = df_teklif[df_teklif["Müşteri Adı"] == secili_musteri].sort_values(by="Tarih", ascending=False)
            if teklifler_bu_musteri.empty:
                st.info("Bu müşteriye ait teklif kaydı yok.")
            else:
                teklif_index = st.selectbox(
                    "Teklif Seçiniz",
                    teklifler_bu_musteri.index,
                    format_func=lambda i: f"{teklifler_bu_musteri.at[i, 'Teklif No']} | {teklifler_bu_musteri.at[i, 'Tarih']}"
                )
                secilen_teklif = teklifler_bu_musteri.loc[teklif_index]
                if secilen_teklif["PDF"]:
                    st.markdown(f"**Teklif PDF:** [{secilen_teklif['Teklif No']}]({secilen_teklif['PDF']})", unsafe_allow_html=True)
                else:
                    st.info("PDF bulunamadı.")
                st.write("**Teklif Detayları:**")
                st.table({
                    "Müşteri Adı": [secilen_teklif["Müşteri Adı"]],
                    "Tarih": [secilen_teklif["Tarih"]],
                    "Teklif No": [secilen_teklif["Teklif No"]],
                    "Tutar": [secilen_teklif["Tutar"]],
                    "Ürün/Hizmet": [secilen_teklif["Ürün/Hizmet"]],
                    "Açıklama": [secilen_teklif["Açıklama"]],
                    "Durum": [secilen_teklif["Durum"]],
                })

### ===========================
### --- PROFORMA TAKİBİ MENÜSÜ ---
### ===========================

elif menu == "Proforma Takibi":
    st.markdown("<h2 style='color:#219A41; font-weight:bold;'>Proforma Takibi</h2>", unsafe_allow_html=True)

    # ==== Yardımcılar: 429 throttling ile güvenli Drive upload ====
    import time

    def _throttled_upload(local_path: str, title: str, parent_id: str, max_retries: int = 4) -> str:
        """
        local_path dosyasını Google Drive'a yükler, link döndürür.
        429 (quota) durumunda exponential backoff ile tekrar dener.
        Başarısız olursa boş string döner.
        """
        for attempt in range(max_retries):
            try:
                meta = {'title': title, 'parents': [{'id': parent_id}]}
                gfile = drive.CreateFile(meta)
                gfile.SetContentFile(local_path)
                # Shared Drive/Ortak sürücüler için destek param'ı
                gfile.Upload(param={'supportsAllDrives': True})
                return f"https://drive.google.com/file/d/{gfile['id']}/view?usp=sharing"
            except Exception as e:
                msg = str(e)
                # 429'a karşı bekleme
                if "429" in msg or "Rate Limit" in msg or "quota" in msg.lower():
                    wait = min(2 ** attempt, 8)  # 1,2,4,8 sn
                    st.info(f"Yükleme limiti aşıldı, tekrar denenecek... ({attempt+1}/{max_retries})")
                    time.sleep(wait)
                    continue
                else:
                    st.warning(f"Dosya yüklenemedi: {e}")
                    break
        return ""

    # ==== Eksik sütunları güvene al ====
    for col in ["Vade (gün)", "Sipariş Formu", "Durum", "PDF", "Sevk Durumu",
                "Ülke", "Satış Temsilcisi", "Ödeme Şekli"]:
        if col not in df_proforma.columns:
            df_proforma[col] = ""

    beklemede_kayitlar = df_proforma[df_proforma["Durum"] == "Beklemede"]

    if not beklemede_kayitlar.empty:
        st.subheader("Bekleyen Proformalar")
        st.dataframe(
            beklemede_kayitlar[
                ["Müşteri Adı", "Proforma No", "Tarih", "Tutar", "Durum", "Vade (gün)", "Sevk Durumu"]
            ],
            use_container_width=True
        )

    musteri_list = sorted([
        x for x in df_musteri["Müşteri Adı"].dropna().unique()
        if isinstance(x, str) and x.strip() != ""
    ]) if not df_musteri.empty else []
    musteri_sec = st.selectbox("Müşteri Seç", [""] + musteri_list)

    if musteri_sec:
        st.write("Proforma işlemi seçin:")
        islem = st.radio("", ["Yeni Kayıt", "Eski Kayıt"], horizontal=True)

        # ---------- YENİ KAYIT ----------
        if islem == "Yeni Kayıt":
            musteri_info = df_musteri[df_musteri["Müşteri Adı"] == musteri_sec]
            default_ulke = musteri_info["Ülke"].values[0] if not musteri_info.empty else ""
            default_temsilci = musteri_info["Satış Temsilcisi"].values[0] if not musteri_info.empty else ""
            default_odeme = musteri_info["Ödeme Şekli"].values[0] if not musteri_info.empty else ""

            with st.form("add_proforma"):
                tarih = st.date_input("Tarih", value=datetime.date.today(), format="DD/MM/YYYY")
                proforma_no = st.text_input("Proforma No")
                tutar = st.text_input("Tutar ($)")
                vade_gun = st.text_input("Vade (gün)")
                ulke = st.text_input("Ülke", value=default_ulke, disabled=True)
                temsilci = st.text_input("Satış Temsilcisi", value=default_temsilci, disabled=True)
                odeme = st.text_input("Ödeme Şekli", value=default_odeme, disabled=True)
                aciklama = st.text_area("Açıklama")
                durum = st.selectbox("Durum", ["Beklemede", "İptal", "Faturası Kesildi", "Siparişe Dönüştü"])
                pdf_file = st.file_uploader("Proforma PDF", type="pdf")
                submitted = st.form_submit_button("Kaydet")
                pdf_link = ""

                if submitted:
                    if not proforma_no.strip() or not vade_gun.strip():
                        st.error("Proforma No ve Vade (gün) boş olamaz!")
                    else:
                        # PDF yüklendiyse Drive'a gönder (EVRAK_KLASOR_ID kullanılacak)
                        if pdf_file:
                            pdf_filename = f"{musteri_sec}_{tarih}_{proforma_no}.pdf".replace(" ", "_")
                            temp_path = os.path.join(".", pdf_filename)
                            with open(temp_path, "wb") as f:
                                f.write(pdf_file.read())
                            pdf_link = _throttled_upload(temp_path, pdf_filename, EVRAK_KLASOR_ID)
                            try:
                                os.remove(temp_path)
                            except:
                                pass
                        # Kayıt ekle (Sipariş Formu boş başlar)
                        new_row = {
                            "Müşteri Adı": musteri_sec,
                            "Tarih": tarih,
                            "Proforma No": proforma_no,
                            "Tutar": tutar,
                            "Vade (gün)": vade_gun,
                            "Ülke": default_ulke,
                            "Satış Temsilcisi": default_temsilci,
                            "Ödeme Şekli": default_odeme,
                            "Açıklama": aciklama,
                            "Durum": "Beklemede",
                            "PDF": pdf_link,
                            "Sipariş Formu": "",
                            "Sevk Durumu": ""
                        }
                        df_proforma = pd.concat([df_proforma, pd.DataFrame([new_row])], ignore_index=True)
                        update_excel()
                        st.success("Proforma eklendi!")
                        st.rerun()

        # ---------- ESKİ KAYIT ----------
        elif islem == "Eski Kayıt":
            eski_kayitlar = df_proforma[
                (df_proforma["Müşteri Adı"] == musteri_sec) &
                (df_proforma["Durum"] == "Beklemede")
            ]
            if eski_kayitlar.empty:
                st.info("Bu müşteriye ait siparişe dönüşmemiş proforma kaydı yok.")
            else:
                st.dataframe(
                    eski_kayitlar[
                        ["Müşteri Adı", "Proforma No", "Tarih", "Tutar", "Durum", "Vade (gün)", "Sevk Durumu"]
                    ],
                    use_container_width=True
                )

                sec_index = st.selectbox(
                    "Proforma Seç",
                    eski_kayitlar.index,
                    format_func=lambda i: f"{eski_kayitlar.at[i, 'Proforma No']} | {eski_kayitlar.at[i, 'Tarih']}"
                ) if not eski_kayitlar.empty else None

                if sec_index is not None:
                    kayit = eski_kayitlar.loc[sec_index]
                    if kayit.get("PDF"):
                        st.markdown(f"**Proforma PDF:** [{kayit['Proforma No']}]({kayit['PDF']})", unsafe_allow_html=True)

                    # — Temel güncelle/sil formu —
                    with st.form("edit_proforma"):
                        tarih_ = st.date_input("Tarih", value=pd.to_datetime(kayit["Tarih"]).date(), format="DD/MM/YYYY")
                        proforma_no_ = st.text_input("Proforma No", value=kayit["Proforma No"])
                        tutar_ = st.text_input("Tutar ($)", value=kayit["Tutar"])
                        vade_gun_ = st.text_input("Vade (gün)", value=str(kayit["Vade (gün)"]))
                        aciklama_ = st.text_area("Açıklama", value=kayit["Açıklama"])
                        durum_ = st.selectbox(
                            "Durum",
                            ["Beklemede", "Siparişe Dönüştü", "İptal", "Faturası Kesildi"],
                            index=["Beklemede", "Siparişe Dönüştü", "İptal", "Faturası Kesildi"].index(kayit["Durum"])
                            if kayit["Durum"] in ["Beklemede", "Siparişe Dönüştü", "İptal", "Faturası Kesildi"] else 0
                        )
                        guncelle = st.form_submit_button("Güncelle")
                        sil = st.form_submit_button("Sil")

                    # — "Siparişe Dönüştü" ise Sipariş Formu ayrı yüklenir —
                    if durum_ == "Siparişe Dönüştü":
                        st.info("Lütfen sipariş formunu yükleyin ve ardından 'Sipariş Formunu Kaydet' butonuna basın.")
                        with st.form(f"siparis_formu_upload_{sec_index}"):
                            siparis_formu_file = st.file_uploader("Sipariş Formu PDF", type="pdf")
                            siparis_kaydet = st.form_submit_button("Sipariş Formunu Kaydet")

                        if siparis_kaydet:
                            if siparis_formu_file is None:
                                st.error("Sipariş formu yüklemelisiniz.")
                            else:
                                sf_name = f"{musteri_sec}_{proforma_no_}_SiparisFormu_{datetime.datetime.now().strftime('%Y%m%d%H%M%S')}.pdf".replace(" ", "_")
                                temp_path = os.path.join(".", sf_name)
                                with open(temp_path, "wb") as f:
                                    f.write(siparis_formu_file.read())
                                sf_url = _throttled_upload(temp_path, sf_name, EVRAK_KLASOR_ID)
                                try:
                                    os.remove(temp_path)
                                except:
                                    pass

                                # Hem sipariş formu hem durum burada güncellenir!
                                df_proforma.at[sec_index, "Sipariş Formu"] = sf_url
                                df_proforma.at[sec_index, "Durum"] = "Siparişe Dönüştü"
                                update_excel()
                                st.success("Sipariş formu kaydedildi ve durum güncellendi!")
                                st.rerun()

                    # — Diğer alanlar için sadece güncelle —
                    if guncelle:
                        df_proforma.at[sec_index, "Tarih"] = tarih_
                        df_proforma.at[sec_index, "Proforma No"] = proforma_no_
                        df_proforma.at[sec_index, "Tutar"] = tutar_
                        df_proforma.at[sec_index, "Vade (gün)"] = vade_gun_
                        df_proforma.at[sec_index, "Açıklama"] = aciklama_
                        if durum_ != "Siparişe Dönüştü":
                            df_proforma.at[sec_index, "Durum"] = durum_
                        update_excel()
                        st.success("Proforma güncellendi!")
                        st.rerun()

                    if sil:
                        df_proforma = df_proforma.drop(sec_index).reset_index(drop=True)
                        update_excel()
                        st.success("Kayıt silindi!")
                        st.rerun()
                else:
                    st.warning("Lütfen bir proforma seçin.")

### ===========================
### --- GÜNCEL SİPARİŞ DURUMU ---
### ===========================

elif menu == "Güncel Sipariş Durumu":
    st.markdown("<h2 style='color:#219A41; font-weight:bold;'>Güncel Sipariş Durumu</h2>", unsafe_allow_html=True)

    # Eksik kolonları kontrol et
    for col in ["Sevk Durumu", "Termin Tarihi", "Sipariş Formu", "Ülke", "Satış Temsilcisi", "Ödeme Şekli"]:
        if col not in df_proforma.columns:
            df_proforma[col] = ""

    # Sadece Siparişe Dönüşen ve Sevkedilmemiş siparişler
    siparisler = df_proforma[
        (df_proforma["Durum"] == "Siparişe Dönüştü") &
        (~df_proforma["Sevk Durumu"].isin(["Sevkedildi", "Ulaşıldı"]))
    ].copy()

    # Termin Tarihine göre sıralama
    siparisler["Termin Tarihi Order"] = pd.to_datetime(siparisler["Termin Tarihi"], errors="coerce")
    siparisler = siparisler.sort_values("Termin Tarihi Order", ascending=True)

    if siparisler.empty:
        st.info("Henüz sevk edilmeyi bekleyen sipariş yok.")
    else:
        # Tarih formatlarını düzenle
        siparisler["Tarih"] = pd.to_datetime(siparisler["Tarih"], errors="coerce").dt.strftime("%d/%m/%Y")
        siparisler["Termin Tarihi"] = pd.to_datetime(siparisler["Termin Tarihi"], errors="coerce").dt.strftime("%d/%m/%Y")

        tablo = siparisler[["Tarih", "Müşteri Adı", "Termin Tarihi", "Ülke", "Satış Temsilcisi", "Ödeme Şekli", "Proforma No", "Tutar", "Açıklama"]]
        st.markdown("<h4 style='color:#219A41; font-weight:bold;'>Tüm Siparişe Dönüşenler</h4>", unsafe_allow_html=True)
        st.dataframe(tablo, use_container_width=True)

        # Termin Tarihi Güncelle
        st.markdown("#### Termin Tarihi Güncelle")
        sec_index = st.selectbox(
            "Termin Tarihi Girilecek Siparişi Seçin",
            options=siparisler.index,
            format_func=lambda i: f"{siparisler.at[i,'Müşteri Adı']} - {siparisler.at[i,'Proforma No']}"
        )

        mevcut_termin = df_proforma.at[sec_index, "Termin Tarihi"]
        try:
            default_termin = pd.to_datetime(mevcut_termin, errors="coerce")
            if pd.isnull(default_termin):
                default_termin = datetime.date.today()
            else:
                default_termin = default_termin.date()
        except:
            default_termin = datetime.date.today()

        yeni_termin = st.date_input("Termin Tarihi", value=default_termin, key="termin_input")
        if st.button("Termin Tarihini Kaydet"):
            df_proforma.at[sec_index, "Termin Tarihi"] = yeni_termin
            update_gsheet_df_proforma(df_proforma)  # 429'a uygun güncelleme
            st.success("Termin tarihi kaydedildi!")
            st.rerun()

        # Sipariş Sevk Et
        st.markdown("#### Sipariş Sevk Et")
        sevk_sec_index = st.selectbox(
            "Sevk Edilecek Siparişi Seçin",
            options=siparisler.index,
            format_func=lambda i: f"{siparisler.at[i,'Müşteri Adı']} - {siparisler.at[i,'Proforma No']}",
            key="sevk_sec"
        )
        if st.button("Sipariş Sevkedildi (ETA Takibine Gönder)"):
            yeni_eta = {
                "Müşteri Adı": siparisler.at[sevk_sec_index, "Müşteri Adı"],
                "Proforma No": siparisler.at[sevk_sec_index, "Proforma No"],
                "ETA Tarihi": "",
                "Açıklama": siparisler.at[sevk_sec_index, "Açıklama"]
            }
            for col in ["Müşteri Adı", "Proforma No", "ETA Tarihi", "Açıklama"]:
                if col not in df_eta.columns:
                    df_eta[col] = ""
            df_eta = pd.concat([df_eta, pd.DataFrame([yeni_eta])], ignore_index=True)
            df_proforma.at[sevk_sec_index, "Sevk Durumu"] = "Sevkedildi"

            # Sheets güncellemeleri
            update_gsheet_df_eta(df_eta)
            update_gsheet_df_proforma(df_proforma)

            st.success("Sipariş sevkedildi ve ETA takibine gönderildi!")
            st.rerun()

        # Siparişi Beklemeye Al (Geri Çağır)
        st.markdown("#### Siparişi Beklemeye Al (Geri Çağır)")
        geri_index = st.selectbox(
            "Beklemeye Alınacak Siparişi Seçin",
            options=siparisler.index,
            format_func=lambda i: f"{siparisler.at[i,'Müşteri Adı']} - {siparisler.at[i,'Proforma No']}",
            key="geri_sec"
        )
        if st.button("Siparişi Beklemeye Al / Geri Çağır"):
            df_proforma.at[geri_index, "Durum"] = "Beklemede"
            df_proforma.at[geri_index, "Sevk Durumu"] = ""
            df_proforma.at[geri_index, "Termin Tarihi"] = ""
            update_gsheet_df_proforma(df_proforma)
            st.success("Sipariş tekrar bekleyen proformalar listesine alındı!")
            st.rerun()

        # PDF & Sipariş Formu linkleri
        st.markdown("#### Tıklanabilir Proforma ve Sipariş Formu Linkleri")
        for _, row in siparisler.iterrows():
            links = []
            if row["PDF"]:
                links.append(f"[Proforma PDF: {row['Proforma No']}]({row['PDF']})")
            if row["Sipariş Formu"]:
                fname = f"{row['Müşteri Adı']}__{row['Proforma No']}__SiparisFormu"
                links.append(f"[Sipariş Formu: {fname}]({row['Sipariş Formu']})")
            if links:
                st.markdown(" - " + " | ".join(links), unsafe_allow_html=True)

        # Toplam Bekleyen Sevk Tutarı
        try:
            toplam = pd.to_numeric(siparisler["Tutar"], errors="coerce").sum()
        except:
            toplam = 0
        st.markdown(f"<div style='color:#219A41; font-weight:bold;'>*Toplam Bekleyen Sevk: {toplam:,.2f} $*</div>", unsafe_allow_html=True)

# ===========================
# --- FATURA & İHRACAT EVRAKLARI MENÜSÜ ---
# ===========================

elif menu == "Fatura & İhracat Evrakları":
    st.markdown("<h2 style='color:#219A41; font-weight:bold;'>Fatura & İhracat Evrakları</h2>", unsafe_allow_html=True)

    # Sütun güvenliği
    for col in [
        "Proforma No", "Vade (gün)", "Vade Tarihi", "Ülke", "Satış Temsilcisi", "Ödeme Şekli",
        "Commercial Invoice", "Sağlık Sertifikası", "Packing List",
        "Konşimento", "İhracat Beyannamesi", "Fatura PDF", "Sipariş Formu",
        "Yük Resimleri", "EK Belgeler", "Ödendi"
    ]:
        if col not in df_evrak.columns:
            df_evrak[col] = "" if col != "Ödendi" else False

    # Yardımcılar
    import re, tempfile
    def _safe_name(text, maxlen=120):
        s = str(text or "").strip().replace(" ", "_")
        s = re.sub(r'[\\/*?:"<>|]+', "_", s)
        return s[:maxlen]

    def _upload_to_drive_return_link(file_bytes: bytes, filename: str, parent_id: str) -> str:
        """Tek dosyayı Drive'a yükler ve görüntüleme linkini döndürür."""
        # Geçici dosya (küçük yazma, 429'dan kaçınmak için tek seferde)
        suffix = os.path.splitext(filename)[1] or ".pdf"
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as fp:
            fp.write(file_bytes)
            temp_path = fp.name
        try:
            meta = {'title': filename, 'parents': [{'id': parent_id}]}
            gfile = drive.CreateFile(meta)
            gfile.SetContentFile(temp_path)
            gfile.Upload(param={'supportsAllDrives': True})
            return f"https://drive.google.com/file/d/{gfile['id']}/view?usp=sharing"
        finally:
            try: os.remove(temp_path)
            except: pass

    # Müşteri / Proforma seçimleri
    musteri_secenek = sorted(df_proforma["Müşteri Adı"].dropna().astype(str).unique().tolist())
    secilen_musteri = st.selectbox("Müşteri Seç", [""] + musteri_secenek)
    secilen_proformalar = df_proforma[df_proforma["Müşteri Adı"] == secilen_musteri] if secilen_musteri else pd.DataFrame()

    proforma_no_sec = st.selectbox(
        "Proforma No Seç",
        [""] + (secilen_proformalar["Proforma No"].astype(str).tolist() if not secilen_proformalar.empty else [])
    )

    # Müşteri bilgileri (ülke/temsilci/ödeme)
    musteri_info = df_musteri[df_musteri["Müşteri Adı"] == secilen_musteri]
    ulke = musteri_info["Ülke"].values[0] if not musteri_info.empty else ""
    temsilci = musteri_info["Satış Temsilcisi"].values[0] if not musteri_info.empty else ""
    odeme = musteri_info["Ödeme Şekli"].values[0] if not musteri_info.empty else ""

    # Önceki evraklar (varsa link tut)
    onceki_evrak = df_evrak[
        (df_evrak["Müşteri Adı"] == secilen_musteri) &
        (df_evrak["Proforma No"] == proforma_no_sec)
    ]

    def file_link_html(label, url):
        if url:
            return f'<div style="margin-top:-6px;"><a href="{url}" target="_blank" style="color:#219A41;">[Daha önce yüklenmiş {label}]</a></div>'
        else:
            return f'<div style="margin-top:-6px; color:#b00020; font-size:0.95em;">(Daha önce yüklenmemiş)</div>'

    evrak_tipleri = [
        ("Commercial Invoice", "Commercial Invoice PDF"),
        ("Sağlık Sertifikası", "Sağlık Sertifikası PDF"),
        ("Packing List", "Packing List PDF"),
        ("Konşimento", "Konşimento PDF"),
        ("İhracat Beyannamesi", "İhracat Beyannamesi PDF"),
    ]

    with st.form("add_evrak"):
        fatura_no = st.text_input("Fatura No")
        fatura_tarih = st.date_input("Fatura Tarihi", value=datetime.date.today())
        tutar = st.text_input("Fatura Tutarı ($)")

        # Vade (gün) & Vade Tarihi (proformadan otomatik, sadece gösterim)
        vade_gun = ""
        vade_tarihi = ""
        if secilen_musteri and proforma_no_sec:
            _pf = df_proforma[
                (df_proforma["Müşteri Adı"] == secilen_musteri) &
                (df_proforma["Proforma No"] == proforma_no_sec)
            ]
            if not _pf.empty:
                vade_gun = str(_pf.iloc[0].get("Vade (gün)", "") or "")
                try:
                    vade_gun_int = int(vade_gun)
                    vade_tarihi = fatura_tarih + datetime.timedelta(days=vade_gun_int)
                except Exception:
                    vade_tarihi = ""

        st.text_input("Vade (gün)", value=vade_gun, key="vade_gun", disabled=True)
        st.date_input("Vade Tarihi", value=vade_tarihi if vade_tarihi else fatura_tarih, key="vade_tarihi", disabled=True)
        st.text_input("Ülke", value=ulke, disabled=True)
        st.text_input("Satış Temsilcisi", value=temsilci, disabled=True)
        st.text_input("Ödeme Şekli", value=odeme, disabled=True)

        # Evrak upload alanları + önceki linklerin gösterimi
        uploaded_files = {}
        for col, label in evrak_tipleri:
            uploaded_files[col] = st.file_uploader(label, type="pdf", key=f"{col}_upload")
            prev_url = onceki_evrak.iloc[0][col] if not onceki_evrak.empty else ""
            st.markdown(file_link_html(label, prev_url), unsafe_allow_html=True)

        submitted = st.form_submit_button("Kaydet")

        if submitted:
            if not (secilen_musteri and proforma_no_sec):
                st.error("Lütfen önce müşteri ve proforma seçiniz.")
            elif not fatura_no.strip() or not tutar.strip():
                st.error("Fatura No ve Tutar boş olamaz!")
            else:
                # Yeni dosya yüklendiyse yükle; yoksa eski linki koru
                file_urls = {}
                timestamp = datetime.datetime.now().strftime('%Y%m%d%H%M%S')
                for col, label in evrak_tipleri:
                    up = uploaded_files[col]
                    if up is not None:
                        # güvenli ve anlamlı dosya adı
                        fname = _safe_name(f"{secilen_musteri}__{proforma_no_sec}__{col}__{timestamp}") + ".pdf"
                        file_urls[col] = _upload_to_drive_return_link(
                            up.read(), fname, EVRAK_KLASOR_ID
                        )
                    else:
                        file_urls[col] = onceki_evrak.iloc[0][col] if not onceki_evrak.empty else ""

                # Kayıt ekle
                new_row = {
                    "Müşteri Adı": secilen_musteri,
                    "Proforma No": proforma_no_sec,
                    "Fatura No": fatura_no,
                    "Fatura Tarihi": fatura_tarih,
                    "Tutar": tutar,
                    "Vade (gün)": vade_gun,
                    "Vade Tarihi": vade_tarihi,
                    "Ülke": ulke,
                    "Satış Temsilcisi": temsilci,
                    "Ödeme Şekli": odeme,
                    "Commercial Invoice": file_urls.get("Commercial Invoice", ""),
                    "Sağlık Sertifikası": file_urls.get("Sağlık Sertifikası", ""),
                    "Packing List": file_urls.get("Packing List", ""),
                    "Konşimento": file_urls.get("Konşimento", ""),
                    "İhracat Beyannamesi": file_urls.get("İhracat Beyannamesi", ""),
                    "Fatura PDF": "",    # istersen ayrı yükleme alanı açılabilir
                    "Sipariş Formu": "", # bu menüde dokunmuyoruz
                    "Yük Resimleri": "",
                    "EK Belgeler": "",
                    "Ödendi": False,
                }

                # Tek seferde yaz (429’dan kaçınmak için)
                df_evrak = pd.concat([df_evrak, pd.DataFrame([new_row])], ignore_index=True)
                update_excel()
                st.success("Evrak eklendi!")
                st.rerun()

### ===========================
### --- VADE TAKİBİ MENÜSÜ ---
### ===========================

elif menu == "Vade Takibi":
    st.markdown("<h2 style='color:#219A41; font-weight:bold;'>Vade Takibi</h2>", unsafe_allow_html=True)

    # ==== Güvenlik: Gerekli sütunların varlığı ====
    for col in ["Proforma No", "Vade (gün)", "Vade Tarihi", "Ülke", "Satış Temsilcisi", "Ödeme Şekli",
                "Fatura No", "Fatura Tarihi", "Tutar", "Ödeme Kanıtı", "Ödendi"]:
        if col not in df_evrak.columns:
            df_evrak[col] = "" if col != "Ödendi" else False

    # Tip düzeltmeleri
    df_evrak["Ödendi"] = df_evrak["Ödendi"].fillna(False).astype(bool)
    df_evrak["Vade Tarihi"] = pd.to_datetime(df_evrak["Vade Tarihi"], errors="coerce")
    df_evrak["Fatura Tarihi"] = pd.to_datetime(df_evrak["Fatura Tarihi"], errors="coerce")

    # ==== Drive klasörleri (müşteri/kanıt) ====
    import re, tempfile

    ROOT_EXPORT_FOLDER_ID = EVRAK_KLASOR_ID  # Globalden geliyor

    def safe_name(text, maxlen=120):
        s = str(text or "").strip().replace(" ", "_")
        s = re.sub(r'[\\/*?:"<>|]+', "_", s)
        return s[:maxlen]

    def get_or_create_folder_by_name(name: str, parent_id: str) -> str:
        """Parent altında isme göre klasörü bulur, yoksa oluşturur (Shared Drive uyumlu)."""
        q = (
            f"title = '{name}' and mimeType = 'application/vnd.google-apps.folder' "
            f"and '{parent_id}' in parents and trashed = false"
        )
        try:
            lst = drive.ListFile({
                'q': q, 'supportsAllDrives': True, 'includeItemsFromAllDrives': True
            }).GetList()
            if lst:
                return lst[0]['id']
            meta = {
                'title': name,
                'mimeType': 'application/vnd.google-apps.folder',
                'parents': [{'id': parent_id}],
            }
            f = drive.CreateFile(meta)
            f.Upload(param={'supportsAllDrives': True})
            return f['id']
        except Exception as e:
            st.error(f"Klasör oluşturma/arama hatası: {e}")
            return ""

    def get_or_create_customer_folder(customer_name: str, parent_folder_id: str) -> str:
        return get_or_create_folder_by_name(safe_name(customer_name, 100), parent_folder_id)

    # ==== Liste: yalnızca vadesi tanımlı ve ödenmemişler ====
    today = pd.to_datetime(datetime.date.today())
    vade_df = df_evrak[df_evrak["Vade Tarihi"].notna() & (~df_evrak["Ödendi"])].reset_index()

    if vade_df.empty:
        st.info("Açık vade kaydı yok.")
    else:
        st.markdown("#### Açık Vade Kayıtları (kart görünümü)")
        for i, row in vade_df.iterrows():
            kalan = (row["Vade Tarihi"] - today).days
            mesaj = (
                f"{row['Müşteri Adı']} | {row.get('Ülke','')} | {row.get('Satış Temsilcisi','')} "
                f"| Proforma: {row.get('Proforma No','')} | Fatura: {row.get('Fatura No','')} "
                f"| Vade: {row['Vade Tarihi'].date()} | Ödeme Şekli: {row.get('Ödeme Şekli','')}"
            )

            kart = st.container(border=True)
            with kart:
                if kalan == 1:
                    st.error(f"{mesaj} | **YARIN VADE DOLUYOR!**")
                elif kalan < 0:
                    st.warning(f"{mesaj} | **{abs(kalan)} gün GECİKTİ!**")
                else:
                    st.info(f"{mesaj} | {kalan} gün kaldı.")

                # Önceden yüklenmiş link
                onceki_link = row.get("Ödeme Kanıtı", "")
                if onceki_link:
                    st.markdown(f"[Önceden yüklenmiş ödeme kanıtı]({onceki_link})", unsafe_allow_html=True)

                # Kanıt yükleme (çoklu format)
                kanit = st.file_uploader(
                    "Ödeme Kanıtı (PDF/JPG/PNG/JPEG/WEBP)",
                    type=["pdf", "jpg", "jpeg", "png", "webp"],
                    key=f"kanit_{i}"
                )

                # Ödendi işaretleme — not: sadece tıklandığında yazıyoruz (429 için minimum yazım)
                tik = st.checkbox(
                    f"Ödendi olarak işaretle → {row['Müşteri Adı']} - Proforma: {row.get('Proforma No','')} - Fatura: {row['Fatura No']}",
                    key=f"odendi_{i}"
                )

                if tik:
                    # Kanıt zorunlu (yeni ya da önceden var)
                    if kanit is None and not onceki_link:
                        st.error("Lütfen önce **Ödeme Kanıtı** dosyası yükleyin (PDF/JPG/PNG…).")
                    else:
                        odeme_kaniti_url = onceki_link

                        # Yeni kanıt yüklendiyse Drive'a at
                        if kanit is not None:
                            if not ROOT_EXPORT_FOLDER_ID:
                                st.error("Ana klasör ID tanımlı değil; yükleme iptal edildi.")
                                st.stop()

                            cust_folder_id = get_or_create_customer_folder(row["Müşteri Adı"], ROOT_EXPORT_FOLDER_ID)
                            if not cust_folder_id:
                                st.error("Müşteri klasörü oluşturulamadı; yükleme iptal edildi.")
                                st.stop()

                            kanit_folder_id = get_or_create_folder_by_name("Odeme_Kanitlari", cust_folder_id)
                            if not kanit_folder_id:
                                st.error("Ödeme kanıtı klasörü oluşturulamadı; yükleme iptal edildi.")
                                st.stop()

                            # Dosyayı geçici kaydet ve yükle
                            suffix = os.path.splitext(kanit.name)[1].lower() or ".pdf"
                            ts = datetime.datetime.now().strftime('%Y%m%d%H%M%S')
                            fname = safe_name(
                                f"OdemeKaniti__{row['Müşteri Adı']}__{row.get('Proforma No','')}__{row['Fatura No']}__{ts}"
                            ) + suffix

                            with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as fp:
                                fp.write(kanit.read())
                                temp_path = fp.name

                            meta = {'title': fname, 'parents': [{'id': kanit_folder_id}]}
                            gfile = drive.CreateFile(meta)
                            gfile.SetContentFile(temp_path)
                            try:
                                gfile.Upload(param={'supportsAllDrives': True})
                                odeme_kaniti_url = f"https://drive.google.com/file/d/{gfile['id']}/view?usp=sharing"
                            except Exception as e:
                                st.error(f"Ödeme kanıtı yüklenirken hata: {e}")
                            finally:
                                try: os.remove(temp_path)
                                except: pass

                        # === TEK NOKTA YAZIM (429 için) ===
                        df_evrak.at[row['index'], "Ödeme Kanıtı"] = odeme_kaniti_url
                        df_evrak.at[row['index'], "Ödendi"] = True
                        update_excel()  # sadece değişiklik olduğunda yaz
                        st.success("Kayıt 'Ödendi' olarak işaretlendi ve ödeme kanıtı kaydedildi.")
                        st.rerun()

        # Alt kısımda tablo özeti
        st.markdown("#### Açık Vade Kayıtları (tablo)")
        tablo = df_evrak[
            df_evrak["Vade Tarihi"].notna() & (~df_evrak["Ödendi"])
        ].copy()

        # Görsel formatlar
        tablo["Fatura Tarihi"] = pd.to_datetime(tablo["Fatura Tarihi"], errors="coerce").dt.strftime("%d/%m/%Y")
        tablo["Vade Tarihi"] = pd.to_datetime(tablo["Vade Tarihi"], errors="coerce").dt.strftime("%d/%m/%Y")

        st.dataframe(
            tablo[["Müşteri Adı", "Ülke", "Satış Temsilcisi", "Ödeme Şekli",
                   "Proforma No", "Fatura No", "Fatura Tarihi", "Vade (gün)", "Vade Tarihi", "Tutar"]],
            use_container_width=True
        )

### ===========================
### --- ETA TAKİBİ MENÜSÜ ---
### ===========================
elif menu == "ETA Takibi":
    st.markdown("<h2 style='color:#219A41; font-weight:bold;'>ETA Takibi</h2>", unsafe_allow_html=True)

    import re, tempfile, time

    # ---- Sabitler (GLOBAL'den kullan) ----
    ROOT_EXPORT_FOLDER_ID = EVRAK_KLASOR_ID  # İhracat Evrakları ana klasör ID'si

    # ---- Güvenlik: gerekli kolonlar ----
    for col in ["Sevk Durumu", "Proforma No", "Sevk Tarihi", "Ulaşma Tarihi", "Termin Tarihi", "PDF", "Sipariş Formu"]:
        if col not in df_proforma.columns:
            df_proforma[col] = ""

    for col in ["Müşteri Adı", "Proforma No", "ETA Tarihi", "Açıklama"]:
        if col not in df_eta.columns:
            df_eta[col] = ""

    # ---- Yardımcılar ----
    def safe_name(text, maxlen=120):
        s = str(text or "").strip().replace(" ", "_")
        s = re.sub(r'[\\/*?:"<>|]+', "_", s)
        return s[:maxlen]

    def _drive_list(q: str):
        """Drive listesinde 429/5xx hatalarında kısa bekleme ile 2 kez daha dene."""
        tries = 3
        last_err = None
        for i in range(tries):
            try:
                return drive.ListFile({
                    'q': q,
                    'supportsAllDrives': True,
                    'includeItemsFromAllDrives': True
                }).GetList()
            except Exception as e:
                last_err = e
                # Aşırı isteklerde (429) veya geçici hatalarda kısa bekleme
                time.sleep(1.2 * (i + 1))
        raise last_err

    def get_or_create_folder_by_name(name: str, parent_id: str) -> str:
        """Parent altında isme göre klasör bulur; yoksa oluşturur. Shared Drive uyumlu."""
        q = (
            f"title = '{name}' and mimeType = 'application/vnd.google-apps.folder' "
            f"and '{parent_id}' in parents and trashed = false"
        )
        try:
            lst = _drive_list(q)
            if lst:
                return lst[0]['id']
            meta = {
                'title': name,
                'mimeType': 'application/vnd.google-apps.folder',
                'parents': [{'id': parent_id}],
            }
            f = drive.CreateFile(meta)
            # supportsAllDrives => Shared Drive desteği
            f.Upload(param={'supportsAllDrives': True})
            return f['id']
        except Exception as e:
            st.error(f"Klasör oluşturma/arama hatası: {e}")
            return ""

    def get_proforma_yukleme_folder(proforma_no: str) -> str:
        """
        Ana klasör altında <Proforma No> / Yükleme Resimleri hiyerarşisini hazırlar ve döndürür.
        """
        if not ROOT_EXPORT_FOLDER_ID:
            return ""
        proforma_folder = get_or_create_folder_by_name(safe_name(proforma_no, 100), ROOT_EXPORT_FOLDER_ID)
        if not proforma_folder:
            return ""
        yukleme_folder = get_or_create_folder_by_name("Yükleme Resimleri", proforma_folder)
        return yukleme_folder

    # ==== SEVKEDİLENLER (Yolda) ====
    sevkedilenler = df_proforma[df_proforma["Sevk Durumu"] == "Sevkedildi"].copy()
    if sevkedilenler.empty:
        st.info("Sevkedilmiş sipariş bulunmuyor.")
    else:
        # Seçim
        secenekler = sevkedilenler[["Müşteri Adı", "Proforma No"]].drop_duplicates()
        secenekler["sec_text"] = secenekler["Müşteri Adı"].astype(str) + " - " + sevkedilenler["Proforma No"].astype(str)
        secenekler = secenekler.drop_duplicates("sec_text")
        selected = st.selectbox("Sevkedilen Sipariş Seç", secenekler["sec_text"])
        selected_row = secenekler[secenekler["sec_text"] == selected].iloc[0]
        sec_musteri = selected_row["Müşteri Adı"]
        sec_proforma = selected_row["Proforma No"]

        # ========== YÜKLEME FOTOĞRAFLARI (Proforma → “Yükleme Resimleri”) ==========
        st.markdown("#### 🖼️ Yükleme Fotoğrafları (Proforma bazlı)")

        hedef_klasor = get_proforma_yukleme_folder(sec_proforma)
        if not hedef_klasor:
            st.error("Proforma klasörü / 'Yükleme Resimleri' klasörü oluşturulamadı.")
        else:
            # 1) Klasörü yeni sekmede aç butonu
            drive_link = f"https://drive.google.com/drive/folders/{hedef_klasor}?usp=sharing"
            st.markdown(f"[🔗 Klasörü yeni sekmede aç]({drive_link})")

            # 2) Panel içinde gömülü görüntüleme – sadece gezinme
            with st.expander("📂 Panelde klasörü görüntüle"):
                embed = f"https://drive.google.com/embeddedfolderview?id={hedef_klasor}#grid"
                st.markdown(
                    f'<iframe src="{embed}" width="100%" height="520" frameborder="0" '
                    f'style="border:1px solid #eee; border-radius:12px;"></iframe>',
                    unsafe_allow_html=True
                )

            # 3) Mevcut dosyaları say ve özetle (ilk 10 isim) — tek liste çağrısı
            try:
                mevcut_dosyalar = _drive_list(
                    f"'{hedef_klasor}' in parents and trashed = false"
                )
            except Exception as e:
                mevcut_dosyalar = []
                st.warning(f"Dosyalar listelenemedi: {e}")

            if mevcut_dosyalar:
                st.caption(f"Bu klasörde {len(mevcut_dosyalar)} dosya var.")
                names = [f"- {f['title']}" for f in mevcut_dosyalar[:10]]
                if names:
                    st.write("\n".join(names))
                if len(mevcut_dosyalar) > 10:
                    st.write("…")

            # 4) (OPSİYONEL) Dosya Ekle – duplike önleme (aynı isim SKIP)
            with st.expander("➕ Dosya Ekle (opsiyonel, duplike önleme)"):
                files = st.file_uploader(
                    "Yüklenecek dosyaları seçin",
                    type=["pdf", "jpg", "jpeg", "png", "webp"],
                    accept_multiple_files=True,
                    key=f"yuk_resimleri_dedupe_{sec_proforma}"
                )

                if files:
                    var_olan_isimler = set(f["title"] for f in mevcut_dosyalar)
                    yuklenen_say = 0
                    atlanan_duplike = 0

                    for up in files:
                        suffix = os.path.splitext(up.name)[1].lower()
                        base = os.path.splitext(up.name)[0]
                        fname = safe_name(base) + (suffix if suffix else "")

                        if fname in var_olan_isimler:
                            atlanan_duplike += 1
                            continue

                        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as fp:
                            fp.write(up.read())
                            temp_path = fp.name

                        meta = {'title': fname, 'parents': [{'id': hedef_klasor}]}
                        gfile = drive.CreateFile(meta)
                        gfile.SetContentFile(temp_path)
                        try:
                            gfile.Upload(param={'supportsAllDrives': True})
                            yuklenen_say += 1
                            var_olan_isimler.add(fname)
                        except Exception as e:
                            st.error(f"{up.name} yüklenemedi: {e}")
                        finally:
                            try: os.remove(temp_path)
                            except: pass

                    if yuklenen_say:
                        # Bu menüde veri eklemiyor olsak da tek çıkış noktası tutarlılık için:
                        update_excel()
                        st.success(f"{yuklenen_say} yeni dosya yüklendi.")
                        if atlanan_duplike:
                            st.info(f"{atlanan_duplike} dosya, aynı isimle bulunduğu için atlandı.")
                        st.rerun()
                    else:
                        if atlanan_duplike and not yuklenen_say:
                            st.warning("Tüm dosyalar klasörde zaten mevcut görünüyor (isimleri aynı).")

        st.markdown("---")

        # ========== ETA Düzenleme ==========
        filtre = (df_eta["Müşteri Adı"] == sec_musteri) & (df_eta["Proforma No"] == sec_proforma)
        if filtre.any():
            mevcut_eta = df_eta.loc[filtre, "ETA Tarihi"].values[0]
            mevcut_aciklama = df_eta.loc[filtre, "Açıklama"].values[0]
        else:
            mevcut_eta = ""
            mevcut_aciklama = ""

        with st.form("edit_eta"):
            try:
                varsayilan_eta = pd.to_datetime(mevcut_eta, errors="coerce")
                varsayilan_eta = varsayilan_eta.date() if pd.notnull(varsayilan_eta) else datetime.date.today()
            except Exception:
                varsayilan_eta = datetime.date.today()
            eta_tarih = st.date_input("ETA Tarihi", value=varsayilan_eta)
            aciklama = st.text_area("Açıklama", value=mevcut_aciklama)
            colA, colB, colC = st.columns(3)
            with colA:
                guncelle = st.form_submit_button("ETA'yı Kaydet/Güncelle")
            with colB:
                ulasti = st.form_submit_button("Ulaştı")
            with colC:
                geri_al = st.form_submit_button("Sevki Geri Al")

        if guncelle:
            if filtre.any():
                df_eta.loc[filtre, "ETA Tarihi"] = eta_tarih
                df_eta.loc[filtre, "Açıklama"] = aciklama
            else:
                new_row = {
                    "Müşteri Adı": sec_musteri,
                    "Proforma No": sec_proforma,
                    "ETA Tarihi": eta_tarih,
                    "Açıklama": aciklama
                }
                df_eta = pd.concat([df_eta, pd.DataFrame([new_row])], ignore_index=True)
            update_excel()
            st.success("ETA kaydedildi/güncellendi!")
            st.rerun()

        if ulasti:
            # Ulaşıldı: ETA listesinden çıkar, proforma'da Sevk Durumu "Ulaşıldı" ve bugünün tarihi "Ulaşma Tarihi" olarak kaydet
            df_eta = df_eta[~((df_eta["Müşteri Adı"] == sec_musteri) & (df_eta["Proforma No"] == sec_proforma))].reset_index(drop=True)
            idx = df_proforma[(df_proforma["Müşteri Adı"] == sec_musteri) & (df_proforma["Proforma No"] == sec_proforma)].index
            if len(idx) > 0:
                df_proforma.at[idx[0], "Sevk Durumu"] = "Ulaşıldı"
                df_proforma.at[idx[0], "Ulaşma Tarihi"] = datetime.date.today()
            update_excel()
            st.success("Sipariş 'Ulaşıldı' olarak işaretlendi ve ETA takibinden çıkarıldı!")
            st.rerun()

        if geri_al:
            # Siparişi geri al: ETA'dan çıkar, proforma'da sevk durumunu boş yap (Güncel Sipariş Durumu'na döner)
            df_eta = df_eta[~((df_eta["Müşteri Adı"] == sec_musteri) & (df_eta["Proforma No"] == sec_proforma))].reset_index(drop=True)
            idx = df_proforma[(df_proforma["Müşteri Adı"] == sec_musteri) & (df_proforma["Proforma No"] == sec_proforma)].index
            if len(idx) > 0:
                df_proforma.at[idx[0], "Sevk Durumu"] = ""
            update_excel()
            st.success("Sevkiyat geri alındı! Sipariş tekrar Güncel Sipariş Durumu'na gönderildi.")
            st.rerun()

    # ==== ETA TAKİP LİSTESİ ====
    st.markdown("#### ETA Takip Listesi")
    for col in ["Proforma No", "ETA Tarihi"]:
        if col not in df_eta.columns:
            df_eta[col] = ""
    if not df_eta.empty:
        df_eta["ETA Tarihi"] = pd.to_datetime(df_eta["ETA Tarihi"], errors="coerce")
        today = pd.to_datetime(datetime.date.today())
        df_eta["Kalan Gün"] = (df_eta["ETA Tarihi"] - today).dt.days
        tablo = df_eta[["Müşteri Adı", "Proforma No", "ETA Tarihi", "Kalan Gün", "Açıklama"]].copy()
        tablo = tablo.sort_values(["ETA Tarihi", "Müşteri Adı", "Proforma No"], ascending=[True, True, True])
        st.dataframe(tablo, use_container_width=True)

        st.markdown("##### ETA Kaydı Sil")
        silinecekler = df_eta.index.tolist()
        if silinecekler:
            sil_sec = st.selectbox(
                "Silinecek Kaydı Seçin",
                options=silinecekler,
                format_func=lambda i: f"{df_eta.at[i, 'Müşteri Adı']} - {df_eta.at[i, 'Proforma No']}"
            )
            if st.button("KAYDI SİL"):
                df_eta = df_eta.drop(sil_sec).reset_index(drop=True)
                update_excel()
                st.success("Seçilen ETA kaydı silindi!")
                st.rerun()
    else:
        st.info("Henüz ETA kaydı yok.")

    # ==== ULAŞANLAR (TESLİM EDİLENLER) ====
    ulasanlar = df_proforma[df_proforma["Sevk Durumu"] == "Ulaşıldı"].copy()

    if not ulasanlar.empty:
        ulasanlar["sec_text"] = ulasanlar["Müşteri Adı"].astype(str) + " - " + ulasanlar["Proforma No"].astype(str)
        st.markdown("#### Teslim Edilen Siparişlerde İşlemler")
        selected_ulasan = st.selectbox("Sipariş Seçiniz", ulasanlar["sec_text"])
        row = ulasanlar[ulasanlar["sec_text"] == selected_ulasan].iloc[0]

        # Ulaşma tarihi düzenleme
        try:
            current_ulasma = pd.to_datetime(row.get("Ulaşma Tarihi", None), errors="coerce")
            current_ulasma = current_ulasma.date() if pd.notnull(current_ulasma) else datetime.date.today()
        except Exception:
            current_ulasma = datetime.date.today()

        new_ulasma_tarih = st.date_input("Ulaşma Tarihi", value=current_ulasma, key="ulasan_guncelle")
        if st.button("Ulaşma Tarihini Kaydet"):
            idx = df_proforma[
                (df_proforma["Müşteri Adı"] == row["Müşteri Adı"]) &
                (df_proforma["Proforma No"] == row["Proforma No"])
            ].index
            if len(idx) > 0:
                df_proforma.at[idx[0], "Ulaşma Tarihi"] = new_ulasma_tarih
                update_excel()
                st.success("Ulaşma Tarihi güncellendi!")
                st.rerun()

        st.markdown("---")
        # Ulaşanlardan YOLA GERİ AL (yeniden Sevkedildi + ETA’ya ekle/güncelle)
        with st.form("ulasan_geri_al_form"):
            st.markdown("##### 🔄 Ulaşan siparişi yeniden **Yolda Olanlar (ETA)** listesine al")
            yeni_eta = st.date_input("Yeni ETA (opsiyonel)", value=datetime.date.today() + datetime.timedelta(days=7))
            aciklama_geri = st.text_input("Açıklama (opsiyonel)", value="Geri alındı - tekrar yolda")
            onay = st.form_submit_button("Yola Geri Al")

        if onay:
            musteri = row["Müşteri Adı"]
            pno = row["Proforma No"]

            # Proforma statüsü
            idx = df_proforma[(df_proforma["Müşteri Adı"] == musteri) & (df_proforma["Proforma No"] == pno)].index
            if len(idx) > 0:
                df_proforma.at[idx[0], "Sevk Durumu"] = "Sevkedildi"
                df_proforma.at[idx[0], "Ulaşma Tarihi"] = ""

            # ETA ekle/güncelle
            filtre_eta = (df_eta["Müşteri Adı"] == musteri) & (df_eta["Proforma No"] == pno)
            eta_deger = pd.to_datetime(yeni_eta) if yeni_eta else ""
            if filtre_eta.any():
                if yeni_eta:
                    df_eta.loc[filtre_eta, "ETA Tarihi"] = eta_deger
                if aciklama_geri:
                    df_eta.loc[filtre_eta, "Açıklama"] = aciklama_geri
            else:
                yeni_satir = {
                    "Müşteri Adı": musteri,
                    "Proforma No": pno,
                    "ETA Tarihi": eta_deger if yeni_eta else "",
                    "Açıklama": aciklama_geri,
                }
                df_eta = pd.concat([df_eta, pd.DataFrame([yeni_satir])], ignore_index=True)

            update_excel()
            st.success("Sipariş, Ulaşanlar'dan geri alındı ve ETA listesine taşındı (Sevkedildi).")
            st.rerun()

        # Ulaşanlar Tablosu (özet)
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

        tablo = ulasanlar[[
            "Müşteri Adı", "Proforma No", "Termin Tarihi", "Sevk Tarihi",
            "Ulaşma Tarihi", "Gün Farkı", "Tutar", "Açıklama"
        ]]
        st.dataframe(tablo, use_container_width=True)
    else:
        st.info("Henüz ulaşan sipariş yok.")

# ==============================
# FUAR MÜŞTERİ KAYITLARI MENÜSÜ
# ==============================

if menu == "Fuar Müşteri Kayıtları":
    st.markdown("<h2 style='color:#8e54e9; font-weight:bold; text-align:center;'>🎫 FUAR MÜŞTERİ KAYITLARI</h2>", unsafe_allow_html=True)
    st.info("Fuarlarda müşteri görüşmelerinizi hızlıca buraya ekleyin. Hem yeni kayıt oluşturabilir hem de mevcut kayıtlarınızı düzenleyebilirsiniz.")

    # --- Eksik kolon güvenliği ---
    FUAR_COLS = ["Fuar Adı", "Müşteri Adı", "Ülke", "Telefon", "E-mail", "Satış Temsilcisi",
                 "Açıklamalar", "Görüşme Kalitesi", "Tarih"]
    for c in FUAR_COLS:
        if c not in df_fuar_musteri.columns:
            df_fuar_musteri[c] = "" if c not in ["Görüşme Kalitesi", "Tarih"] else (0 if c == "Görüşme Kalitesi" else "")

    # --- Fuar Adı Girişi & Seçimi ---
    fuar_isimleri = sorted([x for x in df_fuar_musteri["Fuar Adı"].dropna().unique() if str(x).strip() != ""])
    yeni_fuar = st.text_input("Yeni Fuar Adı Ekleyin (Eklemek istemiyorsanız boş bırakın):").strip()

    if yeni_fuar and yeni_fuar not in fuar_isimleri:
        fuar_isimleri.append(yeni_fuar)

    fuar_adi = st.selectbox("Fuar Seçiniz", ["- Fuar Seçiniz -"] + fuar_isimleri, index=0)
    fuar_adi = "" if fuar_adi == "- Fuar Seçiniz -" else fuar_adi
    if yeni_fuar:
        fuar_adi = yeni_fuar  # öncelik yeni girilene

    secim = st.radio("İşlem Seçiniz:", ["Yeni Kayıt", "Eski Kayıt"], horizontal=True)

    # --- YENİ KAYIT ---
    if secim == "Yeni Kayıt":
        st.markdown("#### Yeni Fuar Müşteri Kaydı Ekle")
        with st.form("fuar_musteri_ekle"):
            musteri_adi = st.text_input("Müşteri Adı").strip()
            ulke = st.selectbox("Ülke Seçin", ulke_listesi)  # global listeden
            tel = st.text_input("Telefon")
            email = st.text_input("E-mail")
            temsilci = st.selectbox("Satış Temsilcisi", temsilci_listesi)  # global listeden
            aciklama = st.text_area("Açıklamalar")
            gorusme_kalitesi = st.slider("Görüşme Kalitesi (1=Kötü, 5=Çok İyi)", 1, 5, 3)
            tarih = st.date_input("Tarih", value=datetime.date.today(), format="DD/MM/YYYY")
            submitted = st.form_submit_button("Kaydet")

        if submitted:
            if not fuar_adi or not musteri_adi:
                st.warning("Lütfen fuar seçin ve müşteri adı girin.")
            else:
                # Duplike önleme: Aynı Fuar + Müşteri varsa güncelle
                mask = (df_fuar_musteri["Fuar Adı"] == fuar_adi) & (df_fuar_musteri["Müşteri Adı"] == musteri_adi)
                new_vals = {
                    "Fuar Adı": fuar_adi,
                    "Müşteri Adı": musteri_adi,
                    "Ülke": ulke,
                    "Telefon": tel,
                    "E-mail": email,
                    "Satış Temsilcisi": temsilci,
                    "Açıklamalar": aciklama,
                    "Görüşme Kalitesi": int(gorusme_kalitesi),
                    "Tarih": tarih
                }
                if mask.any():
                    idx = df_fuar_musteri[mask].index[0]
                    for k, v in new_vals.items():
                        df_fuar_musteri.at[idx, k] = v
                    update_excel()
                    st.success("Mevcut kayıt güncellendi (duplike engellendi).")
                else:
                    df_fuar_musteri = pd.concat([df_fuar_musteri, pd.DataFrame([new_vals])], ignore_index=True)
                    update_excel()
                    st.success("Fuar müşterisi başarıyla eklendi!")
                st.rerun()

    # --- ESKİ KAYIT DÜZENLE/SİL ---
    elif secim == "Eski Kayıt":
        if not fuar_adi:
            st.info("Lütfen önce bir fuar seçiniz.")
        else:
            kolonlar = ["Müşteri Adı", "Ülke", "Telefon", "E-mail", "Satış Temsilcisi", "Açıklamalar", "Görüşme Kalitesi", "Tarih"]
            musteri_df = df_fuar_musteri[df_fuar_musteri["Fuar Adı"] == fuar_adi].copy()

            if musteri_df.empty:
                st.info("Bu fuara ait müşteri kaydı bulunamadı.")
            else:
                # Gösterim için tarih formatı
                goster_df = musteri_df.copy()
                goster_df["Tarih"] = pd.to_datetime(goster_df["Tarih"], errors="coerce").dt.strftime("%d/%m/%Y")

                st.markdown(f"<h4 style='color:#4776e6;'>{fuar_adi} Fuarındaki Müşteri Görüşme Kayıtları</h4>", unsafe_allow_html=True)

                # Seçim kutusu güvenli format_func
                def _fmt(i):
                    try:
                        t = pd.to_datetime(musteri_df.at[i, "Tarih"], errors="coerce")
                        t_str = t.strftime("%d/%m/%Y") if pd.notnull(t) else "-"
                    except Exception:
                        t_str = "-"
                    return f"{musteri_df.at[i, 'Müşteri Adı']} ({t_str})"

                secili_index = st.selectbox(
                    "Düzenlemek/Silmek istediğiniz kaydı seçin:",
                    musteri_df.index,
                    format_func=_fmt
                )

                # Kayıt görüntüle & düzenle
                with st.form("kayit_duzenle"):
                    musteri_adi = st.text_input("Müşteri Adı", value=str(musteri_df.at[secili_index, "Müşteri Adı"]))
                    # Ülke/Temsilci index güvenliği
                    ulke_val = str(musteri_df.at[secili_index, "Ülke"])
                    ulke_idx = ulke_listesi.index(ulke_val) if ulke_val in ulke_listesi else 0
                    ulke = st.selectbox("Ülke", ulke_listesi, index=ulke_idx)

                    tem_val = str(musteri_df.at[secili_index, "Satış Temsilcisi"])
                    tem_idx = temsilci_listesi.index(tem_val) if tem_val in temsilci_listesi else 0
                    temsilci = st.selectbox("Satış Temsilcisi", temsilci_listesi, index=tem_idx)

                    tel = st.text_input("Telefon", value=str(musteri_df.at[secili_index, "Telefon"]))
                    email = st.text_input("E-mail", value=str(musteri_df.at[secili_index, "E-mail"]))
                    aciklama = st.text_area("Açıklamalar", value=str(musteri_df.at[secili_index, "Açıklamalar"]))
                    try:
                        gk_default = int(musteri_df.at[secili_index, "Görüşme Kalitesi"]) if str(musteri_df.at[secili_index, "Görüşme Kalitesi"]).strip() != "" else 3
                    except Exception:
                        gk_default = 3
                    gorusme_kalitesi = st.slider("Görüşme Kalitesi (1=Kötü, 5=Çok İyi)", 1, 5, gk_default)

                    try:
                        tarih_def = pd.to_datetime(musteri_df.at[secili_index, "Tarih"], errors="coerce").date()
                        if pd.isnull(tarih_def):
                            tarih_def = datetime.date.today()
                    except Exception:
                        tarih_def = datetime.date.today()
                    tarih = st.date_input("Tarih", value=tarih_def, format="DD/MM/YYYY")

                    col_a, col_b = st.columns(2)
                    with col_a:
                        guncelle = st.form_submit_button("Kaydı Güncelle")
                    with col_b:
                        sil = st.form_submit_button("Kaydı Sil")

                if guncelle:
                    # Güncelle
                    updates = {
                        "Müşteri Adı": musteri_adi.strip(),
                        "Ülke": ulke,
                        "Telefon": tel,
                        "E-mail": email,
                        "Satış Temsilcisi": temsilci,
                        "Açıklamalar": aciklama,
                        "Görüşme Kalitesi": int(gorusme_kalitesi),
                        "Tarih": tarih
                    }
                    for k, v in updates.items():
                        df_fuar_musteri.at[secili_index, k] = v
                    update_excel()
                    st.success("Kayıt güncellendi!")
                    st.rerun()

                if sil:
                    df_fuar_musteri = df_fuar_musteri.drop(secili_index).reset_index(drop=True)
                    update_excel()
                    st.success("Kayıt silindi!")
                    st.rerun()

                st.dataframe(goster_df[kolonlar], use_container_width=True)

# ===========================
# --- SATIŞ PERFORMANSI MENÜSÜ ---
# ===========================

elif menu == "Satış Performansı":
    st.markdown("<h2 style='color:#219A41; font-weight:bold; text-align:center;'>📈 SATIŞ PERFORMANSI</h2>", unsafe_allow_html=True)
    st.info("Fatura ve satış tutarlarını tarih aralığına göre görüntüleyebilir ve toplamları hesaplayabilirsiniz.")

    # --- Akıllı sayı dönüştürücü ---
    def smart_to_num(x):
        if pd.isna(x):
            return 0.0
        s = str(x).strip()
        for sym in ["USD", "$", "€", "EUR", "₺", "TL", "tl", "Tl"]:
            s = s.replace(sym, "")
        s = s.replace("\u00A0", "").replace(" ", "")
        # 1) US formatı
        try:
            return float(s)
        except:
            pass
        # 2) Avrupa formatı
        if "," in s:
            try:
                return float(s.replace(".", "").replace(",", "."))
            except:
                pass
        return 0.0

    # --- Kolon kontrolü ---
    if "Tutar" not in df_evrak.columns:
        df_evrak["Tutar"] = 0
    date_col = "Fatura Tarihi" if "Fatura Tarihi" in df_evrak.columns else "Tarih"
    if date_col not in df_evrak.columns:
        df_evrak[date_col] = pd.NaT

    # --- Veri hazırlama ---
    df_evrak = df_evrak.copy()
    df_evrak["Tutar_num"] = df_evrak["Tutar"].apply(smart_to_num).fillna(0.0)
    df_evrak[date_col] = pd.to_datetime(df_evrak[date_col], errors="coerce")
    df_evrak = df_evrak[df_evrak[date_col].notna()]  # geçersiz tarihleri çıkar

    if df_evrak.empty:
        st.warning("📭 Kayıt bulunamadı.")
        st.stop()

    # --- Genel toplam ---
    toplam_fatura = float(df_evrak["Tutar_num"].sum())
    st.markdown(f"<div style='font-size:1.3em; color:#185a9d; font-weight:bold;'>💵 Toplam Fatura Tutarı: {toplam_fatura:,.2f} USD</div>", unsafe_allow_html=True)

    # --- Tarih filtresi ---
    min_ts = df_evrak[date_col].min().date()
    max_ts = df_evrak[date_col].max().date()
    d1, d2 = st.date_input("📅 Tarih Aralığı Seçin", value=(min_ts, max_ts), min_value=min_ts, max_value=max_ts)

    start_ts = pd.to_datetime(d1)
    end_ts   = pd.to_datetime(d2) + pd.Timedelta(days=1) - pd.Timedelta(milliseconds=1)

    df_range = df_evrak[df_evrak[date_col].between(start_ts, end_ts, inclusive="both")]

    # --- Aralık toplamı ---
    aralik_toplam = float(df_range["Tutar_num"].sum())
    st.markdown(f"<div style='font-size:1.2em; color:#f7971e; font-weight:bold;'>📊 {d1} - {d2} Arası Toplam: {aralik_toplam:,.2f} USD</div>", unsafe_allow_html=True)

    # --- Detay tablo ---
    show_cols = ["Müşteri Adı", "Fatura No", date_col, "Tutar"]
    show_cols = [c for c in show_cols if c in df_range.columns]

    st.dataframe(df_range[show_cols].sort_values(by=date_col, ascending=False), use_container_width=True)

# ===========================
# --- ÖZET EKRAN (Vade herkese açık) ---
# ===========================

if menu == "Özet Ekran":
    st.markdown("<h2 style='color:#219A41; font-weight:bold;'>📊 Özet Ekran</h2>", unsafe_allow_html=True)

    # --- Akıllı sayı dönüştürücü ---
    def smart_to_num(x):
        if pd.isna(x):
            return 0.0
        s = str(x).strip()
        for sym in ["USD", "$", "€", "EUR", "₺", "TL", "tl", "Tl"]:
            s = s.replace(sym, "")
        s = s.replace("\u00A0", "").replace(" ", "")
        try:
            return float(s)  # US format
        except:
            pass
        if "," in s:
            try:
                return float(s.replace(".", "").replace(",", "."))  # EU format
            except:
                pass
        return 0.0

    # ---------- df_evrak güvenliği + toplam fatura ----------
    toplam_fatura_tutar = 0.0
    if not df_evrak.empty and "Tutar" in df_evrak.columns:
        _ev = df_evrak.copy()
        _ev["Tutar_num"] = _ev["Tutar"].apply(smart_to_num).fillna(0.0)
        toplam_fatura_tutar = float(_ev["Tutar_num"].sum())

    st.markdown(
        f"<div style='font-size:1.4em; color:#B22222; font-weight:bold;'>💰 Toplam Fatura Tutarı: {toplam_fatura_tutar:,.2f} USD</div>",
        unsafe_allow_html=True
    )

    st.markdown("---")

    # ---------- VADE DURUMU ----------
    for col in ["Vade Tarihi", "Ödendi", "Tutar"]:
        if col not in df_evrak.columns:
            df_evrak[col] = "" if col != "Ödendi" else False

    vade_df_all = df_evrak.copy()
    vade_df_all["Ödendi"] = vade_df_all["Ödendi"].fillna(False).astype(bool)
    vade_df_all["Vade Tarihi"] = pd.to_datetime(vade_df_all["Vade Tarihi"], errors="coerce")
    vade_df_all["Tutar_num"] = vade_df_all["Tutar"].apply(smart_to_num).fillna(0.0)

    today_norm = pd.Timestamp.today().normalize()
    od_me = ~vade_df_all["Ödendi"]

    m_gelmemis = (vade_df_all["Vade Tarihi"] > today_norm) & od_me
    m_bugun = (vade_df_all["Vade Tarihi"].dt.date == today_norm.date()) & od_me
    m_gecikmis = (vade_df_all["Vade Tarihi"] < today_norm) & od_me

    sum_gelmemis = float(vade_df_all.loc[m_gelmemis, "Tutar_num"].sum())
    sum_bugun = float(vade_df_all.loc[m_bugun, "Tutar_num"].sum())
    sum_gecikmis = float(vade_df_all.loc[m_gecikmis, "Tutar_num"].sum())

    c1, c2, c3 = st.columns(3)
    c1.metric("📅 Vadesi Gelmemiş", f"{sum_gelmemis:,.2f} USD", f"{int(m_gelmemis.sum())} Fatura")
    c2.metric("⚠️ Bugün Vadesi Dolan", f"{sum_bugun:,.2f} USD", f"{int(m_bugun.sum())} Fatura")
    c3.metric("⛔ Gecikmiş", f"{sum_gecikmis:,.2f} USD", f"{int(m_gecikmis.sum())} Fatura")

    acik_vadeler = vade_df_all[vade_df_all["Vade Tarihi"].notna() & (~vade_df_all["Ödendi"])].copy()
    if not acik_vadeler.empty:
        acik_vadeler["Kalan Gün"] = (acik_vadeler["Vade Tarihi"] - today_norm).dt.days
        st.markdown("#### 💸 Açık Vade Kayıtları")
        cols_show = ["Müşteri Adı", "Ülke", "Fatura No", "Vade Tarihi", "Tutar", "Kalan Gün"]
        cols_show = [c for c in cols_show if c in acik_vadeler.columns]
        if "Vade Tarihi" in cols_show:
            acik_vadeler["Vade Tarihi"] = pd.to_datetime(acik_vadeler["Vade Tarihi"], errors="coerce").dt.strftime("%d/%m/%Y")
        st.dataframe(acik_vadeler[cols_show].sort_values("Kalan Gün"), use_container_width=True)
    else:
        st.info("Açık vade kaydı yok.")

    st.markdown("---")

    # ---------- Bekleyen Teklifler ----------
    st.markdown("### 💰 Bekleyen Teklifler")
    bekleyen_teklifler = df_teklif[df_teklif.get("Durum") == "Açık"] if not df_teklif.empty else pd.DataFrame()
    toplam_teklif = pd.to_numeric(bekleyen_teklifler.get("Tutar", pd.Series()), errors="coerce").sum()
    st.markdown(f"<div style='font-size:1.1em; color:#11998e; font-weight:bold;'>Toplam: {toplam_teklif:,.2f} $</div>", unsafe_allow_html=True)
    if bekleyen_teklifler.empty:
        st.info("Bekleyen teklif yok.")
    else:
        st.dataframe(bekleyen_teklifler[[c for c in ["Müşteri Adı", "Tarih", "Teklif No", "Tutar", "Ürün/Hizmet", "Açıklama"] if c in bekleyen_teklifler.columns]], use_container_width=True)

    # ---------- Bekleyen Proformalar ----------
    st.markdown("### 📄 Bekleyen Proformalar")
    bekleyen_proformalar = df_proforma[df_proforma.get("Durum") == "Beklemede"] if not df_proforma.empty else pd.DataFrame()
    toplam_proforma = pd.to_numeric(bekleyen_proformalar.get("Tutar", pd.Series()), errors="coerce").sum()
    st.markdown(f"<div style='font-size:1.1em; color:#f7971e; font-weight:bold;'>Toplam: {toplam_proforma:,.2f} $</div>", unsafe_allow_html=True)
    if bekleyen_proformalar.empty:
        st.info("Bekleyen proforma yok.")
    else:
        st.dataframe(bekleyen_proformalar[[c for c in ["Müşteri Adı", "Proforma No", "Tarih", "Tutar", "Vade (gün)", "Açıklama"] if c in bekleyen_proformalar.columns]], use_container_width=True)

    # ---------- Sevk Bekleyen ----------
    st.markdown("### 🚚 Siparişe Dönüşen (Sevk Bekleyen) Siparişler")
    for col in ["Sevk Durumu", "Ülke", "Termin Tarihi"]:
        if col not in df_proforma.columns:
            df_proforma[col] = ""
    sevk_bekleyenler = df_proforma[(df_proforma.get("Durum") == "Siparişe Dönüştü") & (~df_proforma["Sevk Durumu"].isin(["Sevkedildi", "Ulaşıldı"]))] if not df_proforma.empty else pd.DataFrame()
    toplam_siparis = pd.to_numeric(sevk_bekleyenler.get("Tutar", pd.Series()), errors="coerce").sum()
    st.markdown(f"<div style='font-size:1.1em; color:#185a9d; font-weight:bold;'>Toplam: {toplam_siparis:,.2f} $</div>", unsafe_allow_html=True)
    if sevk_bekleyenler.empty:
        st.info("Sevk bekleyen sipariş yok.")
    else:
        disp = sevk_bekleyenler.copy()
        disp["Tarih"] = pd.to_datetime(disp["Tarih"], errors="coerce").dt.strftime("%d/%m/%Y")
        disp["Termin Tarihi"] = pd.to_datetime(disp["Termin Tarihi"], errors="coerce").dt.strftime("%d/%m/%Y")
        st.dataframe(disp[[c for c in ["Müşteri Adı", "Ülke", "Proforma No", "Tarih", "Termin Tarihi", "Tutar", "Vade (gün)", "Açıklama"] if c in disp.columns]], use_container_width=True)

    # ---------- Yolda Olan ----------
    st.markdown("### ⏳ Yolda Olan (ETA Takibi) Siparişler")
    eta_yolda = df_proforma[df_proforma.get("Sevk Durumu") == "Sevkedildi"] if not df_proforma.empty else pd.DataFrame()
    toplam_eta = pd.to_numeric(eta_yolda.get("Tutar", pd.Series()), errors="coerce").sum()
    st.markdown(f"<div style='font-size:1.1em; color:#c471f5; font-weight:bold;'>Toplam: {toplam_eta:,.2f} $</div>", unsafe_allow_html=True)
    if eta_yolda.empty:
        st.info("Yolda olan (sevk edilmiş) sipariş yok.")
    else:
        eta_disp = eta_yolda.copy()
        eta_disp["Tarih"] = pd.to_datetime(eta_disp["Tarih"], errors="coerce").dt.strftime("%d/%m/%Y")
        st.dataframe(eta_disp[[c for c in ["Müşteri Adı", "Ülke", "Proforma No", "Tarih", "Tutar", "Vade (gün)", "Açıklama"] if c in eta_disp.columns]], use_container_width=True)

    # ---------- Son Teslim Edilen ----------
    st.markdown("### ✅ Son Teslim Edilen (Ulaşıldı) 5 Sipariş")
    if "Sevk Durumu" in df_proforma.columns:
        teslim_edilenler = df_proforma[df_proforma["Sevk Durumu"] == "Ulaşıldı"].copy()
        if not teslim_edilenler.empty:
            teslim_edilenler = teslim_edilenler.sort_values(by="Tarih", ascending=False).head(5)
            teslim_edilenler["Tarih"] = pd.to_datetime(teslim_edilenler["Tarih"], errors="coerce").dt.strftime("%d/%m/%Y")
            st.dataframe(teslim_edilenler[[c for c in ["Müşteri Adı", "Ülke", "Proforma No", "Tarih", "Tutar", "Vade (gün)", "Açıklama"] if c in teslim_edilenler.columns]], use_container_width=True)
        else:
            st.info("Teslim edilmiş sipariş yok.")
    else:
        st.info("Teslim edilmiş sipariş yok.")

    st.markdown("<hr>", unsafe_allow_html=True)
    st.info("Detay işlemler için soldaki menülerden ilgili bölümlere geçebilirsiniz.")
