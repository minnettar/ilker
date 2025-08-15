# ======================
# 1) IMPORTLAR VE AYARLAR
# ======================
import os
import io
import datetime
import pandas as pd
import streamlit as st
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from google.oauth2 import service_account
from googleapiclient.errors import HttpError
import numpy as np
import smtplib
from email.message import EmailMessage
import uuid

# === Streamlit Ayarları ===
st.set_page_config(page_title="ŞEKEROĞLU İHRACAT CRM", layout="wide")

# === Kullanıcılar ===
USERS = {
    "export1": "Seker12345!",
    "admin": "Seker12345!",
    "Boss": "Seker12345!",
}

# === Giriş Sistemi ===
if "user" not in st.session_state:
    st.session_state.user = None

def login_screen():
    col1, col2 = st.columns([2, 6])
    with col1:
        st.image("https://www.sekeroglugroup.com/storage/settings/xdp5r6DZIFJMNGOStqwvKCiVHDhYxA84jFr61TNp.svg", width=150)
    with col2:
        st.title("ŞEKEROĞLU CRM - Giriş Ekranı")

    username = st.text_input("Kullanıcı Adı")
    password = st.text_input("Şifre", type="password")
    login_btn = st.button("Giriş Yap")

    if login_btn:
        if username in USERS and password == USERS[username]:
            st.session_state.user = username
            st.rerun()
        else:
            st.error("Kullanıcı adı veya şifre hatalı.")

if not st.session_state.user:
    login_screen()
    st.stop()

# === Çıkış ===
if st.sidebar.button("🚪 Çıkış Yap"):
    st.session_state.user = None
    st.rerun()

# ======================
# 2) ÜLKE ve TEMSİLCİ LİSTELERİ
# ======================
ulke_listesi = sorted([
    "Afganistan", "Almanya", "Amerika Birleşik Devletleri", "Andorra", "Angola", "Antigua ve Barbuda", "Arjantin",
    "Arnavutluk", "Avustralya", "Avusturya", "Azerbaycan", "Bahamalar", "Bahreyn", "Bangladeş", "Barbados", "Belçika",
    "Belize", "Benin", "Beyaz Rusya", "Bhutan", "Birleşik Arap Emirlikleri", "Birleşik Krallık", "Bolivya",
    "Bosna-Hersek", "Botsvana", "Brezilya", "Brunei", "Bulgaristan", "Burkina Faso", "Burundi", "Butan",
    "Cezayir", "Çad", "Çekya", "Çin", "Danimarka", "Doğu Timor", "Dominik Cumhuriyeti", "Dominika", "Ekvador",
    "Ekvator Ginesi", "El Salvador", "Endonezya", "Eritre", "Ermenistan", "Estonya", "Etiyopya", "Fas",
    "Fiji", "Fildişi Sahili", "Filipinler", "Filistin", "Finlandiya", "Fransa", "Gabon", "Gambia",
    "Gana", "Gine", "Gine-Bissau", "Grenada", "Guatemala", "Guyana", "Güney Afrika", "Güney Kore",
    "Güney Sudan", "Gürcistan", "Haiti", "Hindistan", "Hırvatistan", "Hollanda", "Honduras", "Hong Kong",
    "Irak", "İran", "İrlanda", "İspanya", "İsrail", "İsveç", "İsviçre", "İtalya", "İzlanda", "Jamaika",
    "Japonya", "Kamboçya", "Kamerun", "Kanada", "Karadağ", "Katar", "Kazakistan", "Kenya", "Kırgızistan",
    "Kiribati", "Kolombiya", "Komorlar", "Kongo", "Kongo Demokratik Cumhuriyeti", "Kostarika", "Küba",
    "Kuveyt", "Kuzey Kore", "Kuzey Makedonya", "Laos", "Lesotho", "Letonya", "Liberya", "Libya",
    "Liechtenstein", "Litvanya", "Lübnan", "Lüksemburg", "Macaristan", "Madagaskar", "Malavi", "Maldivler",
    "Malezya", "Mali", "Malta", "Marshall Adaları", "Meksika", "Mısır", "Mikronezya", "Moğolistan", "Moldova",
    "Monako", "Morityus", "Mozambik", "Myanmar", "Namibya", "Nauru", "Nepal", "Nijer", "Nijerya",
    "Nikaragua", "Norveç", "Orta Afrika Cumhuriyeti", "Özbekistan", "Pakistan", "Palau", "Panama", "Papua Yeni Gine",
    "Paraguay", "Peru", "Polonya", "Portekiz", "Romanya", "Ruanda", "Rusya", "Saint Kitts ve Nevis",
    "Saint Lucia", "Saint Vincent ve Grenadinler", "Samoa", "San Marino", "Sao Tome ve Principe", "Senegal",
    "Seyşeller", "Sırbistan", "Sierra Leone", "Singapur", "Slovakya", "Slovenya", "Solomon Adaları", "Somali",
    "Sri Lanka", "Sudan", "Surinam", "Suriye", "Suudi Arabistan", "Svaziland", "Şili", "Tacikistan", "Tanzanya",
    "Tayland", "Tayvan", "Togo", "Tonga", "Trinidad ve Tobago", "Tunus", "Tuvalu", "Türkiye", "Türkmenistan",
    "Uganda", "Ukrayna", "Umman", "Uruguay", "Ürdün", "Vanuatu", "Vatikan", "Venezuela", "Vietnam",
    "Yemen", "Yeni Zelanda", "Yunanistan", "Zambiya", "Zimbabve"
]) + ["Diğer"]

temsilci_listesi = ["KEMAL İLKER ÇELİKKALKAN", "HÜSEYİN POLAT", "EFE YILDIRIM", "FERHAT ŞEKEROĞLU"]

# ======================
# 3) GOOGLE SHEETS & DRIVE BAĞLANTILARI
# ======================
SHEET_ID         = "1nKuBKJPzpYC5TxNvc4G2OgI7miytuLBQE0n31I3yue0"
FIYAT_TEKLIFI_ID = "1TNjwx-xhmlxNRI3ggCJA7jaCAu9Lt_65"
PROFORMA_PDF_ID  = "17lPkdYcC4BdowLdCsiWxiq0H_6oVGXLs"
SIPARIS_FORMU_ID = "1xeTdhOE1Cc6ohJsRzPVlCMMraBIXWO9w"
EVRAK_KLASOR_ID  = "14FTE1oSeIeJ6Y_7C0oQyZPKC8dK8hr1J"

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]

creds = service_account.Credentials.from_service_account_info(
    st.secrets["gcp_service_account"], scopes=SCOPES
)
sheets_service = build("sheets", "v4", credentials=creds)
sheet = sheets_service.spreadsheets()
drive_service = build("drive", "v3", credentials=creds)

# ======================
# SHEETS <-> DATAFRAME YAZMA/OKUMA (KOTA DOSTU)
# ======================
import time, random, uuid, datetime, pandas as pd
from googleapiclient.errors import HttpError

# --- Retry edilecek HTTP kodları ---
RETRY_STATUS = {429, 500, 502, 503, 504}

def _sheets_retry(callable_fn, *, max_tries=6, base=0.6, jitter=0.4, what="sheets"):
    """Google API çağrılarını 429/5xx/timeout durumlarında exponential backoff ile tekrar dener."""
    attempt = 0
    while True:
        try:
            return callable_fn()
        except HttpError as he:
            code = getattr(getattr(he, "resp", None), "status", None)
            if code in RETRY_STATUS and attempt < max_tries - 1:
                wait = base * (2 ** attempt) + random.uniform(0, jitter)
                print(f"[retry] {what}: HttpError {code}, {attempt+1}/{max_tries} -> {wait:.2f}s")
                time.sleep(wait); attempt += 1; continue
            raise
        except Exception as e:
            msg = str(e).lower()
            transient = any(k in msg for k in ["timed out","timeout","temporarily","reset","connection aborted"])
            if transient and attempt < max_tries - 1:
                wait = base * (2 ** attempt) + random.uniform(0, jitter)
                print(f"[retry] {what}: transient err '{e}', {attempt+1}/{max_tries} -> {wait:.2f}s")
                time.sleep(wait); attempt += 1; continue
            raise

# --- ID güvencesi (tek tanım) ---
def ensure_id(df: pd.DataFrame, id_col: str = "ID") -> pd.DataFrame:
    """
    DataFrame'te id_col sütununu garanti eder; boş olan hücreleri uuid4 ile doldurur.
    Var olan ID'lere dokunmaz, Sheets'e burada yazmaz.
    """
    if df is None:
        return pd.DataFrame({id_col: []})
    if id_col not in df.columns:
        df[id_col] = ""
    mask = df[id_col].astype(str).str.strip().isin(["", "nan", "none", "None"])
    if mask.any():
        df.loc[mask, id_col] = [str(uuid.uuid4()) for _ in range(mask.sum())]
    return df

def _safe_str(x):
    if pd.isna(x): return ""
    if isinstance(x, (pd.Timestamp, datetime.datetime, datetime.date)):
        try: return pd.to_datetime(x).strftime("%Y-%m-%d")
        except Exception: return str(x)
    return str(x)

def df_to_values(df: pd.DataFrame):
    """DataFrame'i Sheets'e uygun 2D listeye çevirir (ilk satır başlıklar)."""
    if not isinstance(df, pd.DataFrame): return [[]]
    if df.empty:
        cols = df.columns.tolist()
        return [cols] if cols else [[]]
    clean = df.copy()
    for c in clean.columns:
        clean[c] = clean[c].map(_safe_str)
    return [clean.columns.tolist()] + clean.values.tolist()

# ---- THROTTLE: çok sık yazmayı boğma (örn. 1.2s) ----
if "_last_sheet_write_ts" not in st.session_state:
    st.session_state._last_sheet_write_ts = 0.0

def _throttle(min_interval_sec=1.2):
    now = time.time()
    delta = now - st.session_state._last_sheet_write_ts
    if delta < min_interval_sec:
        time.sleep(min_interval_sec - delta)
    st.session_state._last_sheet_write_ts = time.time()

def write_df(sheet_name: str, df: pd.DataFrame, *, allow_clear_on_empty: bool = False):
    """
    Kota dostu yazma:
    - CLEAR YOK. A1'den itibaren tek 'update' isteği.
    - df boşsa ve allow_clear_on_empty=False ise yazmaz (sayfayı KORUR).
    """
    try:
        if not isinstance(df, pd.DataFrame):
            print(f"[write_df] {sheet_name}: df DataFrame değil, atlandı."); return
        if df.empty and not allow_clear_on_empty:
            print(f"[write_df] {sheet_name}: DF boş → yazma atlandı (sayfa korundu)."); return

        values = df_to_values(df)

        def _do_update():
            return sheet.values().update(
                spreadsheetId=SHEET_ID,
                range=f"{sheet_name}!A1",
                valueInputOption="RAW",
                body={"values": values}
            ).execute()

        _throttle()
        _sheets_retry(_do_update, what=f"update:{sheet_name}")
        print(f"[write_df] {sheet_name}: {len(df)} satır yazıldı (tek istek, clear yok).")
    except Exception as e:
        print(f"[write_df] '{sheet_name}' yazılırken hata: {e}")

def update_google_sheets():
    """Tüm sayfaları kota dostu şekilde günceller (clear yok, sayfa sayfa update)."""
    for name, df in [
        ("Sayfa1", df_musteri),
        ("Kayıtlar", df_kayit),
        ("Teklifler", df_teklif),
        ("Proformalar", df_proforma),
        ("Evraklar", df_evrak),
        ("ETA", df_eta),
        ("FuarMusteri", df_fuar_musteri),
    ]:
        try:
            write_df(name, df)
        except Exception as e:
            print(f"[update] {name}: {e}")

def load_sheet_as_df(sheet_name: str, columns: list[str]) -> pd.DataFrame:
    """
    Sayfayı okur (retry'li), eksik kolonları ekler ve kolon sırasını 'columns' ile sabitler.
    Boşsa belirtilen kolonlarla boş DF döner.
    """
    try:
        def _do_get():
            return sheet.values().get(spreadsheetId=SHEET_ID, range=sheet_name).execute()

        ws = _sheets_retry(_do_get, what=f"get:{sheet_name}")
        values = ws.get("values", [])
        if not values:
            return pd.DataFrame(columns=columns)

        header = [h.strip() for h in values[0]]
        data_rows = values[1:]
        H = len(header)

        fixed_rows = []
        for r in data_rows:
            r = list(r)
            if len(r) < H: r = r + [""] * (H - len(r))
            elif len(r) > H: r = r[:H]
            fixed_rows.append(r)

        df = pd.DataFrame(fixed_rows, columns=header)

        # Eksik kolonları ekle, sırayı sabitle
        for col in columns:
            if col not in df.columns:
                df[col] = ""
        return df[columns]
    except Exception as e:
        print(f"'{sheet_name}' sayfası yüklenirken hata: {e}")
        return pd.DataFrame(columns=columns)

# ======================
# 3b) DRIVE YARDIMCILARI
# ======================
def _guess_mime_by_ext(filename: str) -> str:
    ext = os.path.splitext(filename.lower())[1]
    return {
        ".pdf":  "application/pdf",
        ".jpg":  "image/jpeg",
        ".jpeg": "image/jpeg",
        ".png":  "image/png",
        ".csv":  "text/csv",
        ".xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        ".xls":  "application/vnd.ms-excel",
        ".txt":  "text/plain",
        ".webp": "image/webp",
    }.get(ext, "application/octet-stream")

def _sanitize_filename(name: str) -> str:
    keep = "-_.() "
    s = "".join(ch if ch.isalnum() or ch in keep else "_" for ch in str(name))
    return s[:180] if s else "dosya"

def upload_file_to_drive(folder_id: str, local_path: str, filename: str) -> str:
    filename = _sanitize_filename(filename.strip())
    folder_id = folder_id.strip()
    media = MediaFileUpload(local_path, mimetype=_guess_mime_by_ext(filename), resumable=False)
    meta = {"name": filename}
    if folder_id: meta["parents"] = [folder_id]
    try:
        created = drive_service.files().create(
            body=meta, media_body=media, fields="id", supportsAllDrives=True
        ).execute()
        fid = created["id"]
        # herkese görüntüleme izni (hata verirse yut)
        try:
            drive_service.permissions().create(
                fileId=fid, body={"role": "reader", "type": "anyone"}, fields="id"
            ).execute()
        except Exception:
            pass
        return f"https://drive.google.com/file/d/{fid}/view?usp=sharing"
    except HttpError as he:
        code = getattr(getattr(he, "resp", None), "status", "unknown")
        try:
            detail = he.content.decode() if getattr(he, "content", None) else str(he)
        except Exception:
            detail = str(he)
        tips = []
        if code in (403, 404):
            tips += [
                "• Klasör ID’si doğru mu ve servis hesabıyla paylaşıldı mı?",
                "• Klasör Paylaşılan Sürücü mü? supportsAllDrives=True eklendi.",
                "• SCOPES içinde tam 'drive' yetkisi var (ekli).",
            ]
        if code == 400:
            tips += ["• 'parents' alanındaki ID mutlaka klasör ID olmalı."]
        raise RuntimeError(f"Drive yükleme hatası (HTTP {code}). Ayrıntı: {detail}\n" + "\n".join(tips)) from he

# ======================
# 3c) SHEETS -> DATAFRAME YÜKLEME ve ID'leri GARANTİ ETME
# ======================
df_musteri = load_sheet_as_df("Sayfa1", [
    "Müşteri Adı","Telefon","E-posta","Adres","Ülke",
    "Satış Temsilcisi","Kategori","Durum","Vade (Gün)","Ödeme Şekli",
    "Para Birimi","DT Seçimi"
])
df_kayit = load_sheet_as_df("Kayıtlar", [
    "Müşteri Adı","Tarih","Tip","Açıklama"
])
df_teklif = load_sheet_as_df("Teklifler", [
    "Müşteri Adı","Tarih","Teklif No","Tutar",
    "Ürün/Hizmet","Açıklama","Durum","PDF"
])
df_proforma = load_sheet_as_df("Proformalar", [
    "Müşteri Adı","Tarih","Proforma No","Tutar","Açıklama",
    "Durum","PDF","Sipariş Formu","Vade (gün)","Sevk Durumu",
    "Ülke","Satış Temsilcisi","Ödeme Şekli","Termin Tarihi",
    "Sevk Tarihi","Ulaşma Tarihi"
])
df_evrak = load_sheet_as_df("Evraklar", [
    "Müşteri Adı","Proforma No","Fatura No","Fatura Tarihi","Vade (gün)","Vade Tarihi","Tutar",
    "Ülke","Satış Temsilcisi","Ödeme Şekli",
    "Commercial Invoice","Sağlık Sertifikası","Packing List","Konşimento","İhracat Beyannamesi",
    "Fatura PDF","Sipariş Formu","Yük Resimleri","EK Belgeler","Ödendi"
])
df_eta = load_sheet_as_df("ETA", [
    "Müşteri Adı","Proforma No","ETA Tarihi","Açıklama"
])
df_fuar_musteri = load_sheet_as_df("FuarMusteri", [
    "Fuar Adı","Müşteri Adı","Ülke","Telefon","E-mail","Satış Temsilcisi",
    "Açıklamalar","Görüşme Kalitesi","Tarih"
])

# --- ID sütunlarını garanti et (tek sefer) ---
df_musteri      = ensure_id(df_musteri)
df_kayit        = ensure_id(df_kayit)
df_teklif       = ensure_id(df_teklif)
df_proforma     = ensure_id(df_proforma)
df_evrak        = ensure_id(df_evrak)
df_eta          = ensure_id(df_eta)
df_fuar_musteri = ensure_id(df_fuar_musteri)

# --- Sayısal yardımcı (örn. vade/özet ekranlar) ---
def smart_to_num(x):
    if pd.isna(x): return 0.0
    s = str(x).strip()
    for sym in ["USD","$","€","EUR","₺","TL","tl","Tl"]:
        s = s.replace(sym, "")
    s = s.replace("\u00A0","").replace(" ","")
    try: return float(s)              # US format
    except Exception: pass
    if "," in s:
        try: return float(s.replace(".","").replace(",", "."))  # EU format
        except Exception: pass
    return 0.0

if "Tutar" in df_evrak.columns and "Tutar_num" not in df_evrak.columns:
    df_evrak["Tutar_num"] = df_evrak["Tutar"].apply(smart_to_num).fillna(0.0)

# ============================================================================ 

# ========= ŞIK SIDEBAR MENÜ (RADIO + ANINDA STATE) =========

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

# 2) Tüm kullanıcılar için aynı menüler (ileride role bazlı filtre eklenebilir)
allowed_menus = menuler

# 3) Etiketler ve haritalar
labels = [f"{ikon} {isim}" for (isim, ikon) in allowed_menus]
name_by_label = {f"{ikon} {isim}": isim for (isim, ikon) in allowed_menus}
label_by_name = {isim: f"{ikon} {isim}" for (isim, ikon) in allowed_menus}

# 4) Varsayılan state
if "menu_state" not in st.session_state:
    st.session_state.menu_state = allowed_menus[0][0]

# 5) CSS (kart görünümü)
st.sidebar.markdown("""
<style>
section[data-testid="stSidebar"] { padding-top: .5rem; }
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
div[data-testid="stSidebar"] .stRadio label:nth-child(1)  { background: linear-gradient(90deg,#1D976C,#93F9B9); }
div[data-testid="stSidebar"] .stRadio label:nth-child(2)  { background: linear-gradient(90deg,#43cea2,#185a9d); }
div[data-testid="stSidebar"] .stRadio label:nth-child(3)  { background: linear-gradient(90deg,#ffb347,#ffcc33); }
div[data-testid="stSidebar"] .stRadio label:nth-child(4)  { background: linear-gradient(90deg,#ff5e62,#ff9966); }
div[data-testid="stSidebar"] .stRadio label:nth-child(5)  { background: linear-gradient(90deg,#8e54e9,#4776e6); }
div[data-testid="stSidebar"] .stRadio label:nth-child(6)  { background: linear-gradient(90deg,#11998e,#38ef7d); }
div[data-testid="stSidebar"] .stRadio label:nth-child(7)  { background: linear-gradient(90deg,#f7971e,#ffd200); }
div[data-testid="stSidebar"] .stRadio label:nth-child(8)  { background: linear-gradient(90deg,#f953c6,#b91d73); }
div[data-testid="stSidebar"] .stRadio label:nth-child(9)  { background: linear-gradient(90deg,#43e97b,#38f9d7); }
div[data-testid="stSidebar"] .stRadio label:nth-child(10) { background: linear-gradient(90deg,#f857a6,#ff5858); }
div[data-testid="stSidebar"] .stRadio label:nth-child(11) { background: linear-gradient(90deg,#8e54e9,#bd4de6); }
div[data-testid="stSidebar"] .stRadio label:nth-child(12) { background: linear-gradient(90deg,#4b79a1,#283e51); }
div[data-testid="stSidebar"] .stRadio label:nth-child(13) { background: linear-gradient(90deg,#2b5876,#4e4376); }
</style>
""", unsafe_allow_html=True)

# 6) Callback: seçilince anında state yaz
def _on_menu_change():
    sel_label = st.session_state.get("menu_radio_label")
    st.session_state.menu_state = name_by_label.get(sel_label, allowed_menus[0][0])

# 7) Radio’yu mevcut state’e göre başlat (güvenli index)
current_label = label_by_name.get(st.session_state.menu_state, labels[0])
try:
    current_index = labels.index(current_label)
except ValueError:
    current_index = 0

st.sidebar.radio(
    "Menü",
    labels,
    index=current_index,
    label_visibility="collapsed",
    key="menu_radio_label",
    on_change=_on_menu_change
)

# 8) Seçili menü adı
menu = st.session_state.menu_state
# ========= /ŞIK MENÜ =========


# ===========================
# === ÖZET EKRAN MENÜSÜ ===
# ===========================

if menu == "Özet Ekran":
    st.markdown("<h2 style='color:#8e44ad; font-weight:bold;'>ŞEKEROĞLU İHRACAT CRM - Özet Ekran</h2>", unsafe_allow_html=True)

    # ---------- Akıllı sayı dönüştürücü ----------
    def smart_to_num(x):
        if pd.isna(x): 
            return 0.0
        s = str(x).strip()
        for sym in ["USD", "$", "€", "EUR", "₺", "TL", "tl", "Tl"]:
            s = s.replace(sym, "")
        s = s.replace("\u00A0", "").replace(" ", "")
        try:
            return float(s)              # US format
        except Exception:
            pass
        if "," in s:
            try:
                return float(s.replace(".", "").replace(",", "."))  # EU format
            except Exception:
                pass
        return 0.0

    # ---------- EVRAK: kolon güvenliği ----------
    for col in ["Tutar", "Vade Tarihi", "Ödendi"]:
        if col not in df_evrak.columns:
            df_evrak[col] = "" if col != "Ödendi" else False

    evr = df_evrak.copy()
    evr["Tutar_num"] = evr["Tutar"].apply(smart_to_num).fillna(0.0)
    evr["Ödendi"] = evr["Ödendi"].fillna(False).astype(bool)
    evr["Vade Tarihi"] = pd.to_datetime(evr["Vade Tarihi"], errors="coerce")

    # ---------- Toplam fatura ----------
    toplam_fatura_tutar = float(evr["Tutar_num"].sum())
    st.markdown(
        f"<div style='font-size:1.5em; color:#d35400; font-weight:bold;'>💵 Toplam Fatura Tutarı: {toplam_fatura_tutar:,.2f} USD</div>",
        unsafe_allow_html=True
    )

    # ---------- Vade durumu kartları ----------
    today_norm = pd.Timestamp.today().normalize()
    odem_dis = ~evr["Ödendi"]

    vadesi_gelmemis_m = (evr["Vade Tarihi"] > today_norm) & odem_dis
    vadesi_bugun_m     = (evr["Vade Tarihi"].dt.date == today_norm.date()) & odem_dis
    gecikmis_m         = (evr["Vade Tarihi"] < today_norm) & odem_dis

    tg_sum  = float(evr.loc[vadesi_gelmemis_m, "Tutar_num"].sum())
    tb_sum  = float(evr.loc[vadesi_bugun_m,     "Tutar_num"].sum())
    gec_sum = float(evr.loc[gecikmis_m,         "Tutar_num"].sum())

    c1, c2, c3 = st.columns(3)
    c1.metric("📅 Vadesi Gelmemiş", f"{tg_sum:,.2f} USD", f"{int(vadesi_gelmemis_m.sum())} Fatura")
    c2.metric("⚠️ Bugün Vadesi Dolan", f"{tb_sum:,.2f} USD", f"{int(vadesi_bugun_m.sum())} Fatura")
    c3.metric("⛔ Gecikmiş",          f"{gec_sum:,.2f} USD", f"{int(gecikmis_m.sum())} Fatura")

    st.markdown("---")

    # ============= AÇIK FİYAT TEKLİFLERİ =============
    for col in ["Durum", "Tutar", "Müşteri Adı", "Tarih", "Teklif No", "Ürün/Hizmet", "Açıklama"]:
        if col not in df_teklif.columns:
            df_teklif[col] = ""
    tkg = df_teklif.copy()
    tkg["Tarih"] = pd.to_datetime(tkg["Tarih"], errors="coerce")
    tkg["Tutar_num"] = tkg["Tutar"].apply(smart_to_num)

    acik_teklifler = tkg[tkg["Durum"] == "Açık"].sort_values(["Müşteri Adı", "Teklif No"])
    toplam_teklif  = float(acik_teklifler["Tutar_num"].sum())

    st.markdown("### 💰 Bekleyen (Açık) Teklifler")
    st.markdown(f"<div style='font-size:1.1em; color:#11998e; font-weight:bold;'>Toplam: {toplam_teklif:,.2f} USD | Adet: {len(acik_teklifler)}</div>", unsafe_allow_html=True)
    if acik_teklifler.empty:
        st.info("Açık teklif bulunmuyor.")
    else:
        goster = acik_teklifler.copy()
        goster["Tarih"] = goster["Tarih"].dt.strftime("%d/%m/%Y")
        st.dataframe(
            goster[["Müşteri Adı", "Tarih", "Teklif No", "Tutar", "Ürün/Hizmet", "Açıklama"]],
            use_container_width=True
        )

    st.markdown("---")

    # ============= BEKLEYEN PROFORMALAR =============
    for col in ["Durum", "Tutar", "Müşteri Adı", "Proforma No", "Tarih", "Vade (gün)", "Açıklama"]:
        if col not in df_proforma.columns:
            df_proforma[col] = ""
    prf = df_proforma.copy()
    prf["Tarih"] = pd.to_datetime(prf["Tarih"], errors="coerce")
    prf["Tutar_num"] = prf["Tutar"].apply(smart_to_num)

    bekleyen_prf = prf[prf["Durum"] == "Beklemede"].sort_values("Tarih", ascending=False)
    toplam_prf   = float(bekleyen_prf["Tutar_num"].sum())

    st.markdown("### 📄 Bekleyen Proformalar")
    st.markdown(f"<div style='font-size:1.1em; color:#f7971e; font-weight:bold;'>Toplam: {toplam_prf:,.2f} USD | Adet: {len(bekleyen_prf)}</div>", unsafe_allow_html=True)
    if bekleyen_prf.empty:
        st.info("Bekleyen proforma yok.")
    else:
        g = bekleyen_prf.copy()
        g["Tarih"] = g["Tarih"].dt.strftime("%d/%m/%Y")
        st.dataframe(
            g[["Müşteri Adı", "Proforma No", "Tarih", "Tutar", "Vade (gün)", "Açıklama"]],
            use_container_width=True
        )

    st.markdown("---")

    # ============= SİPARİŞE DÖNÜŞEN (SEVK BEKLEYEN) =============
    for col in ["Sevk Durumu"]:
        if col not in prf.columns:
            prf[col] = ""
    sevk_bekleyen = prf[(prf["Durum"] == "Siparişe Dönüştü") & (~prf["Sevk Durumu"].isin(["Sevkedildi", "Ulaşıldı"]))].copy()
    toplam_sip    = float(sevk_bekleyen["Tutar_num"].sum())

    st.markdown("### 🚚 Siparişe Dönüşen (Sevk Bekleyen) Siparişler")
    st.markdown(f"<div style='font-size:1.1em; color:#185a9d; font-weight:bold;'>Toplam: {toplam_sip:,.2f} USD | Adet: {len(sevk_bekleyen)}</div>", unsafe_allow_html=True)
    if sevk_bekleyen.empty:
        st.info("Sevk bekleyen sipariş yok.")
    else:
        g = sevk_bekleyen.copy()
        g["Tarih"] = pd.to_datetime(g["Tarih"], errors="coerce").dt.strftime("%d/%m/%Y")
        st.dataframe(
            g[["Müşteri Adı", "Ülke", "Proforma No", "Tarih", "Tutar", "Vade (gün)", "Açıklama"]].reindex(columns=[c for c in ["Müşteri Adı", "Ülke", "Proforma No", "Tarih", "Tutar", "Vade (gün)", "Açıklama"] if c in g.columns]),
            use_container_width=True
        )

    st.markdown("---")

    # ============= YOLDA OLANLAR (ETA) =============
    yolda = prf[(prf["Sevk Durumu"] == "Sevkedildi") & (prf["Sevk Durumu"] != "Ulaşıldı")].copy()
    toplam_eta = float(yolda["Tutar_num"].sum())

    st.markdown("### ⏳ Yolda Olan (ETA Takibi) Siparişler")
    st.markdown(f"<div style='font-size:1.1em; color:#c471f5; font-weight:bold;'>Toplam: {toplam_eta:,.2f} USD | Adet: {len(yolda)}</div>", unsafe_allow_html=True)
    if yolda.empty:
        st.info("Yolda olan (sevk edilmiş) sipariş yok.")
    else:
        g = yolda.copy()
        g["Tarih"] = pd.to_datetime(g["Tarih"], errors="coerce").dt.strftime("%d/%m/%Y")
        st.dataframe(
            g[["Müşteri Adı", "Ülke", "Proforma No", "Tarih", "Tutar", "Vade (gün)", "Açıklama"]].reindex(columns=[c for c in ["Müşteri Adı", "Ülke", "Proforma No", "Tarih", "Tutar", "Vade (gün)", "Açıklama"] if c in g.columns]),
            use_container_width=True
        )

    st.markdown("---")

    # ============= SON TESLİM EDİLENLER (ULAŞILDI) =============
    for col in ["Ulaşma Tarihi"]:
        if col not in prf.columns:
            prf[col] = ""
    teslim = prf[prf["Sevk Durumu"] == "Ulaşıldı"].copy()
    teslim["Ulaşma Tarihi"] = pd.to_datetime(teslim["Ulaşma Tarihi"], errors="coerce")
    teslim = teslim.sort_values("Ulaşma Tarihi", ascending=False).head(5)

    st.markdown("### ✅ Son Teslim Edilen (Ulaşıldı) 5 Sipariş")
    if teslim.empty:
        st.info("Teslim edilmiş sipariş yok.")
    else:
        g = teslim.copy()
        g["Tarih"] = pd.to_datetime(g["Tarih"], errors="coerce").dt.strftime("%d/%m/%Y")
        g["Ulaşma Tarihi"] = g["Ulaşma Tarihi"].dt.strftime("%d/%m/%Y")
        st.dataframe(
            g[["Müşteri Adı", "Ülke", "Proforma No", "Tarih", "Ulaşma Tarihi", "Tutar", "Açıklama"]].reindex(columns=[c for c in ["Müşteri Adı", "Ülke", "Proforma No", "Tarih", "Ulaşma Tarihi", "Tutar", "Açıklama"] if c in g.columns]),
            use_container_width=True
        )

    st.markdown("---")

    # ============= VADE TABLOSU (AÇIK ÖDEMELER) =============
    st.markdown("### 💸 Vadeli Fatura ve Tahsilat Takibi")
    vade_df = evr[(evr["Vade Tarihi"].notna()) & (~evr["Ödendi"])].copy()
    if vade_df.empty:
        st.info("Açık vade kaydı yok.")
    else:
        vade_df["Kalan Gün"] = (vade_df["Vade Tarihi"] - today_norm).dt.days
        g = vade_df.copy()
        g["Vade Tarihi"] = g["Vade Tarihi"].dt.strftime("%d/%m/%Y")
        # Kolon güvenli gösterim
        show_cols = [c for c in ["Müşteri Adı", "Ülke", "Fatura No", "Vade Tarihi", "Tutar", "Kalan Gün"] if c in g.columns]
        st.dataframe(g[show_cols].sort_values(["Kalan Gün", "Vade Tarihi"]), use_container_width=True)

    st.caption("Detay işlem için sol menüden ilgili sayfalara geçebilirsiniz.")


### ===========================
### === CARİ EKLEME MENÜSÜ ===
### ===========================

if menu == "Cari Ekleme":
    st.markdown("<h2 style='color:#219A41; font-weight:bold;'>Yeni Müşteri Ekle</h2>", unsafe_allow_html=True)

    # ---- Yardımcılar: doğrulama & normalizasyon ----
    import re
    def _clean_text(s):
        return (str(s or "")).strip()

    def _valid_email(s):
        s = _clean_text(s)
        if not s:
            return True  # boşsa zorunlu değil; doluysa kontrol
        return re.match(r"^[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}$", s) is not None

    def _normalized_phone(s):
        digits = re.sub(r"\D+", "", str(s or ""))
        return digits

    # Mükerrer kontrol için set (ad+ülke)
    if df_musteri.empty:
        existing_pairs = set()
    else:
        existing_pairs = set(
            (str(a).strip().lower(), str(u).strip().lower())
            for a, u in zip(df_musteri.get("Müşteri Adı", []), df_musteri.get("Ülke", []))
        )

    with st.form("add_customer", clear_on_submit=False):
        c1, c2 = st.columns(2)
        with c1:
            name = st.text_input("Müşteri Adı *", placeholder="Örn: ABC Dış Ticaret Ltd.")
            phone = st.text_input("Telefon", placeholder="+90 ...")
            email = st.text_input("E-posta", placeholder="ornek@firma.com")
            address = st.text_area("Adres")
            kategori = st.selectbox("Kategori", ["Avrupa bayi", "bayi", "müşteri", "yeni müşteri"], index=3)
            aktif_pasif = st.selectbox("Durum", ["Aktif", "Pasif"], index=0)
        with c2:
            ulke = st.selectbox("Ülke *", ulke_listesi)
            temsilci = st.selectbox("Satış Temsilcisi *", temsilci_listesi)
            vade_gun = st.number_input("Vade (Gün Sayısı)", min_value=0, max_value=365, value=0, step=1)
            odeme_sekli = st.selectbox("Ödeme Şekli", ["Peşin", "Mal Mukabili", "Vesaik Mukabili", "Akreditif", "Diğer"])
            para_birimi = st.selectbox("Para Birimi", ["USD", "EUR", "TL"], index=0)
            dt_secim = st.selectbox("DT Seçin", ["DT-1", "DT-2", "DT-3", "DT-4"], index=0)

        submitted = st.form_submit_button("Kaydet")

    if submitted:
        # --- Normalizasyon ---
        name_n = _clean_text(name)
        ulke_n = _clean_text(ulke)
        email_n = _clean_text(email)
        phone_n = _normalized_phone(phone)

        # --- Zorunlu alanlar ---
        errors = []
        if not name_n:
            errors.append("Müşteri adı boş olamaz.")
        if not ulke_n:
            errors.append("Ülke seçimi zorunludur.")
        if not temsilci:
            errors.append("Satış temsilcisi seçimi zorunludur.")
        if not _valid_email(email_n):
            errors.append("E-posta formatı hatalı görünüyor.")

        # --- Mükerrer kontrol (Ad + Ülke) ---
        key = (name_n.lower(), ulke_n.lower())
        if key in existing_pairs:
            errors.append("Aynı ada ve ülkeye ait bir müşteri zaten kayıtlı görünüyor.")

        if errors:
            for e in errors:
                st.error(e)
            st.stop()

        # --- Yeni satır ---
        new_row = {
            "Müşteri Adı": name_n,
            "Telefon": phone_n,
            "E-posta": email_n,
            "Adres": _clean_text(address),
            "Ülke": ulke_n,
            "Satış Temsilcisi": temsilci,
            "Kategori": kategori,
            "Durum": aktif_pasif,
            "Vade (Gün)": vade_gun,
            "Ödeme Şekli": odeme_sekli,
            "Para Birimi": para_birimi,
            "DT Seçimi": dt_secim,
            "Oluşturma Tarihi": datetime.date.today(),
        }

        # --- Kaydet ---
        df_musteri = pd.concat([df_musteri, pd.DataFrame([new_row])], ignore_index=True)
        update_google_sheets()

        # --- Muhasebeye e-posta ---
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
            st.warning(f"Müşteri eklendi ancak e-posta gönderilemedi: {e}")

        st.balloons()
        st.rerun()

                
### ===========================
### === MÜŞTERİ LİSTESİ MENÜSÜ (Cloud-Sağlam) ===
### ===========================

import uuid
import numpy as np  # Eksik bilgi gösterimi için

# — Zorunlu sütunları garanti altına al —
gerekli_kolonlar = [
    "ID", "Müşteri Adı", "Telefon", "E-posta", "Adres",
    "Ülke", "Satış Temsilcisi", "Kategori", "Durum",
    "Vade (Gün)", "Ödeme Şekli", "Para Birimi", "DT Seçimi"
]
for col in gerekli_kolonlar:
    if col not in df_musteri.columns:
        if col == "ID":
            df_musteri[col] = [str(uuid.uuid4()) for _ in range(len(df_musteri))] if len(df_musteri) > 0 else []
        else:
            df_musteri[col] = ""

# — Eski kayıtlarda ID boşsa doldur —
mask_id_bos = df_musteri["ID"].astype(str).str.strip().isin(["", "nan", "None"])
if mask_id_bos.any():
    df_musteri.loc[mask_id_bos, "ID"] = [str(uuid.uuid4()) for _ in range(mask_id_bos.sum())]
    update_google_sheets()

if menu == "Müşteri Listesi":
    st.markdown("<h2 style='color:#219A41; font-weight:bold;'>Müşteri Listesi</h2>", unsafe_allow_html=True)

    # ---- Üst Araçlar: Arama + Filtreler ----
    with st.container():
        c1, c2, c3, c4 = st.columns([2, 1.2, 1.2, 1.2])
        aranacak = c1.text_input("🔎 Arama (Ad / Telefon / E-posta / Adres)", value="")
        ulke_filtre = c2.multiselect(
            "Ülke Filtresi",
            sorted([u for u in df_musteri["Ülke"].dropna().unique() if str(u).strip()]),
            default=[]
        )
        temsilci_filtre = c3.multiselect(
            "Temsilci Filtresi",
            sorted([t for t in df_musteri["Satış Temsilcisi"].dropna().unique() if str(t).strip()]),
            default=[]
        )
        durum_filtre = c4.multiselect("Durum", ["Aktif", "Pasif"], default=["Aktif"])  # Varsayılan: Aktif

    # ---- Filtreleme mantığı ----
    view_df = df_musteri.copy()

    # Durum filtresi
    if len(durum_filtre) > 0:
        view_df = view_df[view_df["Durum"].isin(durum_filtre)]

    # Ülke filtresi
    if len(ulke_filtre) > 0:
        view_df = view_df[view_df["Ülke"].isin(ulke_filtre)]

    # Temsilci filtresi
    if len(temsilci_filtre) > 0:
        view_df = view_df[view_df["Satış Temsilcisi"].isin(temsilci_filtre)]

    # Arama filtresi
    if aranacak.strip():
        s = aranacak.strip().lower()
        def _match(row):
            fields = [
                row.get("Müşteri Adı", ""), row.get("Telefon", ""), row.get("E-posta", ""),
                row.get("Adres", ""), row.get("Ülke", ""), row.get("Satış Temsilcisi", "")
            ]
            return any(s in str(x).lower() for x in fields)
        view_df = view_df[view_df.apply(_match, axis=1)]

    # Görüntü tablosu (boşları sadece tabloda “—” yap)
    show_cols = [
        "Müşteri Adı", "Ülke", "Satış Temsilcisi", "Telefon", "E-posta", "Adres",
        "Kategori", "Durum", "Vade (Gün)", "Ödeme Şekli", "Para Birimi", "DT Seçimi"
    ]
    for c in show_cols:
        if c not in view_df.columns:
            view_df[c] = ""

    table_df = view_df[show_cols].replace({np.nan: "—", "": "—"})
    table_df = table_df.sort_values("Müşteri Adı", na_position="last").reset_index(drop=True)

    # Özet bilgi ve dışa aktar
    top_row = st.columns([3, 1])
    with top_row[0]:
        st.markdown(f"<div style='color:#219A41; font-weight:700;'>Toplam Kayıt: {len(view_df)}</div>", unsafe_allow_html=True)
    with top_row[1]:
        st.download_button(
            "⬇️ CSV indir",
            data=table_df.to_csv(index=False).encode("utf-8"),
            file_name="musteri_listesi.csv",
            mime="text/csv",
            use_container_width=True
        )

    if table_df.empty:
        st.markdown(
            "<div style='color:#b00020; font-weight:bold; font-size:1.1em;'>Kayıt bulunamadı.</div>",
            unsafe_allow_html=True
        )
    else:
        st.dataframe(table_df, use_container_width=True)

    st.markdown("<h4 style='margin-top: 24px;'>Müşteri Düzenle / Sil</h4>", unsafe_allow_html=True)

    # Düzenleme/Silme için seçim: ID ile — güvenli
    secenek_df = view_df.sort_values("Müşteri Adı", na_position="last").reset_index(drop=True)
    if secenek_df.empty:
        st.info("Düzenlemek/silmek için uygun kayıt yok.")
    else:
        secim = st.selectbox(
            "Düzenlenecek Müşteriyi Seçin",
            options=secenek_df["ID"].tolist(),
            format_func=lambda _id: f"{secenek_df.loc[secenek_df['ID']==_id, 'Müşteri Adı'].values[0]} "
                                    f"({secenek_df.loc[secenek_df['ID']==_id, 'Kategori'].values[0]})"
        )

        # Orijinal index (ana df_musteri içinden) — ID ile eşle
        orj_mask = (df_musteri["ID"] == secim)
        if not orj_mask.any():
            st.warning("Beklenmeyen hata: Seçilen kayıt ana tabloda bulunamadı.")
        else:
            orj_idx = df_musteri.index[orj_mask][0]

            with st.form("edit_existing_customer"):
                name = st.text_input("Müşteri Adı", value=str(df_musteri.at[orj_idx, "Müşteri Adı"]))
                phone = st.text_input("Telefon", value=str(df_musteri.at[orj_idx, "Telefon"]))
                email = st.text_input("E-posta", value=str(df_musteri.at[orj_idx, "E-posta"]))
                address = st.text_area("Adres", value=str(df_musteri.at[orj_idx, "Adres"]))

                # Ülke / Temsilci seçimleri
                try:
                    ulke_def = df_musteri.at[orj_idx, "Ülke"]
                    ulke_idx = ulke_listesi.index(ulke_def) if ulke_def in ulke_listesi else 0
                except Exception:
                    ulke_idx = 0
                ulke = st.selectbox("Ülke", ulke_listesi, index=ulke_idx)

                try:
                    tem_def = df_musteri.at[orj_idx, "Satış Temsilcisi"]
                    tem_idx = temsilci_listesi.index(tem_def) if tem_def in temsilci_listesi else 0
                except Exception:
                    tem_idx = 0
                temsilci = st.selectbox("Satış Temsilcisi", temsilci_listesi, index=tem_idx)

                kategori = st.selectbox(
                    "Kategori",
                    sorted(["Avrupa bayi", "bayi", "müşteri", "yeni müşteri"]),
                    index=sorted(["Avrupa bayi", "bayi", "müşteri", "yeni müşteri"]).index(
                        df_musteri.at[orj_idx, "Kategori"]
                    ) if df_musteri.at[orj_idx, "Kategori"] in ["Avrupa bayi", "bayi", "müşteri", "yeni müşteri"] else 0
                )

                aktif_pasif = st.selectbox(
                    "Durum", ["Aktif", "Pasif"],
                    index=(0 if str(df_musteri.at[orj_idx, "Durum"]) == "Aktif" else 1)
                )

                vade = st.text_input(
                    "Vade (Gün)", 
                    value=str(df_musteri.at[orj_idx, "Vade (Gün)"]) if "Vade (Gün)" in df_musteri.columns else ""
                )

                odeme_sekli = st.selectbox(
                    "Ödeme Şekli",
                    ["Peşin", "Mal Mukabili", "Vesaik Mukabili", "Akreditif", "Diğer"],
                    index=["Peşin", "Mal Mukabili", "Vesaik Mukabili", "Akreditif", "Diğer"].index(
                        df_musteri.at[orj_idx, "Ödeme Şekli"]
                    ) if df_musteri.at[orj_idx, "Ödeme Şekli"] in ["Peşin", "Mal Mukabili", "Vesaik Mukabili", "Akreditif", "Diğer"] else 0
                )

                # <<< Güncellendi: Para birimi sadece USD / EUR / TL >>>
                para_birimi = st.selectbox(
                    "Para Birimi",
                    ["USD", "EUR", "TL"],
                    index=["USD", "EUR", "TL"].index(df_musteri.at[orj_idx, "Para Birimi"])
                    if df_musteri.at[orj_idx, "Para Birimi"] in ["USD", "EUR", "TL"] else 0
                )

                dt_secimi = st.selectbox(
                    "DT Seçimi",
                    ["DT-1", "DT-2", "DT-3", "DT-4"],
                    index=["DT-1", "DT-2", "DT-3", "DT-4"].index(
                        df_musteri.at[orj_idx, "DT Seçimi"]
                    ) if df_musteri.at[orj_idx, "DT Seçimi"] in ["DT-1", "DT-2", "DT-3", "DT-4"] else 0
                )

                colu, cols = st.columns(2)
                guncelle = colu.form_submit_button("Güncelle")
                sil = cols.form_submit_button("Sil")

            if guncelle:
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
                df_musteri.at[orj_idx, "Para Birimi"] = para_birimi
                df_musteri.at[orj_idx, "DT Seçimi"] = dt_secimi
                update_google_sheets()
                st.success("Müşteri bilgisi güncellendi!")
                st.rerun()

            if sil:
                df_musteri = df_musteri.drop(orj_idx).reset_index(drop=True)
                update_google_sheets()
                st.success("Müşteri kaydı silindi!")
                st.rerun()


### ===========================
### === GÖRÜŞME / ARAMA / ZİYARET KAYITLARI MENÜSÜ (Cloud-Sağlam) ===
### ===========================

import uuid

# — Zorunlu kolonları garanti et —
_gerekli = ["ID", "Müşteri Adı", "Tarih", "Tip", "Açıklama"]
for c in _gerekli:
    if c not in df_kayit.columns:
        df_kayit[c] = ""

# — Eski satırlarda boş ID'leri doldur —
_mask_bos_id = df_kayit["ID"].astype(str).str.strip().isin(["", "nan", "None"])
if _mask_bos_id.any():
    df_kayit.loc[_mask_bos_id, "ID"] = [str(uuid.uuid4()) for _ in range(_mask_bos_id.sum())]
    update_google_sheets()

if menu == "Görüşme / Arama / Ziyaret Kayıtları":
    st.markdown("<h2 style='color:#219A41; font-weight:bold;'>Görüşme / Arama / Ziyaret Kayıtları</h2>", unsafe_allow_html=True)

    secim = st.radio("Lütfen işlem seçin:", ["Yeni Kayıt", "Eski Kayıt", "Tarih Aralığı ile Kayıtlar"], horizontal=False)

    # — Ortak müşteri listesi (boşlar hariç, alfabetik) —
    musteri_options = [""] + sorted([
        m for m in df_musteri.get("Müşteri Adı", pd.Series(dtype=str)).dropna().unique()
        if isinstance(m, str) and m.strip()
    ])

    # =================
    # YENİ KAYIT
    # =================
    if secim == "Yeni Kayıt":
        with st.form("add_kayit"):
            musteri_sec = st.selectbox("Müşteri Seç *", musteri_options, index=0)
            tarih = st.date_input("Tarih", value=datetime.date.today())
            tip = st.selectbox("Tip *", ["Arama", "Görüşme", "Ziyaret"])
            aciklama = st.text_area("Açıklama")
            submitted = st.form_submit_button("Kaydet")

            if submitted:
                if not musteri_sec:
                    st.error("Lütfen bir müşteri seçiniz.")
                else:
                    new_row = {
                        "ID": str(uuid.uuid4()),
                        "Müşteri Adı": musteri_sec,
                        "Tarih": tarih,
                        "Tip": tip,
                        "Açıklama": aciklama.strip(),
                    }
                    df_kayit = pd.concat([df_kayit, pd.DataFrame([new_row])], ignore_index=True)
                    update_google_sheets()
                    st.success("Kayıt eklendi!")
                    st.rerun()

    # =================
    # ESKİ KAYIT (Listele / Ara / Düzenle / Sil)
    # =================
    elif secim == "Eski Kayıt":
        colf1, colf2, colf3 = st.columns([2, 1, 1])
        musteri_liste = ["(Hepsi)"] + sorted([x for x in df_kayit["Müşteri Adı"].dropna().unique().tolist() if str(x).strip()])
        musteri_f = colf1.selectbox("Müşteri Filtresi", musteri_liste, index=0)
        tip_f = colf2.multiselect("Tip Filtresi", ["Arama", "Görüşme", "Ziyaret"], default=[])
        aranacak = colf3.text_input("🔎 Ara (açıklama)", value="")

        view = df_kayit.copy()

        # Filtreler
        if musteri_f and musteri_f != "(Hepsi)":
            view = view[view["Müşteri Adı"] == musteri_f]
        if tip_f:
            view = view[view["Tip"].isin(tip_f)]
        if aranacak.strip():
            s = aranacak.strip().lower()
            view = view[view["Açıklama"].astype(str).str.lower().str.contains(s, na=False)]

        # Tablo görünümü
        if not view.empty:
            goster = view.copy()
            goster["Tarih"] = pd.to_datetime(goster["Tarih"], errors="coerce").dt.strftime("%d/%m/%Y")
            st.dataframe(
                goster[["Müşteri Adı", "Tarih", "Tip", "Açıklama"]].sort_values("Tarih", ascending=False),
                use_container_width=True
            )

            st.download_button(
                "⬇️ CSV indir",
                data=goster.to_csv(index=False).encode("utf-8"),
                file_name="gorusme_kayitlari.csv",
                mime="text/csv"
            )
        else:
            st.info("Seçilen filtrelere uygun kayıt bulunamadı.")

        # Düzenleme / Silme
        st.markdown("#### Kayıt Düzenle / Sil")
        if view.empty:
            st.caption("Önce filtrelerle bir kayıt listeleyin.")
        else:
            view_sorted = view.sort_values(
                pd.to_datetime(view["Tarih"], errors="coerce")
            , ascending=False).reset_index(drop=True)

            sec_id = st.selectbox(
                "Kayıt Seçin",
                options=view_sorted["ID"].tolist(),
                format_func=lambda _id: f"{view_sorted.loc[view_sorted['ID']==_id, 'Müşteri Adı'].values[0]} "
                                        f"| {view_sorted.loc[view_sorted['ID']==_id, 'Tip'].values[0]}"
            )

            # Orijinal index
            orj_mask = (df_kayit["ID"] == sec_id)
            if not orj_mask.any():
                st.warning("Beklenmeyen hata: Kayıt ana tabloda bulunamadı.")
            else:
                orj_idx = df_kayit.index[orj_mask][0]

                with st.form("edit_kayit"):
                    # Müşteri varsayılan index
                    try:
                        ms_def = df_kayit.at[orj_idx, "Müşteri Adı"]
                        ms_idx = musteri_options.index(ms_def) if ms_def in musteri_options else 0
                    except Exception:
                        ms_idx = 0

                    musteri_g = st.selectbox("Müşteri *", musteri_options, index=ms_idx)

                    # Tarih varsayılanı
                    try:
                        tarih_g = pd.to_datetime(df_kayit.at[orj_idx, "Tarih"], errors="coerce").date()
                        if pd.isna(tarih_g):
                            tarih_g = datetime.date.today()
                    except Exception:
                        tarih_g = datetime.date.today()
                    tarih_g = st.date_input("Tarih", value=tarih_g)

                    tip_g = st.selectbox(
                        "Tip *",
                        ["Arama", "Görüşme", "Ziyaret"],
                        index=(["Arama", "Görüşme", "Ziyaret"].index(df_kayit.at[orj_idx, "Tip"])
                               if df_kayit.at[orj_idx, "Tip"] in ["Arama", "Görüşme", "Ziyaret"] else 0)
                    )
                    aciklama_g = st.text_area("Açıklama", value=str(df_kayit.at[orj_idx, "Açıklama"]))

                    colu, cols = st.columns(2)
                    guncelle = colu.form_submit_button("Güncelle")
                    sil = cols.form_submit_button("Sil")

                if guncelle:
                    df_kayit.at[orj_idx, "Müşteri Adı"] = musteri_g
                    df_kayit.at[orj_idx, "Tarih"] = tarih_g
                    df_kayit.at[orj_idx, "Tip"] = tip_g
                    df_kayit.at[orj_idx, "Açıklama"] = aciklama_g.strip()
                    update_google_sheets()
                    st.success("Kayıt güncellendi!")
                    st.rerun()

                if sil:
                    df_kayit = df_kayit.drop(orj_idx).reset_index(drop=True)
                    update_google_sheets()
                    st.success("Kayıt silindi!")
                    st.rerun()

    # =================
    # TARİH ARALIĞI İLE KAYITLAR
    # =================
    elif secim == "Tarih Aralığı ile Kayıtlar":
        col1, col2 = st.columns(2)
        with col1:
            baslangic = st.date_input(
                "Başlangıç Tarihi",
                value=datetime.date.today() - datetime.timedelta(days=7)
            )
        with col2:
            bitis = st.date_input(
                "Bitiş Tarihi",
                value=datetime.date.today()
            )

        # Sağlam tarih filtrelemesi
        tser = pd.to_datetime(df_kayit["Tarih"], errors="coerce")
        start_ts = pd.to_datetime(baslangic)
        end_ts = pd.to_datetime(bitis) + pd.Timedelta(days=1) - pd.Timedelta(milliseconds=1)
        tarih_arasi = df_kayit[tser.between(start_ts, end_ts, inclusive="both")].copy()

        if not tarih_arasi.empty:
            goster = tarih_arasi.copy()
            goster["Tarih"] = pd.to_datetime(goster["Tarih"], errors="coerce").dt.strftime("%d/%m/%Y")
            st.dataframe(goster.sort_values("Tarih", ascending=False), use_container_width=True)
            st.download_button(
                "⬇️ CSV indir",
                data=goster.to_csv(index=False).encode("utf-8"),
                file_name="gorusme_kayitlari_tarih_araligi.csv",
                mime="text/csv"
            )
        else:
            st.info("Bu tarihler arasında kayıt yok.")


### ===========================
### --- FİYAT TEKLİFLERİ MENÜSÜ (Cloud-Sağlam) ---
### ===========================

elif menu == "Fiyat Teklifleri":
    import uuid, time
    from googleapiclient.http import MediaFileUpload

    st.markdown("<h2 style='color:#219A41; font-weight:bold;'>Fiyat Teklifleri</h2>", unsafe_allow_html=True)

    # --- Zorunlu kolonlar + ID backfill ---
    gerekli = ["ID", "Müşteri Adı", "Tarih", "Teklif No", "Tutar", "Ürün/Hizmet", "Açıklama", "Durum", "PDF"]
    for c in gerekli:
        if c not in df_teklif.columns:
            df_teklif[c] = ""
    mask_bos_id = df_teklif["ID"].astype(str).str.strip().isin(["", "nan", "None"])
    if mask_bos_id.any():
        df_teklif.loc[mask_bos_id, "ID"] = [str(uuid.uuid4()) for _ in range(mask_bos_id.sum())]
        update_google_sheets()

    # --- Akıllı sayı dönüştürücü ---
    def smart_to_num(x):
        if pd.isna(x): return 0.0
        s = str(x).strip()
        for sym in ["USD", "$", "€", "EUR", "₺", "TL", "tl", "Tl"]:
            s = s.replace(sym, "")
        s = s.replace("\u00A0", "").replace(" ", "")
        try:
            return float(s)                     # US format
        except Exception:
            pass
        if "," in s:
            try:
                return float(s.replace(".", "").replace(",", "."))  # EU format
            except Exception:
                pass
        return 0.0

    # --- Otomatik teklif no ---
    def otomatik_teklif_no():
        if df_teklif.empty or "Teklif No" not in df_teklif.columns:
            return "TKF-0001"
        sayilar = pd.to_numeric(
            df_teklif["Teklif No"].astype(str).str.extract(r'(\d+)$')[0],
            errors='coerce'
        ).dropna().astype(int)
        yeni_no = (sayilar.max() + 1) if not sayilar.empty else 1
        return f"TKF-{yeni_no:04d}"

    # --- Güvenli geçici dosya sil ---
    def guvenli_sil(dosya, tekrar=5, bekle=1):
        for _ in range(tekrar):
            try:
                os.remove(dosya)
                return True
            except PermissionError:
                time.sleep(bekle)
            except FileNotFoundError:
                return True
        return False

    # ---------- ÜST ÖZET: Açık teklifler ----------
    tkg = df_teklif.copy()
    tkg["Tarih"] = pd.to_datetime(tkg["Tarih"], errors="coerce")
    acik_teklifler = tkg[tkg["Durum"] == "Açık"].sort_values(["Müşteri Adı", "Teklif No"])
    toplam_teklif = float(acik_teklifler["Tutar"].apply(smart_to_num).sum())
    acik_teklif_sayi = len(acik_teklifler)

    st.subheader("Açık Pozisyondaki Teklifler")
    st.markdown(
        f"<div style='font-size:1.05em; color:#11998e; font-weight:bold;'>Toplam: {toplam_teklif:,.2f} USD | "
        f"Toplam Açık Teklif: {acik_teklif_sayi} adet</div>",
        unsafe_allow_html=True
    )
    if not acik_teklifler.empty:
        goster = acik_teklifler.copy()
        goster["Tarih"] = goster["Tarih"].dt.strftime("%d/%m/%Y")
        st.dataframe(
            goster[["Müşteri Adı", "Tarih", "Teklif No", "Tutar", "Ürün/Hizmet", "Açıklama"]],
            use_container_width=True
        )
    else:
        st.info("Açık teklif bulunmuyor.")

    st.markdown("##### Lütfen bir işlem seçin")
    col1, col2 = st.columns(2)
    with col1:
        yeni_teklif_buton = st.button("Yeni Teklif")
    with col2:
        eski_teklif_buton = st.button("Eski Teklifler / Düzenle")

    if "teklif_view" not in st.session_state:
        st.session_state['teklif_view'] = None
    if yeni_teklif_buton:
        st.session_state['teklif_view'] = "yeni"
    if eski_teklif_buton:
        st.session_state['teklif_view'] = "eski"

    # ============== YENİ TEKLİF ==============
    if st.session_state['teklif_view'] == "yeni":
        musteri_list = [""] + sorted(df_musteri["Müşteri Adı"].dropna().unique().tolist())
        st.subheader("Yeni Teklif Ekle")
        with st.form("add_teklif"):
            musteri_sec = st.selectbox("Müşteri Seç", musteri_list, key="yeni_teklif_musteri")
            tarih = st.date_input("Tarih", value=datetime.date.today())
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
                    # PDF'yi Drive'a yükle (varsa) — drive_service ile
                    if pdf_file:
                        temiz_musteri = "".join(x if x.isalnum() else "_" for x in str(musteri_sec))
                        temiz_tarih = str(tarih).replace("-", "")
                        pdf_filename = f"{temiz_musteri}__{temiz_tarih}__{teklif_no}.pdf"
                        temp_path = os.path.join(".", pdf_filename)
                        with open(temp_path, "wb") as f:
                            f.write(pdf_file.read())

                        try:
                            media = MediaFileUpload(temp_path, mimetype="application/pdf", resumable=False)
                            meta = {"name": pdf_filename, "parents": [FIYAT_TEKLIFI_ID]}
                            created = drive_service.files().create(
                                body=meta,
                                media_body=media,
                                fields="id",
                                supportsAllDrives=True
                            ).execute()
                            file_id = created["id"]
                            # Herkese görüntüleme izni (gömülü/listeler için faydalı)
                            try:
                                drive_service.permissions().create(
                                    fileId=file_id,
                                    body={"role": "reader", "type": "anyone"},
                                    fields="id"
                                ).execute()
                            except Exception:
                                pass
                            pdf_link = f"https://drive.google.com/file/d/{file_id}/view?usp=sharing"
                        finally:
                            guvenli_sil(temp_path)

                    new_row = {
                        "ID": str(uuid.uuid4()),
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
                    update_google_sheets()
                    st.success("Teklif eklendi!")
                    st.session_state['teklif_view'] = None
                    st.rerun()

    # ============== ESKİ TEKLİFLER / DÜZENLE / SİL ==============
    if st.session_state['teklif_view'] == "eski":
        st.subheader("Eski Teklifler")

        # ---- Filtreler ----
        f1, f2, f3, f4 = st.columns([1.5, 1, 1.3, 1.2])
        musteri_f = f1.selectbox("Müşteri", ["(Hepsi)"] + sorted(df_teklif["Müşteri Adı"].dropna().unique().tolist()))
        durum_f = f2.multiselect("Durum", ["Açık", "Beklemede", "Sonuçlandı"], default=[])
        # Tarih aralığı
        tmp = pd.to_datetime(df_teklif["Tarih"], errors="coerce")
        min_dt = (tmp.min().date() if tmp.notna().any() else datetime.date.today())
        max_dt = (tmp.max().date() if tmp.notna().any() else datetime.date.today())
        d1 = f3.date_input("Başlangıç", value=min_dt)
        d2 = f4.date_input("Bitiş", value=max_dt)
        aranacak = st.text_input("🔎 Ara (ürün/açıklama/teklif no)")

        view = df_teklif.copy()
        view["Tarih"] = pd.to_datetime(view["Tarih"], errors="coerce")

        if musteri_f and musteri_f != "(Hepsi)":
            view = view[view["Müşteri Adı"] == musteri_f]
        if durum_f:
            view = view[view["Durum"].isin(durum_f)]

        start_ts = pd.to_datetime(d1)
        end_ts = pd.to_datetime(d2) + pd.Timedelta(days=1) - pd.Timedelta(milliseconds=1)
        view = view[view["Tarih"].between(start_ts, end_ts, inclusive="both")]

        if aranacak.strip():
            s = aranacak.lower().strip()
            view = view[
                view["Ürün/Hizmet"].astype(str).str.lower().str.contains(s, na=False) |
                view["Açıklama"].astype(str).str.lower().str.contains(s, na=False) |
                view["Teklif No"].astype(str).str.lower().str.contains(s, na=False)
            ]

        # Toplam ve tablo
        toplam_view = float(view["Tutar"].apply(smart_to_num).sum())
        st.markdown(
            f"<div style='margin:.25rem 0 .5rem 0; font-weight:600;'>Filtreli Toplam: {toplam_view:,.2f} USD</div>",
            unsafe_allow_html=True
        )

        if not view.empty:
            tablo = view.sort_values("Tarih", ascending=False).copy()
            tablo["Tarih"] = tablo["Tarih"].dt.strftime("%d/%m/%Y")
            st.dataframe(
                tablo[["Müşteri Adı", "Tarih", "Teklif No", "Tutar", "Durum", "Ürün/Hizmet", "Açıklama"]],
                use_container_width=True
            )
            st.download_button(
                "⬇️ CSV indir",
                data=tablo.to_csv(index=False).encode("utf-8"),
                file_name="teklifler.csv",
                mime="text/csv"
            )
        else:
            st.info("Filtrelere göre teklif bulunamadı.")

        # ---- Düzenle / Sil ----
        st.markdown("#### Teklif Düzenle / Sil")
        if view.empty:
            st.caption("Önce filtrelerle bir kayıt listeleyin.")
        else:
            v_sorted = view.sort_values("Tarih", ascending=False).reset_index(drop=True)
            sec_id = st.selectbox(
                "Teklif Seçiniz",
                options=v_sorted["ID"].tolist(),
                format_func=lambda _id: f"{v_sorted.loc[v_sorted['ID']==_id, 'Müşteri Adı'].values[0]} | "
                                        f"{v_sorted.loc[v_sorted['ID']==_id, 'Teklif No'].values[0]}"
            )

            orj_mask = (df_teklif["ID"] == sec_id)
            if not orj_mask.any():
                st.warning("Beklenmeyen hata: Teklif ana tabloda bulunamadı.")
            else:
                orj_idx = df_teklif.index[orj_mask][0]

                mevcut_pdf = str(df_teklif.at[orj_idx, "PDF"]) if pd.notna(df_teklif.at[orj_idx, "PDF"]) else ""
                if mevcut_pdf:
                    st.markdown(f"**Mevcut PDF:** [Görüntüle]({mevcut_pdf})", unsafe_allow_html=True)

                with st.form("edit_teklif"):
                    try:
                        tarih_g = pd.to_datetime(df_teklif.at[orj_idx, "Tarih"]).date()
                    except Exception:
                        tarih_g = datetime.date.today()
                    tarih_g = st.date_input("Tarih", value=tarih_g)

                    teklif_no_g = st.text_input("Teklif No", value=str(df_teklif.at[orj_idx, "Teklif No"]))

                    musteri_list_duz = [""] + sorted(df_musteri["Müşteri Adı"].dropna().unique().tolist())
                    try:
                        ms_idx = musteri_list_duz.index(df_teklif.at[orj_idx, "Müşteri Adı"])
                    except Exception:
                        ms_idx = 0
                    musteri_g = st.selectbox("Müşteri", musteri_list_duz, index=ms_idx)

                    tutar_g = st.text_input("Tutar ($)", value=str(df_teklif.at[orj_idx, "Tutar"]))
                    urun_g = st.text_input("Ürün/Hizmet", value=str(df_teklif.at[orj_idx, "Ürün/Hizmet"]))
                    aciklama_g = st.text_area("Açıklama", value=str(df_teklif.at[orj_idx, "Açıklama"]))
                    durum_g = st.selectbox(
                        "Durum", ["Açık", "Beklemede", "Sonuçlandı"],
                        index=(["Açık", "Beklemede", "Sonuçlandı"].index(df_teklif.at[orj_idx, "Durum"])
                               if df_teklif.at[orj_idx, "Durum"] in ["Açık","Beklemede","Sonuçlandı"] else 0)
                    )
                    pdf_yeni = st.file_uploader("PDF Güncelle (opsiyonel)", type="pdf", key=f"pdf_guncel_{sec_id}")

                    colu, cols = st.columns(2)
                    guncelle = colu.form_submit_button("Güncelle")
                    sil = cols.form_submit_button("Sil")

                if guncelle:
                    pdf_link_final = mevcut_pdf
                    if pdf_yeni:
                        temiz_m = "".join(x if x.isalnum() else "_" for x in str(musteri_g or "musteri"))
                        temiz_t = str(tarih_g).replace("-", "")
                        fname = f"{temiz_m}__{temiz_t}__{teklif_no_g}.pdf"
                        tmp_path = os.path.join(".", fname)
                        with open(tmp_path, "wb") as f:
                            f.write(pdf_yeni.read())

                        try:
                            media = MediaFileUpload(tmp_path, mimetype="application/pdf", resumable=False)
                            meta = {"name": fname, "parents": [FIYAT_TEKLIFI_ID]}
                            created = drive_service.files().create(
                                body=meta,
                                media_body=media,
                                fields="id",
                                supportsAllDrives=True
                            ).execute()
                            file_id = created["id"]
                            try:
                                drive_service.permissions().create(
                                    fileId=file_id,
                                    body={"role": "reader", "type": "anyone"},
                                    fields="id"
                                ).execute()
                            except Exception:
                                pass
                            pdf_link_final = f"https://drive.google.com/file/d/{file_id}/view?usp=sharing"
                        finally:
                            guvenli_sil(tmp_path)

                    df_teklif.at[orj_idx, "Tarih"] = tarih_g
                    df_teklif.at[orj_idx, "Teklif No"] = teklif_no_g
                    df_teklif.at[orj_idx, "Müşteri Adı"] = musteri_g
                    df_teklif.at[orj_idx, "Tutar"] = tutar_g
                    df_teklif.at[orj_idx, "Ürün/Hizmet"] = urun_g
                    df_teklif.at[orj_idx, "Açıklama"] = aciklama_g
                    df_teklif.at[orj_idx, "Durum"] = durum_g
                    df_teklif.at[orj_idx, "PDF"] = pdf_link_final
                    update_google_sheets()
                    st.success("Teklif güncellendi!")
                    st.rerun()

                if sil:
                    df_teklif = df_teklif.drop(orj_idx).reset_index(drop=True)
                    update_google_sheets()
                    st.success("Teklif silindi!")
                    st.rerun()


### ===========================
### --- PROFORMA TAKİBİ MENÜSÜ (Cloud-Sağlam) ---
### ===========================

elif menu == "Proforma Takibi":
    import uuid, tempfile, time

    st.markdown("<h2 style='color:#219A41; font-weight:bold;'>Proforma Takibi</h2>", unsafe_allow_html=True)

    # ---- Drive klasör ID'leri ----
    # Üstte tanımlı sabitlerden çekiyoruz; yoksa EVRAK_KLASOR_ID'ye düşer.
    PROFORMA_PDF_FOLDER_ID  = globals().get("PROFORMA_PDF_ID",  globals().get("EVRAK_KLASOR_ID", ""))
    SIPARIS_FORMU_FOLDER_ID = globals().get("SIPARIS_FORMU_ID", globals().get("EVRAK_KLASOR_ID", ""))

    # ---- Kolon güvenliği + ID backfill ----
    gerekli = [
        "ID","Müşteri Adı","Tarih","Proforma No","Tutar","Açıklama","Durum","PDF",
        "Vade (gün)","Sevk Durumu","Ülke","Satış Temsilcisi","Ödeme Şekli",
        "Termin Tarihi","Sevk Tarihi","Ulaşma Tarihi","Sipariş Formu"
    ]
    for c in gerekli:
        if c not in df_proforma.columns:
            df_proforma[c] = ""
    mask_bos_id = df_proforma["ID"].astype(str).str.strip().isin(["", "nan", "None"])
    if mask_bos_id.any():
        df_proforma.loc[mask_bos_id, "ID"] = [str(uuid.uuid4()) for _ in range(mask_bos_id.sum())]
        update_google_sheets()

    # --- Akıllı sayı dönüştürücü (toplamlar için) ---
    def smart_to_num(x):
        if pd.isna(x): return 0.0
        s = str(x).strip()
        for sym in ["USD","$","€","EUR","₺","TL","tl","Tl"]:
            s = s.replace(sym, "")
        s = s.replace("\u00A0","").replace(" ","")
        try: return float(s)
        except: pass
        if "," in s:
            try: return float(s.replace(".","").replace(",","."))
            except: pass
        return 0.0

    # --- Güvenli tarih string'i ---
    def _safe_date_str(v, fmt="%d/%m/%Y"):
        try:
            dt = pd.to_datetime(v, errors="coerce")
            if pd.isna(dt): return ""
            return dt.strftime(fmt)
        except Exception:
            return ""

    # ---------- ÜST ÖZET: Bekleyen Proformalar ----------
    pview = df_proforma.copy()
    pview["Tarih"] = pd.to_datetime(pview["Tarih"], errors="coerce")
    beklemede_kayitlar = pview[pview["Durum"] == "Beklemede"].sort_values(
        ["Tarih","Müşteri Adı"], ascending=[False, True]
    )
    toplam_bekleyen = float(beklemede_kayitlar["Tutar"].apply(smart_to_num).sum())

    st.subheader("Bekleyen Proformalar")
    st.markdown(
        f"<div style='font-weight:600;'>Toplam Bekleyen: {toplam_bekleyen:,.2f} USD</div>",
        unsafe_allow_html=True
    )
    if not beklemede_kayitlar.empty:
        g = beklemede_kayitlar.copy()
        g["Tarih"] = g["Tarih"].dt.strftime("%d/%m/%Y")
        st.dataframe(
            g[["Müşteri Adı","Proforma No","Tarih","Tutar","Durum","Vade (gün)","Sevk Durumu"]],
            use_container_width=True
        )
    else:
        st.info("Beklemede proforma bulunmuyor.")

    # ---------- Müşteri seçimi ----------
    musteri_list = sorted([
        x for x in df_musteri["Müşteri Adı"].dropna().unique()
        if str(x).strip()!=""
    ]) if not df_musteri.empty else []
    musteri_sec = st.selectbox("Müşteri Seç", [""] + musteri_list)

    if musteri_sec:
        st.write("Proforma işlemi seçin:")
        islem = st.radio("", ["Yeni Kayıt","Eski Kayıt / Düzenle"], horizontal=True)

        # ============== YENİ KAYIT ==============
        if islem == "Yeni Kayıt":
            musteri_info = df_musteri[df_musteri["Müşteri Adı"] == musteri_sec]
            default_ulke      = musteri_info["Ülke"].values[0] if not musteri_info.empty else ""
            default_temsilci  = musteri_info["Satış Temsilcisi"].values[0] if not musteri_info.empty else ""
            default_odeme     = musteri_info["Ödeme Şekli"].values[0] if not musteri_info.empty else ""

            with st.form("add_proforma"):
                tarih       = st.date_input("Tarih", value=datetime.date.today())
                proforma_no = st.text_input("Proforma No")
                tutar       = st.text_input("Tutar ($)")
                vade_gun    = st.text_input("Vade (gün)")
                ulke        = st.text_input("Ülke", value=default_ulke, disabled=True)
                temsilci    = st.text_input("Satış Temsilcisi", value=default_temsilci, disabled=True)
                odeme       = st.text_input("Ödeme Şekli", value=default_odeme, disabled=True)
                aciklama    = st.text_area("Açıklama")
                durum       = st.selectbox("Durum", ["Beklemede","İptal","Faturası Kesildi","Siparişe Dönüştü"], index=0)
                pdf_file    = st.file_uploader("Proforma PDF", type="pdf")
                submitted   = st.form_submit_button("Kaydet")

                if submitted:
                    if not proforma_no.strip() or not vade_gun.strip():
                        st.error("Proforma No ve Vade (gün) boş olamaz!")
                    else:
                        # Aynı müşteri+proforma no duplike kontrolü
                        if ((df_proforma["Müşteri Adı"]==musteri_sec) & (df_proforma["Proforma No"].astype(str)==proforma_no.strip())).any():
                            st.warning("Bu Proforma No bu müşteri için zaten kayıtlı.")
                        else:
                            pdf_link = ""
                            if pdf_file and PROFORMA_PDF_FOLDER_ID:
                                fname = f"{musteri_sec}_{tarih}_{proforma_no}.pdf"
                                tmp_path = os.path.join(".", fname)
                                with open(tmp_path, "wb") as f:
                                    f.write(pdf_file.read())
                                # Google Drive’a yükle
                                pdf_link = upload_file_to_drive(PROFORMA_PDF_FOLDER_ID, tmp_path, fname)
                                try: os.remove(tmp_path)
                                except: pass

                            new_row = {
                                "ID": str(uuid.uuid4()),
                                "Müşteri Adı": musteri_sec,
                                "Tarih": tarih,
                                "Proforma No": proforma_no.strip(),
                                "Tutar": tutar,
                                "Vade (gün)": vade_gun,
                                "Ülke": default_ulke,
                                "Satış Temsilcisi": default_temsilci,
                                "Ödeme Şekli": default_odeme,
                                "Açıklama": aciklama,
                                "Durum": "Beklemede" if durum!="Siparişe Dönüştü" else "Siparişe Dönüştü",
                                "PDF": pdf_link,
                                "Sipariş Formu": "",
                                "Sevk Durumu": "",
                                "Termin Tarihi": "",
                                "Sevk Tarihi": "",
                                "Ulaşma Tarihi": ""
                            }
                            df_proforma = pd.concat([df_proforma, pd.DataFrame([new_row])], ignore_index=True)
                            update_google_sheets()
                            st.success("Proforma eklendi!")
                            st.rerun()

        # ============== ESKİ KAYIT / DÜZENLE / SİL / SİPARİŞE DÖNÜŞTÜR ==============
        elif islem == "Eski Kayıt / Düzenle":
            kayitlar = df_proforma[df_proforma["Müşteri Adı"] == musteri_sec].copy()
            if kayitlar.empty:
                st.info("Bu müşteriye ait proforma kaydı yok.")
            else:
                kayitlar["Tarih"] = pd.to_datetime(kayitlar["Tarih"], errors="coerce")
                g = kayitlar.sort_values("Tarih", ascending=False).copy()
                g["Tarih"] = g["Tarih"].apply(lambda x: _safe_date_str(x))
                st.dataframe(
                    g[["Müşteri Adı","Proforma No","Tarih","Tutar","Durum","Vade (gün)","Sevk Durumu"]],
                    use_container_width=True
                )

                # ID tabanlı güvenli seçim
                def _fmt(_id: str) -> str:
                    row = kayitlar.loc[kayitlar["ID"] == _id]
                    if row.empty: return _id
                    pno  = str(row["Proforma No"].values[0])
                    trh  = _safe_date_str(row["Tarih"].values[0])
                    return f"{pno} | {trh}"

                sec_id = st.selectbox(
                    "Proforma Seç",
                    options=kayitlar["ID"].tolist(),
                    format_func=_fmt
                )

                orj_mask = (df_proforma["ID"] == sec_id)
                if not orj_mask.any():
                    st.warning("Beklenmeyen hata: Kayıt bulunamadı.")
                else:
                    idx = df_proforma.index[orj_mask][0]
                    kayit = df_proforma.loc[idx]

                    mevcut_pdf = str(kayit.get("PDF","")).strip()
                    if mevcut_pdf:
                        st.markdown(f"**Proforma PDF:** [Görüntüle]({mevcut_pdf})", unsafe_allow_html=True)

                    with st.form("edit_proforma"):
                        tarih_       = st.date_input(
                            "Tarih",
                            value=(pd.to_datetime(kayit["Tarih"], errors="coerce").date()
                                   if pd.notna(pd.to_datetime(kayit["Tarih"], errors="coerce"))
                                   else datetime.date.today())
                        )
                        proforma_no_ = st.text_input("Proforma No", value=str(kayit["Proforma No"]))
                        tutar_       = st.text_input("Tutar ($)", value=str(kayit["Tutar"]))
                        vade_gun_    = st.text_input("Vade (gün)", value=str(kayit["Vade (gün)"]))
                        aciklama_    = st.text_area("Açıklama", value=str(kayit["Açıklama"]))
                        durum_       = st.selectbox(
                            "Durum",
                            ["Beklemede","Siparişe Dönüştü","İptal","Faturası Kesildi"],
                            index=(["Beklemede","Siparişe Dönüştü","İptal","Faturası Kesildi"].index(kayit["Durum"])
                                   if kayit["Durum"] in ["Beklemede","Siparişe Dönüştü","İptal","Faturası Kesildi"] else 0)
                        )
                        termin_      = st.date_input(
                            "Termin Tarihi",
                            value=(
                                pd.to_datetime(kayit.get("Termin Tarihi",""), errors="coerce").date()
                                if pd.notna(pd.to_datetime(kayit.get("Termin Tarihi",""), errors="coerce"))
                                else datetime.date.today()
                            ),
                            key=f"termin_inp_{sec_id}"
                        )
                        pdf_yeni     = st.file_uploader("Proforma PDF (güncelle - opsiyonel)", type="pdf", key=f"prpdf_{sec_id}")
                        colu, colm, cols = st.columns(3)
                        guncelle = colu.form_submit_button("Güncelle")
                        donustur = colm.form_submit_button("Siparişe Dönüştür (+ Sipariş Formu)")
                        sil      = cols.form_submit_button("Sil")

                    # --- GÜNCELLE ---
                    if guncelle:
                        pdf_final = mevcut_pdf
                        if pdf_yeni and PROFORMA_PDF_FOLDER_ID:
                            fname = f"{musteri_sec}_{tarih_}_{proforma_no_}.pdf"
                            tmp_path = os.path.join(".", fname)
                            with open(tmp_path, "wb") as f:
                                f.write(pdf_yeni.read())
                            pdf_final = upload_file_to_drive(PROFORMA_PDF_FOLDER_ID, tmp_path, fname)
                            try: os.remove(tmp_path)
                            except: pass

                        df_proforma.at[idx, "Tarih"]       = tarih_
                        df_proforma.at[idx, "Proforma No"] = proforma_no_
                        df_proforma.at[idx, "Tutar"]       = tutar_
                        df_proforma.at[idx, "Vade (gün)"]  = vade_gun_
                        df_proforma.at[idx, "Açıklama"]    = aciklama_
                        # "Siparişe Dönüştür" butonu ayrı; burada diğer durumları yazalım
                        if durum_ != "Siparişe Dönüştü":
                            df_proforma.at[idx, "Durum"] = durum_
                        df_proforma.at[idx, "Termin Tarihi"] = termin_
                        df_proforma.at[idx, "PDF"] = pdf_final
                        update_google_sheets()
                        st.success("Proforma güncellendi!")
                        st.rerun()

                    # --- SİPARİŞE DÖNÜŞTÜR (Sipariş Formu zorunlu) ---
                    if donustur:
                        with st.form(f"siparis_formu_upload_{sec_id}"):
                            st.info("Lütfen sipariş formunu (PDF) yükleyin ve kaydedin.")
                            siparis_formu_file = st.file_uploader("Sipariş Formu PDF", type="pdf", key=f"sf_{sec_id}")
                            kaydet_sf = st.form_submit_button("Sipariş Formunu Kaydet ve Dönüştür")

                        if kaydet_sf:
                            if siparis_formu_file is None:
                                st.error("Sipariş formu yüklenmeli.")
                            else:
                                sf_name = f"{musteri_sec}_{proforma_no_}_SiparisFormu_{datetime.datetime.now().strftime('%Y%m%d%H%M%S')}.pdf"
                                tmp_path = os.path.join(".", sf_name)
                                with open(tmp_path, "wb") as f:
                                    f.write(siparis_formu_file.read())
                                sf_url = upload_file_to_drive(SIPARIS_FORMU_FOLDER_ID, tmp_path, sf_name)
                                try: os.remove(tmp_path)
                                except: pass

                                df_proforma.at[idx, "Sipariş Formu"] = sf_url
                                df_proforma.at[idx, "Durum"]         = "Siparişe Dönüştü"
                                df_proforma.at[idx, "Sevk Durumu"]   = ""   # Sevk akışı diğer menülerde
                                update_google_sheets()
                                st.success("Sipariş formu kaydedildi ve durum 'Siparişe Dönüştü' olarak güncellendi!")
                                st.rerun()

                    # --- SİL ---
                    if sil:
                        df_proforma = df_proforma.drop(idx).reset_index(drop=True)
                        update_google_sheets()
                        st.success("Kayıt silindi!")
                        st.rerun()

### ===========================
### --- GÜNCEL SİPARİŞ DURUMU (ID tabanlı) ---
### ===========================

elif menu == "Güncel Sipariş Durumu":
    import uuid

    st.header("Güncel Sipariş Durumu")

    # ---- Kolon güvenliği + ID backfill ----
    gerekli = [
        "ID","Sevk Durumu","Termin Tarihi","Sipariş Formu","Ülke","Satış Temsilcisi",
        "Ödeme Şekli","PDF","Durum","Tarih","Tutar","Müşteri Adı","Proforma No","Açıklama"
    ]
    for c in gerekli:
        if c not in df_proforma.columns:
            df_proforma[c] = ""

    bos_id = df_proforma["ID"].astype(str).str.strip().isin(["","nan","None"])
    if bos_id.any():
        df_proforma.loc[bos_id, "ID"] = [str(uuid.uuid4()) for _ in range(bos_id.sum())]
        update_google_sheets()

    # ---- Filtre: Siparişe dönmüş ama sevk edilmemiş/ulaşmamış kayıtlar
    siparisler = df_proforma[
        (df_proforma["Durum"] == "Siparişe Dönüştü") &
        (~df_proforma["Sevk Durumu"].isin(["Sevkedildi","Ulaşıldı"]))
    ].copy()

    if siparisler.empty:
        st.info("Henüz sevk edilmeyi bekleyen sipariş yok.")
        st.stop()

    # ---- Sıralama: Termin Tarihi, sonra Proforma Tarihi
    siparisler["Termin Tarihi Order"] = pd.to_datetime(siparisler["Termin Tarihi"], errors="coerce")
    siparisler["Tarih"] = pd.to_datetime(siparisler["Tarih"], errors="coerce")
    siparisler = siparisler.sort_values(["Termin Tarihi Order","Tarih"], ascending=[True, True])

    # ---- Görünüm için format (NaT güvenli)
    g = siparisler.copy()
    g["Tarih"] = pd.to_datetime(g["Tarih"], errors="coerce").dt.strftime("%d/%m/%Y")
    g["Termin Tarihi"] = pd.to_datetime(g["Termin Tarihi"], errors="coerce").dt.strftime("%d/%m/%Y")

    # --- PYARROW duplicate column name guard ---
    def _dedupe_columns(df: pd.DataFrame) -> pd.DataFrame:
        seen = {}
        new_cols = []
        for c in df.columns:
            if c not in seen:
                seen[c] = 0
                new_cols.append(c)
            else:
                seen[c] += 1
                new_cols.append(f"{c}__{seen[c]}")  # Açıklama__1 gibi
        out = df.copy()
        out.columns = new_cols
        return out

    def _first_present(df: pd.DataFrame, name: str):
        cols = [c for c in df.columns if c == name]
        return cols[0] if cols else None

    wanted = ["Tarih","Müşteri Adı","Termin Tarihi","Ülke",
              "Satış Temsilcisi","Ödeme Şekli","Proforma No","Tutar","Açıklama"]
    safe_cols = [c for c in (_first_present(g, n) for n in wanted) if c]

    st.markdown("<h4 style='color:#219A41; font-weight:bold;'>Tüm Siparişe Dönüşenler</h4>", unsafe_allow_html=True)
    st.dataframe(_dedupe_columns(g[safe_cols]), use_container_width=True)

    # ================= Termin Tarihi Güncelle =================
    st.markdown("#### Termin Tarihi Güncelle")
    sec_id_termin = st.selectbox(
        "Termin Tarihi Girilecek Sipariş",
        options=siparisler["ID"].astype(str).tolist(),
        format_func=lambda _id: f"{siparisler.loc[siparisler['ID'].astype(str)==_id, 'Müşteri Adı'].values[0]} - {siparisler.loc[siparisler['ID'].astype(str)==_id, 'Proforma No'].values[0]}"
    )

    mask_termin = (df_proforma["ID"].astype(str) == str(sec_id_termin))
    try:
        mevcut_termin_ts = pd.to_datetime(df_proforma.loc[mask_termin, "Termin Tarihi"].values[0], errors="coerce")
        default_termin = mevcut_termin_ts.date() if pd.notna(mevcut_termin_ts) else datetime.date.today()
    except Exception:
        default_termin = datetime.date.today()

    yeni_termin = st.date_input("Termin Tarihi", value=default_termin, key="termin_input")

    if st.button("Termin Tarihini Kaydet"):
        df_proforma.loc[mask_termin, "Termin Tarihi"] = pd.to_datetime(yeni_termin)
        update_google_sheets()
        st.success("Termin tarihi kaydedildi!")
        st.rerun()

    # ================= Sevk Et (ETA’ya gönder) =================
    st.markdown("#### Siparişi Sevk Et (ETA Takibine Gönder)")
    sec_id_sevk = st.selectbox(
        "Sevk Edilecek Sipariş",
        options=siparisler["ID"].astype(str).tolist(),
        format_func=lambda _id: f"{siparisler.loc[siparisler['ID'].astype(str)==_id, 'Müşteri Adı'].values[0]} - {siparisler.loc[siparisler['ID'].astype(str)==_id, 'Proforma No'].values[0]}",
        key="sevk_sec"
    )
    if st.button("Sevkedildi → ETA'ya Ekle"):
        # Proforma'dan bilgiler
        row = df_proforma.loc[df_proforma["ID"].astype(str) == str(sec_id_sevk)].iloc[0]

        # ETA kolon güvenliği
        for col in ["Müşteri Adı","Proforma No","ETA Tarihi","Açıklama"]:
            if col not in df_eta.columns:
                df_eta[col] = ""

        # ETA'ya ekle (varsa güncelle)
        filt = (df_eta["Müşteri Adı"] == row["Müşteri Adı"]) & (df_eta["Proforma No"] == row["Proforma No"])
        if filt.any():
            df_eta.loc[filt, "Açıklama"] = row.get("Açıklama","")
        else:
            df_eta = pd.concat([df_eta, pd.DataFrame([{
                "Müşteri Adı": row["Müşteri Adı"],
                "Proforma No": row["Proforma No"],
                "ETA Tarihi": "",
                "Açıklama": row.get("Açıklama","")
            }])], ignore_index=True)

        # Proforma'yı işaretle
        df_proforma.loc[df_proforma["ID"].astype(str) == str(sec_id_sevk), "Sevk Durumu"] = "Sevkedildi"
        update_google_sheets()
        st.success("Sipariş sevkedildi ve ETA takibine gönderildi!")
        st.rerun()

    # ================= Beklemeye Al (Geri Çağır) =================
    st.markdown("#### Siparişi Beklemeye Al (Geri Çağır)")
    sec_id_geri = st.selectbox(
        "Beklemeye Alınacak Sipariş",
        options=siparisler["ID"].astype(str).tolist(),
        format_func=lambda _id: f"{siparisler.loc[siparisler['ID'].astype(str)==_id, 'Müşteri Adı'].values[0]} - {siparisler.loc[siparisler['ID'].astype(str)==_id, 'Proforma No'].values[0]}",
        key="geri_sec"
    )
    if st.button("Beklemeye Al / Geri Çağır"):
        m = (df_proforma["ID"].astype(str) == str(sec_id_geri))
        df_proforma.loc[m, ["Durum","Sevk Durumu","Termin Tarihi"]] = ["Beklemede","",""]
        update_google_sheets()
        st.success("Sipariş tekrar bekleyen proformalar listesine alındı!")
        st.rerun()

    # ================= Linkler + Toplam =================
    st.markdown("#### Tıklanabilir Proforma ve Sipariş Formu Linkleri")
    for _, r in siparisler.iterrows():
        links = []
        if str(r.get("PDF","")).strip():
            links.append(f"[Proforma PDF: {r['Proforma No']}]({r['PDF']})")
        if str(r.get("Sipariş Formu","")).strip():
            fname = f"{r['Müşteri Adı']}__{r['Proforma No']}__SiparisFormu"
            links.append(f"[Sipariş Formu: {fname}]({r['Sipariş Formu']})")
        if links:
            st.markdown(" - " + " | ".join(links), unsafe_allow_html=True)

    # Toplam bekleyen sevk tutarı (çoklu para birimi güvenli parse)
    def smart_to_num(x):
        if pd.isna(x): return 0.0
        s = str(x).strip()
        for sym in ["USD","$","€","EUR","₺","TL","tl","Tl"]:
            s = s.replace(sym,"")
        s = s.replace("\u00A0","").replace(" ","")
        try:
            return float(s)
        except Exception:
            pass
        if "," in s:
            try:
                return float(s.replace(".","").replace(",","."))
            except Exception:
                pass
        return 0.0

    toplam = float(siparisler["Tutar"].apply(smart_to_num).sum())
    st.markdown(
        f"<div style='color:#219A41; font-weight:bold;'>*Toplam Bekleyen Sevk: {toplam:,.2f} $*</div>",
        unsafe_allow_html=True
    )
    
### ===========================
### --- FATURA & İHRACAT EVRAKLARI MENÜSÜ (Cloud‑sağlam, ID + upsert) ---
### ===========================

elif menu == "Fatura & İhracat Evrakları":
    import uuid, tempfile, re

    st.markdown("<h2 style='color:#219A41; font-weight:bold;'>Fatura & İhracat Evrakları</h2>", unsafe_allow_html=True)

    # ---- Zorunlu sütunlar + ID doldurma ----
    gerekli = [
        "ID","Müşteri Adı","Proforma No","Fatura No","Fatura Tarihi","Tutar",
        "Vade (gün)","Vade Tarihi","Ülke","Satış Temsilcisi","Ödeme Şekli",
        "Commercial Invoice","Sağlık Sertifikası","Packing List","Konşimento",
        "İhracat Beyannamesi","Fatura PDF","Sipariş Formu","Yük Resimleri",
        "EK Belgeler","Ödendi"
    ]
    for c in gerekli:
        if c not in df_evrak.columns:
            df_evrak[c] = (False if c == "Ödendi" else "")

    bos_id = df_evrak["ID"].astype(str).str.strip().isin(["","nan","None"])
    if bos_id.any():
        df_evrak.loc[bos_id, "ID"] = [str(uuid.uuid4()) for _ in range(bos_id.sum())]
        update_google_sheets()

    # ---- Müşteri / Proforma seçimleri ----
    musteri_secenek = sorted(df_proforma["Müşteri Adı"].dropna().astype(str).unique().tolist())
    secilen_musteri = st.selectbox("Müşteri Seç", [""] + musteri_secenek)

    if secilen_musteri:
        p_list = (
            df_proforma.loc[df_proforma["Müşteri Adı"] == secilen_musteri, "Proforma No"]
            .dropna().astype(str).unique().tolist()
        )
        proforma_no_sec = st.selectbox("Proforma No Seç", [""] + sorted(p_list))
    else:
        proforma_no_sec = ""

    # ---- Müşteri varsayılanları (ülke/temsilci/ödeme) ----
    musteri_info = df_musteri[df_musteri["Müşteri Adı"] == secilen_musteri]
    ulke      = musteri_info["Ülke"].values[0] if not musteri_info.empty else ""
    temsilci  = musteri_info["Satış Temsilcisi"].values[0] if not musteri_info.empty else ""
    odeme     = musteri_info["Ödeme Şekli"].values[0] if not musteri_info.empty else ""

    # ---- Proforma'dan Vade (gün) çek ----
    vade_gun = ""
    if secilen_musteri and proforma_no_sec:
        pr = df_proforma[
            (df_proforma["Müşteri Adı"] == secilen_musteri) &
            (df_proforma["Proforma No"] == proforma_no_sec)
        ]
        if not pr.empty:
            vade_gun = pr.iloc[0].get("Vade (gün)", "")

    # ---- Eski evrak linkleri (aynı müşteri+proforma altındaki son satır) ----
    onceki_evrak = df_evrak[
        (df_evrak["Müşteri Adı"] == secilen_musteri) &
        (df_evrak["Proforma No"] == proforma_no_sec)
    ].tail(1)

    def file_link_html(label, url):
        if url:
            return f'<div style="margin-top:-6px;"><a href="{url}" target="_blank" style="color:#219A41;">[Daha önce yüklenmiş {label}]</a></div>'
        return '<div style="margin-top:-6px; color:#b00020; font-size:0.95em;">(Daha önce yüklenmemiş)</div>'

    evrak_tipleri = [
        ("Commercial Invoice",  "Commercial Invoice PDF"),
        ("Sağlık Sertifikası",  "Sağlık Sertifikası PDF"),
        ("Packing List",        "Packing List PDF"),
        ("Konşimento",          "Konşimento PDF"),
        ("İhracat Beyannamesi", "İhracat Beyannamesi PDF"),
        ("Fatura PDF",          "Fatura PDF"),  # isteğe bağlı
    ]

    # ---- Form ----
    with st.form("add_evrak"):
        fatura_no = st.text_input("Fatura No")
        fatura_tarih = st.date_input("Fatura Tarihi", value=datetime.date.today())
        tutar = st.text_input("Fatura Tutarı ($)")

        # Vade (gün) & Vade Tarihi (salt okunur)
        st.text_input("Vade (gün)", value=str(vade_gun), key="vade_gun", disabled=True)
        try:
            vade_int = int(vade_gun)
            vade_tarihi_hesap = fatura_tarih + datetime.timedelta(days=vade_int)
        except Exception:
            vade_tarihi_hesap = None
        st.date_input("Vade Tarihi", value=(vade_tarihi_hesap or fatura_tarih), key="vade_tarihi", disabled=True)

        st.text_input("Ülke", value=ulke, disabled=True)
        st.text_input("Satış Temsilcisi", value=temsilci, disabled=True)
        st.text_input("Ödeme Şekli", value=odeme, disabled=True)

        # Evrak yüklemeleri + eski link gösterimleri
        uploaded_files = {}
        for col, label in evrak_tipleri:
            uploaded_files[col] = st.file_uploader(label, type="pdf", key=f"{col}_upload")
            prev_url = onceki_evrak.iloc[0][col] if not onceki_evrak.empty else ""
            st.markdown(file_link_html(label, prev_url), unsafe_allow_html=True)

        submitted = st.form_submit_button("Kaydet")

    if submitted:
        # Zorunlu kontroller
        if not (secilen_musteri and proforma_no_sec and fatura_no.strip() and tutar.strip()):
            st.error("Müşteri, Proforma No, Fatura No ve Tutar zorunludur.")
            st.stop()

        # 1) Dosyaları Drive'a yükle (varsa). Yoksa eski linki koru.
        file_urls = {}
        for col, _label in evrak_tipleri:
            upfile = uploaded_files[col]
            if upfile:
                clean_base = re.sub(r'[\\/*?:"<>|]+', "_",
                                    f"{secilen_musteri}__{proforma_no_sec}__{col}__{datetime.datetime.now().strftime('%Y%m%d%H%M%S')}")
                fname = f"{clean_base}.pdf"
                # Geçici dosyaya yazıp helper ile yükle
                tmp_path = os.path.join(".", fname)
                with open(tmp_path, "wb") as f:
                    f.write(upfile.read())
                try:
                    file_urls[col] = upload_file_to_drive(EVRAK_KLASOR_ID, tmp_path, fname)
                finally:
                    try: os.remove(tmp_path)
                    except Exception: pass
            else:
                file_urls[col] = onceki_evrak.iloc[0][col] if not onceki_evrak.empty else ""

        # 2) Upsert: aynı (Müşteri, Proforma, Fatura No) varsa GÜNCELLE; yoksa EKLE
        key_mask = (
            (df_evrak["Müşteri Adı"] == secilen_musteri) &
            (df_evrak["Proforma No"] == proforma_no_sec) &
            (df_evrak["Fatura No"] == fatura_no)
        )

        vade_tarihi_yaz = (vade_tarihi_hesap if vade_tarihi_hesap else "")

        if key_mask.any():
            idx = df_evrak[key_mask].index[0]
            df_evrak.at[idx, "Fatura Tarihi"]    = fatura_tarih
            df_evrak.at[idx, "Tutar"]            = tutar
            df_evrak.at[idx, "Vade (gün)"]       = vade_gun
            df_evrak.at[idx, "Vade Tarihi"]      = vade_tarihi_yaz
            df_evrak.at[idx, "Ülke"]             = ulke
            df_evrak.at[idx, "Satış Temsilcisi"] = temsilci
            df_evrak.at[idx, "Ödeme Şekli"]      = odeme
            for col, _ in evrak_tipleri:
                df_evrak.at[idx, col] = file_urls.get(col, "")
            islem = "güncellendi"
        else:
            new_row = {
                "ID": str(uuid.uuid4()),
                "Müşteri Adı": secilen_musteri,
                "Proforma No": proforma_no_sec,
                "Fatura No": fatura_no,
                "Fatura Tarihi": fatura_tarih,
                "Tutar": tutar,
                "Vade (gün)": vade_gun,
                "Vade Tarihi": vade_tarihi_yaz,
                "Ülke": ulke,
                "Satış Temsilcisi": temsilci,
                "Ödeme Şekli": odeme,
                "Ödendi": False,
                **{col: file_urls.get(col, "") for col, _ in evrak_tipleri},
                "Sipariş Formu": "",
                "Yük Resimleri": "",
                "EK Belgeler": "",
            }
            df_evrak = pd.concat([df_evrak, pd.DataFrame([new_row])], ignore_index=True)
            islem = "eklendi"

        update_google_sheets()
        st.success(f"Evrak {islem}!")
        st.rerun()
        
### ===========================
### --- VADE TAKİBİ MENÜSÜ ---
### ===========================
elif menu == "Vade Takibi":
    st.markdown("<h2 style='color:#219A41; font-weight:bold;'>Vade Takibi</h2>", unsafe_allow_html=True)

    # df_evrak hiç yok/boş olabilir → koru
    if "df_evrak" not in globals() or df_evrak is None:
        df_evrak = pd.DataFrame()

    # Gerekli kolonlar yoksa ekle
    for c in ["Müşteri Adı","Fatura No","Vade Tarihi","Tutar","Ülke","Satış Temsilcisi","Ödeme Şekli","Ödendi"]:
        if c not in df_evrak.columns:
            df_evrak[c] = (False if c == "Ödendi" else "")

    # --- Tutarı sayıya çevir (USD/EUR/TL vs. temizler) ---
    def smart_to_num(x):
        if pd.isna(x): return 0.0
        s = str(x).strip()
        for sym in ["USD","$","€","EUR","₺","TL","tl","Tl"]:
            s = s.replace(sym, "")
        s = s.replace("\u00A0","").replace(" ","")
        try:
            return float(s)  # US format
        except Exception:
            pass
        if "," in s:
            try:
                return float(s.replace(".","").replace(",", "."))  # EU format
            except Exception:
                pass
        return 0.0

    # --- Ödendi'yi güvenli bool'a çevir ---
    TRUE_SET  = {"true","1","evet","yes","y","paid","ödendi","ödenmiş"}
    FALSE_SET = {"false","0","hayir","hayır","no","n","unpaid","ödenmedi","beklemede",""}

    def to_bool(x):
        if isinstance(x, bool): return x
        if pd.isna(x):          return False  # boşsa ödenmemiş kabul
        s = str(x).strip().lower()
        if s in TRUE_SET:  return True
        if s in FALSE_SET: return False
        try:
            return float(s) != 0.0
        except Exception:
            return False

    # --- Çalışma kopyası ---
    vade_df = df_evrak.copy()

    if vade_df.empty:
        st.info("Vade takibi için kayıt bulunmuyor.")
        st.stop()

    # Tutar_num üret (sadece görünüme, Sheets'e yazılmıyor)
    vade_df["Tutar_num"] = vade_df["Tutar"].apply(smart_to_num).fillna(0.0)

    # Vade Tarihi tarih tipine
    vade_df["Vade Tarihi"] = pd.to_datetime(vade_df["Vade Tarihi"], errors="coerce")

    # Sadece vadesi olanlar
    vade_df = vade_df[vade_df["Vade Tarihi"].notna()]

    if vade_df.empty:
        st.info("Vade tarihi girilmiş kayıt bulunmuyor.")
    else:
        # Ödendi_bool üret
        vade_df["Ödendi_bool"] = vade_df["Ödendi"].apply(to_bool)

        today = pd.Timestamp.today().normalize()
        vade_df["Kalan Gün"] = (vade_df["Vade Tarihi"] - today).dt.days

        # Ödenmemişler üzerinden özet kutucukları
        acik = vade_df[~vade_df["Ödendi_bool"]].copy()
        vadesi_gelmemis = acik[acik["Kalan Gün"] > 0]
        bugun            = acik[acik["Kalan Gün"] == 0]
        gecikmis         = acik[acik["Kalan Gün"] < 0]

        c1, c2, c3 = st.columns(3)
        c1.metric("📅 Vadesi Gelmemiş", f"{float(vadesi_gelmemis['Tutar_num'].sum()):,.2f} USD", f"{len(vadesi_gelmemis)} Fatura")
        c2.metric("⚠️ Bugün Vadesi",   f"{float(bugun['Tutar_num'].sum()):,.2f} USD",           f"{len(bugun)} Fatura")
        c3.metric("⛔ Gecikmiş",        f"{float(gecikmis['Tutar_num'].sum()):,.2f} USD",        f"{len(gecikmis)} Fatura")

        st.markdown("---")

        # Filtreler
        f1, f2, f3, f4 = st.columns([1.4, 1.2, 1.2, 1.1])
        ulke_f   = f1.multiselect("Ülke", sorted([u for u in vade_df["Ülke"].dropna().unique() if str(u).strip()]))
        tem_f    = f2.multiselect("Satış Temsilcisi", sorted([t for t in vade_df["Satış Temsilcisi"].dropna().unique() if str(t).strip()]))
        durum_f  = f3.selectbox("Ödeme Durumu", ["Ödenmemiş (varsayılan)", "Hepsi", "Sadece Ödenmiş"], index=0)
        arama    = f4.text_input("Ara (Müşteri/Fatura)")

        view = vade_df.copy()
        if ulke_f:
            view = view[view["Ülke"].isin(ulke_f)]
        if tem_f:
            view = view[view["Satış Temsilcisi"].isin(tem_f)]
        if durum_f == "Ödenmemiş (varsayılan)":
            view = view[~view["Ödendi_bool"]]
        elif durum_f == "Sadece Ödenmiş":
            view = view[view["Ödendi_bool"]]
        if arama.strip():
            s = arama.lower().strip()
            view = view[
                view["Müşteri Adı"].astype(str).str.lower().str.contains(s, na=False) |
                view["Fatura No"].astype(str).str.lower().str.contains(s, na=False)
            ]

        # Görüntü tablosu
        show = view.copy()
        show["Vade Tarihi"] = pd.to_datetime(show["Vade Tarihi"], errors="coerce").dt.strftime("%d/%m/%Y")
        show["Tutar (USD)"] = show["Tutar_num"].map(lambda x: f"{float(x):,.2f}")
        cols = ["Müşteri Adı","Ülke","Satış Temsilcisi","Fatura No","Vade Tarihi","Kalan Gün","Tutar (USD)","Ödendi_bool"]
        cols = [c for c in cols if c in show.columns]
        show = show[cols].rename(columns={"Ödendi_bool":"Ödendi"})

        top_cols = st.columns([3, 1])
        with top_cols[0]:
            st.markdown(f"<div style='color:#219A41; font-weight:700;'>Listelenen Kayıt: {len(show)}</div>", unsafe_allow_html=True)
        with top_cols[1]:
            st.download_button(
                "⬇️ CSV indir",
                data=show.to_csv(index=False).encode("utf-8"),
                file_name="vade_takibi.csv",
                mime="text/csv",
                use_container_width=True
            )

        st.dataframe(show.sort_values(["Kalan Gün","Vade Tarihi"], ascending=[True, True]), use_container_width=True)

        # --- Ödeme durumu güncelle ---
        st.markdown("#### Ödeme Durumu Güncelle")
        if not view.empty:
            # df_evrak orijinal indexini saklayarak seçim yaptır
            sel_df = view.reset_index(drop=False).rename(columns={"index":"_row"})  # _row = df_evrak'taki orijinal index
            sec = st.selectbox(
                "Kayıt Seç",
                options=sel_df["_row"].tolist(),
                format_func=lambda i: f"{sel_df.loc[sel_df['_row']==i,'Müşteri Adı'].values[0]} | {sel_df.loc[sel_df['_row']==i,'Fatura No'].values[0]}"
            )

            current_paid = bool(sel_df.loc[sel_df["_row"] == sec, "Ödendi_bool"].values[0])
            odendi_mi = st.checkbox("Ödendi olarak işaretle", value=current_paid)

            if st.button("Kaydet / Güncelle"):
                ana_index = int(sec)  # df_evrak'ın gerçek satırı
                df_evrak.at[ana_index, "Ödendi"] = bool(odendi_mi)
                update_google_sheets()
                st.success("Ödeme durumu güncellendi!")
                st.rerun()
        else:
            st.caption("Filtrelere uyan kayıt olmadığı için güncelleme alanı gizlendi.")


# ===========================
# --- ETA TAKİBİ MENÜSÜ ---
# ===========================
elif menu == "ETA Takibi":
    import os
    import re
    import tempfile
    import datetime
    import pandas as pd
    from googleapiclient.http import MediaFileUpload

    # ---- Yedek: update_google_sheets yoksa no-op yap ----
    update_google_sheets = globals().get("update_google_sheets", lambda: None)

    # ---- Sabitler ----
    # Ana İhracat Evrak klasörü (My Drive veya Paylaşılan Sürücü olabilir)
    ROOT_EXPORT_FOLDER_ID = globals().get("EVRAK_KLASOR_ID", "")

    # ---- Kolon güvenliği ----
    for col in ["Sevk Durumu", "Proforma No", "Sevk Tarihi", "Ulaşma Tarihi", "Termin Tarihi", "Tutar", "Açıklama", "Müşteri Adı"]:
        if col not in df_proforma.columns:
            df_proforma[col] = ""
    for col in ["Müşteri Adı", "Proforma No", "ETA Tarihi", "Açıklama"]:
        if col not in df_eta.columns:
            df_eta[col] = ""

    # ---- Yardımcılar: Drive isim temizliği ----
    def safe_name(text: str, maxlen: int = 120) -> str:
        s = str(text or "").strip()
        s = re.sub(r"\s+", " ", s)        # çoklu boşluk -> tek
        s = s.replace(" ", "_")           # boşluk -> _
        s = re.sub(r'[\\/*?:"<>|]+', "_", s)  # Drive yasak karakterleri
        return s[:maxlen] or "dosya"

    # ---- Drive: klasör bul ----
    def _find_folder_id(name: str, parent_id: str | None) -> str | None:
        if not name:
            return None
        # Tek tırnak kaçışı
        safe = name.replace("'", r"\'")
        parts = [
            f"name = '{safe}'",
            "mimeType = 'application/vnd.google-apps.folder'",
            "trashed = false",
        ]
        if parent_id:
            parts.append(f"'{parent_id}' in parents")
        q = " and ".join(parts)
        resp = drive_service.files().list(
            q=q,
            fields="files(id,name)",
            supportsAllDrives=True,
            includeItemsFromAllDrives=True,
            corpora="allDrives",
            pageSize=5,
        ).execute()
        files = resp.get("files", [])
        return files[0]["id"] if files else None

    # ---- Drive: klasör oluştur ya da getir ----
    def get_or_create_folder_by_name(name: str, parent_id: str | None) -> str:
        fid = _find_folder_id(name, parent_id)
        if fid:
            return fid
        meta = {"name": name, "mimeType": "application/vnd.google-apps.folder"}
        if parent_id:
            meta["parents"] = [parent_id]
        created = drive_service.files().create(
            body=meta,
            fields="id",
            supportsAllDrives=True
        ).execute()
        return created["id"]

    # ---- Klasör tarihi seçim mantığı ----
    def resolve_folder_date(musteri: str, proforma_no: str) -> datetime.date:
        # 1) Sevk Tarihi
        pm = (df_proforma["Müşteri Adı"] == musteri) & (df_proforma["Proforma No"] == proforma_no)
        if pm.any():
            sevk_ts = pd.to_datetime(df_proforma.loc[pm, "Sevk Tarihi"].values[0], errors="coerce")
            if pd.notna(sevk_ts):
                try:
                    return sevk_ts.date()
                except Exception:
                    pass
        # 2) ETA Tarihi
        em = (df_eta["Müşteri Adı"] == musteri) & (df_eta["Proforma No"] == proforma_no)
        if em.any():
            eta_ts = pd.to_datetime(df_eta.loc[em, "ETA Tarihi"].values[0], errors="coerce")
            if pd.notna(eta_ts):
                try:
                    return eta_ts.date()
                except Exception:
                    pass
        # 3) Bugün
        return datetime.date.today()

    # ---- Müşteri + Tarih bazlı Yükleme Resimleri klasörü ----
    def get_loading_photos_folder(musteri_adi: str, tarih: datetime.date) -> str:
        if not ROOT_EXPORT_FOLDER_ID:
            return ""
        musteri_tarih = f"{safe_name(musteri_adi)}_{tarih.strftime('%Y-%m-%d')}"
        parent = get_or_create_folder_by_name(musteri_tarih, ROOT_EXPORT_FOLDER_ID)
        return get_or_create_folder_by_name("Yükleme Resimleri", parent)

    # UI Başlık
    st.markdown("<h2 style='color:#219A41; font-weight:bold;'>ETA Takibi</h2>", unsafe_allow_html=True)

    # ==== SEVKEDİLENLER (Yolda) ====
    sevkedilenler = df_proforma[df_proforma["Sevk Durumu"] == "Sevkedildi"].copy()
    if sevkedilenler.empty:
        st.info("Sevkedilmiş sipariş bulunmuyor.")
    else:
        # Seçim
        secenekler = sevkedilenler[["Müşteri Adı", "Proforma No"]].drop_duplicates()
        secenekler["sec_text"] = secenekler["Müşteri Adı"].astype(str) + " - " + secenekler["Proforma No"].astype(str)
        selected = st.selectbox("Sevkedilen Sipariş Seç", secenekler["sec_text"])
        sel_row = secenekler[secenekler["sec_text"] == selected].iloc[0]
        sec_musteri = str(sel_row["Müşteri Adı"])
        sec_proforma = str(sel_row["Proforma No"])

        # Klasör tarihi (Sevk/ETA/bugün)
        klasor_tarih = resolve_folder_date(sec_musteri, sec_proforma)

        # ========== YÜKLEME FOTOĞRAFLARI ==========
        st.markdown("#### 🖼️ Yükleme Fotoğrafları (Müşteri + Tarih)")

        hedef_klasor = get_loading_photos_folder(sec_musteri, klasor_tarih)
        if not hedef_klasor:
            st.error("Klasör hiyerarşisi oluşturulamadı. Lütfen ROOT_EXPORT_FOLDER_ID (EVRAK_KLASOR_ID) kontrol edin.")
        else:
            # Aç butonu
            st.markdown(f"[🔗 Klasörü yeni sekmede aç](https://drive.google.com/drive/folders/{hedef_klasor}?usp=sharing)")

            # Panel içinde embed
            with st.expander(f"📂 Panelde klasörü görüntüle – {sec_musteri} / {klasor_tarih.strftime('%Y-%m-%d')}"):
                embed = f"https://drive.google.com/embeddedfolderview?id={hedef_klasor}#grid"
                st.markdown(
                    f'<iframe src="{embed}" width="100%" height="520" frameborder="0" '
                    f'style="border:1px solid #eee; border-radius:12px;"></iframe>',
                    unsafe_allow_html=True
                )

            # Mevcut dosyaları say
            try:
                resp = drive_service.files().list(
                    q=f"'{hedef_klasor}' in parents and trashed = false",
                    fields="files(id,name)",
                    supportsAllDrives=True,
                    includeItemsFromAllDrives=True,
                    corpora="allDrives",
                    pageSize=200,
                ).execute()
                mevcut_dosyalar = resp.get("files", [])
            except Exception as e:
                mevcut_dosyalar = []
                st.warning(f"Dosyalar listelenemedi: {e}")

            if mevcut_dosyalar:
                st.caption(f"Bu klasörde {len(mevcut_dosyalar)} dosya var.")
                preview = "\n".join(f"- {f['name']}" for f in mevcut_dosyalar[:10])
                if preview:
                    st.write(preview)
                if len(mevcut_dosyalar) > 10:
                    st.write("…")

            # Dosya ekle (duplike isim engelle)
            with st.expander("➕ Dosya Ekle (duplike isimleri atlar)"):
                files = st.file_uploader(
                    "Yüklenecek dosyaları seçin",
                    type=["pdf", "jpg", "jpeg", "png", "webp"],
                    accept_multiple_files=True,
                    key=f"yuk_resimleri_{sec_musteri}_{klasor_tarih}"
                )
                if files:
                    var_olan_isimler = {f["name"] for f in mevcut_dosyalar}
                    yuklenen_say = 0
                    atlanan_duplike = 0

                    for up in files:
                        suffix = os.path.splitext(up.name)[1].lower() or ""
                        base = os.path.splitext(up.name)[0]
                        fname = safe_name(base) + suffix
                        if fname in var_olan_isimler:
                            atlanan_duplike += 1
                            continue

                        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as fp:
                            fp.write(up.read())
                            tmp_path = fp.name

                        media = MediaFileUpload(tmp_path, resumable=False)
                        meta = {"name": fname, "parents": [hedef_klasor]}
                        try:
                            drive_service.files().create(
                                body=meta, media_body=media, fields="id",
                                supportsAllDrives=True
                            ).execute()
                            yuklenen_say += 1
                            var_olan_isimler.add(fname)
                        except Exception as e:
                            st.error(f"{up.name} yüklenemedi: {e}")
                        finally:
                            try: os.remove(tmp_path)
                            except: pass

                    if yuklenen_say:
                        st.success(f"{yuklenen_say} yeni dosya yüklendi.")
                        if atlanan_duplike:
                            st.info(f"{atlanan_duplike} dosya aynı isimle bulunduğu için atlandı.")
                    elif atlanan_duplike and not yuklenen_say:
                        st.warning("Tüm dosyalar klasörde zaten mevcut (isimler aynı).")

        st.markdown("---")

        # ========== ETA Düzenleme ==========
        flt = (df_eta["Müşteri Adı"] == sec_musteri) & (df_eta["Proforma No"] == sec_proforma)
        mevcut_eta = df_eta.loc[flt, "ETA Tarihi"].values[0] if flt.any() else ""
        mevcut_aciklama = df_eta.loc[flt, "Açıklama"].values[0] if flt.any() else ""

        with st.form("edit_eta"):
            try:
                varsayilan_eta = pd.to_datetime(mevcut_eta).date() if mevcut_eta and pd.notna(mevcut_eta) else datetime.date.today()
            except Exception:
                varsayilan_eta = datetime.date.today()
            eta_tarih = st.date_input("ETA Tarihi", value=varsayilan_eta)
            aciklama = st.text_area("Açıklama", value=str(mevcut_aciklama or ""))
            col_a, col_b, col_c = st.columns(3)
            guncelle = col_a.form_submit_button("ETA'yı Kaydet/Güncelle")
            ulasti   = col_b.form_submit_button("Ulaştı")
            geri_al  = col_c.form_submit_button("Sevki Geri Al")

        if guncelle:
            if flt.any():
                df_eta.loc[flt, "ETA Tarihi"] = eta_tarih
                df_eta.loc[flt, "Açıklama"] = aciklama
            else:
                df_eta = pd.concat([df_eta, pd.DataFrame([{
                    "Müşteri Adı": sec_musteri,
                    "Proforma No": sec_proforma,
                    "ETA Tarihi": eta_tarih,
                    "Açıklama": aciklama
                }])], ignore_index=True)
            update_google_sheets()
            st.success("ETA kaydedildi/güncellendi!")
            st.rerun()

        if ulasti:
            # Ulaşıldı: ETA'dan çıkar, proforma'da Sevk Durumu=Ulaşıldı + Ulaşma Tarihi=today
            df_eta = df_eta[~flt].reset_index(drop=True)
            pidx = df_proforma[(df_proforma["Müşteri Adı"] == sec_musteri) &
                               (df_proforma["Proforma No"] == sec_proforma)].index
            if len(pidx) > 0:
                df_proforma.at[pidx[0], "Sevk Durumu"] = "Ulaşıldı"
                df_proforma.at[pidx[0], "Ulaşma Tarihi"] = datetime.date.today()
            update_google_sheets()
            st.success("Sipariş 'Ulaşıldı' olarak işaretlendi ve ETA takibinden çıkarıldı!")
            st.rerun()

        if geri_al:
            # Siparişi geri al: ETA'dan çıkar, proforma'da sevk durumunu boş yap
            df_eta = df_eta[~flt].reset_index(drop=True)
            pidx = df_proforma[(df_proforma["Müşteri Adı"] == sec_musteri) &
                               (df_proforma["Proforma No"] == sec_proforma)].index
            if len(pidx) > 0:
                df_proforma.at[pidx[0], "Sevk Durumu"] = ""
            update_google_sheets()
            st.success("Sevkiyat geri alındı! Sipariş tekrar Güncel Sipariş Durumu'na döndü.")
            st.rerun()

    # ==== ETA TAKİP LİSTESİ ====
    st.markdown("#### ETA Takip Listesi")
    if not df_eta.empty:
        df_eta_disp = df_eta.copy()
        df_eta_disp["ETA Tarihi"] = pd.to_datetime(df_eta_disp["ETA Tarihi"], errors="coerce")
        today = pd.to_datetime(datetime.date.today())
        df_eta_disp["Kalan Gün"] = (df_eta_disp["ETA Tarihi"] - today).dt.days
        tablo = df_eta_disp[["Müşteri Adı", "Proforma No", "ETA Tarihi", "Kalan Gün", "Açıklama"]].copy()
        tablo = tablo.sort_values(["ETA Tarihi", "Müşteri Adı", "Proforma No"], ascending=[True, True, True])
        st.dataframe(tablo, use_container_width=True)

        # Silme
        st.markdown("##### ETA Kaydı Sil")
        sil_ops = df_eta.index.tolist()
        sil_sec = st.selectbox(
            "Silinecek Kaydı Seçin",
            options=sil_ops,
            format_func=lambda i: f"{df_eta.at[i, 'Müşteri Adı']} - {df_eta.at[i, 'Proforma No']}"
        )
        if st.button("KAYDI SİL"):
            df_eta = df_eta.drop(sil_sec).reset_index(drop=True)
            update_google_sheets()
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
            current_ulasma = pd.to_datetime(row.get("Ulaşma Tarihi", None), errors="coerce").date()
            if pd.isnull(current_ulasma):
                current_ulasma = datetime.date.today()
        except Exception:
            current_ulasma = datetime.date.today()

        new_ulasma_tarih = st.date_input("Ulaşma Tarihi", value=current_ulasma, key="ulasan_guncelle")
        if st.button("Ulaşma Tarihini Kaydet"):
            pidx = df_proforma[(df_proforma["Müşteri Adı"] == row["Müşteri Adı"]) &
                               (df_proforma["Proforma No"] == row["Proforma No"])].index
            if len(pidx) > 0:
                df_proforma.at[pidx[0], "Ulaşma Tarihi"] = new_ulasma_tarih
                update_google_sheets()
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
            musteri = str(row["Müşteri Adı"])
            pno = str(row["Proforma No"])

            # Proforma statüsü
            pidx = df_proforma[(df_proforma["Müşteri Adı"] == musteri) & (df_proforma["Proforma No"] == pno)].index
            if len(pidx) > 0:
                df_proforma.at[pidx[0], "Sevk Durumu"] = "Sevkedildi"
                df_proforma.at[pidx[0], "Ulaşma Tarihi"] = ""

            # ETA ekle/güncelle
            flt_eta = (df_eta["Müşteri Adı"] == musteri) & (df_eta["Proforma No"] == pno)
            eta_deger = pd.to_datetime(yeni_eta) if yeni_eta else ""
            if flt_eta.any():
                if yeni_eta:
                    df_eta.loc[flt_eta, "ETA Tarihi"] = eta_deger
                if aciklama_geri:
                    df_eta.loc[flt_eta, "Açıklama"] = aciklama_geri
            else:
                yeni_satir = {
                    "Müşteri Adı": musteri,
                    "Proforma No": pno,
                    "ETA Tarihi": eta_deger if yeni_eta else "",
                    "Açıklama": aciklama_geri,
                }
                df_eta = pd.concat([df_eta, pd.DataFrame([yeni_satir])], ignore_index=True)

            update_google_sheets()
            st.success("Sipariş, Ulaşanlar'dan geri alındı ve ETA listesine taşındı (Sevkedildi).")
            st.rerun()

        # Ulaşanlar Tablosu
        st.markdown("#### Ulaşan (Teslim Edilmiş) Siparişler")
        for dtcol in ["Sevk Tarihi", "Termin Tarihi", "Ulaşma Tarihi"]:
            ulasanlar[dtcol] = pd.to_datetime(ulasanlar[dtcol], errors="coerce")
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

# --- Session başlangıç değerleri ---
if "current_fuar" not in st.session_state:
    st.session_state.current_fuar = ""
if "fuarlar_extra" not in st.session_state:
    st.session_state.fuarlar_extra = set()  # df'e girmeyen, geçici eklenen fuarlar

FUAR_KOLONLAR = [
    "Fuar Adı", "Müşteri Adı", "Ülke", "Telefon", "E-mail",
    "Satış Temsilcisi", "Açıklamalar", "Görüşme Kalitesi", "Tarih"
]
for c in FUAR_KOLONLAR:
    if c not in df_fuar_musteri.columns:
        df_fuar_musteri[c] = "" if c not in ["Görüşme Kalitesi", "Tarih"] else np.nan

def _to_int_1_5(x, default=3):
    v = pd.to_numeric(x, errors="coerce")
    if pd.isna(v): return default
    v = int(v)
    return min(max(v, 1), 5)

def _to_date(x, default=None):
    if default is None:
        default = datetime.date.today()
    try:
        ts = pd.to_datetime(x, errors="coerce")
        return ts.date() if pd.notna(ts) else default
    except Exception:
        return default

if menu == "Fuar Müşteri Kayıtları":
    st.markdown("<h2 style='color:#8e54e9; font-weight:bold; text-align:center;'>🎫 FUAR MÜŞTERİ KAYITLARI</h2>", unsafe_allow_html=True)
    st.info("Fuarlarda müşteri görüşmelerinizi hızlıca buraya ekleyin. Yeni kayıt oluşturun, mevcutları düzenleyin.")

    # --- Fuar seçimi / oluşturma ---
    mevcut_fuarlar = sorted([f for f in df_fuar_musteri["Fuar Adı"].dropna().unique() if str(f).strip() != ""])
    # Session'da geçici eklenen fuarları da göster
    tum_fuarlar = sorted(set(mevcut_fuarlar) | set(st.session_state.fuarlar_extra))

    col_f1, col_f2 = st.columns([2, 1])
    with col_f1:
        dd_items = ["— Fuar Seçiniz —"] + tum_fuarlar
        # Varsayılan, session’daki current_fuar ise onu seçtirelim
        idx = 0
        if st.session_state.current_fuar and st.session_state.current_fuar in tum_fuarlar:
            idx = dd_items.index(st.session_state.current_fuar) if st.session_state.current_fuar in dd_items else 0
        fuar_adi_sel = st.selectbox("Fuar Seçiniz", dd_items, index=idx, key="fuar_dd")
        fuar_adi = "" if fuar_adi_sel == "— Fuar Seçiniz —" else fuar_adi_sel
        # Dropdowndan seçim yapınca current_fuar'ı güncelle
        st.session_state.current_fuar = fuar_adi
    with col_f2:
        yeni_fuar = st.text_input("Yeni Fuar Adı (opsiyonel)")
        if st.button("Fuar Ekle"):
            y = yeni_fuar.strip()
            if not y:
                st.warning("Fuar adı boş olamaz.")
            elif y in tum_fuarlar:
                st.info("Bu fuar zaten listede.")
                st.session_state.current_fuar = y
            else:
                # Geçici listeye ekle, seçili yap
                st.session_state.fuarlar_extra.add(y)
                st.session_state.current_fuar = y
                st.success(f"Fuar eklendi: {y}")
            st.rerun()

    secim = st.radio("İşlem Seçiniz:", ["Yeni Kayıt", "Eski Kayıt"], horizontal=True)

    # --- YENİ KAYIT ---
    if secim == "Yeni Kayıt":
        st.markdown("#### Yeni Fuar Müşteri Kaydı")
        with st.form("fuar_musteri_ekle"):
            # Üstte seçilmiş fuar varsayılan gelir; istenirse burada değiştirilebilir
            fuar_in_form = st.selectbox(
                "Fuar Adı",
                ["— Fuar Seçiniz —"] + tum_fuarlar,
                index=(["— Fuar Seçiniz —"] + tum_fuarlar).index(st.session_state.current_fuar) if st.session_state.current_fuar in tum_fuarlar else 0
            )
            fuar_in_form = "" if fuar_in_form == "— Fuar Seçiniz —" else fuar_in_form

            musteri_adi = st.text_input("Müşteri Adı")
            ulke = st.selectbox("Ülke Seçin", ulke_listesi)  # global
            tel = st.text_input("Telefon")
            email = st.text_input("E-mail")
            temsilci = st.selectbox("Satış Temsilcisi", temsilci_listesi)  # global
            aciklama = st.text_area("Açıklamalar")
            gorusme_kalitesi = st.slider("Görüşme Kalitesi (1=Kötü, 5=Çok İyi)", 1, 5, 3)
            tarih = st.date_input("Tarih", value=datetime.date.today())

            kaydet = st.form_submit_button("Kaydet")
            if kaydet:
                if not fuar_in_form:
                    st.warning("Lütfen bir fuar seçin veya ekleyin.")
                elif not musteri_adi.strip():
                    st.warning("Müşteri adı gerekli.")
                else:
                    yeni = {
                        "Fuar Adı": fuar_in_form,
                        "Müşteri Adı": musteri_adi.strip(),
                        "Ülke": ulke,
                        "Telefon": tel.strip(),
                        "E-mail": email.strip(),
                        "Satış Temsilcisi": temsilci,
                        "Açıklamalar": aciklama.strip(),
                        "Görüşme Kalitesi": int(gorusme_kalitesi),
                        "Tarih": tarih,
                    }
                    df_fuar_musteri = pd.concat([df_fuar_musteri, pd.DataFrame([yeni])], ignore_index=True)
                    # Bu fuar artık df'de de var; gerekirse geçicilerden kaldır
                    if fuar_in_form in st.session_state.fuarlar_extra:
                        st.session_state.fuarlar_extra.discard(fuar_in_form)
                    st.session_state.current_fuar = fuar_in_form
                    update_google_sheets()
                    st.success("Fuar müşterisi eklendi!")
                    st.rerun()

    # --- ESKİ KAYIT: listele / filtrele / düzenle / sil ---
    elif secim == "Eski Kayıt":
        if not st.session_state.current_fuar:
            st.info("Önce bir fuar seçin.")
        else:
            fuar_adi = st.session_state.current_fuar
            st.markdown(f"<h4 style='color:#4776e6;'>{fuar_adi} – Kayıtlar</h4>", unsafe_allow_html=True)

            fuar_df = df_fuar_musteri[df_fuar_musteri["Fuar Adı"] == fuar_adi].copy()

            # Hızlı filtreler
            col_fa, col_fb, col_fc = st.columns([1, 1, 1])
            with col_fa:
                min_puan = st.slider("Min. Görüşme Kalitesi", 1, 5, 1)
            with col_fb:
                tarih_bas = st.date_input("Başlangıç Tarihi", value=datetime.date.today() - datetime.timedelta(days=30))
            with col_fc:
                tarih_bit = st.date_input("Bitiş Tarihi", value=datetime.date.today())

            # Tip dönüşümleri ve filtre uygula
            fuar_df["Görüşme Kalitesi"] = pd.to_numeric(fuar_df["Görüşme Kalitesi"], errors="coerce")
            fuar_df["Tarih"] = pd.to_datetime(fuar_df["Tarih"], errors="coerce")
            mask = (
                (fuar_df["Görüşme Kalitesi"].fillna(0) >= min_puan) &
                (fuar_df["Tarih"].dt.date >= tarih_bas) &
                (fuar_df["Tarih"].dt.date <= tarih_bit)
            )
            fuar_df = fuar_df[mask].copy().sort_values("Tarih", ascending=False)

            if fuar_df.empty:
                st.info("Filtrelere uyan kayıt yok.")
            else:
                # Seçim
                secili_index = st.selectbox(
                    "Düzenlemek/Silmek istediğiniz kaydı seçin:",
                    fuar_df.index,
                    format_func=lambda i: f"{fuar_df.at[i, 'Müşteri Adı']} ({_to_date(fuar_df.at[i, 'Tarih']).strftime('%d/%m/%Y')})"
                )

                # Detay formu
                with st.form("kayit_duzenle"):
                    musteri_adi = st.text_input("Müşteri Adı", value=str(fuar_df.at[secili_index, "Müşteri Adı"] or ""))
                    u_val = fuar_df.at[secili_index, "Ülke"]
                    ulke = st.selectbox("Ülke", ulke_listesi, index=ulke_listesi.index(u_val) if u_val in ulke_listesi else ulke_listesi.index("Diğer"))
                    t_val = fuar_df.at[secili_index, "Satış Temsilcisi"]
                    temsilci = st.selectbox("Satış Temsilcisi", temsilci_listesi, index=temsilci_listesi.index(t_val) if t_val in temsilci_listesi else 0)
                    tel = st.text_input("Telefon", value=str(fuar_df.at[secili_index, "Telefon"] or ""))
                    email = st.text_input("E-mail", value=str(fuar_df.at[secili_index, "E-mail"] or ""))
                    aciklama = st.text_area("Açıklamalar", value=str(fuar_df.at[secili_index, "Açıklamalar"] or ""))
                    gk_default = _to_int_1_5(fuar_df.at[secili_index, "Görüşme Kalitesi"], default=3)
                    gorusme_kalitesi = st.slider("Görüşme Kalitesi (1-5)", 1, 5, gk_default)
                    tarih = st.date_input("Tarih", value=_to_date(fuar_df.at[secili_index, "Tarih"]))

                    col_b1, col_b2 = st.columns(2)
                    with col_b1:
                        guncelle = st.form_submit_button("Kaydı Güncelle")
                    with col_b2:
                        sil = st.form_submit_button("Kaydı Sil")

                # Güncelle
                if guncelle:
                    updates = {
                        "Müşteri Adı": musteri_adi.strip(),
                        "Ülke": ulke,
                        "Telefon": tel.strip(),
                        "E-mail": email.strip(),
                        "Satış Temsilcisi": temsilci,
                        "Açıklamalar": aciklama.strip(),
                        "Görüşme Kalitesi": int(gorusme_kalitesi),
                        "Tarih": tarih,
                    }
                    for k, v in updates.items():
                        df_fuar_musteri.at[secili_index, k] = v
                    update_google_sheets()
                    st.success("Kayıt güncellendi!")
                    st.rerun()

                # Sil
                if sil:
                    df_fuar_musteri = df_fuar_musteri.drop(secili_index).reset_index(drop=True)
                    update_google_sheets()
                    st.success("Kayıt silindi!")
                    st.rerun()

                # Görsel tablo
                tablo = fuar_df.copy()
                tablo["Tarih"] = tablo["Tarih"].dt.strftime("%d/%m/%Y")
                st.dataframe(tablo[[
                    "Müşteri Adı", "Ülke", "Telefon", "E-mail",
                    "Satış Temsilcisi", "Açıklamalar", "Görüşme Kalitesi", "Tarih"
                ]], use_container_width=True)
# ===========================
# === MEDYA ÇEKMECESİ MENÜSÜ ===
# ===========================

elif menu == "Medya Çekmecesi":
    st.markdown("<h2 style='color:#8e54e9; font-weight:bold;'>Medya Çekmecesi</h2>", unsafe_allow_html=True)
    st.info("Google Drive’daki medya, ürün görselleri, kalite evrakları ve arşiv klasörlerini buradan görüntüleyebilir ve Arşiv’e dosya yükleyebilirsiniz.")

    # --- Klasör ID'leri (görüntüleme) ---
    DRIVE_FOLDER_IDS = {
        "Genel Medya Klasörü": "1gFAaK-6v1e3346e-W0TsizOqSq43vHLY",
        "Ürün Görselleri":      "18NNlmadm5NNFkI1Amzt_YMwB53j6AmbD",
        "Kalite Evrakları":     "1pbArzYfA4Tp50zvdyTzSPF2ThrMWrGJc",
        "Arşiv":                "1uXq2OZxQaAT_dRoRCUa3w3BioudJ5m5A",  # <- sizin arşiv klasör ID
    }

    def embed_url(folder_id: str) -> str:
        return f"https://drive.google.com/embeddedfolderview?id={folder_id}#list"

    def open_url(folder_id: str) -> str:
        return f"https://drive.google.com/drive/folders/{folder_id}?usp=sharing"

    # --- Yardımcılar (yükleme için) ---
    try:
        _ = _guess_mime_by_ext  # projede zaten varsa kullan
    except NameError:
        def _guess_mime_by_ext(filename: str) -> str:
            ext = os.path.splitext(filename.lower())[1]
            return {
                ".pdf":  "application/pdf",
                ".jpg":  "image/jpeg",
                ".jpeg": "image/jpeg",
                ".png":  "image/png",
                ".webp": "image/webp",
                ".csv":  "text/csv",
                ".xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                ".xls":  "application/vnd.ms-excel",
                ".txt":  "text/plain",
            }.get(ext, "application/octet-stream")

    try:
        _ = _sanitize_filename
    except NameError:
        def _sanitize_filename(name: str) -> str:
            keep = "-_.() "
            s = "".join(ch if ch.isalnum() or ch in keep else "_" for ch in str(name))
            return s[:180] if s else "dosya"

    # Klasördeki mevcut dosya adlarını çek (duplike kontrolü için)
    def _list_file_names_in_folder(folder_id: str) -> set[str]:
        names = set()
        page_token = None
        while True:
            resp = drive_service.files().list(
                q=f"'{folder_id}' in parents and trashed = false",
                fields="nextPageToken, files(id, name)",
                supportsAllDrives=True,
                includeItemsFromAllDrives=True,
                corpora="allDrives",
                pageSize=1000,
                pageToken=page_token
            ).execute()
            for f in resp.get("files", []):
                names.add(f["name"])
            page_token = resp.get("nextPageToken")
            if not page_token:
                break
        return names

    # --- Gömülü görünüm yüksekliği ---
    h = st.slider("Gömülü görünüm yüksekliği (px)", min_value=450, max_value=900, value=600, step=50)

    # Sekmeler
    tab_names = list(DRIVE_FOLDER_IDS.keys())
    tabs = st.tabs(tab_names)

    for tab, tab_name in zip(tabs, tab_names):
        with tab:
            fid = DRIVE_FOLDER_IDS[tab_name]

            # Gömülü liste + hızlı link
            st.markdown(
                f"""
                <iframe src="{embed_url(fid)}"
                        width="100%" height="{h}" frameborder="0"
                        style="border:1px solid #eee; border-radius:12px; margin-top:10px;"></iframe>
                """,
                unsafe_allow_html=True
            )
            col_a, col_b = st.columns([1, 2])
            with col_a:
                st.link_button("🔗 Klasörü yeni sekmede aç", open_url(fid))
            with col_b:
                st.caption("Gömülü listeden dosyaları görüntüleyebilirsiniz.")

            # --- SADECE ARŞİV TABINDA YÜKLEME ---
            if tab_name == "Arşiv":
                st.markdown("#### 📤 Arşive Dosya Ekle")
                st.caption("Aşağıdan bir veya daha fazla dosya seçip yükleyebilirsiniz. Aynı isimli dosyalar atlanır.")

                uploads = st.file_uploader(
                    "Dosyaları seçin",
                    type=["pdf", "jpg", "jpeg", "png", "webp", "txt", "csv", "xlsx"],
                    accept_multiple_files=True
                )

                if uploads:
                    import tempfile
                    from googleapiclient.http import MediaFileUpload

                    # Klasördeki mevcut adlar (duplike isim skip)
                    mevcut_isimler = _list_file_names_in_folder(fid)

                    yuklenen = 0
                    atlanan = 0
                    detay_links = []

                    for up in uploads:
                        # Güvenli dosya adı
                        clean_name = _sanitize_filename(up.name)
                        if clean_name in mevcut_isimler:
                            atlanan += 1
                            continue

                        # Geçici dosyaya yaz
                        suffix = os.path.splitext(clean_name)[1] or ""
                        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as fp:
                            fp.write(up.read())
                            temp_path = fp.name

                        try:
                            media = MediaFileUpload(temp_path, mimetype=_guess_mime_by_ext(clean_name), resumable=False)
                            meta = {"name": clean_name, "parents": [fid]}
                            created = drive_service.files().create(
                                body=meta,
                                media_body=media,
                                fields="id",
                                supportsAllDrives=True
                            ).execute()
                            file_id = created["id"]

                            # İsteğe bağlı: herkese görüntüleme izni (gömülü zaten gösteriyor ama link için faydalı)
                            try:
                                drive_service.permissions().create(
                                    fileId=file_id,
                                    body={"role": "reader", "type": "anyone"},
                                    fields="id"
                                ).execute()
                            except Exception:
                                pass

                            detay_links.append(f"https://drive.google.com/file/d/{file_id}/view?usp=sharing")
                            mevcut_isimler.add(clean_name)
                            yuklenen += 1
                        finally:
                            try:
                                os.remove(temp_path)
                            except Exception:
                                pass

                    if yuklenen:
                        st.success(f"{yuklenen} dosya yüklendi.")
                        if detay_links:
                            for url in detay_links[:10]:
                                st.write(f"• {url}")
                            if len(detay_links) > 10:
                                st.write("…")
                        # Görünümü yenilemek isterseniz kullanıcıya sayfayı yeniden yükletin
                        st.caption("İpucu: Gömülü listeyi yenilemek için sayfayı yeniden yükleyebilirsiniz.")
                    if atlanan:
                        st.warning(f"{atlanan} dosya aynı isimde mevcut olduğu için atlandı.")

### ===========================
### --- SATIŞ PERFORMANSI MENÜSÜ ---
### ===========================

elif menu == "Satış Performansı":
    st.markdown("<h2 style='color:#219A41; font-weight:bold;'>Satış Performansı</h2>", unsafe_allow_html=True)

    # --- Akıllı sayı dönüştürücü ---
    def smart_to_num(x):
        if pd.isna(x): return 0.0
        s = str(x).strip()
        for sym in ["USD", "$", "€", "EUR", "₺", "TL", "tl", "Tl"]:
            s = s.replace(sym, "")
        s = s.replace("\u00A0", "").replace(" ", "")
        # 1) Doğrudan parse (US)
        try: return float(s)
        except: pass
        # 2) Avrupa formatı
        if "," in s:
            try: return float(s.replace(".", "").replace(",", "."))
            except: pass
        return 0.0

    # ---- Kolon güvenliği ----
    if "Tutar" not in df_evrak.columns:
        df_evrak["Tutar"] = 0
    date_col = "Fatura Tarihi" if "Fatura Tarihi" in df_evrak.columns else "Tarih"
    if date_col not in df_evrak.columns:
        df_evrak[date_col] = pd.NaT

    # ---- Tip dönüşümleri ----
    df_evrak = df_evrak.copy()
    df_evrak["Tutar_num"] = df_evrak["Tutar"].apply(smart_to_num).fillna(0.0)
    df_evrak[date_col] = pd.to_datetime(df_evrak[date_col], errors="coerce")
    df_evrak = df_evrak[df_evrak[date_col].notna()]  # geçersiz tarihleri at

    # ---- Toplamlar ----
    toplam_fatura = float(df_evrak["Tutar_num"].sum())
    st.markdown(f"<div style='font-size:1.3em; color:#185a9d; font-weight:bold;'>💵 Toplam Fatura Tutarı: {toplam_fatura:,.2f} USD</div>", unsafe_allow_html=True)

    # ---- Tarih aralığı filtresi (Timestamp ile) ----
    min_ts = df_evrak[date_col].min()
    max_ts = df_evrak[date_col].max()
    d1, d2 = st.date_input("📅 Tarih Aralığı", value=(min_ts.date(), max_ts.date()))

    start_ts = pd.to_datetime(d1)  # 00:00
    end_ts   = pd.to_datetime(d2) + pd.Timedelta(days=1) - pd.Timedelta(milliseconds=1)  # gün sonu

    mask = df_evrak[date_col].between(start_ts, end_ts, inclusive="both")
    df_range = df_evrak[mask]

    aralik_toplam = float(df_range["Tutar_num"].sum())
    st.markdown(f"<div style='font-size:1.2em; color:#f7971e; font-weight:bold;'>📊 {d1} - {d2} Arası Toplam: {aralik_toplam:,.2f} USD</div>", unsafe_allow_html=True)

    # ---- Detay tablo ----
    show_cols = ["Müşteri Adı", "Fatura No", date_col, "Tutar"]
    show_cols = [c for c in show_cols if c in df_range.columns]
    st.dataframe(df_range[show_cols].sort_values(by=date_col, ascending=False), use_container_width=True)

with st.expander("🔎 Google Sheets Bağlantı Testi", expanded=False):
    try:
        resp = sheet.values().get(spreadsheetId=SHEET_ID, range="Sayfa1!A1:Z5").execute()
        st.write("Sayfa1 ilk satırlar:", resp.get("values", []))
    except Exception as e:
        st.error(f"Sheets erişim hatası: {e}")
