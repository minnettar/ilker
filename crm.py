import streamlit as st
import pandas as pd
from google.oauth2 import service_account
from googleapiclient.discovery import build

# Kimlik doğrulama: Streamlit secrets üzerinden al
SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]
creds = service_account.Credentials.from_service_account_info(
    st.secrets["gcp_service_account"],
    scopes=SCOPES
)

# Google Sheets servisi oluştur
service = build("sheets", "v4", credentials=creds)
sheet = service.spreadsheets()

# Google Sheet ID ve aralık
SHEET_ID = "1nKuBKJPzpYC5TxNvc4G2OgI7miytuLBQE0n31I3yue0"

try:
    result = sheet.values().get(spreadsheetId=SHEET_ID, range=RANGE).execute()
    values = result.get("values", [])

    if not values:
        st.warning("⚠️ Sheet boş görünüyor.")
    else:
        df = pd.DataFrame(values[1:], columns=values[0])
        st.success("✅ Google Sheets bağlantısı başarılı.")
        st.dataframe(df)

except Exception as e:
    st.error(f"❌ Google Sheet bağlantısı başarısız: {e}")
