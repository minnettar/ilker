# === Blok-1: Kurulum, Yetkilendirme, Yardımcı Fonksiyonlar ===
import os
import io
import datetime
import pandas as pd
import streamlit as st
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload  # Drive upload için

# --- Ayarlar ---
SHEET_ID = "1nKuBKJPzpYC5TxNvc4G2OgI7miytuLBQE0n31I3yue0"   # Google Sheets ID
HAVE_DRIVE = True  # PDF yükleme kullanacaksanız True bırakın
SIPARIS_FORMU_FOLDER_ID = "1xeTdhOE1Cc6ohJsRzPVlCMMraBIXWO9w"  # Drive klasör ID (sipariş formları)

# --- Kimlik (Streamlit secrets üzerinden) ---
# st.secrets["gcp_service_account"] içinde tüm service account JSON'u olmalı.
SCOPES_SHEETS = ["https://www.googleapis.com/auth/spreadsheets"]
SCOPES_DRIVE  = ["https://www.googleapis.com/auth/drive.file"]

# Sheets creds
creds_sheets = service_account.Credentials.from_service_account_info(
    st.secrets["gcp_service_account"],
    scopes=SCOPES_SHEETS
)

# Drive creds (isteğe bağlı)
creds_drive = service_account.Credentials.from_service_account_info(
    st.secrets["gcp_service_account"],
    scopes=SCOPES_DRIVE
) if HAVE_DRIVE else None

# --- Servisler ---
sheets_service = build("sheets", "v4", credentials=creds_sheets)
sheet = sheets_service.spreadsheets()

drive_service = build("drive", "v3", credentials=creds_drive) if HAVE_DRIVE else None


# --- Yardımcılar ---

def load_sheet_as_df(sheet_name: str, expected_columns: list[str]) -> pd.DataFrame:
    """
    Google Sheets'ten (sheet_name) aralığını okuyup DataFrame döner.
    İlk satır başlık kabul edilir. Eksik kolonları boş string ile tamamlar.
    """
    try:
        resp = sheet.values().get(spreadsheetId=SHEET_ID, range=sheet_name).execute()
        values = resp.get("values", [])
        if not values:
            return pd.DataFrame(columns=expected_columns)
        header, rows = values[0], values[1:]
        df = pd.DataFrame(rows, columns=header)

        # Eksik kolonları ekle
        for col in expected_columns:
            if col not in df.columns:
                df[col] = ""

        # Extra başlıklar olabilir; ama biz expected_columns sırasını tercih ederiz
        # olmayanlar zaten eklendi; sıralamayı koru:
        df = df[[c for c in expected_columns]]
        return df
    except Exception as e:
        st.warning(f"{sheet_name} okunamadı: {e}")
        return pd.DataFrame(columns=expected_columns)


def _df_sanitize_for_sheets(df: pd.DataFrame) -> pd.DataFrame:
    """
    NaN -> "" ve tüm hücreleri stringe çevirir (Sheets API JSON hatalarını önler).
    """
    safe = df.copy()
    safe = safe.fillna("")
    for c in safe.columns:
        safe[c] = safe[c].astype(str)
    return safe


def df_to_sheet(sheet_name: str, df: pd.DataFrame):
    """
    Bir DataFrame'i (başlık dahil) verilen sayfaya yazar.
    Mevcut içeriği temizler, sonra komple günceller.
    """
    safe = _df_sanitize_for_sheets(df)
    body = {"values": [list(safe.columns)] + safe.values.tolist()}

    # Önce temizle
    sheet.values().clear(spreadsheetId=SHEET_ID, range=sheet_name).execute()
    # Sonra yaz
    sheet.values().update(
        spreadsheetId=SHEET_ID,
        range=sheet_name,
        valueInputOption="RAW",
        body=body
    ).execute()


def upload_file_to_drive(file_path: str, filename: str, folder_id: str = None) -> str:
    """
    Dosyayı Drive'a yükler, 'link ile herkes görüntüleyebilir' izni verir,
    ve webViewLink (veya klasik paylaşım linkini) döner.
    HAVE_DRIVE=False ise boş string döner.
    """
    if not HAVE_DRIVE or drive_service is None:
        return ""
    if folder_id is None:
        folder_id = SIPARIS_FORMU_FOLDER_ID

    file_metadata = {"name": filename, "parents": [folder_id]}
    media = MediaFileUpload(file_path, mimetype="application/pdf", resumable=True)
    created = drive_service.files().create(
        body=file_metadata, media_body=media, fields="id"
    ).execute()
    file_id = created["id"]

    # Bağlantıya sahip olanlar görüntüleyebilsin
    try:
        drive_service.permissions().create(
            fileId=file_id, body={"type": "anyone", "role": "reader"}
        ).execute()
    except Exception:
        pass

    # Kullanışlı link
    link_info = drive_service.files().get(fileId=file_id, fields="webViewLink").execute()
    return link_info.get("webViewLink", f"https://drive.google.com/file/d/{file_id}/view?usp=sharing")
