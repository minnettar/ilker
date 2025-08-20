import streamlit as st
import gspread
from google.oauth2.service_account import Credentials

# ------------------------
# CONFIG
# ------------------------
SHEET_ID = "1A_gL11UL6JFAoZrMrg92K8bAegeCn_KzwUyU8AWzE_0"

# ------------------------
# CONNECT GOOGLE SHEETS
# ------------------------
@st.cache_resource
def connect_gsheets():
    try:
        creds = Credentials.from_service_account_info(
            st.secrets["gcp_service_account"],
            scopes=["https://www.googleapis.com/auth/spreadsheets"]
        )
        client = gspread.authorize(creds)
        sh = client.open_by_key(SHEET_ID)
        return sh
    except Exception as e:
        st.error(f"Sheets bağlantı hatası: {e}")
        return None

# ------------------------
# LOGIN
# ------------------------
def login():
    st.sidebar.header("🔑 Kullanıcı Girişi")
    username = st.sidebar.text_input("Kullanıcı Adı")
    password = st.sidebar.text_input("Şifre", type="password")
    if st.sidebar.button("Giriş Yap"):
        if username == "admin" and password == "1234":  # TODO: SQLite yapabilirsin
            st.session_state["auth"] = True
            st.experimental_rerun()
        else:
            st.sidebar.error("❌ Hatalı giriş bilgileri")

# ------------------------
# MENU FUNCTIONS
# ------------------------
def menu_kayitlar(sh):
    ws = sh.worksheet("Kayıtlar")
    data = ws.get_all_records()
    st.subheader("📋 Kayıtlar")
    st.dataframe(data)

def menu_teklifler(sh):
    ws = sh.worksheet("Teklifler")
    data = ws.get_all_records()
    st.subheader("📑 Teklifler")
    st.dataframe(data)

def menu_proformalar(sh):
    ws = sh.worksheet("Proformalar")
    data = ws.get_all_records()
    st.subheader("📄 Proformalar")
    st.dataframe(data)

def menu_evraklar(sh):
    ws = sh.worksheet("Evraklar")
    data = ws.get_all_records()
    st.subheader("📦 Evraklar")
    st.dataframe(data)

def menu_eta(sh):
    ws = sh.worksheet("ETA")
    data = ws.get_all_records()
    st.subheader("🚢 ETA Takibi")
    st.dataframe(data)

def menu_fuar(sh):
    ws = sh.worksheet("FuarMusteri")
    data = ws.get_all_records()
    st.subheader("🎪 Fuar Kayıtları")
    st.dataframe(data)

# ------------------------
# MAIN
# ------------------------
def main():
    st.set_page_config(page_title="CRM", layout="wide")

    if "auth" not in st.session_state or not st.session_state["auth"]:
        login()
        return

    sh = connect_gsheets()
    if not sh:
        st.stop()

    # Debug: mevcut sekmeleri yaz
    st.sidebar.success(f"Sheets bağlantısı OK → Sekmeler: {[ws.title for ws in sh.worksheets()]}")

    menu = st.sidebar.radio(
        "Menü",
        ["Kayıtlar", "Teklifler", "Proformalar", "Evraklar", "ETA", "Fuar"]
    )

    if menu == "Kayıtlar":
        menu_kayitlar(sh)
    elif menu == "Teklifler":
        menu_teklifler(sh)
    elif menu == "Proformalar":
        menu_proformalar(sh)
    elif menu == "Evraklar":
        menu_evraklar(sh)
    elif menu == "ETA":
        menu_eta(sh)
    elif menu == "Fuar":
        menu_fuar(sh)

# ------------------------
if __name__ == "__main__":
    main()
