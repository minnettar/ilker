import streamlit as st
import pandas as pd
import json
from google.oauth2 import service_account
from googleapiclient.discovery import build

creds = service_account.Credentials.from_service_account_info(info, scopes=[
    "https://www.googleapis.com/auth/spreadsheets.readonly"
])

# Google Sheets servisini başlat
service = build("sheets", "v4", credentials=creds)
sheet = service.spreadsheets()

# Google Sheets ID ve aralık
SPREADSHEET_ID = "1IF6CN4oHEMk6IEE40ZGixPkfnNHLYXnQ"
RANGE_NAME = "A1:K10"  # İlk 10 satırı getir

try:
    result = sheet.values().get(spreadsheetId=SPREADSHEET_ID, range=RANGE_NAME).execute()
    values = result.get("values", [])

    if not values:
        st.error("❌ Tablo boş görünüyor.")
    else:
        df = pd.DataFrame(values[1:], columns=values[0]) if len(values) > 1 else pd.DataFrame(values)
        st.success("✅ Google Sheets bağlantısı başarılı.")
        st.dataframe(df)

except Exception as e:
    st.error(f"❌ Bağlantı kurulamadı: {e}")
