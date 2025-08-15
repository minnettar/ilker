import streamlit as st
import pandas as pd
import numpy as np
import gspread
import datetime
import io
import json
import os
import re
import smtplib
import sqlite3
import tempfile
import time
from gspread_dataframe import set_with_dataframe
from google.oauth2.service_account import Credentials as _SA_Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload
from oauth2client.service_account import ServiceAccountCredentials
from pydrive2.auth import GoogleAuth
from pydrive2.drive import GoogleDrive
from email.message import EmailMessage
from typing import Any, Dict, List, Optional, Tuple, Tuple
import pandas as pd
import pandas as _pd

# === Lazy Google Drive init helpers ===
@st.cache_resource(show_spinner=False)
def get_drive_or_none():
    """Return Drive client or None without raising UI warnings."""
    try:
        return get_drive()  # your Service Account-based function
    except Exception:
        return None

def ensure_drive():
    """Initialize Drive client on demand; returns None if unavailable."""
    key = "__drive_client__"
    if key not in st.session_state:
        st.session_state[key] = get_drive_or_none()
    return st.session_state[key]
# === /Lazy helpers ===


SHEET_ID = "1A_gL11UL6JFAoZrMrg92K8bAegeCn_KzwUyU8AWzE_0"

# =============================
# === CRM ILKER: Revizyon 1 ===
# === Güvenli erişim & yardımcılar
# =============================


# ---- Google Service Account ile Drive & Sheets istemcileri ----
try:


    _HAS_GSPREAD = True
except Exception:
    _HAS_GSPREAD = False
    _SA_Credentials = None

_SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]

def _get_sa_info() -> dict:
    """st.secrets['gcp_service_account'] içeriğini döndürür; yoksa KeyError."""
    return dict(st.secrets.get("gcp_service_account", {}))

@st.cache_resource(show_spinner=False)
def get_drive_client():
    """PyDrive2 için GoogleDrive istemcisi (Service Account) üretir."""
    sa_info = _get_sa_info()
    if not sa_info:
        raise RuntimeError("Service Account bilgisi bulunamadı: st.secrets['gcp_service_account']")

    credentials = _LegacySA.from_json_keyfile_dict(sa_info, scopes=_SCOPES)
    gauth = GoogleAuth()
    gauth.credentials = credentials
    drive_client = GoogleDrive(gauth)
    return drive_client

@st.cache_resource(show_spinner=False)
def get_gspread_client():
    """Varsa gspread istemcisi döndürür; yoksa None."""
    if not _HAS_GSPREAD or _SA_Credentials is None:
        return None
    sa_info = _get_sa_info()
    creds = _SA_Credentials.from_service_account_info(sa_info, scopes=_SCOPES)
    return gspread.authorize(creds)

# ---- Cache yardımcıları ----
def cache_data(ttl: int = 300):
    """Kısa yol: @cache_data(ttl=300)."""
    return st.cache_data(ttl=ttl, show_spinner=False)

def cache_resource():
    """Kısa yol: @cache_resource."""
    return st.cache_resource(show_spinner=False)

# ---- Tarih & Para yardımcıları ----


def parse_date(s: Any) -> Optional[_pd.Timestamp]:
    try:
        return _pd.to_datetime(s)
    except Exception:
        return None

def parse_money(x: Any) -> float:
    if x is None:
        return 0.0
    if isinstance(x, (int, float)):
        return float(x)
    s = str(x).replace(".", "").replace(" ", "").replace("₺", "").replace("$", "").replace("€", "")
    s = s.replace(",", ".")
    try:
        return float(s)
    except Exception:
        return 0.0

def fmt_money(x: float, suffix: str = " USD") -> str:
    try:
        return f"{float(x):,.2f}{suffix}"
    except Exception:
        return f"{x}{suffix}"

# ---- UI yardımcıları ----
def confirm_modal(key: str, title: str, text: str) -> bool:
    """Kritik işlemler için onay modalı. True dönerse onaylanmış demektir."""
    opened = st.session_state.get(f"__modal_open_{key}", False)
    if st.button(title, key=f"btn_open_{key}"):
        st.session_state[f"__modal_open_{key}"] = True
        opened = True
    if opened:
        with st.modal(title):
            st.write(text)
            c1, c2 = st.columns(2)
            ok = c1.button("Onayla", key=f"ok_{key}")
            cancel = c2.button("Vazgeç", key=f"cancel_{key}")
            if ok:
                st.session_state[f"__modal_open_{key}"] = False
                return True
            if cancel:
                st.session_state[f"__modal_open_{key}"] = False
                return False
    return False

# ---- Global drive nesnesi (yoksa) ----
try:
    _ = drive  # mevcutsa dokunma
except NameError:
    try:
        drive = get_drive_client()
    except Exception as e:
        st.warning("Google Drive istemcisi oluşturulamadı. st.secrets ayarlarınızı kontrol edin.")
        drive = None
# ===========================

# ---- Ana Sheet erişim yardımcıları ----


@st.cache_resource(show_spinner=False)
def open_main_sheet():
    """
    Ana Google Sheet'i açar.
    Öncelik: secrets.app.sheet_id -> yoksa kod içindeki SHEET_ID sabiti.
    """
    try:
        sheet_id = (st.secrets.get("app", {}).get("sheet_id", "") or SHEET_ID).strip()
    except Exception:
        sheet_id = SHEET_ID
    if not sheet_id:
        st.error("Ana Sheet ID tanımlı değil. secrets.app.sheet_id girin veya SHEET_ID sabitini doldurun.")
        st.stop()
    gc = get_gspread_client()
    if gc is None:
        st.error("gspread istemcisi oluşturulamadı. Google Service Account ayarlarını kontrol edin.")
        st.stop()
    try:
        return gc.open_by_key(sheet_id)
    except Exception as e:
        st.error(f"Ana Sheet açılamadı: {e}")
        st.stop()


@st.cache_data(ttl=300, show_spinner=False)
def load_ws(ws_name: str) -> pd.DataFrame:
    """Ana Sheet içindeki bir çalışma sayfasını DataFrame olarak döndürür."""
    sh = open_main_sheet()
    try:
        ws = sh.worksheet(ws_name)
    except Exception as e:
        st.error(f"Çalışma sayfası bulunamadı: {ws_name} - {e}")
        return pd.DataFrame()
    rows = ws.get_all_records()
    return pd.DataFrame(rows)

# === /Revizyon 1 bloğu ===
# ===========================

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

LOGO_FILE_ID = "1DCxtSsAeR7Zfk2IQU0UMGmD0uTdNO1B3"
LOGO_LOCAL_NAME = "logo1.png"
EXCEL_FILE_ID = '1IF6CN4oHEMk6IEE40ZGixPkfnNHLYXnQ'
EVRAK_KLASOR_ID = '14FTE1oSeIeJ6Y_7C0oQyZPKC8dK8hr1J'
FIYAT_TEKLIFI_ID = '1TNjwx-xhmlxNRI3ggCJA7jaCAu9Lt_65'



# --- PyDrive2 + Service Account (Streamlit Cloud uyumlu) ---



_SCOPES = [
    "https://www.googleapis.com/auth/drive",
    "https://www.googleapis.com/auth/spreadsheets",
]


SCOPES = [
    "https://www.googleapis.com/auth/drive",
    "https://www.googleapis.com/auth/spreadsheets",
]

@st.cache_resource(show_spinner=False)
def get_drive():
    """Google Drive istemcisi (Service Account)."""
    sa_info = dict(st.secrets["gcp_service_account"])
    creds = ServiceAccountCredentials.from_json_keyfile_dict(sa_info, scopes=SCOPES)
    gauth = GoogleAuth()
    gauth.credentials = creds
    return GoogleDrive(gauth)


# INIT REMOVED: lazy initialization will be used


# drive = get_drive()

if not os.path.exists(LOGO_LOCAL_NAME):
    logo_file = drive.CreateFile({'id': LOGO_FILE_ID})
    logo_file.GetContentFile(LOGO_LOCAL_NAME)

col1, col2 = st.columns([3, 7])
with col1:
    st.image(LOGO_LOCAL_NAME, width=300)
with col2:
 st.markdown("""
    <style>
    .block-container { padding-top: 0.2rem !important; }
    </style>
    <div style="display:flex; flex-direction:column; align-items:flex-start; width:100%; margin-bottom:10px;">
        <h1 style="color: #219A41; font-weight: bold; font-size: 2.8em; letter-spacing:2px; margin:0; margin-top:-8px;">
            ŞEKEROĞLU İHRACAT CRM
        </h1>
    </div>
""", unsafe_allow_html=True)

downloaded = drive.CreateFile({'id': EXCEL_FILE_ID})
downloaded.FetchMetadata(fetch_all=True)
downloaded.GetContentFile("temp.xlsx")

# --- Dataframe yükleme ---
if os.path.exists("temp.xlsx"):
    try:
        df_musteri = pd.read_excel("temp.xlsx", sheet_name=0)
    except Exception:
        df_musteri = pd.DataFrame(columns=[
            "Müşteri Adı", "Telefon", "E-posta", "Adres", "Ülke", "Satış Temsilcisi", "Kategori", "Durum", "Vade (Gün)", "Ödeme Şekli"
        ])
    try:
        df_kayit = pd.read_excel("temp.xlsx", sheet_name="Kayıtlar")
    except Exception:
        df_kayit = pd.DataFrame(columns=["Müşteri Adı", "Tarih", "Tip", "Açıklama"])
    try:
        df_teklif = pd.read_excel("temp.xlsx", sheet_name="Teklifler")
    except Exception:
        df_teklif = pd.DataFrame(columns=[
            "Müşteri Adı", "Tarih", "Teklif No", "Tutar", "Ürün/Hizmet", "Açıklama", "Durum", "PDF"
        ])
    try:
        df_proforma = pd.read_excel("temp.xlsx", sheet_name="Proformalar")
        for col in ["Proforma No", "Vade", "Sevk Durumu"]:
            if col not in df_proforma.columns:
                df_proforma[col] = ""
    except Exception:
        df_proforma = pd.DataFrame(columns=[
            "Müşteri Adı", "Tarih", "Proforma No", "Tutar", "Açıklama", "Durum", "PDF", "Sipariş Formu", "Vade", "Sevk Durumu"
        ])
    try:
        df_evrak = pd.read_excel("temp.xlsx", sheet_name="Evraklar")
        for col in ["Yük Resimleri", "EK Belgeler"]:
            if col not in df_evrak.columns:
                df_evrak[col] = ""
    except Exception:
        df_evrak = pd.DataFrame(columns=[
            "Müşteri Adı", "Fatura No", "Fatura Tarihi", "Vade Tarihi", "Tutar",
            "Commercial Invoice", "Sağlık Sertifikası", "Packing List",
            "Konşimento", "İhracat Beyannamesi", "Fatura PDF", "Sipariş Formu",
            "Yük Resimleri", "EK Belgeler"
        ])
    try:
        df_eta = pd.read_excel("temp.xlsx", sheet_name="ETA")
    except Exception:
        df_eta = pd.DataFrame(columns=["Müşteri Adı", "Proforma No", "ETA Tarihi", "Açıklama"])
    try:
        df_fuar_musteri = pd.read_excel("temp.xlsx", sheet_name="FuarMusteri")
    except Exception:
        df_fuar_musteri = pd.DataFrame(columns=[
            "Fuar Adı", "Müşteri Adı", "Ülke", "Telefon", "E-mail", "Açıklamalar", "Tarih"
        ])
else:
    df_musteri = pd.DataFrame(columns=[
        "Müşteri Adı", "Telefon", "E-posta", "Adres", "Ülke", "Satış Temsilcisi", "Kategori", "Durum", "Vade (Gün)", "Ödeme Şekli"
    ])
    df_kayit = pd.DataFrame(columns=["Müşteri Adı", "Tarih", "Tip", "Açıklama"])
    df_teklif = pd.DataFrame(columns=[
        "Müşteri Adı", "Tarih", "Teklif No", "Tutar", "Ürün/Hizmet", "Açıklama", "Durum", "PDF"
    ])
    df_proforma = pd.DataFrame(columns=[
        "Müşteri Adı", "Tarih", "Proforma No", "Tutar", "Açıklama", "Durum", "PDF", "Sipariş Formu", "Vade", "Sevk Durumu"
    ])
    df_evrak = pd.DataFrame(columns=[
        "Müşteri Adı", "Fatura No", "Fatura Tarihi", "Vade Tarihi", "Tutar",
        "Commercial Invoice", "Sağlık Sertifikası", "Packing List",
        "Konşimento", "İhracat Beyannamesi", "Fatura PDF", "Sipariş Formu",
        "Yük Resimleri", "EK Belgeler"
    ])
    df_eta = pd.DataFrame(columns=["Müşteri Adı", "Proforma No", "ETA Tarihi", "Açıklama"])
    df_fuar_musteri = pd.DataFrame(columns=[
        "Fuar Adı", "Müşteri Adı", "Ülke", "Telefon", "E-mail", "Açıklamalar", "Tarih"
    ])

def update_excel():
    buffer = io.BytesIO()
    with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
        df_musteri.to_excel(writer, sheet_name="Sayfa1", index=False)
        df_kayit.to_excel(writer, sheet_name="Kayıtlar", index=False)
        df_teklif.to_excel(writer, sheet_name="Teklifler", index=False)
        df_proforma.to_excel(writer, sheet_name="Proformalar", index=False)
        df_evrak.to_excel(writer, sheet_name="Evraklar", index=False)
        df_eta.to_excel(writer, sheet_name="ETA", index=False)
        df_fuar_musteri.to_excel(writer, sheet_name="FuarMusteri", index=False)
    buffer.seek(0)
    with open("temp.xlsx", "wb") as f:
        f.write(buffer.read())
    downloaded.SetContentFile("temp.xlsx")
    downloaded.Upload()

# ========= ŞIK SIDEBAR MENÜ (RADIO TABANLI) =========

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
    sel_label = st.session_state.menu_radio_label
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


# Yeni cari için txt dosyasını oluşturma fonksiyonu
def yeni_cari_txt_olustur(cari_dict, file_path="yeni_cari.txt"):
    with open(file_path, "w", encoding="utf-8") as f:
        f.write(
            f"Müşteri Adı: {cari_dict['Müşteri Adı']}\n"
            f"Telefon: {cari_dict['Telefon']}\n"
            f"E-posta: {cari_dict['E-posta']}\n"
            f"Adres: {cari_dict['Adres']}\n"
            f"Ülke: {cari_dict.get('Ülke', '')}\n"
            f"Satış Temsilcisi: {cari_dict.get('Satış Temsilcisi', '')}\n"
            f"Kategori: {cari_dict.get('Kategori', '')}\n"
            f"Durum: {cari_dict.get('Durum', '')}\n"
            f"Vade (Gün): {cari_dict.get('Vade (Gün)', '')}\n"
            f"Ödeme Şekli: {cari_dict.get('Ödeme Şekli', '')}\n"
            f"Para Birimi: {cari_dict.get('Para Birimi', '')}\n"  # Para birimini de ekliyoruz
            f"DT Seçimi: {cari_dict.get('DT Seçimi', '')}\n"  # DT seçimini de ekliyoruz
        )

# E-posta göndermek için fonksiyon
def send_email_with_txt(to_email, subject, body, file_path):
    from_email = "todo@sekeroglugroup.com"  # Gönderen e-posta adresi
    password = "vbgvforwwbcpzhxf"  # Gönderen e-posta şifresi

    # E-posta mesajını oluştur
    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = from_email
    msg["To"] = ", ".join(to_email)  # Birden fazla alıcıyı virgülle ayırarak ekliyoruz
    msg.set_content(body)

    # TXT dosyasını e-postaya ekle
    with open(file_path, "rb") as f:
        msg.add_attachment(
            f.read(),
            maintype="text",
            subtype="plain",
            filename="yeni_cari.txt"  # Dosyanın ismi
        )

    # E-posta göndermek için SMTP kullan
    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as smtp:
        smtp.login(from_email, password)
        smtp.send_message(msg)

# ===========================
# --- ÖZET EKRAN (Vade herkese açık) ---
# ===========================

if menu == "Özet Ekran":
    st.markdown("<h2 style='color:#219A41; font-weight:bold;'>📊 Özet Ekran</h2>", unsafe_allow_html=True)

    # --- Akıllı sayı dönüştürücü (USD/EUR/TL, . , ) ---
    def smart_to_num(x):
        if pd.isna(x): 
            return 0.0
        s = str(x).strip()
        for sym in ["USD", "$", "€", "EUR", "₺", "TL", "tl", "Tl"]:
            s = s.replace(sym, "")
        s = s.replace("\u00A0", "").replace(" ", "")
        try:
            return float(s)              # US format
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
    if "Tutar" in df_evrak.columns and not df_evrak.empty:
        _ev = df_evrak.copy()
        _ev["Tutar_num"] = _ev["Tutar"].apply(smart_to_num).fillna(0.0)
        toplam_fatura_tutar = float(_ev["Tutar_num"].sum())
    st.markdown(f"<div style='font-size:1.4em; color:#B22222; font-weight:bold;'>💰 Toplam Fatura Tutarı: {toplam_fatura_tutar:,.2f} USD</div>", unsafe_allow_html=True)

    st.markdown("---")

    # ---------- VADE DURUMU (HERKESE AÇIK) ----------
    # Kolon güvenliği
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
    m_bugun     = (vade_df_all["Vade Tarihi"].dt.date == today_norm.date()) & od_me
    m_gecikmis  = (vade_df_all["Vade Tarihi"] < today_norm) & od_me

    sum_gelmemis = float(vade_df_all.loc[m_gelmemis, "Tutar_num"].sum())
    sum_bugun    = float(vade_df_all.loc[m_bugun,    "Tutar_num"].sum())
    sum_gecikmis = float(vade_df_all.loc[m_gecikmis, "Tutar_num"].sum())

    c1, c2, c3 = st.columns(3)
    c1.metric("📅 Vadesi Gelmemiş", f"{sum_gelmemis:,.2f} USD", f"{int(m_gelmemis.sum())} Fatura")
    c2.metric("⚠️ Bugün Vadesi Dolan", f"{sum_bugun:,.2f} USD", f"{int(m_bugun.sum())} Fatura")
    c3.metric("⛔ Gecikmiş", f"{sum_gecikmis:,.2f} USD", f"{int(m_gecikmis.sum())} Fatura")

    # Açık vade listesi (ödenmemiş)
    acik_vadeler = vade_df_all[vade_df_all["Vade Tarihi"].notna() & (~vade_df_all["Ödendi"])].copy()
    if not acik_vadeler.empty:
        acik_vadeler["Kalan Gün"] = (acik_vadeler["Vade Tarihi"] - today_norm).dt.days
        st.markdown("#### 💸 Açık Vade Kayıtları")
        cols_show = ["Müşteri Adı", "Ülke", "Fatura No", "Vade Tarihi", "Tutar", "Kalan Gün"]
        cols_show = [c for c in cols_show if c in acik_vadeler.columns]
        # Tarih güzel format
        if "Vade Tarihi" in cols_show:
            acik_vadeler["Vade Tarihi"] = pd.to_datetime(acik_vadeler["Vade Tarihi"], errors="coerce").dt.strftime("%d/%m/%Y")
        st.dataframe(acik_vadeler[cols_show].sort_values("Kalan Gün"), use_container_width=True)
    else:
        st.info("Açık vade kaydı yok.")

    st.markdown("---")

    # ---------- Bekleyen Teklifler ----------
    st.markdown("### 💰 Bekleyen Teklifler")
    bekleyen_teklifler = df_teklif[df_teklif["Durum"] == "Açık"] if "Durum" in df_teklif.columns else pd.DataFrame()
    try:
        toplam_teklif = pd.to_numeric(bekleyen_teklifler["Tutar"], errors="coerce").sum()
    except Exception:
        toplam_teklif = 0
    st.markdown(f"<div style='font-size:1.1em; color:#11998e; font-weight:bold;'>Toplam: {toplam_teklif:,.2f} $</div>", unsafe_allow_html=True)
    if bekleyen_teklifler.empty:
        st.info("Bekleyen teklif yok.")
    else:
        st.dataframe(
            bekleyen_teklifler[["Müşteri Adı", "Tarih", "Teklif No", "Tutar", "Ürün/Hizmet", "Açıklama"]],
            use_container_width=True
        )

    # ---------- Bekleyen Proformalar ----------
    st.markdown("### 📄 Bekleyen Proformalar")
    bekleyen_proformalar = df_proforma[df_proforma["Durum"] == "Beklemede"] if "Durum" in df_proforma.columns else pd.DataFrame()
    try:
        toplam_proforma = pd.to_numeric(bekleyen_proformalar["Tutar"], errors="coerce").sum()
    except Exception:
        toplam_proforma = 0
    st.markdown(f"<div style='font-size:1.1em; color:#f7971e; font-weight:bold;'>Toplam: {toplam_proforma:,.2f} $</div>", unsafe_allow_html=True)
    if bekleyen_proformalar.empty:
        st.info("Bekleyen proforma yok.")
    else:
        st.dataframe(
            bekleyen_proformalar[["Müşteri Adı", "Proforma No", "Tarih", "Tutar", "Vade (gün)", "Açıklama"]],
            use_container_width=True
        )

    # ---------- Sevk Bekleyen (Termin dahil) ----------
    st.markdown("### 🚚 Siparişe Dönüşen (Sevk Bekleyen) Siparişler")
    for col in ["Sevk Durumu", "Ülke", "Termin Tarihi"]:
        if col not in df_proforma.columns:
            df_proforma[col] = ""
    sevk_bekleyenler = df_proforma[
        (df_proforma["Durum"] == "Siparişe Dönüştü") &
        (~df_proforma["Sevk Durumu"].isin(["Sevkedildi", "Ulaşıldı"]))
    ] if "Durum" in df_proforma.columns else pd.DataFrame()
    try:
        toplam_siparis = pd.to_numeric(sevk_bekleyenler["Tutar"], errors="coerce").sum()
    except Exception:
        toplam_siparis = 0
    st.markdown(f"<div style='font-size:1.1em; color:#185a9d; font-weight:bold;'>Toplam: {toplam_siparis:,.2f} $</div>", unsafe_allow_html=True)

    if sevk_bekleyenler.empty:
        st.info("Sevk bekleyen sipariş yok.")
    else:
        disp = sevk_bekleyenler.copy()
        disp["Tarih"] = pd.to_datetime(disp["Tarih"], errors="coerce").dt.strftime("%d/%m/%Y")
        disp["Termin Tarihi"] = pd.to_datetime(disp["Termin Tarihi"], errors="coerce").dt.strftime("%d/%m/%Y")
        st.dataframe(
            disp[["Müşteri Adı", "Ülke", "Proforma No", "Tarih", "Termin Tarihi", "Tutar", "Vade (gün)", "Açıklama"]],
            use_container_width=True
        )

    # ---------- Yolda Olan (Sevkedildi) ----------
    st.markdown("### ⏳ Yolda Olan (ETA Takibi) Siparişler")
    eta_yolda = df_proforma[(df_proforma["Sevk Durumu"] == "Sevkedildi")] if "Sevk Durumu" in df_proforma.columns else pd.DataFrame()
    try:
        toplam_eta = pd.to_numeric(eta_yolda["Tutar"], errors="coerce").sum()
    except Exception:
        toplam_eta = 0
    st.markdown(f"<div style='font-size:1.1em; color:#c471f5; font-weight:bold;'>Toplam: {toplam_eta:,.2f} $</div>", unsafe_allow_html=True)
    if eta_yolda.empty:
        st.info("Yolda olan (sevk edilmiş) sipariş yok.")
    else:
        eta_disp = eta_yolda.copy()
        eta_disp["Tarih"] = pd.to_datetime(eta_disp["Tarih"], errors="coerce").dt.strftime("%d/%m/%Y")
        st.dataframe(
            eta_disp[["Müşteri Adı", "Ülke", "Proforma No", "Tarih", "Tutar", "Vade (gün)", "Açıklama"]],
            use_container_width=True
        )

    # ---------- Son Teslim Edilen 5 Sipariş ----------
    st.markdown("### ✅ Son Teslim Edilen (Ulaşıldı) 5 Sipariş")
    if "Sevk Durumu" in df_proforma.columns:
        teslim_edilenler = df_proforma[df_proforma["Sevk Durumu"] == "Ulaşıldı"]
        if not teslim_edilenler.empty:
            teslim_edilenler = teslim_edilenler.sort_values(by="Tarih", ascending=False).head(5).copy()
            teslim_edilenler["Tarih"] = pd.to_datetime(teslim_edilenler["Tarih"], errors="coerce").dt.strftime("%d/%m/%Y")
            st.dataframe(
                teslim_edilenler[["Müşteri Adı", "Ülke", "Proforma No", "Tarih", "Tutar", "Vade (gün)", "Açıklama"]],
                use_container_width=True
            )
        else:
            st.info("Teslim edilmiş sipariş yok.")
    else:
        st.info("Teslim edilmiş sipariş yok.")

    st.markdown("<hr>", unsafe_allow_html=True)
    st.info("Detay işlemler için soldaki menülerden ilgili bölümlere geçebilirsiniz.")




### ===========================
### === CARİ EKLEME MENÜSÜ ===
### ===========================

# Cari Ekleme Formu Güncelleme
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

        # Yeni Para Birimi Seçeneği Ekledik
        para_birimi = st.selectbox("Para Birimi", ["EURO", "USD", "TL", "RUBLE"])

        # Yeni DT Seçeneklerini Ekledik (DT-1, DT-2, DT-3, DT-4)
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
                    "Para Birimi": para_birimi,  # Para birimini ekliyoruz
                    "DT Seçimi": dt_secim  # DT seçimini ekliyoruz
                }
                df_musteri = pd.concat([df_musteri, pd.DataFrame([new_row])], ignore_index=True)
                update_excel()

                # Yeni cari için TXT oluştur ve maille gönder
                yeni_cari_txt_olustur(new_row)
                try:
                    send_email_with_txt(
                        to_email=["muhasebe@sekeroglugroup.com", "h.boy@sekeroglugroup.com"],  # Birden fazla alıcı ekledik
                        subject="Yeni Cari Açılışı",
                        body="Muhasebe için yeni cari açılışı ekte gönderilmiştir.",
                        file_path="yeni_cari.txt"
                    )
                    st.success("Müşteri eklendi ve e-posta ile muhasebeye gönderildi!")
                except Exception as e:
                    st.warning(f"Müşteri eklendi ama e-posta gönderilemedi: {e}")
                st.rerun()



                

### ===========================
### === MÜŞTERİ LİSTESİ MENÜSÜ ===
### ===========================

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
            ulke = st.selectbox("Ülke", ulke_listesi, index=ulke_listesi.index(df_musteri_sorted.at[sec_index, "Ülke"]) if df_musteri_sorted.at[sec_index, "Ülke"] in ulke_listesi else 0)
            temsilci = st.selectbox("Satış Temsilcisi", temsilci_listesi, index=temsilci_listesi.index(df_musteri_sorted.at[sec_index, "Satış Temsilcisi"]) if df_musteri_sorted.at[sec_index, "Satış Temsilcisi"] in temsilci_listesi else 0)
            kategori = st.selectbox(
                "Kategori", 
                sorted(["Avrupa bayi", "bayi", "müşteri", "yeni müşteri"]), 
                index=sorted(["Avrupa bayi", "bayi", "müşteri", "yeni müşteri"]).index(df_musteri_sorted.at[sec_index, "Kategori"])
                if df_musteri_sorted.at[sec_index, "Kategori"] in ["Avrupa bayi", "bayi", "müşteri", "yeni müşteri"] else 0
            )
            aktif_pasif = st.selectbox("Durum", ["Aktif", "Pasif"], index=0 if df_musteri_sorted.at[sec_index, "Durum"] == "Aktif" else 1)
            vade = st.text_input("Vade (Gün)", value=str(df_musteri_sorted.at[sec_index, "Vade (Gün)"]) if "Vade (Gün)" in df_musteri_sorted.columns else "")
            odeme_sekli = st.selectbox("Ödeme Şekli", ["Peşin", "Mal Mukabili", "Vesaik Mukabili", "Akreditif", "Diğer"], 
                                       index=["Peşin", "Mal Mukabili", "Vesaik Mukabili", "Akreditif", "Diğer"].index(df_musteri_sorted.at[sec_index, "Ödeme Şekli"]) if df_musteri_sorted.at[sec_index, "Ödeme Şekli"] in ["Peşin", "Mal Mukabili", "Vesaik Mukabili", "Akreditif", "Diğer"] else 0)
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
                    update_excel()
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
                update_excel()
                st.success("Müşteri kaydı silindi!")
                st.rerun()
            else:
                st.warning("Beklenmeyen hata: Silinecek kayıt bulunamadı.")
    else:
        st.markdown("<div style='color:#b00020; font-weight:bold; font-size:1.2em;'>Henüz müşteri kaydı yok.</div>", unsafe_allow_html=True)


### ===========================
### === GÖRÜŞME / ARAMA / ZİYARET KAYITLARI MENÜSÜ ===
### ===========================

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
                    update_excel()
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

    def güvenli_sil(dosya_adı, tekrar=5, bekle=1):
        for _ in range(tekrar):
            try:
                os.remove(dosya_adı)
                return True
            except PermissionError:
                time.sleep(bekle)
        return False

    st.subheader("Açık Pozisyondaki Teklifler Listesi")
    teklif_goster = df_teklif.copy()
    teklif_goster["Tarih"] = pd.to_datetime(teklif_goster["Tarih"]).dt.strftime("%d/%m/%Y")
    acik_teklifler = teklif_goster[teklif_goster["Durum"] == "Açık"].sort_values(by=["Müşteri Adı", "Teklif No"])
    acik_teklif_sayi = len(acik_teklifler)
    try:
        toplam_teklif = pd.to_numeric(acik_teklifler["Tutar"], errors="coerce").sum()
    except Exception:
        toplam_teklif = 0
    st.markdown(f"<div style='font-size:1.1em; color:#11998e; font-weight:bold;'>Toplam: {toplam_teklif:,.2f} $ | Toplam Açık Teklif: {acik_teklif_sayi} adet</div>", unsafe_allow_html=True)
    st.dataframe(acik_teklifler[[
        "Müşteri Adı", "Tarih", "Teklif No", "Tutar", "Ürün/Hizmet", "Açıklama"
    ]], use_container_width=True)

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

    # --- YENİ TEKLİF EKLEME FORMU ---
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
                    st.session_state['teklif_view'] = None  # formu kapat
                    st.rerun()

    # --- ESKİ TEKLİFLER: PROFORMA BENZERİ SEÇİMLİ ---
    if st.session_state['teklif_view'] == "eski":
        st.subheader("Eski Teklifler Listesi")

        # Müşteri seç
        eski_teklif_musteriler = df_teklif["Müşteri Adı"].dropna().unique().tolist()
        eski_teklif_musteriler = [""] + sorted(eski_teklif_musteriler)
        secili_musteri = st.selectbox("Müşteri Seçiniz", eski_teklif_musteriler, key="eski_teklif_musteri_sec")

        if secili_musteri:
            # Seçilen müşterinin teklifleri
            teklifler_bu_musteri = df_teklif[df_teklif["Müşteri Adı"] == secili_musteri].sort_values(by="Tarih", ascending=False)
            if teklifler_bu_musteri.empty:
                st.info("Bu müşteriye ait teklif kaydı yok.")
            else:
                # Teklifler arasında seçim için kombo
                teklif_index = st.selectbox(
                    "Teklif Seçiniz",
                    teklifler_bu_musteri.index,
                    format_func=lambda i: f"{teklifler_bu_musteri.at[i, 'Teklif No']} | {teklifler_bu_musteri.at[i, 'Tarih']}"
                )
                secilen_teklif = teklifler_bu_musteri.loc[teklif_index]

                # Teklif PDF varsa göster
                if secilen_teklif["PDF"]:
                    st.markdown(f"**Teklif PDF:** [{secilen_teklif['Teklif No']}]({secilen_teklif['PDF']})", unsafe_allow_html=True)
                else:
                    st.info("PDF bulunamadı.")

                # Tüm detayları göster
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

    # Eksik sütunları kontrol et
    for col in ["Vade (gün)", "Sipariş Formu", "Durum", "PDF", "Sevk Durumu", "Ülke", "Satış Temsilcisi", "Ödeme Şekli"]:
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
        
        if islem == "Yeni Kayıt":
            musteri_info = df_musteri[df_musteri["Müşteri Adı"] == musteri_sec]
            default_ulke = musteri_info["Ülke"].values[0] if not musteri_info.empty else ""
            default_temsilci = musteri_info["Satış Temsilcisi"].values[0] if not musteri_info.empty else ""
            default_odeme = musteri_info["Ödeme Şekli"].values[0] if not musteri_info.empty else ""

            with st.form("add_proforma"):
                tarih = st.date_input("Tarih", value=datetime.date.today())
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
                        if pdf_file:
                            pdf_filename = f"{musteri_sec}_{tarih}_{proforma_no}.pdf"
                            temp_path = os.path.join(".", pdf_filename)
                            with open(temp_path, "wb") as f:
                                f.write(pdf_file.read())
                            gfile = drive.CreateFile({'title': pdf_filename, 'parents': [{'id': "17lPkdYcC4BdowLdCsiWxiq0H_6oVGXLs"}]})
                            gfile.SetContentFile(temp_path)
                            gfile.Upload()
                            pdf_link = f"https://drive.google.com/file/d/{gfile['id']}/view?usp=sharing"
                            try: os.remove(temp_path)
                            except: pass
                        # Sipariş Formu ve Siparişe Dönüştü ayrı formla ekleniyor!
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
                    if kayit["PDF"]:
                        st.markdown(f"**Proforma PDF:** [{kayit['Proforma No']}]({kayit['PDF']})", unsafe_allow_html=True)

                    # Esas form sadece güncelleme ve silme için
                    with st.form("edit_proforma"):
                        tarih_ = st.date_input("Tarih", value=pd.to_datetime(kayit["Tarih"]).date())
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

                    # Siparişe Dönüştü ise ayrı form!
                    if durum_ == "Siparişe Dönüştü":
                        st.info("Lütfen sipariş formunu yükleyin ve ardından 'Sipariş Formunu Kaydet' butonuna basın.")
                        with st.form(f"siparis_formu_upload_{sec_index}"):
                            siparis_formu_file = st.file_uploader("Sipariş Formu PDF", type="pdf")
                            siparis_kaydet = st.form_submit_button("Sipariş Formunu Kaydet")

                        if siparis_kaydet:
                            if siparis_formu_file is None:
                                st.error("Sipariş formu yüklemelisiniz.")
                            else:
                                siparis_formu_fname = f"{musteri_sec}_{proforma_no_}_SiparisFormu_{datetime.datetime.now().strftime('%Y%m%d%H%M%S')}.pdf"
                                temp_path = os.path.join(".", siparis_formu_fname)
                                with open(temp_path, "wb") as f:
                                    f.write(siparis_formu_file.read())
                                gfile = drive.CreateFile({'title': siparis_formu_fname, 'parents': [{'id': "1xeTdhOE1Cc6ohJsRzPVlCMMraBIXWO9w"}]})
                                gfile.SetContentFile(temp_path)
                                gfile.Upload()
                                siparis_formu_url = f"https://drive.google.com/file/d/{gfile['id']}/view?usp=sharing"
                                try: os.remove(temp_path)
                                except: pass
                                # Hem sipariş formu hem durum burada güncellenir!
                                df_proforma.at[sec_index, "Sipariş Formu"] = siparis_formu_url
                                df_proforma.at[sec_index, "Durum"] = "Siparişe Dönüştü"
                                update_excel()
                                st.success("Sipariş formu kaydedildi ve durum güncellendi!")
                                st.rerun()

                    # Diğer alanlar için sadece güncelle!
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
    st.header("Güncel Sipariş Durumu")

    if "Sevk Durumu" not in df_proforma.columns:
        df_proforma["Sevk Durumu"] = ""
    if "Termin Tarihi" not in df_proforma.columns:
        df_proforma["Termin Tarihi"] = ""

    siparisler = df_proforma[
        (df_proforma["Durum"] == "Siparişe Dönüştü") & (~df_proforma["Sevk Durumu"].isin(["Sevkedildi", "Ulaşıldı"]))
    ].copy()

    for col in ["Termin Tarihi", "Sipariş Formu", "Ülke", "Satış Temsilcisi", "Ödeme Şekli"]:
        if col not in siparisler.columns:
            siparisler[col] = ""

    # ---- Termin Tarihi Sıralaması ----
    siparisler["Termin Tarihi Order"] = pd.to_datetime(siparisler["Termin Tarihi"], errors="coerce")
    siparisler = siparisler.sort_values("Termin Tarihi Order", ascending=True)

    if siparisler.empty:
        st.info("Henüz sevk edilmeyi bekleyen sipariş yok.")
    else:
        # Tarih formatlarını iyileştir
        siparisler["Tarih"] = pd.to_datetime(siparisler["Tarih"], errors="coerce").dt.strftime("%d/%m/%Y")
        siparisler["Termin Tarihi"] = pd.to_datetime(siparisler["Termin Tarihi"], errors="coerce").dt.strftime("%d/%m/%Y")

        tablo = siparisler[["Tarih", "Müşteri Adı", "Termin Tarihi", "Ülke", "Satış Temsilcisi", "Ödeme Şekli", "Proforma No", "Tutar", "Açıklama"]]
        st.markdown("<h4 style='color:#219A41; font-weight:bold;'>Tüm Siparişe Dönüşenler</h4>", unsafe_allow_html=True)
        st.dataframe(tablo, use_container_width=True)

        # Termin Tarihi Güncelleme
        st.markdown("#### Termin Tarihi Güncelle")
        sec_index = st.selectbox(
            "Termin Tarihi Girilecek Siparişi Seçin",
            options=siparisler.index,
            format_func=lambda i: f"{siparisler.at[i,'Müşteri Adı']} - {siparisler.at[i,'Proforma No']}"
        )
        mevcut_termin = df_proforma.at[sec_index, "Termin Tarihi"] if "Termin Tarihi" in df_proforma.columns else ""
        try:
            default_termin = pd.to_datetime(mevcut_termin, errors="coerce")
            if pd.isnull(default_termin):
                default_termin = datetime.date.today()
            else:
                default_termin = default_termin.date()
        except Exception:
            default_termin = datetime.date.today()

        yeni_termin = st.date_input("Termin Tarihi", value=default_termin, key="termin_input")
        if st.button("Termin Tarihini Kaydet"):
            df_proforma.at[sec_index, "Termin Tarihi"] = yeni_termin
            update_excel()
            st.success("Termin tarihi kaydedildi!")
            st.rerun()

        # Sevk Etme Butonu
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
            update_excel()
            st.success("Sipariş sevkedildi ve ETA takibine gönderildi!")
            st.rerun()

        # --- YENİ EKLENECEK: Siparişi Beklemeye Al (Geri Çağır) ---
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
            update_excel()
            st.success("Sipariş tekrar bekleyen proformalar listesine alındı!")
            st.rerun()

        # Altında PDF bağlantıları ve toplam tutar
        st.markdown("#### Tıklanabilir Proforma ve Sipariş Formu Linkleri")
        for i, row in siparisler.iterrows():
            links = []
            if pd.notnull(row["PDF"]) and row["PDF"]:
                links.append(f"[Proforma PDF: {row['Proforma No']}]({row['PDF']})")
            if pd.notnull(row["Sipariş Formu"]) and row["Sipariş Formu"]:
                fname = f"{row['Müşteri Adı']}__{row['Proforma No']}__SiparisFormu"
                links.append(f"[Sipariş Formu: {fname}]({row['Sipariş Formu']})")
            if links:
                st.markdown(" - " + " | ".join(links), unsafe_allow_html=True)

        try:
            toplam = pd.to_numeric(siparisler["Tutar"], errors="coerce").sum()
        except Exception:
            toplam = 0
        st.markdown(f"<div style='color:#219A41; font-weight:bold;'>*Toplam Bekleyen Sevk: {toplam:,.2f} $*</div>", unsafe_allow_html=True)

### ===========================
### --- FATURA & İHRACAT EVRAKLARI MENÜSÜ ---
### ===========================

elif menu == "Fatura & İhracat Evrakları":
    st.markdown("<h2 style='color:#219A41; font-weight:bold;'>Fatura & İhracat Evrakları</h2>", unsafe_allow_html=True)

    for col in [
        "Proforma No", "Vade (gün)", "Vade Tarihi", "Ülke", "Satış Temsilcisi", "Ödeme Şekli",
        "Commercial Invoice", "Sağlık Sertifikası", "Packing List",
        "Konşimento", "İhracat Beyannamesi", "Fatura PDF", "Sipariş Formu",
        "Yük Resimleri", "EK Belgeler", "Ödendi"
    ]:
        if col not in df_evrak.columns:
            df_evrak[col] = "" if col != "Ödendi" else False

    musteri_secenek = sorted(df_proforma["Müşteri Adı"].dropna().unique().tolist())
    secilen_musteri = st.selectbox("Müşteri Seç", [""] + musteri_secenek)
    secilen_proformalar = df_proforma[df_proforma["Müşteri Adı"] == secilen_musteri] if secilen_musteri else pd.DataFrame()
    proforma_no_sec = ""
    if not secilen_proformalar.empty:
        proforma_no_sec = st.selectbox("Proforma No Seç", [""] + secilen_proformalar["Proforma No"].astype(str).tolist())
    else:
        proforma_no_sec = st.selectbox("Proforma No Seç", [""])

    musteri_info = df_musteri[df_musteri["Müşteri Adı"] == secilen_musteri]
    ulke = musteri_info["Ülke"].values[0] if not musteri_info.empty else ""
    temsilci = musteri_info["Satış Temsilcisi"].values[0] if not musteri_info.empty else ""
    odeme = musteri_info["Ödeme Şekli"].values[0] if not musteri_info.empty else ""

    # --- 1. Önceki evrakların linklerini çek ---
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
        vade_gun = ""
        vade_tarihi = ""
        if secilen_musteri and proforma_no_sec:
            proforma_kayit = df_proforma[(df_proforma["Müşteri Adı"] == secilen_musteri) & (df_proforma["Proforma No"] == proforma_no_sec)]
            if not proforma_kayit.empty:
                vade_gun = proforma_kayit.iloc[0].get("Vade (gün)", "")
                try:
                    vade_gun_int = int(vade_gun)
                    vade_tarihi = fatura_tarih + datetime.timedelta(days=vade_gun_int)
                except:
                    vade_tarihi = ""
        st.text_input("Vade (gün)", value=vade_gun, key="vade_gun", disabled=True)
        st.date_input("Vade Tarihi", value=vade_tarihi if vade_tarihi else fatura_tarih, key="vade_tarihi", disabled=True)
        st.text_input("Ülke", value=ulke, disabled=True)
        st.text_input("Satış Temsilcisi", value=temsilci, disabled=True)
        st.text_input("Ödeme Şekli", value=odeme, disabled=True)
        
        # --- 2. Evrak yükleme alanları ve eski dosya linkleri ---
        uploaded_files = {}
        for col, label in evrak_tipleri:
            uploaded_files[col] = st.file_uploader(label, type="pdf", key=f"{col}_upload")
            prev_url = onceki_evrak.iloc[0][col] if not onceki_evrak.empty else ""
            st.markdown(file_link_html(label, prev_url), unsafe_allow_html=True)
        
        submitted = st.form_submit_button("Kaydet")

        if submitted:
            if not fatura_no.strip() or not tutar.strip():
                st.error("Fatura No ve Tutar boş olamaz!")
            else:
                # Dosya yükleme ve eski dosya kontrolü
                file_urls = {}
                for col, label in evrak_tipleri:
                    uploaded_file = uploaded_files[col]
                    # Önce yeni dosya yüklendiyse Drive'a yükle, yoksa eski dosya linkini al
                    if uploaded_file:
                        file_name = f"{col}_{datetime.datetime.now().strftime('%Y%m%d%H%M%S')}.pdf"
                        temp_path = os.path.join(".", file_name)
                        with open(temp_path, "wb") as f:
                            f.write(uploaded_file.read())
                        gfile = drive.CreateFile({'title': file_name, 'parents': [{'id': "14FTE1oSeIeJ6Y_7C0oQyZPKC8dK8hr1J"}]})
                        gfile.SetContentFile(temp_path)
                        gfile.Upload()
                        file_urls[col] = f"https://drive.google.com/file/d/{gfile['id']}/view?usp=sharing"
                        try:
                            os.remove(temp_path)
                        except:
                            pass
                    else:
                        file_urls[col] = onceki_evrak.iloc[0][col] if not onceki_evrak.empty else ""

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
                    "Fatura PDF": "",  # Gerekirse ekle
                    "Sipariş Formu": "",
                    "Yük Resimleri": "",
                    "EK Belgeler": "",
                    "Ödendi": False,
                }
                df_evrak = pd.concat([df_evrak, pd.DataFrame([new_row])], ignore_index=True)
                update_excel()
                st.success("Evrak eklendi!")
                st.rerun()

### ===========================
### --- VADE TAKİBİ MENÜSÜ ---
### ===========================

elif menu == "Vade Takibi":
    st.markdown("<h2 style='color:#219A41; font-weight:bold;'>Vade Takibi</h2>", unsafe_allow_html=True)

    # ==== Drive ayarları (ANA klasörünüz) ====

    ROOT_EXPORT_FOLDER_ID = "14FTE1oSeIeJ6Y_7C0oQyZPKC8dK8hr1J"  # İhracat evrakları ana klasör ID

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
            if lst: return lst[0]['id']
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

    # ==== Sütun güvenliği ====
    for col in ["Proforma No", "Vade (gün)", "Ödendi", "Ülke", "Satış Temsilcisi", "Ödeme Şekli",
                "Vade Tarihi", "Fatura No", "Müşteri Adı", "Ödeme Kanıtı"]:
        if col not in df_evrak.columns:
            df_evrak[col] = "" if col not in ["Ödendi"] else False

    df_evrak["Ödendi"] = df_evrak["Ödendi"].fillna(False).astype(bool)
    df_evrak["Vade Tarihi"] = pd.to_datetime(df_evrak["Vade Tarihi"], errors="coerce")

    today = pd.to_datetime(datetime.date.today())

    # Sadece ödenmemiş ve vadeli kayıtlar
    vade_df = df_evrak[df_evrak["Vade Tarihi"].notna() & (~df_evrak["Ödendi"])].reset_index()

    if vade_df.empty:
        st.info("Açık vade kaydı yok.")
    else:
        # Her satır için bilgi + ödeme kanıtı yükleme + Ödendi checkbox
        for i, row in vade_df.iterrows():
            kalan = (row["Vade Tarihi"] - today).days
            mesaj = (
                f"{row['Müşteri Adı']} | {row.get('Ülke','')} | {row.get('Satış Temsilcisi','')} "
                f"| Proforma No: {row.get('Proforma No','')} | Fatura No: {row['Fatura No']} "
                f"| Vade Tarihi: {row['Vade Tarihi'].date()} | Ödeme: {row.get('Ödeme Şekli','')}"
            )

            box = st.container(border=True)
            with box:
                if kalan == 1:
                    st.error(f"{mesaj} | **YARIN VADE DOLUYOR!**")
                elif kalan < 0:
                    st.warning(f"{mesaj} | **{abs(kalan)} gün GECİKTİ!**")
                else:
                    st.info(f"{mesaj} | {kalan} gün kaldı.")

                # Ödeme kanıtı uploader (çoklu format)
                kanit_file = st.file_uploader(
                    "Ödeme Kanıtı (PDF/JPG/PNG/JPEG/WEBP)",
                    type=["pdf", "jpg", "jpeg", "png", "webp"],
                    key=f"kanit_{i}"
                )

                # Daha önce yüklenmiş link varsa göster
                prev_link = row.get("Ödeme Kanıtı", "")
                if prev_link:
                    st.markdown(f"[Önceden yüklenmiş ödeme kanıtı]({prev_link})", unsafe_allow_html=True)

                tick = st.checkbox(
                    f"Ödendi olarak işaretle → {row['Müşteri Adı']} - Proforma No: {row.get('Proforma No','')} - Fatura No: {row['Fatura No']}",
                    key=f"odendi_{i}"
                )

                if tick:
                    # Kanıt zorunlu
                    if kanit_file is None and not prev_link:
                        st.error("Lütfen önce **Ödeme Kanıtı** dosyası yükleyin (PDF/JPG/PNG…).")
                    else:
                        # Eğer yeni dosya geldiyse Drive'a yükle
                        odeme_kaniti_url = prev_link
                        if kanit_file is not None:
                            if not ROOT_EXPORT_FOLDER_ID:
                                st.error("Ana klasör ID tanımlı değil; yükleme iptal edildi.")
                                st.stop()

                            cust_folder_id = get_or_create_customer_folder(row["Müşteri Adı"], ROOT_EXPORT_FOLDER_ID)
                            if not cust_folder_id:
                                st.error("Müşteri klasörü oluşturulamadı; yükleme iptal edildi.")
                                st.stop()

                            # Müşteri altında 'Odeme_Kanitlari' alt klasörü
                            kanit_folder_id = get_or_create_folder_by_name("Odeme_Kanitlari", cust_folder_id)
                            if not kanit_folder_id:
                                st.error("Ödeme kanıtı klasörü oluşturulamadı; yükleme iptal edildi.")
                                st.stop()

                            # Dosyayı geçici kaydet ve yükle
                            suffix = os.path.splitext(kanit_file.name)[1].lower() or ".pdf"
                            ts = datetime.datetime.now().strftime('%Y%m%d%H%M%S')
                            fname = safe_name(f"OdemeKaniti__{row['Müşteri Adı']}__{row.get('Proforma No','')}__{row['Fatura No']}__{ts}") + suffix

                            with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as fp:
                                fp.write(kanit_file.read())
                                temp_path = fp.name

                            meta = {
                                'title': fname,
                                'parents': [{'id': kanit_folder_id}],
                            }
                            gfile = drive.CreateFile(meta)
                            gfile.SetContentFile(temp_path)
                            try:
                                # supportsAllDrives => Shared Drive desteği
                                gfile.Upload(param={'supportsAllDrives': True})
                                odeme_kaniti_url = f"https://drive.google.com/file/d/{gfile['id']}/view?usp=sharing"
                            except Exception as e:
                                st.error(f"Ödeme kanıtı yüklenirken hata: {e}")
                            finally:
                                try: os.remove(temp_path)
                                except: pass

                        # Kayıt güncelle: kanıt linki + Ödendi = True
                        df_evrak.at[row['index'], "Ödeme Kanıtı"] = odeme_kaniti_url
                        df_evrak.at[row['index'], "Ödendi"] = True
                        update_excel()
                        st.success("Kayıt 'Ödendi' olarak işaretlendi ve ödeme kanıtı kaydedildi.")
                        st.rerun()

        st.markdown("#### Açık Vade Kayıtları")
        st.dataframe(
            df_evrak[
                df_evrak["Vade Tarihi"].notna() & (~df_evrak["Ödendi"])
            ][["Müşteri Adı", "Ülke", "Satış Temsilcisi", "Ödeme Şekli",
               "Proforma No", "Fatura No", "Fatura Tarihi", "Vade (gün)", "Vade Tarihi", "Tutar"]],
            use_container_width=True
        )



### ===========================
### --- ETA TAKİBİ MENÜSÜ ---
### ===========================
elif menu == "ETA Takibi":
    st.markdown("<h2 style='color:#219A41; font-weight:bold;'>ETA Takibi</h2>", unsafe_allow_html=True)

    # ---- Sabitler ----
    ROOT_EXPORT_FOLDER_ID = "14FTE1oSeIeJ6Y_7C0oQyZPKC8dK8hr1J"  # İhracat Evrakları ana klasör ID

    # ---- Güvenlik: gerekli kolonlar ----
    for col in ["Sevk Durumu", "Proforma No", "Sevk Tarihi", "Ulaşma Tarihi"]:
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

    def get_or_create_folder_by_name(name: str, parent_id: str) -> str:
        """Parent altında isme göre klasör bulur; yoksa oluşturur. Shared Drive uyumlu."""
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
        secenekler["sec_text"] = secenekler["Müşteri Adı"] + " - " + secenekler["Proforma No"]
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

            # 3) Mevcut dosyaları say ve özetle (ilk 10 isim)
            try:
                mevcut_dosyalar = drive.ListFile({
                    'q': f"'{hedef_klasor}' in parents and trashed = false",
                    'supportsAllDrives': True,
                    'includeItemsFromAllDrives': True
                }).GetList()
            except Exception as e:
                mevcut_dosyalar = []
                st.warning(f"Dosyalar listelenemedi: {e}")

            if mevcut_dosyalar:
                st.caption(f"Bu klasörde {len(mevcut_dosyalar)} dosya var.")
                names = [f"- {f['title']}" for f in mevcut_dosyalar[:10]]
                st.write("\n".join(names) if names else "")
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
                        update_excel()  # veri kaydımız yok ama genel dosya güncelleme için
                        st.success(f"{yuklenen_say} yeni dosya yüklendi.")
                        if atlanan_duplike:
                            st.info(f"{atlanan_duplike} dosya aynı isimle bulunduğu için atlandı.")
                        st.rerun()
                    else:
                        if atlanan_duplike and not yuklenen_say:
                            st.warning("Tüm dosyalar klasörde zaten mevcut görünüyor (isimleri aynı).")

        st.markdown("---")

        # ========== ETA Düzenleme ==========
        # Önceden ETA girilmiş mi?
        filtre = (df_eta["Müşteri Adı"] == sec_musteri) & (df_eta["Proforma No"] == sec_proforma)
        if filtre.any():
            mevcut_eta = df_eta.loc[filtre, "ETA Tarihi"].values[0]
            mevcut_aciklama = df_eta.loc[filtre, "Açıklama"].values[0]
        else:
            mevcut_eta = ""
            mevcut_aciklama = ""

        with st.form("edit_eta"):
            try:
                varsayilan_eta = pd.to_datetime(mevcut_eta).date() if mevcut_eta and pd.notnull(mevcut_eta) and str(mevcut_eta) != "NaT" else datetime.date.today()
            except Exception:
                varsayilan_eta = datetime.date.today()
            eta_tarih = st.date_input("ETA Tarihi", value=varsayilan_eta)
            aciklama = st.text_area("Açıklama", value=mevcut_aciklama)
            guncelle = st.form_submit_button("ETA'yı Kaydet/Güncelle")
            ulasti = st.form_submit_button("Ulaştı")
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
                df_eta = df_eta[~((df_eta["Müşteri Adı"] == sec_musteri) & (df_eta["Proforma No"] == sec_proforma))]
                idx = df_proforma[(df_proforma["Müşteri Adı"] == sec_musteri) & (df_proforma["Proforma No"] == sec_proforma)].index
                if len(idx) > 0:
                    df_proforma.at[idx[0], "Sevk Durumu"] = "Ulaşıldı"
                    df_proforma.at[idx[0], "Ulaşma Tarihi"] = datetime.date.today()
                update_excel()
                st.success("Sipariş 'Ulaşıldı' olarak işaretlendi ve ETA takibinden çıkarıldı!")
                st.rerun()

            if geri_al:
                # Siparişi geri al: ETA'dan çıkar, proforma'da sevk durumunu boş yap (Güncel Sipariş Durumu'na döner)
                df_eta = df_eta[~((df_eta["Müşteri Adı"] == sec_musteri) & (df_eta["Proforma No"] == sec_proforma))]
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
        sil_sec = st.selectbox("Silinecek Kaydı Seçin", options=silinecekler,
            format_func=lambda i: f"{df_eta.at[i, 'Müşteri Adı']} - {df_eta.at[i, 'Proforma No']}")
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
        ulasanlar["sec_text"] = ulasanlar["Müşteri Adı"] + " - " + ulasanlar["Proforma No"]
        st.markdown("#### Teslim Edilen Siparişlerde İşlemler")
        selected_ulasan = st.selectbox("Sipariş Seçiniz", ulasanlar["sec_text"])
        row = ulasanlar[ulasanlar["sec_text"] == selected_ulasan].iloc[0]

        # Ulaşma tarihi düzenleme
        try:
            current_ulasma = pd.to_datetime(row.get("Ulaşma Tarihi", None)).date()
            if pd.isnull(current_ulasma) or str(current_ulasma) == "NaT":
                current_ulasma = datetime.date.today()
        except Exception:
            current_ulasma = datetime.date.today()

        new_ulasma_tarih = st.date_input("Ulaşma Tarihi", value=current_ulasma, key="ulasan_guncelle")
        if st.button("Ulaşma Tarihini Kaydet"):
            idx = df_proforma[(df_proforma["Müşteri Adı"] == row["Müşteri Adı"]) & 
                              (df_proforma["Proforma No"] == row["Proforma No"])].index
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

        # Ulaşanlar Tablosu
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

        tablo = ulasanlar[["Müşteri Adı", "Proforma No", "Termin Tarihi", "Sevk Tarihi", "Ulaşma Tarihi", "Gün Farkı", "Tutar", "Açıklama"]]
        st.dataframe(tablo, use_container_width=True)
    else:
        st.info("Henüz ulaşan sipariş yok.")




 

# ==============================
# FUAR MÜŞTERİ KAYITLARI MENÜSÜ
# ==============================

if menu == "Fuar Müşteri Kayıtları":
    st.markdown("<h2 style='color:#8e54e9; font-weight:bold; text-align:center;'>🎫 FUAR MÜŞTERİ KAYITLARI</h2>", unsafe_allow_html=True)
    st.info("Fuarlarda müşteri görüşmelerinizi hızlıca buraya ekleyin. Hem yeni kayıt oluşturabilir hem de mevcut kayıtlarınızı düzenleyebilirsiniz.")

    # --- Fuar Adı Girişi & Seçimi ---
    fuar_isimleri = list(df_fuar_musteri["Fuar Adı"].dropna().unique())
    yeni_fuar = st.text_input("Yeni Fuar Adı Ekleyin (Eklemek istemiyorsanız boş bırakın):")
    if yeni_fuar and yeni_fuar not in fuar_isimleri:
        fuar_isimleri.append(yeni_fuar)
        fuar_adi = yeni_fuar
    else:
        fuar_adi = st.selectbox("Fuar Seçiniz", ["- Fuar Seçiniz -"] + sorted(fuar_isimleri), index=0)
        if fuar_adi == "- Fuar Seçiniz -":
            fuar_adi = ""

    secim = st.radio("İşlem Seçiniz:", ["Yeni Kayıt", "Eski Kayıt"])

    # Ülke ve Satış Temsilcisi Listeleri
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

    temsilci_listesi = ["Hüseyin POLAT", "Kemal İlker Çelikkalkan", "Efe Yıldırım"]

    # --- YENİ KAYIT ---
    if secim == "Yeni Kayıt":
        st.markdown("#### Yeni Fuar Müşteri Kaydı Ekle")
        with st.form("fuar_musteri_ekle"):
            musteri_adi = st.text_input("Müşteri Adı")
            ulke = st.selectbox("Ülke Seçin", ulke_listesi)  # Ülke Seçimi
            tel = st.text_input("Telefon")
            email = st.text_input("E-mail")
            temsilci = st.selectbox("Satış Temsilcisi", temsilci_listesi)  # Satış Temsilcisi Seçimi
            aciklama = st.text_area("Açıklamalar")
            gorusme_kalitesi = st.slider("Görüşme Kalitesi (1=Kötü, 5=Çok İyi)", 1, 5, 3)
            tarih = st.date_input("Tarih", value=datetime.date.today())
            submitted = st.form_submit_button("Kaydet")
            if submitted:
                if not musteri_adi.strip() or not fuar_adi:
                    st.warning("Lütfen fuar seçin ve müşteri adı girin.")
                else:
                    new_row = {
                        "Fuar Adı": fuar_adi,
                        "Müşteri Adı": musteri_adi,
                        "Ülke": ulke,
                        "Telefon": tel,
                        "E-mail": email,
                        "Satış Temsilcisi": temsilci,
                        "Açıklamalar": aciklama,
                        "Görüşme Kalitesi": gorusme_kalitesi,
                        "Tarih": tarih
                    }
                    df_fuar_musteri = pd.concat([df_fuar_musteri, pd.DataFrame([new_row])], ignore_index=True)
                    update_excel()
                    st.success("Fuar müşterisi başarıyla eklendi!")
                    st.rerun()

    # --- ESKİ KAYIT DÜZENLE/SİL ---
    elif secim == "Eski Kayıt":
        kolonlar = ["Müşteri Adı", "Ülke", "Telefon", "E-mail", "Satış Temsilcisi", "Açıklamalar", "Görüşme Kalitesi", "Tarih"]
        musteri_df = df_fuar_musteri[df_fuar_musteri["Fuar Adı"] == fuar_adi].copy()
        if musteri_df.empty:
            st.info("Bu fuara ait müşteri kaydı bulunamadı.")
        else:
            st.markdown(f"<h4 style='color:#4776e6;'>{fuar_adi} Fuarındaki Müşteri Görüşme Kayıtları</h4>", unsafe_allow_html=True)
            secili_index = st.selectbox(
                "Düzenlemek/Silmek istediğiniz kaydı seçin:",
                musteri_df.index,
                format_func=lambda i: f"{musteri_df.at[i, 'Müşteri Adı']} ({musteri_df.at[i, 'Tarih']})"
            )
            # Kayıt görüntüle & düzenle
            with st.form("kayit_duzenle"):
                musteri_adi = st.text_input("Müşteri Adı", value=musteri_df.at[secili_index, "Müşteri Adı"])
                ulke = st.selectbox("Ülke", ulke_listesi, index=ulke_listesi.index(musteri_df.at[secili_index, "Ülke"]))
                temsilci = st.selectbox("Satış Temsilcisi", temsilci_listesi, index=temsilci_listesi.index(musteri_df.at[secili_index, "Satış Temsilcisi"]))
                tel = st.text_input("Telefon", value=musteri_df.at[secili_index, "Telefon"])
                email = st.text_input("E-mail", value=musteri_df.at[secili_index, "E-mail"])
                aciklama = st.text_area("Açıklamalar", value=musteri_df.at[secili_index, "Açıklamalar"])
                gorusme_kalitesi = st.slider(
                    "Görüşme Kalitesi (1=Kötü, 5=Çok İyi)", 1, 5,
                    int(musteri_df.at[secili_index, "Görüşme Kalitesi"]) if musteri_df.at[secili_index, "Görüşme Kalitesi"] else 3
                )
                tarih = st.date_input(
                    "Tarih",
                    value=pd.to_datetime(musteri_df.at[secili_index, "Tarih"]).date()
                    if musteri_df.at[secili_index, "Tarih"] else datetime.date.today()
                )
                guncelle = st.form_submit_button("Kaydı Güncelle")
                sil = st.form_submit_button("Kaydı Sil")
            if guncelle:
                for key, value in zip(kolonlar, [musteri_adi, ulke, tel, email, temsilci, aciklama, gorusme_kalitesi, tarih]):
                    df_fuar_musteri.at[secili_index, key] = value
                update_excel()
                st.success("Kayıt güncellendi!")
                st.rerun()
            if sil:
                df_fuar_musteri = df_fuar_musteri.drop(secili_index).reset_index(drop=True)
                update_excel()
                st.success("Kayıt silindi!")
                st.rerun()
            st.dataframe(musteri_df[kolonlar], use_container_width=True)


# ===========================
# === MEDYA ÇEKMECESİ MENÜSÜ ===
# ===========================

elif menu == "Medya Çekmecesi":
    st.markdown("<h2 style='color:#8e54e9; font-weight:bold;'>Medya Çekmecesi</h2>", unsafe_allow_html=True)
    st.info("Google Drive’daki medya, ürün görselleri ve kalite evraklarına aşağıdaki sekmelerden ulaşabilirsiniz.")

    # Klasör linkleri
    drive_folders = {
        "Genel Medya Klasörü": "https://drive.google.com/embeddedfolderview?id=1gFAaK-6v1e3346e-W0TsizOqSq43vHLY#list",
        "Ürün Görselleri": "https://drive.google.com/embeddedfolderview?id=18NNlmadm5NNFkI1Amzt_YMwB53j6AmbD#list",
        "Kalite Evrakları": "https://drive.google.com/embeddedfolderview?id=1pbArzYfA4Tp50zvdyTzSPF2ThrMWrGJc#list"
    }

    tab1, tab2, tab3 = st.tabs(list(drive_folders.keys()))

    with tab1:
        st.markdown(
            f"""
            <iframe src="{drive_folders['Genel Medya Klasörü']}" width="100%" height="600" frameborder="0" style="border:1px solid #eee; border-radius:12px; margin-top:10px;"></iframe>
            """,
            unsafe_allow_html=True
        )
        st.info("İlgili dosyanın üstüne çift tıklayarak yeni sekmede açabilir veya indirebilirsiniz.")

    with tab2:
        st.markdown(
            f"""
            <iframe src="{drive_folders['Ürün Görselleri']}" width="100%" height="600" frameborder="0" style="border:1px solid #eee; border-radius:12px; margin-top:10px;"></iframe>
            """,
            unsafe_allow_html=True
        )
        st.info("İlgili dosyanın üstüne çift tıklayarak yeni sekmede açabilir veya indirebilirsiniz.")

    with tab3:
        st.markdown(
            f"""
            <iframe src="{drive_folders['Kalite Evrakları']}" width="100%" height="600" frameborder="0" style="border:1px solid #eee; border-radius:12px; margin-top:10px;"></iframe>
            """,
            unsafe_allow_html=True
        )
        st.info("Kalite sertifikalarını ve ilgili dokümanları bu klasörden inceleyebilir ve indirebilirsiniz.")

    st.warning("Not: Klasörlerin paylaşım ayarlarının 'Bağlantıya sahip olan herkes görüntüleyebilir' olduğundan emin olun.")



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


# =============================
# === Google Sheets <-> Lokal Excel Senkron Yardımcıları ===
# Kaynak gerçek: Google Sheets.
# Lokal dosya: temp.xlsx (dış dünyada rahat düzenlemek için)
# Davranış:
# - Uygulama açılırken "auto sync" çalışır:
#   - Hem secrets (sheet_id) hem temp.xlsx varsa:
#       - Meta sayfasındaki "last_sheet_update" ile temp.xlsx mtime karşılaştırılır.
#       - Hangisi daha yeni ise diğer tarafa yazılır.
#   - Sadece sheet varsa: sheet -> temp.xlsx çekilir (lokalde güncel kopya oluşur).
#   - Sadece temp.xlsx varsa ve sheet bağlanabiliyorsa: temp.xlsx -> sheet push yapılır.
# - UI'da "Şimdi Senkronize Et" butonu ile manuel sync tetiklenebilir.
# Not: Lokal senkron için secrets gereklidir (service account ile bağlanmak için).
# =============================




def _get_meta_ws():
    """Meta sayfasını getirir; yoksa oluşturur."""
    sh = open_main_sheet()
    try:
        ws = sh.worksheet("Meta")
    except Exception:
        ws = sh.add_worksheet(title="Meta", rows=10, cols=5)
        ws.update("A1", [["key", "value"], ["last_sheet_update", str(time.time())]])
    return ws

def _get_last_sheet_update_ts() -> float:
    ws = _get_meta_ws()
    try:
        vals = ws.get("A1:B10")
        meta = {row[0]: row[1] for row in vals[1:] if len(row) >= 2}
        return float(meta.get("last_sheet_update", "0"))
    except Exception:
        return 0.0

def _set_last_sheet_update_ts(ts: Optional[float] = None):
    if ts is None:
        ts = time.time()
    ws = _get_meta_ws()
    # "last_sheet_update" satırını bul ve güncelle
    vals = ws.get("A1:B10")
    found = False
    for i, row in enumerate(vals[1:], start=2):  # 2. satırdan itibaren
        if len(row) >= 1 and row[0] == "last_sheet_update":
            ws.update_cell(i, 2, str(ts))
            found = True
            break
    if not found:
        ws.append_row(["last_sheet_update", str(ts)])

def _expected_sheets() -> List[str]:
    # Uygulamada kullanılan sheet sayfaları
    return ["Sayfa1", "Kayıtlar", "Teklifler", "Proformalar", "Evraklar", "ETA", "FuarMusteri"]

def _read_local_all(path: str = "temp.xlsx") -> Dict[str, pd.DataFrame]:
    dfs = {}
    if not os.path.exists(path):
        return dfs
    try:
        for ws in _expected_sheets():
            try:
                dfs[ws] = pd.read_excel(path, sheet_name=ws)
            except Exception:
                dfs[ws] = pd.DataFrame()
    except Exception:
        pass
    return dfs

def _read_sheet_all() -> Dict[str, pd.DataFrame]:
    dfs = {}
    for ws in _expected_sheets():
        dfs[ws] = load_ws(ws)
    return dfs

def _write_local_all(dfs: Dict[str, pd.DataFrame], path: str = "temp.xlsx"):
    # Tüm sayfaları aynı dosyaya çoklu sheet olarak yaz
    with pd.ExcelWriter(path, engine="xlsxwriter") as writer:
        for name, df in dfs.items():
            (df if isinstance(df, pd.DataFrame) else pd.DataFrame()).to_excel(writer, index=False, sheet_name=name)

def _write_sheet_all(dfs: Dict[str, pd.DataFrame]):
    # Tüm sayfaları Google Sheets'e yaz (tam sayfa güncelleme)
    # gspread-dataframe kullanımı:
    try:
        for sheet_name, df in dfs.items():
            ws = sh.worksheet(sheet_name)
            set_with_dataframe(ws, df)
    except Exception:
        st.error("gspread-dataframe kütüphanesi eksik. requirements.txt içine 'gspread-dataframe' ekleyin.")
        st.stop()

    sh = open_main_sheet()

    # Eksik çalışma sayfalarını tamamla
    existing_titles = [ws.title for ws in sh.worksheets()]
    for title in _expected_sheets():
        if title not in existing_titles:
            sh.add_worksheet(title=title, rows=1000, cols=26)

    for name, df in dfs.items():
        ws = sh.worksheet(name)
        # Sayfayı temizle ve baştan yaz
        ws.clear()
        set_with_dataframe(ws, (df if isinstance(df, pd.DataFrame) else pd.DataFrame()))
    _set_last_sheet_update_ts(time.time())

def sync_local_and_sheet(auto: bool = True, path: str = "temp.xlsx") -> str:
    """Lokal temp.xlsx ile Google Sheets arasında çift yönlü senkron.
    Dönüş: yapılan işlem özeti (string)."""
    gc = get_gspread_client()
    sheet_ok = gc is not None
    local_ok = os.path.exists(path)

    if not sheet_ok and not local_ok:
        return "Ne Google Sheets'e bağlanabildim ne de temp.xlsx bulundu."

    if sheet_ok and local_ok:
        local_ts = os.path.getmtime(path)
        sheet_ts = _get_last_sheet_update_ts()
        if local_ts > sheet_ts:
            # Lokal daha yeni -> Sheet'i güncelle
            dfs = _read_local_all(path)
            _write_sheet_all(dfs)
            return "Lokal (temp.xlsx) daha yeniydi → Google Sheets güncellendi."
        elif sheet_ts > local_ts:
            # Sheet daha yeni -> Lokali güncelle
            dfs = _read_sheet_all()
            _write_local_all(dfs, path)
            # Dosya mtime'ı da yeni timestamp ile hizala
            os.utime(path, (time.time(), sheet_ts))
            return "Google Sheets daha yeniydi → Lokal temp.xlsx güncellendi."
        else:
            return "Her iki taraf da güncel görünüyor. Değişiklik yapılmadı."
    elif sheet_ok and not local_ok:
        # Sadece Sheet var → Lokale indir
        dfs = _read_sheet_all()
        _write_local_all(dfs, path)
        os.utime(path, (time.time(), _get_last_sheet_update_ts()))
        return "Sadece Google Sheets erişilebilir → Lokal temp.xlsx oluşturuldu."
    elif local_ok and not sheet_ok:
        # Sadece lokal var → Sheet'e yazılamaz, bilgi ver
        return "Sadece temp.xlsx mevcut; Google Sheets'e bağlanılamadı. secrets ayarlarını kontrol edin."

# Uygulama açılışında otomatik senkronizasyon
try:
    with st.spinner("Veriler senkronize ediliyor..."):
        sync_message = sync_local_and_sheet(auto=True, path="temp.xlsx")
    st.toast(sync_message)
except Exception as _e:
    st.warning(f"Senkron sırasında bir uyarı oluştu: {_e}")

# UI: manuel senkronizasyon
with st.expander("🔄 Senkronizasyon", expanded=False):
    if st.button("Şimdi Senkronize Et"):
        msg = sync_local_and_sheet(auto=False, path="temp.xlsx")
        st.success(msg)


# === Conditional auto-sync (quiet) ===
try:
    _has_sheet_id = bool(st.secrets.get("app", {}).get("sheet_id", "")) or bool(globals().get("SHEET_ID", ""))
except Exception:
    _has_sheet_id = bool(globals().get("SHEET_ID", ""))

if _has_sheet_id and "sync_local_and_sheet" in globals() and not st.session_state.get("__auto_sync_done__", False):
    try:
        with st.spinner("Veriler senkronize ediliyor..."):
            msg = sync_local_and_sheet(auto=True, path="temp.xlsx")  # function should exist in your code
        st.toast(str(msg))
        st.session_state["__auto_sync_done__"] = True
    except Exception:
        # Quietly skip if not configured; avoid noisy warnings on login screen
        pass
# === /Conditional auto-sync ===

