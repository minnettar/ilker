import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime

# === Streamlit Ayarları ===
st.set_page_config(page_title="ŞEKEROĞLU İHRACAT CRM", layout="wide")

# === Kullanıcılar ===
USERS = {
    "export1": "Seker12345!",
    "admin": "Seker12345!",
    "Boss": "Seker12345!",
}

# === Giriş Sistemi ===
if "user" not in st.session_state:
    st.session_state.user = None

def login_screen():
    col1, col2 = st.columns([2, 6])
    with col1:
        st.image("https://www.sekeroglugroup.com/storage/settings/xdp5r6DZIFJMNGOStqwvKCiVHDhYxA84jFr61TNp.svg", width=150)
    with col2:
        st.title("ŞEKEROĞLU CRM - Giriş Ekranı")

    username = st.text_input("Kullanıcı Adı")
    password = st.text_input("Şifre", type="password")
    login_btn = st.button("Giriş Yap")

    if login_btn:
        if username in USERS and password == USERS[username]:
            st.session_state.user = username
            st.rerun()
        else:
            st.error("Kullanıcı adı veya şifre hatalı.")

if not st.session_state.user:
    login_screen()
    st.stop()

# === Çıkış ===
if st.sidebar.button("🚪 Çıkış Yap"):
    st.session_state.user = None
    st.rerun()

# === Google Sheets Bağlantısı ===
scope = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
credentials = Credentials.from_service_account_info(st.secrets["gcp_service_account"], scopes=scope)
client = gspread.authorize(credentials)

# === Sheet Ayarları ===
SPREADSHEET_URL = "https://docs.google.com/spreadsheets/d/1nKuBKJPzpYC5TxNvc4G2OgI7miytuLBQE0n31I3yue0"
sheet = client.open_by_url(SPREADSHEET_URL)

try:
    musteri_sheet = sheet.worksheet("Sayfa1")
    kayit_sheet = sheet.worksheet("Kayıtlar")

    df_musteri = pd.DataFrame(musteri_sheet.get_all_records())
    df_kayit = pd.DataFrame(kayit_sheet.get_all_records())
except Exception as e:
    st.error(f"Google Sheet bağlantısı başarısız: {e}")
    st.stop()

# === Ülke ve Temsilci Listeleri ===
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

# === Menü Butonları ===
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

# --- Menü Butonları (kullanıcıya göre) ---
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

# Kullanıcıya özel menü
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


import smtplib
from email.message import EmailMessage

# Yeni cari için txt dosyasını oluşturma fonksiyonu
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
            f"Para Birimi: {cari_dict.get('Para Birimi', '')}\n"  # Para birimini de ekliyoruz
            f"DT Seçimi: {cari_dict.get('DT Seçimi', '')}\n"  # DT seçimini de ekliyoruz
        )

# E-posta göndermek için fonksiyon
def send_email_with_txt(to_email, subject, body, file_path):
    from_email = "todo@sekeroglugroup.com"  # Gönderen e-posta adresi
    password = "vbgvforwwbcpzhxf"  # Gönderen e-posta şifresi

    # E-posta mesajını oluştur
    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = from_email
    msg["To"] = ", ".join(to_email)  # Birden fazla alıcıyı virgülle ayırarak ekliyoruz
    msg.set_content(body)

    # TXT dosyasını e-postaya ekle
    with open(file_path, "rb") as f:
        msg.add_attachment(
            f.read(),
            maintype="text",
            subtype="plain",
            filename="yeni_cari.txt"  # Dosyanın ismi
        )

    # E-posta göndermek için SMTP kullan
    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as smtp:
        smtp.login(from_email, password)
        smtp.send_message(msg)
