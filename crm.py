import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
import datetime

st.set_page_config(page_title="ŞEKEROĞLU İHRACAT CRM", layout="wide")

# ==== LOGIN ====
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
    if st.button("Giriş Yap"):
        if username in USERS and password == USERS[username]:
            st.session_state.user = username
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

# ==== GOOGLE SHEETS BAĞLANTI ====
SHEET_ID = "1A_gL11UL6JFAoZrMrg92K8bAegeCn_KzwUyU8AWzE"

@st.cache_resource
def connect_gsheets():
    creds = Credentials.from_service_account_info(
        st.secrets["gcp_service_account"],
        scopes=["https://www.googleapis.com/auth/spreadsheets"],
    )
    client = gspread.authorize(creds)
    return client.open_by_key(SHEET_ID)

sh = connect_gsheets()

# ==== HELPER ====
def load_data(sheet_name):
    try:
        ws = sh.worksheet(sheet_name)
        data = ws.get_all_records()
        df = pd.DataFrame(data)
        return df
    except Exception as e:
        st.error(f"{sheet_name} yüklenemedi: {e}")
        return pd.DataFrame()

# ==== MENÜ ====
menu = st.sidebar.selectbox(
    "Menü", 
    ["Sayfa1 (Genel)", "Kayıtlar", "Teklifler", "Proformalar", "Evraklar", "ETA", "FuarMusteri"]
)

if menu == "Sayfa1 (Genel)":
    st.header("📌 Genel Kayıtlar (Sayfa1)")
    df = load_data("Sayfa1")
    st.dataframe(df, use_container_width=True)

elif menu == "Kayıtlar":
    st.header("🗂️ Kayıtlar")
    df = load_data("Kayıtlar")
    st.dataframe(df, use_container_width=True)

elif menu == "Teklifler":
    st.header("📑 Teklifler")
    df = load_data("Teklifler")
    st.dataframe(df, use_container_width=True)

elif menu == "Proformalar":
    st.header("📄 Proformalar")
    df = load_data("Proformalar")
    st.dataframe(df, use_container_width=True)

elif menu == "Evraklar":
    st.header("📦 Evraklar")
    df = load_data("Evraklar")
    st.dataframe(df, use_container_width=True)

elif menu == "ETA":
    st.header("🚢 ETA Takibi")
    df = load_data("ETA")
    st.dataframe(df, use_container_width=True)

elif menu == "FuarMusteri":
    st.header("🎪 Fuar Müşteri Kayıtları")
    df = load_data("FuarMusteri")
    st.dataframe(df, use_container_width=True)
