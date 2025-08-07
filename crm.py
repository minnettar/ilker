import streamlit as st
import pandas as pd
import numpy as np
import os
import io
import datetime
from google.oauth2 import service_account
from googleapiclient.discovery import build
import smtplib
from email.message import EmailMessage

# ==== KULLANICI GİRİŞİ SİSTEMİ ====
st.set_page_config(page_title="ŞEKEROĞLU İHRACAT CRM", layout="wide")

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

temsilci_listesi = [
    "KEMAL İLKER ÇELİKKALKAN",
    "HÜSEYİN POLAT",
    "EFE YILDIRIM",
    "FERHAT ŞEKEROĞLU"
]

# --- LOGO URL'inden SVG GÖSTER ---
LOGO_URL = "https://www.sekeroglugroup.com/storage/settings/xdp5r6DZIFJMNGOStqwvKCiVHDhYxA84jFr61TNp.svg"

col1, col2 = st.columns([2, 8])
with col1:
    st.markdown(
        f"""
        <img src="{LOGO_URL}" width="180" style="margin-bottom:12px;margin-top:-10px;" />
        """,
        unsafe_allow_html=True,
    )
with col2:
    st.markdown("""
        <h1 style="color: #219A41; font-weight: bold; font-size: 2.6em; letter-spacing:2px; margin:0; margin-top:-8px;">
            ŞEKEROĞLU İHRACAT CRM
        </h1>
    """, unsafe_allow_html=True)

    import streamlit as st
import pandas as pd
from google.oauth2 import service_account
from googleapiclient.discovery import build

# --- Service Account ve Sheet Kimlikleri ---
SHEET_ID = "1nKuBKJPzpYC5TxNvc4G2OgI7miytuLBQE0n31I3yue0"
SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]
SHEET_NAMES = {
    "df_musteri": "Sayfa1",
    "df_kayit": "Kayıtlar",
    "df_teklif": "Teklifler",
    "df_proforma": "Proformalar",
    "df_evrak": "Evraklar",
    "df_eta": "ETA",
    "df_fuar_musteri": "FuarMusteri"
}

# --- Google Sheets API Bağlantısı ---
@st.cache_resource
def get_service():
    credentials = service_account.Credentials.from_service_account_info(
        st.secrets["gcp_service_account"], scopes=SCOPES
    )
    service = build("sheets", "v4", credentials=credentials)
    return service.spreadsheets()

sheet = get_service()

# --- Sheet'ten DataFrame Yükleme ---
def sheet_to_df(sheet_name, header_row=1):
    result = sheet.values().get(
        spreadsheetId=SHEET_ID,
        range=sheet_name
    ).execute()
    values = result.get("values", [])
    if not values or len(values) < header_row:
        return pd.DataFrame()
    return pd.DataFrame(values[header_row:], columns=values[header_row - 1])

# --- DataFrame'i Sheet'e Yazma ---
def df_to_sheet(df, sheet_name):
    values = [df.columns.tolist()] + df.astype(str).fillna("").values.tolist()
    sheet.values().update(
        spreadsheetId=SHEET_ID,
        range=sheet_name,
        valueInputOption="RAW",
        body={"values": values}
    ).execute()

# --- DataFrame Yükle (Her sheet için) ---
df_musteri = sheet_to_df(SHEET_NAMES["df_musteri"])
if df_musteri.empty:
    df_musteri = pd.DataFrame(columns=[
        "Müşteri Adı", "Telefon", "E-posta", "Adres", "Ülke",
        "Satış Temsilcisi", "Kategori", "Durum", "Vade (Gün)", "Ödeme Şekli"
    ])

df_kayit = sheet_to_df(SHEET_NAMES["df_kayit"])
if df_kayit.empty:
    df_kayit = pd.DataFrame(columns=["Müşteri Adı", "Tarih", "Tip", "Açıklama"])

df_teklif = sheet_to_df(SHEET_NAMES["df_teklif"])
if df_teklif.empty:
    df_teklif = pd.DataFrame(columns=[
        "Müşteri Adı", "Tarih", "Teklif No", "Tutar",
        "Ürün/Hizmet", "Açıklama", "Durum", "PDF"
    ])

df_proforma = sheet_to_df(SHEET_NAMES["df_proforma"])
if df_proforma.empty:
    df_proforma = pd.DataFrame(columns=[
        "Müşteri Adı", "Tarih", "Proforma No", "Tutar", "Açıklama",
        "Durum", "PDF", "Sipariş Formu", "Vade", "Sevk Durumu"
    ])

df_evrak = sheet_to_df(SHEET_NAMES["df_evrak"])
if df_evrak.empty:
    df_evrak = pd.DataFrame(columns=[
        "Müşteri Adı", "Fatura No", "Fatura Tarihi", "Vade Tarihi", "Tutar",
        "Commercial Invoice", "Sağlık Sertifikası", "Packing List",
        "Konşimento", "İhracat Beyannamesi", "Fatura PDF", "Sipariş Formu",
        "Yük Resimleri", "EK Belgeler"
    ])

df_eta = sheet_to_df(SHEET_NAMES["df_eta"])
if df_eta.empty:
    df_eta = pd.DataFrame(columns=["Müşteri Adı", "Proforma No", "ETA Tarihi", "Açıklama"])

df_fuar_musteri = sheet_to_df(SHEET_NAMES["df_fuar_musteri"])
if df_fuar_musteri.empty:
    df_fuar_musteri = pd.DataFrame(columns=[
        "Fuar Adı", "Müşteri Adı", "Ülke", "Telefon", "E-mail", "Açıklamalar", "Tarih"
    ])

# --- Tüm DataFrame'leri Sheet'e Güncelleme Fonksiyonu ---
def update_all_sheets():
    df_to_sheet(df_musteri, SHEET_NAMES["df_musteri"])
    df_to_sheet(df_kayit, SHEET_NAMES["df_kayit"])
    df_to_sheet(df_teklif, SHEET_NAMES["df_teklif"])
    df_to_sheet(df_proforma, SHEET_NAMES["df_proforma"])
    df_to_sheet(df_evrak, SHEET_NAMES["df_evrak"])
    df_to_sheet(df_eta, SHEET_NAMES["df_eta"])
    df_to_sheet(df_fuar_musteri, SHEET_NAMES["df_fuar_musteri"])

    # --- Menü Stili ---
st.sidebar.markdown("""
<style>
.menu-btn {
    display: block;
    width: 100%;
    padding: 1em;
    margin-bottom: 10px;
    border: none;
    border-radius: 10px;
    font-size: 1.1em;
    font-weight: bold;
    color: white;
    cursor: pointer;
    transition: background 0.2s;
}
.menu-cari {background: linear-gradient(90deg, #43cea2, #185a9d);}
.menu-musteri {background: linear-gradient(90deg, #ffb347, #ffcc33);}
.menu-gorusme {background: linear-gradient(90deg, #ff5e62, #ff9966);}
.menu-teklif {background: linear-gradient(90deg, #8e54e9, #4776e6);}
.menu-proforma {background: linear-gradient(90deg, #11998e, #38ef7d);}
.menu-siparis {background: linear-gradient(90deg, #f7971e, #ffd200);}
.menu-evrak {background: linear-gradient(90deg, #f953c6, #b91d73);}
.menu-vade {background: linear-gradient(90deg, #43e97b, #38f9d7);}
.menu-eta {background: linear-gradient(90deg, #f857a6, #ff5858);}
.menu-btn:hover {filter: brightness(1.2);}
</style>
""", unsafe_allow_html=True)

# --- Menü Butonları (kullanıcıya göre) ---
menuler = [
    ("Özet Ekran", "menu-ozet", "📊"),
    ("Cari Ekleme", "menu-cari", "🧑‍💼"),
    ("Müşteri Listesi", "menu-musteri", "📒"),
    ("Görüşme / Arama / Ziyaret Kayıtları", "menu-gorusme", "☎️"),
    ("Fiyat Teklifleri", "menu-teklif", "💰"),
    ("Proforma Takibi", "menu-proforma", "📄"),
    ("Güncel Sipariş Durumu", "menu-siparis", "🚚"),
    ("Fatura & İhracat Evrakları", "menu-evrak", "📑"),
    ("Vade Takibi", "menu-vade", "⏰"),
    ("ETA Takibi", "menu-eta", "🛳️"),
    ("Fuar Müşteri Kayıtları", "menu-fuar", "🎫"),
    ("Medya Çekmecesi", "menu-medya", "🗂️"),
]

# Kullanıcıya özel menü kontrolü
if st.session_state.user == "Boss":
    allowed_menus = [("Özet Ekran", "menu-ozet", "📊")]
else:
    allowed_menus = menuler

if "menu_state" not in st.session_state or st.session_state.menu_state not in [m[0] for m in allowed_menus]:
    st.session_state.menu_state = allowed_menus[0][0]

for i, (isim, renk, ikon) in enumerate(allowed_menus):
    if st.sidebar.button(f"{ikon} {isim}", key=f"menu_{isim}_{i}", help=isim):
        st.session_state.menu_state = isim

menu = st.session_state.menu_state

