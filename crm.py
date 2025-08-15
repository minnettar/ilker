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


drive = get_drive()

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
