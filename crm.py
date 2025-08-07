import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime

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

# === Google Sheets Bağlantısı ===
scope = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
credentials = Credentials.from_service_account_info(st.secrets["gcp_service_account"], scopes=scope)
client = gspread.authorize(credentials)

# === Sheet Ayarları ===
SPREADSHEET_URL = "https://docs.google.com/spreadsheets/d/1nKuBKJPzpYC5TxNvc4G2OgI7miytuLBQE0n31I3yue0"
sheet = client.open_by_url(SPREADSHEET_URL)

try:
    musteri_sheet = sheet.worksheet("Müşteri")
    kayit_sheet = sheet.worksheet("Kayıtlar")

    df_musteri = pd.DataFrame(musteri_sheet.get_all_records())
    df_kayit = pd.DataFrame(kayit_sheet.get_all_records())
except Exception as e:
    st.error(f"Google Sheet bağlantısı başarısız: {e}")
    st.stop()

# === Ülke ve Temsilci Listeleri ===
ulke_listesi = sorted(["Türkiye", "Almanya", "Fransa", "Azerbaycan", "Katar", "Hollanda", "Libya", "Benin", "İsveç", "Ukrayna", "Irak", "Birleşik Arap Emirlikleri", "Diğer"])
temsilci_listesi = ["KEMAL İLKER ÇELİKKALKAN", "HÜSEYİN POLAT", "EFE YILDIRIM", "FERHAT ŞEKEROĞLU"]

# === Menü Butonları ===
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
.menu-btn:hover {filter: brightness(1.2);}
</style>
""", unsafe_allow_html=True)

menuler = [
    ("Müşteri Listesi", "menu-musteri", "📒"),
    ("Görüşme Kayıtları", "menu-gorusme", "☎️"),
]

for i, (isim, renk, ikon) in enumerate(menuler):
    if st.sidebar.button(f"{ikon} {isim}", key=f"menu_{isim}_{i}", help=isim):
        st.session_state.menu_state = isim

menu = st.session_state.get("menu_state", "Müşteri Listesi")

# === Menü: Müşteri Listesi ===
if menu == "Müşteri Listesi":
    st.subheader("📒 Müşteri Listesi")
    st.dataframe(df_musteri)

# === Menü: Görüşme Kayıtları ===
if menu == "Görüşme Kayıtları":
    st.subheader("☎️ Görüşme / Ziyaret / Arama Kayıtları")
    st.dataframe(df_kayit)
