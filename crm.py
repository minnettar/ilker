import streamlit as st
from google.oauth2 import service_account
from googleapiclient.discovery import build

# Yetki alanı
SCOPES = ["https://www.googleapis.com/auth/spreadsheets.readonly"]

# Streamlit Secrets'tan kimlik bilgilerini oku
try:
    creds = service_account.Credentials.from_service_account_info(
        st.secrets["gcp_service_account"],
        scopes=SCOPES
    )

    # Google Sheets API servisini başlat
    service = build("sheets", "v4", credentials=creds)
    sheet = service.spreadsheets()

    # Deneme için hücre okuma
    SHEET_ID = "1nKuBKJPzpYC5TxNvc4G2OgI7miytuLBQE0n31I3yue0"  # Kendi Sheet ID'nizi girin
    RANGE = "Müşteriler!A1"

    result = sheet.values().get(spreadsheetId=SHEET_ID, range=RANGE).execute()

    if "values" in result:
        st.success("✅ Google Sheets bağlantısı başarılı!")
        st.write("Okunan veri:", result["values"])
    else:
        st.warning("⚠️ Google Sheets bağlantısı var ama veri alınamadı.")

except Exception as e:
    st.error(f"❌ Bağlantı kurulamadı: {e}")
