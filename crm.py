import streamlit as st
import pandas as pd
from google.oauth2 import service_account
from googleapiclient.discovery import build
import datetime
import numpy as np
from google.oauth2 import service_account
from googleapiclient.discovery import build
import smtplib
from email.message import EmailMessage
import io

import streamlit as st
import pandas as pd
from google.oauth2 import service_account
from googleapiclient.discovery import build

import streamlit as st
import pandas as pd
from google.oauth2 import service_account
from googleapiclient.discovery import build

# Google Sheets kimlik bilgisi
SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]
creds = service_account.Credentials.from_service_account_info(
    st.secrets["gcp_service_account"],
    scopes=SCOPES
)

# Servisi oluştur
service = build("sheets", "v4", credentials=creds)
sheet = service.spreadsheets()

# Sheet ID ve Range
SHEET_ID = "1nKuBKJPzpYC5TxNvc4G2OgI7miytuLBQE0n31I3yue0"
RANGE = "Sayfa1!A1:Z100"

try:
    result = sheet.values().get(spreadsheetId=SHEET_ID, range=RANGE).execute()
    values = result.get("values", [])

    if not values:
        st.warning("⚠️ Sheet boş görünüyor.")
    else:
        # En uzun satır kaç sütun içeriyor?
        max_len = max(len(row) for row in values)

        # Her satırı max uzunluğa tamamla (eksikse None ekle)
        padded_values = [row + [None] * (max_len - len(row)) for row in values]

        df = pd.DataFrame(padded_values[1:], columns=padded_values[0])
        st.success("✅ Google Sheets bağlantısı başarılı.")
        st.dataframe(df)

except Exception as e:
    st.error(f"❌ Google Sheet bağlantısı başarısız: {e}")
