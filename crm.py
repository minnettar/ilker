# crm.py – Streamlit CRM with Google Sheets
import streamlit as st
import gspread
import pandas as pd
import json, base64
from google.oauth2.service_account import Credentials

# -------------- CONFIG --------------
SPREADSHEET_ID = "1A_gL11UL6JFAoZrMrg92K8bAegeCn_KzwUyU8AWzE"   # Sheet ID açık
SA_JSON_B64    = st.secrets["general"]["GOOGLE_SA_JSON_B64"]    # sadece JSON secrets'ta

# -------------- GOOGLE SHEETS --------------
@st.cache_resource
def get_client():
    info = json.loads(base64.b64decode(SA_JSON_B64).decode("utf-8"))
    scopes = ["https://www.googleapis.com/auth/spreadsheets"]
    creds  = Credentials.from_service_account_info(info, scopes=scopes)
    return gspread.authorize(creds)

def get_ws(sheet_name):
    gc = get_client()
    sh = gc.open_by_key(SPREADSHEET_ID)
    try:
        return sh.worksheet(sheet_name)
    except gspread.WorksheetNotFound:
        ws = sh.add_worksheet(sheet_name, rows=1000, cols=20)
        return ws

def sheet_to_df(ws):
    data = ws.get_all_records()
    return pd.DataFrame(data)

def append_row(ws, row):
    ws.append_row(row)

# -------------- LOGIN --------------
USERS = {"admin": "1234", "demo": "demo"}

def login():
    st.title("🔐 CRM Giriş")
    u = st.text_input("Kullanıcı Adı")
    p = st.text_input("Şifre", type="password")
    if st.button("Giriş"):
        if u in USERS and USERS[u] == p:
            st.session_state["logged_in"] = True
            st.success("Giriş başarılı ✅")
            st.rerun()
        else:
            st.error("Hatalı kullanıcı adı veya şifre")
    st.stop()

# -------------- PAGES --------------
def dashboard_page():
    st.header("📊 Dashboard")
    try:
        cust = sheet_to_df(get_ws("Müşteriler"))
        pro  = sheet_to_df(get_ws("Proformalar"))
        ords = sheet_to_df(get_ws("Siparişler"))
        vads = sheet_to_df(get_ws("Vadeler"))
        st.metric("Müşteri Sayısı", len(cust))
        st.metric("Proforma Sayısı", len(pro))
        st.metric("Sipariş Sayısı", len(ords))
        st.metric("Bekleyen Vadeler", len(vads))
    except Exception as e:
        st.warning(f"Dashboard okunamadı: {e}")

def customers_page():
    st.header("👥 Müşteri Listesi")
    ws = get_ws("Müşteriler")
    df = sheet_to_df(ws)
    st.dataframe(df)
    st.subheader("Yeni Müşteri Ekle")
    name = st.text_input("Ad Soyad")
    email = st.text_input("Email")
    phone = st.text_input("Telefon")
    if st.button("Ekle"):
        append_row(ws, [name, email, phone])
        st.success("Müşteri eklendi ✅")
        st.rerun()

def proformas_page():
    st.header("📄 Proforma Takip")
    ws = get_ws("Proformalar")
    df = sheet_to_df(ws)
    st.dataframe(df)
    st.subheader("Yeni Proforma")
    no    = st.text_input("Proforma No")
    cust  = st.text_input("Müşteri")
    tutar = st.number_input("Tutar", min_value=0.0)
    tarih = st.date_input("Tarih")
    durum = st.selectbox("Durum", ["Beklemede","Onaylandı","İptal"])
    if st.button("Proforma Kaydet"):
        append_row(ws, [no, cust, tutar, str(tarih), durum])
        st.success("Proforma kaydedildi ✅")
        st.rerun()

def orders_page():
    st.header("📦 Güncel Sipariş Durumu")
    ws = get_ws("Siparişler")
    df = sheet_to_df(ws)
    st.dataframe(df)
    st.subheader("Yeni Sipariş")
    no    = st.text_input("Sipariş No")
    cust  = st.text_input("Müşteri")
    urun  = st.text_input("Ürün")
    miktar= st.number_input("Miktar", min_value=1)
    durum = st.selectbox("Durum", ["Hazırlanıyor","Sevkedildi","Tamamlandı"])
    tarih = st.date_input("Sipariş Tarihi")
    if st.button("Sipariş Ekle"):
        append_row(ws, [no, cust, urun, miktar, durum, str(tarih)])
        st.success("Sipariş eklendi ✅")
        st.rerun()

def vade_page():
    st.header("💰 Vade Takip")
    ws = get_ws("Vadeler")
    df = sheet_to_df(ws)
    st.dataframe(df)
    st.subheader("Yeni Vade Ekle")
    fatura = st.text_input("Fatura No")
    musteri= st.text_input("Müşteri")
    tutar  = st.number_input("Tutar", min_value=0.0)
    tarih  = st.date_input("Vade Tarihi")
    odendi = st.selectbox("Ödendi mi?", ["FALSE","TRUE"])
    if st.button("Vade Kaydet"):
        append_row(ws, [fatura, musteri, tutar, str(tarih), odendi])
        st.success("Vade eklendi ✅")
        st.rerun()

def eta_page():
    st.header("🚢 ETA Takip")
    ws = get_ws("ETA")
    df = sheet_to_df(ws)
    st.dataframe(df)
    st.subheader("Yeni ETA Kaydı")
    konteyner = st.text_input("Konteyner No")
    urun      = st.text_input("Ürün")
    tarih     = st.date_input("ETA Tarihi")
    durum     = st.selectbox("Durum", ["Yolda","Gümrükte","Teslim"])
    if st.button("ETA Kaydet"):
        append_row(ws, [konteyner, urun, str(tarih), durum])
        st.success("ETA kaydedildi ✅")
        st.rerun()

def sales_page():
    st.header("📈 Satış Performansı")
    ws = get_ws("Satışlar")
    df = sheet_to_df(ws)
    st.dataframe(df)
    st.subheader("Yeni Satış Kaydı")
    musteri= st.text_input("Müşteri")
    tutar  = st.number_input("Satış Tutarı", min_value=0.0)
    tarih  = st.date_input("Satış Tarihi")
    satici = st.text_input("Satışçı")
    if st.button("Satış Kaydet"):
        append_row(ws, [musteri, tutar, str(tarih), satici])
        st.success("Satış kaydedildi ✅")
        st.rerun()

def fairs_page():
    st.header("🎪 Fuar Kayıt")
    ws = get_ws("Fuarlar")
    df = sheet_to_df(ws)
    st.dataframe(df)
    st.subheader("Yeni Fuar Kaydı")
    fuar  = st.text_input("Fuar Adı")
    tarih = st.date_input("Tarih")
    musteri = st.text_input("Müşteri")
    notlar  = st.text_area("Notlar")
    if st.button("Fuar Kaydet"):
        append_row(ws, [fuar, str(tarih), musteri, notlar])
        st.success("Fuar kaydedildi ✅")
        st.rerun()

def tasks_page():
    st.header("📝 Görevler")
    ws = get_ws("Görevler")
    df = sheet_to_df(ws)
    st.dataframe(df)
    st.subheader("Yeni Görev")
    gorev = st.text_input("Görev")
    sorumlu = st.text_input("Sorumlu")
    tarih   = st.date_input("Tarih")
    durum   = st.selectbox("Durum", ["Beklemede","Tamamlandı"])
    if st.button("Görev Ekle"):
        append_row(ws, [gorev, sorumlu, str(tarih), durum])
        st.success("Görev eklendi ✅")
        st.rerun()

def settings_page():
    st.header("⚙️ Ayarlar")
    if st.button("Çıkış Yap"):
        st.session_state["logged_in"] = False
        st.rerun()

# -------------- MAIN --------------
def main():
    st.set_page_config(page_title="CRM", layout="wide")

    if "logged_in" not in st.session_state:
        st.session_state["logged_in"] = False

    if not st.session_state["logged_in"]:
        login()

    menu = st.sidebar.radio("Menü", [
        "Dashboard","Müşteriler","Proformalar","Siparişler",
        "Vadeler","ETA","Satışlar","Fuarlar","Görevler","Ayarlar"
    ])

    if menu == "Dashboard": dashboard_page()
    elif menu == "Müşteriler": customers_page()
    elif menu == "Proformalar": proformas_page()
    elif menu == "Siparişler": orders_page()
    elif menu == "Vadeler": vade_page()
    elif menu == "ETA": eta_page()
    elif menu == "Satışlar": sales_page()
    elif menu == "Fuarlar": fairs_page()
    elif menu == "Görevler": tasks_page()
    elif menu == "Ayarlar": settings_page()

if __name__ == "__main__":
    main()
