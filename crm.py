import streamlit as st
import pandas as pd
import numpy as np
import os
import io
import datetime
from google.oauth2 import service_account
from googleapiclient.discovery import build
import smtplib
from email.message import EmailMessage
import tempfile 

# ==== KULLANICI GİRİŞİ SİSTEMİ ====
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

# Sol menüde çıkış butonu
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

temsilci_listesi = [
    "KEMAL İLKER ÇELİKKALKAN",
    "HÜSEYİN POLAT",
    "EFE YILDIRIM",
    "FERHAT ŞEKEROĞLU"
]

# --- LOGO URL'inden SVG GÖSTER ---
LOGO_URL = "https://www.sekeroglugroup.com/storage/settings/xdp5r6DZIFJMNGOStqwvKCiVHDhYxA84jFr61TNp.svg"

col1, col2 = st.columns([2, 8])
with col1:
    st.markdown(
        f"""
        <img src="{LOGO_URL}" width="180" style="margin-bottom:12px;margin-top:-10px;" />
        """,
        unsafe_allow_html=True,
    )
with col2:
    st.markdown("""
        <h1 style="color: #219A41; font-weight: bold; font-size: 2.6em; letter-spacing:2px; margin:0; margin-top:-8px;">
            ŞEKEROĞLU İHRACAT CRM
        </h1>
    """, unsafe_allow_html=True)

    import streamlit as st
import pandas as pd
from google.oauth2 import service_account
from googleapiclient.discovery import build

# --- Service Account ve Sheet Kimlikleri ---
SHEET_ID = "1nKuBKJPzpYC5TxNvc4G2OgI7miytuLBQE0n31I3yue0"
SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]
SHEET_NAMES = {
    "df_musteri": "Sayfa1",
    "df_kayit": "Kayıtlar",
    "df_teklif": "Teklifler",
    "df_proforma": "Proformalar",
    "df_evrak": "Evraklar",
    "df_eta": "ETA",
    "df_fuar_musteri": "FuarMusteri"
}

# --- Google Sheets API Bağlantısı ---
@st.cache_resource
def get_service():
    credentials = service_account.Credentials.from_service_account_info(
        st.secrets["gcp_service_account"], scopes=SCOPES
    )
    service = build("sheets", "v4", credentials=credentials)
    return service.spreadsheets()

sheet = get_service()

# --- Sheet'ten DataFrame Yükleme ---
def sheet_to_df(sheet_name, header_row=1):
    result = sheet.values().get(
        spreadsheetId=SHEET_ID,
        range=sheet_name
    ).execute()
    values = result.get("values", [])
    if not values or len(values) < header_row:
        return pd.DataFrame()
    return pd.DataFrame(values[header_row:], columns=values[header_row - 1])

# --- DataFrame'i Sheet'e Yazma ---
def df_to_sheet(df, sheet_name):
    values = [df.columns.tolist()] + df.astype(str).fillna("").values.tolist()
    sheet.values().update(
        spreadsheetId=SHEET_ID,
        range=sheet_name,
        valueInputOption="RAW",
        body={"values": values}
    ).execute()

# --- DataFrame Yükle (Her sheet için) ---
df_musteri = sheet_to_df(SHEET_NAMES["df_musteri"])
if df_musteri.empty:
    df_musteri = pd.DataFrame(columns=[
        "Müşteri Adı", "Telefon", "E-posta", "Adres", "Ülke",
        "Satış Temsilcisi", "Kategori", "Durum", "Vade (Gün)", "Ödeme Şekli"
    ])

df_kayit = sheet_to_df(SHEET_NAMES["df_kayit"])
if df_kayit.empty:
    df_kayit = pd.DataFrame(columns=["Müşteri Adı", "Tarih", "Tip", "Açıklama"])

df_teklif = sheet_to_df(SHEET_NAMES["df_teklif"])
if df_teklif.empty:
    df_teklif = pd.DataFrame(columns=[
        "Müşteri Adı", "Tarih", "Teklif No", "Tutar",
        "Ürün/Hizmet", "Açıklama", "Durum", "PDF"
    ])

df_proforma = sheet_to_df(SHEET_NAMES["df_proforma"])
if df_proforma.empty:
    df_proforma = pd.DataFrame(columns=[
        "Müşteri Adı", "Tarih", "Proforma No", "Tutar", "Açıklama",
        "Durum", "PDF", "Sipariş Formu", "Vade", "Sevk Durumu"
    ])

df_evrak = sheet_to_df(SHEET_NAMES["df_evrak"])
if df_evrak.empty:
    df_evrak = pd.DataFrame(columns=[
        "Müşteri Adı", "Fatura No", "Fatura Tarihi", "Vade Tarihi", "Tutar",
        "Commercial Invoice", "Sağlık Sertifikası", "Packing List",
        "Konşimento", "İhracat Beyannamesi", "Fatura PDF", "Sipariş Formu",
        "Yük Resimleri", "EK Belgeler"
    ])

df_eta = sheet_to_df(SHEET_NAMES["df_eta"])
if df_eta.empty:
    df_eta = pd.DataFrame(columns=["Müşteri Adı", "Proforma No", "ETA Tarihi", "Açıklama"])

df_fuar_musteri = sheet_to_df(SHEET_NAMES["df_fuar_musteri"])
if df_fuar_musteri.empty:
    df_fuar_musteri = pd.DataFrame(columns=[
        "Fuar Adı", "Müşteri Adı", "Ülke", "Telefon", "E-mail", "Açıklamalar", "Tarih"
    ])

# --- Tüm DataFrame'leri Sheet'e Güncelleme Fonksiyonu ---
def update_all_sheets():
    df_to_sheet(df_musteri, SHEET_NAMES["df_musteri"])
    df_to_sheet(df_kayit, SHEET_NAMES["df_kayit"])
    df_to_sheet(df_teklif, SHEET_NAMES["df_teklif"])
    df_to_sheet(df_proforma, SHEET_NAMES["df_proforma"])
    df_to_sheet(df_evrak, SHEET_NAMES["df_evrak"])
    df_to_sheet(df_eta, SHEET_NAMES["df_eta"])
    df_to_sheet(df_fuar_musteri, SHEET_NAMES["df_fuar_musteri"])

    # --- Menü Stili ---
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

# Kullanıcıya özel menü kontrolü
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

def yeni_cari_txt_olustur(cari_dict):
    txt_content = (
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
    # Geçici dosya ile bulutta güvenli kaydet
    temp = tempfile.NamedTemporaryFile(mode="w+", delete=False, suffix=".txt", encoding="utf-8")
    temp.write(txt_content)
    temp.flush()
    return temp.name  # Dosya yolunu döndür

def send_email_with_txt(to_email, subject, body, file_path):
    from_email = "todo@sekeroglugroup.com"
    password = st.secrets["MAIL_PASSWORD"]  # Şifreyi secrets.toml'a taşı!
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

if menu == "Özet Ekran":
    st.markdown("<h2 style='color:#219A41; font-weight:bold;'>ŞEKEROĞLU İHRACAT CRM - Özet Ekran</h2>", unsafe_allow_html=True)

    # ---- Bekleyen Teklifler Tablosu ----
    st.markdown("### 💰 Bekleyen Teklifler")
    bekleyen_teklifler = df_teklif[df_teklif["Durum"] == "Açık"] if "Durum" in df_teklif.columns else pd.DataFrame()
    try:
        toplam_teklif = pd.to_numeric(bekleyen_teklifler["Tutar"], errors="coerce").sum()
    except Exception:
        toplam_teklif = 0
    st.markdown(f"<div style='font-size:1.3em; color:#11998e; font-weight:bold;'>Toplam: {toplam_teklif:,.2f} $</div>", unsafe_allow_html=True)
    if bekleyen_teklifler.empty:
        st.info("Bekleyen teklif yok.")
    else:
        st.dataframe(
            bekleyen_teklifler[["Müşteri Adı", "Tarih", "Teklif No", "Tutar", "Ürün/Hizmet", "Açıklama"]],
            use_container_width=True
        )

    # ---- Bekleyen Proformalar Tablosu ----
    st.markdown("### 📄 Bekleyen Proformalar")
    bekleyen_proformalar = df_proforma[df_proforma["Durum"] == "Beklemede"] if "Durum" in df_proforma.columns else pd.DataFrame()
    try:
        toplam_proforma = pd.to_numeric(bekleyen_proformalar["Tutar"], errors="coerce").sum()
    except Exception:
        toplam_proforma = 0
    st.markdown(f"<div style='font-size:1.3em; color:#f7971e; font-weight:bold;'>Toplam: {toplam_proforma:,.2f} $</div>", unsafe_allow_html=True)
    if bekleyen_proformalar.empty:
        st.info("Bekleyen proforma yok.")
    else:
        st.dataframe(
            bekleyen_proformalar[["Müşteri Adı", "Proforma No", "Tarih", "Tutar", "Açıklama"]],
            use_container_width=True
        )

    # ---- Siparişe Dönüşen (Sevk Bekleyen) Tablosu (Termin Tarihine Göre) ----
    st.markdown("### 🚚 Siparişe Dönüşen (Sevk Bekleyen) Siparişler")
    for col in ["Sevk Durumu", "Termin Tarihi", "Satış Temsilcisi", "Ödeme Şekli", "Ülke"]:
        if col not in df_proforma.columns:
            df_proforma[col] = ""
    siparisler = df_proforma[
        (df_proforma["Durum"] == "Siparişe Dönüştü") &
        (~df_proforma["Sevk Durumu"].isin(["Sevkedildi", "Ulaşıldı"]))
    ].copy()
    siparisler["Termin Tarihi Order"] = pd.to_datetime(siparisler["Termin Tarihi"], errors="coerce")
    siparisler = siparisler.sort_values("Termin Tarihi Order", ascending=True)
    if siparisler.empty:
        st.info("Henüz sevk edilmeyi bekleyen sipariş yok.")
    else:
        siparisler["Tarih"] = pd.to_datetime(siparisler["Tarih"], errors="coerce").dt.strftime("%d/%m/%Y")
        siparisler["Termin Tarihi"] = pd.to_datetime(siparisler["Termin Tarihi"], errors="coerce").dt.strftime("%d/%m/%Y")
        tablo = siparisler[
            ["Tarih", "Müşteri Adı", "Termin Tarihi", "Ülke", "Satış Temsilcisi", "Ödeme Şekli", "Proforma No", "Tutar", "Açıklama"]
        ]
        st.dataframe(tablo, use_container_width=True)
        try:
            toplam = pd.to_numeric(siparisler["Tutar"], errors="coerce").sum()
        except Exception:
            toplam = 0
        st.markdown(f"<div style='color:#219A41; font-weight:bold;'>*Toplam Bekleyen Sevk: {toplam:,.2f} $*</div>", unsafe_allow_html=True)

    # ---- Yolda Olan (Sevk Edildi) Siparişler [ETA] ----
    st.markdown("### ⏳ Yolda Olan (ETA Takibi) Siparişler")
    eta_yolda = df_proforma[
        (df_proforma["Sevk Durumu"] == "Sevkedildi") & (~df_proforma["Sevk Durumu"].isin(["Ulaşıldı"]))
    ] if "Sevk Durumu" in df_proforma.columns else pd.DataFrame()
    try:
        toplam_eta = pd.to_numeric(eta_yolda["Tutar"], errors="coerce").sum()
    except Exception:
        toplam_eta = 0
    st.markdown(f"<div style='font-size:1.3em; color:#c471f5; font-weight:bold;'>Toplam: {toplam_eta:,.2f} $</div>", unsafe_allow_html=True)
    if eta_yolda.empty:
        st.info("Yolda olan (sevk edilmiş) sipariş yok.")
    else:
        st.dataframe(
            eta_yolda[
                ["Müşteri Adı", "Ülke", "Proforma No", "Tarih", "Tutar", "Termin Tarihi", "Açıklama"]
            ],
            use_container_width=True
        )

    # ---- Son Teslim Edilmiş (Ulaşıldı) 5 Sipariş ----
    st.markdown("### ✅ Son Teslim Edilen (Ulaşıldı) 5 Sipariş")
    if "Sevk Durumu" in df_proforma.columns:
        teslim_edilenler = df_proforma[df_proforma["Sevk Durumu"] == "Ulaşıldı"]
        if not teslim_edilenler.empty:
            teslim_edilenler = teslim_edilenler.sort_values(
                by="Tarih", ascending=False
            ).head(5)
            teslim_edilenler["Termin Tarihi"] = pd.to_datetime(teslim_edilenler["Termin Tarihi"], errors="coerce").dt.strftime("%d/%m/%Y")
            teslim_edilenler["Tarih"] = pd.to_datetime(teslim_edilenler["Tarih"], errors="coerce").dt.strftime("%d/%m/%Y")
            st.dataframe(
                teslim_edilenler[
                    ["Müşteri Adı", "Ülke", "Proforma No", "Tarih", "Tutar", "Termin Tarihi", "Açıklama"]
                ],
                use_container_width=True
            )
        else:
            st.info("Teslim edilmiş sipariş yok.")
    else:
        st.info("Teslim edilmiş sipariş yok.")

    # ---- Vade Takibi Tablosu (sadece Boss görebilir) ----
    if st.session_state.user == "Boss":
        st.markdown("### 💸 Vadeli Fatura ve Tahsilat Takibi")
        for col in ["Proforma No", "Vade (gün)", "Ödendi", "Ülke", "Satış Temsilcisi", "Ödeme Şekli"]:
            if col not in df_evrak.columns:
                df_evrak[col] = "" if col != "Ödendi" else False
        df_evrak["Ödendi"] = df_evrak["Ödendi"].fillna(False).astype(bool)
        vade_df = df_evrak[df_evrak["Vade Tarihi"].notna() & (~df_evrak["Ödendi"])].copy()
        if vade_df.empty:
            st.info("Açık vade kaydı yok.")
        else:
            vade_df["Vade Tarihi"] = pd.to_datetime(vade_df["Vade Tarihi"])
            vade_df["Kalan Gün"] = (vade_df["Vade Tarihi"] - pd.to_datetime(datetime.date.today())).dt.days
            st.dataframe(
                vade_df[["Müşteri Adı", "Ülke", "Fatura No", "Vade Tarihi", "Tutar", "Kalan Gün"]],
                use_container_width=True
            )

    st.markdown("<hr>", unsafe_allow_html=True)
    st.info("Daha detaylı işlem yapmak için sol menüden ilgili bölüme geçebilirsiniz.")
        

