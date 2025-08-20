import streamlit as st
import gspread
from google.oauth2.service_account import Credentials
import pandas as pd
import matplotlib.pyplot as plt

# --- Google Sheets Bağlantı ---
def get_gs_client():
    try:
        service_account_info = st.secrets["gcp_service_account"]  # secrets.toml içinden
        creds = Credentials.from_service_account_info(
            service_account_info,
            scopes=["https://www.googleapis.com/auth/spreadsheets"]
        )
        return gspread.authorize(creds)
    except Exception as e:
        st.error(f"Google Sheets bağlantı hatası: {e}")
        return None

def load_data(sheet_id: str, worksheet: str):
    gc = get_gs_client()
    if not gc:
        return pd.DataFrame()
    try:
        sh = gc.open_by_key(sheet_id)
        ws = sh.worksheet(worksheet)
        data = ws.get_all_records()
        return pd.DataFrame(data)
    except Exception as e:
        st.error(f"Worksheet okunamadı ({worksheet}): {e}")
        return pd.DataFrame()

# --- Raporlar ---
def proforma_takip(df):
    st.subheader("📜 Proforma Takip")
    if df.empty:
        st.warning("Proforma verisi bulunamadı.")
        return
    st.dataframe(df)
    # Örnek: toplam tutar
    if "Tutar" in df.columns:
        toplam = df["Tutar"].sum()
        st.success(f"Toplam Proforma Tutarı: {toplam:,.2f}")

def siparis_durumu(df):
    st.subheader("📦 Güncel Sipariş Durumu")
    if df.empty:
        st.warning("Sipariş verisi yok.")
        return
    st.dataframe(df)
    if "Durum" in df.columns:
        durum_count = df["Durum"].value_counts()
        st.bar_chart(durum_count)

def vade_takip(df):
    st.subheader("⏰ Vade Takip")
    if df.empty:
        st.warning("Evrak verisi yok.")
        return
    if "VadeTarihi" not in df.columns:
        st.error("Evraklarda 'VadeTarihi' sütunu bulunamadı.")
        return
    df["VadeTarihi"] = pd.to_datetime(df["VadeTarihi"], errors="coerce")
    bugun = pd.to_datetime("today").normalize()
    vadesi_gelen = df[df["VadeTarihi"] == bugun]
    if vadesi_gelen.empty:
        st.info("Bugün vadesi gelen fatura yok.")
    else:
        st.warning("Bugün vadesi gelenler:")
        st.dataframe(vadesi_gelen)

def eta_takip(df):
    st.subheader("🚢 ETA Takip")
    if df.empty:
        st.warning("ETA verisi yok.")
        return
    st.dataframe(df)
    if "ETA" in df.columns:
        df["ETA"] = pd.to_datetime(df["ETA"], errors="coerce")
        yaklasan = df[df["ETA"] < pd.to_datetime("today") + pd.Timedelta(days=7)]
        st.info("Önümüzdeki 7 gün içinde gelecekler:")
        st.dataframe(yaklasan)

def satis_performansi(df):
    st.subheader("📈 Satış Performansı")
    if df.empty:
        st.warning("Satış verisi yok.")
        return
    if "Tarih" in df.columns and "Tutar" in df.columns:
        df["Tarih"] = pd.to_datetime(df["Tarih"], errors="coerce")
        aylik = df.groupby(df["Tarih"].dt.to_period("M"))["Tutar"].sum()
        fig, ax = plt.subplots()
        aylik.plot(kind="bar", ax=ax)
        st.pyplot(fig)

def fuar_kayit(df):
    st.subheader("🎪 Fuar Kayıt")
    if df.empty:
        st.warning("Fuar müşteri verisi yok.")
        return
    st.dataframe(df)

# --- Ana Uygulama ---
def main():
    st.set_page_config(page_title="CRM Dashboard", layout="wide")
    st.title("📊 CRM Dashboard")

    SHEET_ID = "1A_gL11UL6JFAoZrMrg92K8bAegeCn_KzwUyU8AWzE"  # senin Google Sheet ID

    menu = st.sidebar.radio(
        "Menü Seçin",
        [
            "📌 Kayıtlar",
            "📑 Teklifler",
            "📜 Proformalar",
            "📂 Evraklar",
            "🚢 ETA",
            "🎪 Fuar Müşteri",
            "📜 Proforma Takip",
            "📦 Güncel Sipariş Durumu",
            "⏰ Vade Takip",
            "🚢 ETA Takip",
            "📈 Satış Performansı",
            "🎪 Fuar Kayıt"
        ]
    )

    if menu == "📌 Kayıtlar":
        df = load_data(SHEET_ID, "Kayıtlar")
        st.dataframe(df)

    elif menu == "📑 Teklifler":
        df = load_data(SHEET_ID, "Teklifler")
        st.dataframe(df)

    elif menu == "📜 Proformalar":
        df = load_data(SHEET_ID, "Proformalar")
        st.dataframe(df)

    elif menu == "📂 Evraklar":
        df = load_data(SHEET_ID, "Evraklar")
        st.dataframe(df)

    elif menu == "🚢 ETA":
        df = load_data(SHEET_ID, "ETA")
        st.dataframe(df)

    elif menu == "🎪 Fuar Müşteri":
        df = load_data(SHEET_ID, "FuarMusteri")
        st.dataframe(df)

    elif menu == "📜 Proforma Takip":
        df = load_data(SHEET_ID, "Proformalar")
        proforma_takip(df)

    elif menu == "📦 Güncel Sipariş Durumu":
        df = load_data(SHEET_ID, "Kayıtlar")
        siparis_durumu(df)

    elif menu == "⏰ Vade Takip":
        df = load_data(SHEET_ID, "Evraklar")
        vade_takip(df)

    elif menu == "🚢 ETA Takip":
        df = load_data(SHEET_ID, "ETA")
        eta_takip(df)

    elif menu == "📈 Satış Performansı":
        df = load_data(SHEET_ID, "Proformalar")
        satis_performansi(df)

    elif menu == "🎪 Fuar Kayıt":
        df = load_data(SHEET_ID, "FuarMusteri")
        fuar_kayit(df)

if __name__ == "__main__":
    main()
