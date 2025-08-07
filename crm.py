import streamlit as st
import pandas as pd
from google.oauth2 import service_account
from googleapiclient.discovery import build

# Gerekli scope
SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]

# Kimlik doğrulama: Streamlit secrets üzerinden
creds = service_account.Credentials.from_service_account_info(
    st.secrets["gcp_service_account"],
    scopes=SCOPES
)

# Google Sheets servis nesnesi oluştur
service = build('sheets', 'v4', credentials=creds)
sheet = service.spreadsheets()

# Test: Google Sheet'e bağlanabiliyor muyuz?
SHEET_ID = "1nKuBKJPzpYC5TxNvc4G2OgI7miytuLBQE0n31I3yue0"  # kendi sheet ID'n ile değiştir
RANGE = "Sayfa1!A1:D5"  # örnek aralık

try:
    result = sheet.values().get(spreadsheetId=SHEET_ID, range=RANGE).execute()
    values = result.get('values', [])
    st.success("✅ Google Sheet bağlantısı başarılı.")
    st.write(values)
except Exception as e:
    st.error(f"❌ Google Sheet bağlantısı başarısız: {e}")
