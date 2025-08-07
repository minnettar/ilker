import streamlit as st
import pandas as pd
import datetime
import numpy as np
from google.oauth2 import service_account
from googleapiclient.discovery import build
import smtplib
from email.message import EmailMessage
import io

 # --- Google Sheets Ayarları ---
SHEET_ID = "1nKuBKJPzpYC5TxNvc4G2OgI7miytuLBQE0n31I3yue0"

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive"
]

# Cloud'da service_account bilgileri secrets.toml'dan okunur:
creds = service_account.Credentials.from_service_account_info(
    st.secrets["gcp_service_account"],
    scopes=SCOPES
)

service = build('sheets', 'v4', credentials=creds)
sheet = service.spreadsheets()

# --- Fonksiyonlar (Google Sheet'le okuma/yazma) ---
def sheet_to_df(sheet, sheet_id, sheet_name):
    result = sheet.values().get(spreadsheetId=sheet_id, range=sheet_name).execute()
    values = result.get('values', [])
    if not values:
        return pd.DataFrame()
    return pd.DataFrame(values[1:], columns=values[0])

def df_to_sheet(sheet, sheet_id, sheet_name, df):
    values = [df.columns.tolist()] + df.fillna("").astype(str).values.tolist()
    sheet.values().update(
        spreadsheetId=sheet_id,
        range=sheet_name,
        valueInputOption="RAW",
        body={"values": values}
    ).execute()

# --- Login Sistemi ---
st.set_page_config(page_title="ŞEKEROĞLU İHRACAT CRM", layout="wide")

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
    login_btn = st.button("Giriş Yap")
    if login_btn:
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

# --- Ülke ve Temsilci Listeleri ---
ulke_listesi = sorted([
    "Afganistan", "Almanya", "Amerika Birleşik Devletleri", "Andorra", "Angola", "Antigua ve Barbuda", "Arjantin",
    "Arnavutluk", "Avustralya", "Avusturya", "Azerbaycan", "Bahamalar", "Bahreyn", "Bangladeş", "Barbados", "Belçika",
    "Belize", "Benin", "Beyaz Rusya", "Bhutan", "Birleşik Arap Emirlikleri", "Birleşik Krallık", "Bolivya",
    "Bosna-Hersek", "Botsvana", "Brezilya", "Brunei", "Bulgaristan", "Burkina Faso", "Burundi", "Butan",
    "Cezayir", "Çad", "Çekya", "Çin", "Danimarka", "Doğu Timor", "Dominik Cumhuriyeti", "Dominika", "Ekvador",
    "Ekvator Ginesi", "El Salvador", "Endonezya", "Eritre", "Ermenistan", "Estonya", "Etiyopya", "Fas",
    "Fiji", "Fildişi Sahili", "Filipinler", "Filistin", "Finlandiya", "Fransa", "Gabon", "Gambia",
    "Gana", "Gine", "Gine-Bissau", "Grenada", "Guatemala", "Guyana", "Güney Afrika", "Güney Kore",
    "Güney Sudan", "Gürcistan", "Haiti", "Hindistan", "Hırvatistan", "Hollanda", "Honduras", "Hong Kong",
    "Irak", "İran", "İrlanda", "İspanya", "İsrail", "İsveç", "İsviçre", "İtalya", "İzlanda", "Jamaika",
    "Japonya", "Kamboçya", "Kamerun", "Kanada", "Karadağ", "Katar", "Kazakistan", "Kenya", "Kırgızistan",
    "Kiribati", "Kolombiya", "Komorlar", "Kongo", "Kongo Demokratik Cumhuriyeti", "Kostarika", "Küba",
    "Kuveyt", "Kuzey Kore", "Kuzey Makedonya", "Laos", "Lesotho", "Letonya", "Liberya", "Libya",
    "Liechtenstein", "Litvanya", "Lübnan", "Lüksemburg", "Macaristan", "Madagaskar", "Malavi", "Maldivler",
    "Malezya", "Mali", "Malta", "Marshall Adaları", "Meksika", "Mısır", "Mikronezya", "Moğolistan", "Moldova",
    "Monako", "Morityus", "Mozambik", "Myanmar", "Namibya", "Nauru", "Nepal", "Nijer", "Nijerya",
    "Nikaragua", "Norveç", "Orta Afrika Cumhuriyeti", "Özbekistan", "Pakistan", "Palau", "Panama", "Papua Yeni Gine",
    "Paraguay", "Peru", "Polonya", "Portekiz", "Romanya", "Ruanda", "Rusya", "Saint Kitts ve Nevis",
    "Saint Lucia", "Saint Vincent ve Grenadinler", "Samoa", "San Marino", "Sao Tome ve Principe", "Senegal",
    "Seyşeller", "Sırbistan", "Sierra Leone", "Singapur", "Slovakya", "Slovenya", "Solomon Adaları", "Somali",
    "Sri Lanka", "Sudan", "Surinam", "Suriye", "Suudi Arabistan", "Svaziland", "Şili", "Tacikistan", "Tanzanya",
    "Tayland", "Tayvan", "Togo", "Tonga", "Trinidad ve Tobago", "Tunus", "Tuvalu", "Türkiye", "Türkmenistan",
    "Uganda", "Ukrayna", "Umman", "Uruguay", "Ürdün", "Vanuatu", "Vatikan", "Venezuela", "Vietnam",
    "Yemen", "Yeni Zelanda", "Yunanistan", "Zambiya", "Zimbabve"
]) + ["Diğer"]

temsilci_listesi = ["KEMAL İLKER ÇELİKKALKAN", "HÜSEYİN POLAT", "EFE YILDIRIM", "FERHAT ŞEKEROĞLU"]

# --- LOGO ---
LOGO_URL = "https://www.sekeroglugroup.com/storage/settings/xdp5r6DZIFJMNGOStqwvKCiVHDhYxA84jFr61TNp.svg"
col1, col2 = st.columns([3, 7])
with col1:
    st.image(LOGO_URL, width=300)
with col2:
    st.markdown("""
        <style>
        .block-container { padding-top: 0.2rem !important; }
        </style>
        <div style="display:flex; flex-direction:column; align-items:flex-start; width:100%; margin-bottom:10px;">
            <h1 style="color: #219A41; font-weight: bold; font-size: 2.8em; letter-spacing:2px; margin:0; margin-top:-8px;">
                ŞEKEROĞLU İHRACAT CRM
            </h1>
        </div>
    """, unsafe_allow_html=True)

# --- Sheetlerden DataFrame'e Yükle ---
try:
    df_musteri = sheet_to_df(sheet, SHEET_ID, "Sayfa1")
except Exception:
    df_musteri = pd.DataFrame(columns=[
        "Müşteri Adı", "Telefon", "E-posta", "Adres", "Ülke", "Satış Temsilcisi", "Kategori", "Durum", "Vade (Gün)", "Ödeme Şekli",
        "Para Birimi", "DT Seçimi"
    ])
try:
    df_teklif = sheet_to_df(sheet, SHEET_ID, "Teklifler")
except Exception:
    df_teklif = pd.DataFrame(columns=[
        "Müşteri Adı", "Tarih", "Teklif No", "Tutar", "Ürün/Hizmet", "Açıklama", "Durum", "PDF"
    ])
try:
    df_proforma = sheet_to_df(sheet, SHEET_ID, "Proformalar")
except Exception:
    df_proforma = pd.DataFrame(columns=[
        "Müşteri Adı", "Tarih", "Proforma No", "Tutar", "Açıklama", "Durum", "PDF", "Sipariş Formu", "Vade", "Sevk Durumu"
    ])
try:
    df_evrak = sheet_to_df(sheet, SHEET_ID, "Evraklar")
except Exception:
    df_evrak = pd.DataFrame(columns=[
        "Müşteri Adı", "Fatura No", "Fatura Tarihi", "Vade Tarihi", "Tutar",
        "Commercial Invoice", "Sağlık Sertifikası", "Packing List",
        "Konşimento", "İhracat Beyannamesi", "Fatura PDF", "Sipariş Formu",
        "Yük Resimleri", "EK Belgeler"
    ])

# --- Menü Butonları ---
st.sidebar.markdown("""
<style>
.menu-btn {
    display: block;
    width: 100%;
    padding: 1em;
    margin-bottom: 10px;
    border: none;
    border-radius: 10px;
    font-size: 1.1em;
    font-weight: bold;
    color: white;
    cursor: pointer;
    transition: background 0.2s;
}
.menu-cari {background: linear-gradient(90deg, #43cea2, #185a9d);}
.menu-musteri {background: linear-gradient(90deg, #ffb347, #ffcc33);}
.menu-gorusme {background: linear-gradient(90deg, #ff5e62, #ff9966);}
.menu-teklif {background: linear-gradient(90deg, #8e54e9, #4776e6);}
.menu-proforma {background: linear-gradient(90deg, #11998e, #38ef7d);}
.menu-siparis {background: linear-gradient(90deg, #f7971e, #ffd200);}
.menu-evrak {background: linear-gradient(90deg, #f953c6, #b91d73);}
.menu-vade {background: linear-gradient(90deg, #43e97b, #38f9d7);}
.menu-eta {background: linear-gradient(90deg, #f857a6, #ff5858);}
.menu-btn:hover {filter: brightness(1.2);}
</style>
""", unsafe_allow_html=True)

menuler = [
    ("Özet Ekran", "menu-ozet", "📊"),
    ("Cari Ekleme", "menu-cari", "🧑‍💼"),
    ("Müşteri Listesi", "menu-musteri", "📒"),
    ("Görüşme / Arama / Ziyaret Kayıtları", "menu-gorusme", "☎️"),
    ("Fiyat Teklifleri", "menu-teklif", "💰"),
    ("Proforma Takibi", "menu-proforma", "📄"),
    ("Güncel Sipariş Durumu", "menu-siparis", "🚚"),
    ("Fatura & İhracat Evrakları", "menu-evrak", "📑"),
    ("Vade Takibi", "menu-vade", "⏰"),
    ("ETA Takibi", "menu-eta", "🛳️"),
    ("Fuar Müşteri Kayıtları", "menu-fuar", "🎫"),
    ("Medya Çekmecesi", "menu-medya", "🗂️"),
]

if st.session_state.user == "Boss":
    allowed_menus = [("Özet Ekran", "menu-ozet", "📊")]
else:
    allowed_menus = menuler

if "menu_state" not in st.session_state or st.session_state.menu_state not in [m[0] for m in allowed_menus]:
    st.session_state.menu_state = allowed_menus[0][0]

for i, (isim, renk, ikon) in enumerate(allowed_menus):
    if st.sidebar.button(f"{ikon} {isim}", key=f"menu_{isim}_{i}", help=isim):
        st.session_state.menu_state = isim

menu = st.session_state.menu_state

# --- Yeni Cari için txt oluştur ve e-posta gönder ---
def yeni_cari_txt_olustur(cari_dict, file_path="yeni_cari.txt"):
    with open(file_path, "w", encoding="utf-8") as f:
        f.write(
            f"Müşteri Adı: {cari_dict['Müşteri Adı']}\n"
            f"Telefon: {cari_dict['Telefon']}\n"
            f"E-posta: {cari_dict['E-posta']}\n"
            f"Adres: {cari_dict['Adres']}\n"
            f"Ülke: {cari_dict.get('Ülke', '')}\n"
            f"Satış Temsilcisi: {cari_dict.get('Satış Temsilcisi', '')}\n"
            f"Kategori: {cari_dict.get('Kategori', '')}\n"
            f"Durum: {cari_dict.get('Durum', '')}\n"
            f"Vade (Gün): {cari_dict.get('Vade (Gün)', '')}\n"
            f"Ödeme Şekli: {cari_dict.get('Ödeme Şekli', '')}\n"
            f"Para Birimi: {cari_dict.get('Para Birimi', '')}\n"
            f"DT Seçimi: {cari_dict.get('DT Seçimi', '')}\n"
        )

def send_email_with_txt(to_email, subject, body, file_path):
    from_email = "todo@sekeroglugroup.com"
    password = "vbgvforwwbcpzhxf"
    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = from_email
    msg["To"] = ", ".join(to_email)
    msg.set_content(body)
    with open(file_path, "rb") as f:
        msg.add_attachment(
            f.read(),
            maintype="text",
            subtype="plain",
            filename="yeni_cari.txt"
        )
    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as smtp:
        smtp.login(from_email, password)
        smtp.send_message(msg)

# --- Cari Ekleme Menüsü ---
if menu == "Cari Ekleme":
    st.markdown("<h2 style='color:#219A41; font-weight:bold;'>Yeni Müşteri Ekle</h2>", unsafe_allow_html=True)
    with st.form("add_customer"):
        name = st.text_input("Müşteri Adı")
        phone = st.text_input("Telefon")
        email = st.text_input("E-posta")
        address = st.text_area("Adres")
        ulke = st.selectbox("Ülke", ulke_listesi)
        temsilci = st.selectbox("Satış Temsilcisi", temsilci_listesi)
        kategori = st.selectbox("Kategori", ["Avrupa bayi", "bayi", "müşteri", "yeni müşteri"])
        aktif_pasif = st.selectbox("Durum", ["Aktif", "Pasif"])
        vade_gun = st.number_input("Vade (Gün Sayısı)", min_value=0, max_value=365, value=0, step=1)
        odeme_sekli = st.selectbox("Ödeme Şekli", ["Peşin", "Mal Mukabili", "Vesaik Mukabili", "Akreditif", "Diğer"])
        para_birimi = st.selectbox("Para Birimi", ["EURO", "USD", "TL", "RUBLE"])
        dt_secim = st.selectbox("DT Seçin", ["DT-1", "DT-2", "DT-3", "DT-4"])
        submitted = st.form_submit_button("Kaydet")
        if submitted:
            if name.strip() == "":
                st.error("Müşteri adı boş olamaz!")
            else:
                new_row = {
                    "Müşteri Adı": name,
                    "Telefon": phone,
                    "E-posta": email,
                    "Adres": address,
                    "Ülke": ulke,
                    "Satış Temsilcisi": temsilci,
                    "Kategori": kategori,
                    "Durum": aktif_pasif,
                    "Vade (Gün)": vade_gun,
                    "Ödeme Şekli": odeme_sekli,
                    "Para Birimi": para_birimi,
                    "DT Seçimi": dt_secim
                }
                df_musteri = pd.concat([df_musteri, pd.DataFrame([new_row])], ignore_index=True)
                df_to_sheet(sheet, SHEET_ID, "Sayfa1", df_musteri)
                yeni_cari_txt_olustur(new_row)
                try:
                    send_email_with_txt(
                        to_email=["muhasebe@sekeroglugroup.com", "h.boy@sekeroglugroup.com"],
                        subject="Yeni Cari Açılışı",
                        body="Muhasebe için yeni cari açılışı ekte gönderilmiştir.",
                        file_path="yeni_cari.txt"
                    )
                    st.success("Müşteri eklendi ve e-posta ile muhasebeye gönderildi!")
                except Exception as e:
                    st.warning(f"Müşteri eklendi ama e-posta gönderilemedi: {e}")
                st.rerun()
