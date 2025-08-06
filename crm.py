import streamlit as st
import pandas as pd
from pydrive2.auth import GoogleAuth
from pydrive2.drive import GoogleDrive
import io
import os
import datetime
import smtplib
from email.message import EmailMessage
import numpy as np
import gspread
from google.oauth2.service_account import Credentials
from gspread_dataframe import get_as_dataframe, set_with_dataframe


st.set_page_config(page_title="ŞEKEROĞLU İHRACAT CRM", layout="wide")

# ==== KULLANICI GİRİŞİ SİSTEMİ ====
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

temsilci_listesi = ["KEMAL İLKER ÇELİKKALKAN", "HÜSEYİN POLAT", "EFE YILDIRIM", "FERHAT ŞEKEROĞLU"]

# --- LOGO (WEB LINKİNDEN AL) ---
logo_url = "https://www.sekeroglugroup.com/storage/settings/xdp5r6DZIFJMNGOStqwvKCiVHDhYxA84jFr61TNp.svg"

col1, col2 = st.columns([3, 7])
with col1:
    st.image(logo_url, width=300)
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

# --- Google Sheets ile bağlantı ---
SERVICE_ACCOUNT_FILE = 'service_account.json'
SPREADSHEET_ID = "1oQecN1xnsi9Eir0z3yyGWBcpOUKpg13lT_pAr5zp5AM"

gc = gspread.service_account(filename=SERVICE_ACCOUNT_FILE)
sh = gc.open_by_key(SPREADSHEET_ID)

# --- DataFrame'leri Google Sheets'ten Okuma ---
def read_all_dataframes():
    # Sayfa1: Müşteri tablosu
    try:
        ws_musteri = sh.worksheet("Sayfa1")
        df_musteri = get_as_dataframe(ws_musteri, evaluate_formulas=True, na_filter=False)
        df_musteri = df_musteri.loc[:, ~df_musteri.columns.str.contains('^Unnamed')]
    except Exception:
        df_musteri = pd.DataFrame(columns=[
            "Müşteri Adı", "Telefon", "E-posta", "Adres", "Ülke", "Satış Temsilcisi", "Kategori", "Durum", "Vade (Gün)", "Ödeme Şekli"
        ])

    try:
        ws_kayit = sh.worksheet("Kayıtlar")
        df_kayit = get_as_dataframe(ws_kayit, evaluate_formulas=True, na_filter=False)
        df_kayit = df_kayit.loc[:, ~df_kayit.columns.str.contains('^Unnamed')]
    except Exception:
        df_kayit = pd.DataFrame(columns=["Müşteri Adı", "Tarih", "Tip", "Açıklama"])

    try:
        ws_teklif = sh.worksheet("Teklifler")
        df_teklif = get_as_dataframe(ws_teklif, evaluate_formulas=True, na_filter=False)
        df_teklif = df_teklif.loc[:, ~df_teklif.columns.str.contains('^Unnamed')]
    except Exception:
        df_teklif = pd.DataFrame(columns=[
            "Müşteri Adı", "Tarih", "Teklif No", "Tutar", "Ürün/Hizmet", "Açıklama", "Durum", "PDF"
        ])

    try:
        ws_proforma = sh.worksheet("Proformalar")
        df_proforma = get_as_dataframe(ws_proforma, evaluate_formulas=True, na_filter=False)
        df_proforma = df_proforma.loc[:, ~df_proforma.columns.str.contains('^Unnamed')]
    except Exception:
        df_proforma = pd.DataFrame(columns=[
            "Müşteri Adı", "Tarih", "Proforma No", "Tutar", "Açıklama", "Durum", "PDF", "Sipariş Formu", "Vade", "Sevk Durumu"
        ])

    try:
        ws_evrak = sh.worksheet("Evraklar")
        df_evrak = get_as_dataframe(ws_evrak, evaluate_formulas=True, na_filter=False)
        df_evrak = df_evrak.loc[:, ~df_evrak.columns.str.contains('^Unnamed')]
    except Exception:
        df_evrak = pd.DataFrame(columns=[
            "Müşteri Adı", "Fatura No", "Fatura Tarihi", "Vade Tarihi", "Tutar",
            "Commercial Invoice", "Sağlık Sertifikası", "Packing List",
            "Konşimento", "İhracat Beyannamesi", "Fatura PDF", "Sipariş Formu",
            "Yük Resimleri", "EK Belgeler"
        ])

    try:
        ws_eta = sh.worksheet("ETA")
        df_eta = get_as_dataframe(ws_eta, evaluate_formulas=True, na_filter=False)
        df_eta = df_eta.loc[:, ~df_eta.columns.str.contains('^Unnamed')]
    except Exception:
        df_eta = pd.DataFrame(columns=["Müşteri Adı", "Proforma No", "ETA Tarihi", "Açıklama"])

    try:
        ws_fuar_musteri = sh.worksheet("FuarMusteri")
        df_fuar_musteri = get_as_dataframe(ws_fuar_musteri, evaluate_formulas=True, na_filter=False)
        df_fuar_musteri = df_fuar_musteri.loc[:, ~df_fuar_musteri.columns.str.contains('^Unnamed')]
    except Exception:
        df_fuar_musteri = pd.DataFrame(columns=[
            "Fuar Adı", "Müşteri Adı", "Ülke", "Telefon", "E-mail", "Açıklamalar", "Tarih"
        ])

    return (df_musteri, df_kayit, df_teklif, df_proforma, df_evrak, df_eta, df_fuar_musteri)

# --- DataFrame'leri Google Sheets'e Yazma ---
def update_all_sheets(df_musteri, df_kayit, df_teklif, df_proforma, df_evrak, df_eta, df_fuar_musteri):
    set_with_dataframe(sh.worksheet("Sayfa1"), df_musteri)
    set_with_dataframe(sh.worksheet("Kayıtlar"), df_kayit)
    set_with_dataframe(sh.worksheet("Teklifler"), df_teklif)
    set_with_dataframe(sh.worksheet("Proformalar"), df_proforma)
    set_with_dataframe(sh.worksheet("Evraklar"), df_evrak)
    set_with_dataframe(sh.worksheet("ETA"), df_eta)
    set_with_dataframe(sh.worksheet("FuarMusteri"), df_fuar_musteri)

# --- KODUNUN BAŞLANGICINDA BU SATIRI KOY! ---
df_musteri, df_kayit, df_teklif, df_proforma, df_evrak, df_eta, df_fuar_musteri = read_all_dataframes()



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

### ===========================
### === ÖZET MENÜ ===
### ===========================

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
            bekleyen_proformalar[["Müşteri Adı", "Proforma No", "Tarih", "Tutar", "Vade (gün)", "Açıklama"]],
            use_container_width=True
        )

    # ---- Siparişe Dönüşen Ama Sevkedilmemiş ve Ulaşıldı Olmayanlar ----
    st.markdown("### 🚚 Siparişe Dönüşen (Sevk Bekleyen) Siparişler")
    if "Sevk Durumu" not in df_proforma.columns:
        df_proforma["Sevk Durumu"] = ""
    if "Ülke" not in df_proforma.columns:
        df_proforma["Ülke"] = ""
    sevk_bekleyenler = df_proforma[
        (df_proforma["Durum"] == "Siparişe Dönüştü") &
        (~df_proforma["Sevk Durumu"].isin(["Sevkedildi", "Ulaşıldı"]))
    ] if "Durum" in df_proforma.columns else pd.DataFrame()
    try:
        toplam_siparis = pd.to_numeric(sevk_bekleyenler["Tutar"], errors="coerce").sum()
    except Exception:
        toplam_siparis = 0
    st.markdown(f"<div style='font-size:1.3em; color:#185a9d; font-weight:bold;'>Toplam: {toplam_siparis:,.2f} $</div>", unsafe_allow_html=True)
    if sevk_bekleyenler.empty:
        st.info("Sevk bekleyen sipariş yok.")
    else:
        st.dataframe(
            sevk_bekleyenler[
                ["Müşteri Adı", "Ülke", "Proforma No", "Tarih", "Tutar", "Vade (gün)", "Açıklama"]
            ],
            use_container_width=True
        )

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
                ["Müşteri Adı", "Ülke", "Proforma No", "Tarih", "Tutar", "Vade (gün)", "Açıklama"]
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
            st.dataframe(
                teslim_edilenler[
                    ["Müşteri Adı", "Ülke", "Proforma No", "Tarih", "Tutar", "Vade (gün)", "Açıklama"]
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
        # Eksikse yeni alanları ekle
        for col in ["Proforma No", "Vade (gün)", "Ödendi", "Ülke", "Satış Temsilcisi", "Ödeme Şekli"]:
            if col not in df_evrak.columns:
                df_evrak[col] = "" if col != "Ödendi" else False
        df_evrak["Ödendi"] = df_evrak["Ödendi"].fillna(False).astype(bool)

        # Vade tarihi boş olmayan ve ödenmemiş kayıtlar
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

### ===========================
### === CARİ EKLEME MENÜSÜ ===
### ===========================

# Cari Ekleme Formu Güncelleme
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

        # Yeni Para Birimi Seçeneği Ekledik
        para_birimi = st.selectbox("Para Birimi", ["EURO", "USD", "TL", "RUBLE"])

        # Yeni DT Seçeneklerini Ekledik (DT-1, DT-2, DT-3, DT-4)
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
                    "Para Birimi": para_birimi,  # Para birimini ekliyoruz
                    "DT Seçimi": dt_secim  # DT seçimini ekliyoruz
                }
                df_musteri = pd.concat([df_musteri, pd.DataFrame([new_row])], ignore_index=True)
                update_excel()

                # Yeni cari için TXT oluştur ve maille gönder
                yeni_cari_txt_olustur(new_row)
                try:
                    send_email_with_txt(
                        to_email=["muhasebe@sekeroglugroup.com", "h.boy@sekeroglugroup.com"],  # Birden fazla alıcı ekledik
                        subject="Yeni Cari Açılışı",
                        body="Muhasebe için yeni cari açılışı ekte gönderilmiştir.",
                        file_path="yeni_cari.txt"
                    )
                    st.success("Müşteri eklendi ve e-posta ile muhasebeye gönderildi!")
                except Exception as e:
                    st.warning(f"Müşteri eklendi ama e-posta gönderilemedi: {e}")
                st.rerun()

                

### ===========================
### === MÜŞTERİ LİSTESİ MENÜSÜ ===
### ===========================

import numpy as np  # Eksik bilgi mesajı için gerekli

if "Vade (Gün)" not in df_musteri.columns:
    df_musteri["Vade (Gün)"] = ""
if "Ülke" not in df_musteri.columns:
    df_musteri["Ülke"] = ""
if "Satış Temsilcisi" not in df_musteri.columns:
    df_musteri["Satış Temsilcisi"] = ""
if "Ödeme Şekli" not in df_musteri.columns:
    df_musteri["Ödeme Şekli"] = ""

if menu == "Müşteri Listesi":
    st.markdown("<h2 style='color:#219A41; font-weight:bold;'>Müşteri Listesi</h2>", unsafe_allow_html=True)
    
    # Sadece Aktif müşterileri göster
    if not df_musteri.empty:
        aktif_df = df_musteri[df_musteri["Durum"] == "Aktif"].sort_values("Müşteri Adı").reset_index(drop=True)
        # Eksik (NaN veya boş) alanlara uyarı metni ekle
        aktif_df = aktif_df.replace({np.nan: "Eksik bilgi, lütfen tamamlayın", "": "Eksik bilgi, lütfen tamamlayın"})
        if aktif_df.shape[0] == 0:
            st.markdown("<div style='color:#b00020; font-weight:bold; font-size:1.2em;'>Aktif müşteri kaydı yok.</div>", unsafe_allow_html=True)
        else:
            st.dataframe(aktif_df, use_container_width=True)

        st.markdown("<h4 style='margin-top: 32px;'>Müşteri Düzenle</h4>", unsafe_allow_html=True)
        # Kombo box seçenekleri yine tüm müşterilerden, alfabetik
        df_musteri_sorted = df_musteri.sort_values("Müşteri Adı").reset_index(drop=True)
        musteri_options = df_musteri_sorted.index.tolist()
        sec_index = st.selectbox(
            "Düzenlenecek Müşteriyi Seçin",
            options=musteri_options,
            format_func=lambda i: f"{df_musteri_sorted.at[i,'Müşteri Adı']} ({df_musteri_sorted.at[i,'Kategori']})"
        )
        with st.form("edit_existing_customer"):
            name = st.text_input("Müşteri Adı", value=df_musteri_sorted.at[sec_index, "Müşteri Adı"])
            phone = st.text_input("Telefon", value=df_musteri_sorted.at[sec_index, "Telefon"])
            email = st.text_input("E-posta", value=df_musteri_sorted.at[sec_index, "E-posta"])
            address = st.text_area("Adres", value=df_musteri_sorted.at[sec_index, "Adres"])
            ulke = st.selectbox("Ülke", ulke_listesi, index=ulke_listesi.index(df_musteri_sorted.at[sec_index, "Ülke"]) if df_musteri_sorted.at[sec_index, "Ülke"] in ulke_listesi else 0)
            temsilci = st.selectbox("Satış Temsilcisi", temsilci_listesi, index=temsilci_listesi.index(df_musteri_sorted.at[sec_index, "Satış Temsilcisi"]) if df_musteri_sorted.at[sec_index, "Satış Temsilcisi"] in temsilci_listesi else 0)
            kategori = st.selectbox(
                "Kategori", 
                sorted(["Avrupa bayi", "bayi", "müşteri", "yeni müşteri"]), 
                index=sorted(["Avrupa bayi", "bayi", "müşteri", "yeni müşteri"]).index(df_musteri_sorted.at[sec_index, "Kategori"])
                if df_musteri_sorted.at[sec_index, "Kategori"] in ["Avrupa bayi", "bayi", "müşteri", "yeni müşteri"] else 0
            )
            aktif_pasif = st.selectbox("Durum", ["Aktif", "Pasif"], index=0 if df_musteri_sorted.at[sec_index, "Durum"] == "Aktif" else 1)
            vade = st.text_input("Vade (Gün)", value=str(df_musteri_sorted.at[sec_index, "Vade (Gün)"]) if "Vade (Gün)" in df_musteri_sorted.columns else "")
            odeme_sekli = st.selectbox("Ödeme Şekli", ["Peşin", "Mal Mukabili", "Vesaik Mukabili", "Akreditif", "Diğer"], 
                                       index=["Peşin", "Mal Mukabili", "Vesaik Mukabili", "Akreditif", "Diğer"].index(df_musteri_sorted.at[sec_index, "Ödeme Şekli"]) if df_musteri_sorted.at[sec_index, "Ödeme Şekli"] in ["Peşin", "Mal Mukabili", "Vesaik Mukabili", "Akreditif", "Diğer"] else 0)
            guncelle = st.form_submit_button("Güncelle")
            if guncelle:
                # Eski indexi bulup güncelle (çünkü sorted kopyada çalışıyoruz)
                filtre = (df_musteri["Müşteri Adı"] == df_musteri_sorted.at[sec_index, "Müşteri Adı"])
                if filtre.any():
                    orj_idx = df_musteri[filtre].index[0]
                    df_musteri.at[orj_idx, "Müşteri Adı"] = name
                    df_musteri.at[orj_idx, "Telefon"] = phone
                    df_musteri.at[orj_idx, "E-posta"] = email
                    df_musteri.at[orj_idx, "Adres"] = address
                    df_musteri.at[orj_idx, "Ülke"] = ulke
                    df_musteri.at[orj_idx, "Satış Temsilcisi"] = temsilci
                    df_musteri.at[orj_idx, "Kategori"] = kategori
                    df_musteri.at[orj_idx, "Durum"] = aktif_pasif
                    df_musteri.at[orj_idx, "Vade (Gün)"] = vade
                    df_musteri.at[orj_idx, "Ödeme Şekli"] = odeme_sekli
                    update_excel()
                    st.success("Müşteri bilgisi güncellendi!")
                    st.rerun()
                else:
                    st.warning("Beklenmeyen hata: Kayıt bulunamadı.")
        # Silme butonu
        st.markdown("<h4 style='margin-top: 32px;'>Müşteri Sil</h4>", unsafe_allow_html=True)
        sil_btn = st.button("Seçili Müşteriyi Sil")
        if sil_btn:
            filtre = (df_musteri["Müşteri Adı"] == df_musteri_sorted.at[sec_index, "Müşteri Adı"])
            if filtre.any():
                orj_idx = df_musteri[filtre].index[0]
                df_musteri = df_musteri.drop(orj_idx).reset_index(drop=True)
                update_excel()
                st.success("Müşteri kaydı silindi!")
                st.rerun()
            else:
                st.warning("Beklenmeyen hata: Silinecek kayıt bulunamadı.")
    else:
        st.markdown("<div style='color:#b00020; font-weight:bold; font-size:1.2em;'>Henüz müşteri kaydı yok.</div>", unsafe_allow_html=True)

### ===========================
### === GÖRÜŞME / ARAMA / ZİYARET KAYITLARI MENÜSÜ ===
### ===========================

elif menu == "Görüşme / Arama / Ziyaret Kayıtları":
    # --- Her menüye geçişte dataframe’leri tekrar yükle ---
    if os.path.exists("temp.xlsx"):
        df_musteri = pd.read_excel("temp.xlsx", sheet_name=0)
        try:
            df_kayit = pd.read_excel("temp.xlsx", sheet_name="Kayıtlar")
        except Exception:
            df_kayit = pd.DataFrame(columns=["Müşteri Adı", "Tarih", "Tip", "Açıklama"])
    else:
        df_musteri = pd.DataFrame(columns=["Müşteri Adı", "Telefon", "E-posta", "Adres", "Ek Bilgi"])
        df_kayit = pd.DataFrame(columns=["Müşteri Adı", "Tarih", "Tip", "Açıklama"])

    st.markdown("<h2 style='color:#219A41; font-weight:bold;'>Görüşme / Arama / Ziyaret Kayıtları</h2>", unsafe_allow_html=True)

    # --- Müşterileri alfabetik sırala ve başa boş ekle ---
    musteri_listesi = [
        m for m in df_musteri["Müşteri Adı"].dropna().unique() if isinstance(m, str) and m.strip() != ""
    ]
    musteri_options = [""] + sorted(musteri_listesi)

    st.subheader("Kayıt Ekranı")

    secim = st.radio(
        "Lütfen işlem seçin:",
        ["Yeni Kayıt", "Eski Kayıt", "Tarih Aralığı ile Kayıtlar"]
    )

    # === YENİ KAYIT ===
    if secim == "Yeni Kayıt":
        with st.form("add_kayit"):
            musteri_sec = st.selectbox("Müşteri Seç", musteri_options, index=0)
            tarih = st.date_input("Tarih", value=datetime.date.today(), format="DD/MM/YYYY")
            tip = st.selectbox("Tip", ["Arama", "Görüşme", "Ziyaret"])
            aciklama = st.text_area("Açıklama")
            submitted = st.form_submit_button("Kaydet")
            if submitted:
                if not musteri_sec:
                    st.error("Lütfen bir müşteri seçiniz.")
                else:
                    new_row = {
                        "Müşteri Adı": musteri_sec,
                        "Tarih": tarih,
                        "Tip": tip,
                        "Açıklama": aciklama
                    }
                    df_kayit = pd.concat([df_kayit, pd.DataFrame([new_row])], ignore_index=True)
                    update_excel()
                    st.success("Kayıt eklendi!")
                    st.rerun()

    # === ESKİ KAYIT ===
    elif secim == "Eski Kayıt":
        musteri_sec = st.selectbox("Müşteri Seç", musteri_options, index=0, key="eski_musteri")
        if musteri_sec:
            musteri_kayitlar = df_kayit[df_kayit["Müşteri Adı"] == musteri_sec].sort_values("Tarih", ascending=False)
            if not musteri_kayitlar.empty:
                tablo_goster = musteri_kayitlar.copy()
                if "Tarih" in tablo_goster.columns:
                    tablo_goster["Tarih"] = pd.to_datetime(tablo_goster["Tarih"], errors="coerce").dt.strftime('%d/%m/%Y')
                st.dataframe(tablo_goster, use_container_width=True)
            else:
                st.info("Seçili müşteri için kayıt yok.")
        else:
            st.info("Lütfen müşteri seçin.")

    # === TARİH ARALIĞI İLE KAYITLAR ===
    elif secim == "Tarih Aralığı ile Kayıtlar":
        col1, col2 = st.columns(2)
        with col1:
            baslangic = st.date_input("Başlangıç Tarihi", value=datetime.date.today() - datetime.timedelta(days=7), format="DD/MM/YYYY")
        with col2:
            bitis = st.date_input("Bitiş Tarihi", value=datetime.date.today(), format="DD/MM/YYYY")
        tarih_arasi = df_kayit[
            (pd.to_datetime(df_kayit["Tarih"], errors="coerce") >= pd.to_datetime(baslangic)) &
            (pd.to_datetime(df_kayit["Tarih"], errors="coerce") <= pd.to_datetime(bitis))
        ]
        if not tarih_arasi.empty:
            tablo_goster = tarih_arasi.copy()
            if "Tarih" in tablo_goster.columns:
                tablo_goster["Tarih"] = pd.to_datetime(tablo_goster["Tarih"], errors="coerce").dt.strftime('%d/%m/%Y')
            st.dataframe(tablo_goster.sort_values("Tarih", ascending=False), use_container_width=True)
        else:
            st.info("Bu tarihler arasında kayıt yok.")

### ===========================
### --- FİYAT TEKLİFLERİ MENÜSÜ ---
### ===========================

elif menu == "Fiyat Teklifleri":
    st.markdown("<h2 style='color:#219A41; font-weight:bold;'>Fiyat Teklifleri</h2>", unsafe_allow_html=True)

    def otomatik_teklif_no():
        if df_teklif.empty or "Teklif No" not in df_teklif.columns:
            return "TKF-0001"
        mevcut_nolar = pd.to_numeric(
            df_teklif["Teklif No"].astype(str).str.extract(r'(\d+)$')[0], errors='coerce'
        ).dropna().astype(int)
        if mevcut_nolar.empty:
            return "TKF-0001"
        yeni_no = max(mevcut_nolar) + 1
        return f"TKF-{yeni_no:04d}"

    import time
    def güvenli_sil(dosya_adı, tekrar=5, bekle=1):
        for _ in range(tekrar):
            try:
                os.remove(dosya_adı)
                return True
            except PermissionError:
                time.sleep(bekle)
        return False

    st.subheader("Açık Pozisyondaki Teklifler Listesi")
    teklif_goster = df_teklif.copy()
    teklif_goster["Tarih"] = pd.to_datetime(teklif_goster["Tarih"]).dt.strftime("%d/%m/%Y")
    acik_teklifler = teklif_goster[teklif_goster["Durum"] == "Açık"].sort_values(by=["Müşteri Adı", "Teklif No"])
    acik_teklif_sayi = len(acik_teklifler)
    try:
        toplam_teklif = pd.to_numeric(acik_teklifler["Tutar"], errors="coerce").sum()
    except Exception:
        toplam_teklif = 0
    st.markdown(f"<div style='font-size:1.1em; color:#11998e; font-weight:bold;'>Toplam: {toplam_teklif:,.2f} $ | Toplam Açık Teklif: {acik_teklif_sayi} adet</div>", unsafe_allow_html=True)
    st.dataframe(acik_teklifler[[
        "Müşteri Adı", "Tarih", "Teklif No", "Tutar", "Ürün/Hizmet", "Açıklama"
    ]], use_container_width=True)

    st.markdown("##### Lütfen bir işlem seçin")
    col1, col2 = st.columns(2)
    with col1:
        yeni_teklif_buton = st.button("Yeni Teklif")
    with col2:
        eski_teklif_buton = st.button("Eski Teklif")

    if "teklif_view" not in st.session_state:
        st.session_state['teklif_view'] = None
    if yeni_teklif_buton:
        st.session_state['teklif_view'] = "yeni"
    if eski_teklif_buton:
        st.session_state['teklif_view'] = "eski"

    # --- YENİ TEKLİF EKLEME FORMU ---
    if st.session_state['teklif_view'] == "yeni":
        musteri_list = [""] + sorted(df_musteri["Müşteri Adı"].dropna().unique().tolist())
        st.subheader("Yeni Teklif Ekle")
        with st.form("add_teklif"):
            musteri_sec = st.selectbox("Müşteri Seç", musteri_list, key="yeni_teklif_musteri")
            tarih = st.date_input("Tarih", value=datetime.date.today(), format="DD/MM/YYYY")
            teklif_no = st.text_input("Teklif No", value=otomatik_teklif_no())
            tutar = st.text_input("Tutar ($)")
            urun = st.text_input("Ürün/Hizmet")
            aciklama = st.text_area("Açıklama")
            durum = st.selectbox("Durum", ["Açık", "Sonuçlandı", "Beklemede"])
            pdf_file = st.file_uploader("Teklif PDF", type="pdf")
            submitted = st.form_submit_button("Kaydet")
            pdf_link = ""
            if submitted:
                if not teklif_no.strip():
                    st.error("Teklif No boş olamaz!")
                elif not musteri_sec:
                    st.error("Lütfen müşteri seçiniz!")
                else:
                    if pdf_file:
                        temiz_musteri = "".join(x if x.isalnum() else "_" for x in str(musteri_sec))
                        temiz_tarih = str(tarih).replace("-", "")
                        pdf_filename = f"{temiz_musteri}__{temiz_tarih}__{teklif_no}.pdf"
                        temp_path = os.path.join(".", pdf_filename)
                        with open(temp_path, "wb") as f:
                            f.write(pdf_file.read())
                        gfile = drive.CreateFile({'title': pdf_filename, 'parents': [{'id': FIYAT_TEKLIFI_ID}]})
                        gfile.SetContentFile(temp_path)
                        gfile.Upload()
                        pdf_link = f"https://drive.google.com/file/d/{gfile['id']}/view?usp=sharing"
                        güvenli_sil(temp_path)
                    new_row = {
                        "Müşteri Adı": musteri_sec,
                        "Tarih": tarih,
                        "Teklif No": teklif_no,
                        "Tutar": tutar,
                        "Ürün/Hizmet": urun,
                        "Açıklama": aciklama,
                        "Durum": durum,
                        "PDF": pdf_link
                    }
                    df_teklif = pd.concat([df_teklif, pd.DataFrame([new_row])], ignore_index=True)
                    update_excel()
                    st.success("Teklif eklendi!")
                    st.session_state['teklif_view'] = None  # formu kapat
                    st.rerun()

    # --- ESKİ TEKLİFLER: PROFORMA BENZERİ SEÇİMLİ ---
    if st.session_state['teklif_view'] == "eski":
        st.subheader("Eski Teklifler Listesi")

        # Müşteri seç
        eski_teklif_musteriler = df_teklif["Müşteri Adı"].dropna().unique().tolist()
        eski_teklif_musteriler = [""] + sorted(eski_teklif_musteriler)
        secili_musteri = st.selectbox("Müşteri Seçiniz", eski_teklif_musteriler, key="eski_teklif_musteri_sec")

        if secili_musteri:
            # Seçilen müşterinin teklifleri
            teklifler_bu_musteri = df_teklif[df_teklif["Müşteri Adı"] == secili_musteri].sort_values(by="Tarih", ascending=False)
            if teklifler_bu_musteri.empty:
                st.info("Bu müşteriye ait teklif kaydı yok.")
            else:
                # Teklifler arasında seçim için kombo
                teklif_index = st.selectbox(
                    "Teklif Seçiniz",
                    teklifler_bu_musteri.index,
                    format_func=lambda i: f"{teklifler_bu_musteri.at[i, 'Teklif No']} | {teklifler_bu_musteri.at[i, 'Tarih']}"
                )
                secilen_teklif = teklifler_bu_musteri.loc[teklif_index]

                # Teklif PDF varsa göster
                if secilen_teklif["PDF"]:
                    st.markdown(f"**Teklif PDF:** [{secilen_teklif['Teklif No']}]({secilen_teklif['PDF']})", unsafe_allow_html=True)
                else:
                    st.info("PDF bulunamadı.")

                # Tüm detayları göster
                st.write("**Teklif Detayları:**")
                st.table({
                    "Müşteri Adı": [secilen_teklif["Müşteri Adı"]],
                    "Tarih": [secilen_teklif["Tarih"]],
                    "Teklif No": [secilen_teklif["Teklif No"]],
                    "Tutar": [secilen_teklif["Tutar"]],
                    "Ürün/Hizmet": [secilen_teklif["Ürün/Hizmet"]],
                    "Açıklama": [secilen_teklif["Açıklama"]],
                    "Durum": [secilen_teklif["Durum"]],
                })

### ===========================
### --- PROFORMA TAKİBİ MENÜSÜ ---
### ===========================

elif menu == "Proforma Takibi":
    st.markdown("<h2 style='color:#219A41; font-weight:bold;'>Proforma Takibi</h2>", unsafe_allow_html=True)

    # Eksik sütunları kontrol et
    for col in ["Vade (gün)", "Sipariş Formu", "Durum", "PDF", "Sevk Durumu", "Ülke", "Satış Temsilcisi", "Ödeme Şekli"]:
        if col not in df_proforma.columns:
            df_proforma[col] = ""

    beklemede_kayitlar = df_proforma[df_proforma["Durum"] == "Beklemede"]

    if not beklemede_kayitlar.empty:
        st.subheader("Bekleyen Proformalar")
        st.dataframe(
            beklemede_kayitlar[
                ["Müşteri Adı", "Proforma No", "Tarih", "Tutar", "Durum", "Vade (gün)", "Sevk Durumu"]
            ],
            use_container_width=True
        )

    musteri_list = sorted([
        x for x in df_musteri["Müşteri Adı"].dropna().unique()
        if isinstance(x, str) and x.strip() != ""
    ]) if not df_musteri.empty else []
    musteri_sec = st.selectbox("Müşteri Seç", [""] + musteri_list)
    
    if musteri_sec:
        st.write("Proforma işlemi seçin:")
        islem = st.radio("", ["Yeni Kayıt", "Eski Kayıt"], horizontal=True)
        
        if islem == "Yeni Kayıt":
            musteri_info = df_musteri[df_musteri["Müşteri Adı"] == musteri_sec]
            default_ulke = musteri_info["Ülke"].values[0] if not musteri_info.empty else ""
            default_temsilci = musteri_info["Satış Temsilcisi"].values[0] if not musteri_info.empty else ""
            default_odeme = musteri_info["Ödeme Şekli"].values[0] if not musteri_info.empty else ""

            with st.form("add_proforma"):
                tarih = st.date_input("Tarih", value=datetime.date.today())
                proforma_no = st.text_input("Proforma No")
                tutar = st.text_input("Tutar ($)")
                vade_gun = st.text_input("Vade (gün)")
                ulke = st.text_input("Ülke", value=default_ulke, disabled=True)
                temsilci = st.text_input("Satış Temsilcisi", value=default_temsilci, disabled=True)
                odeme = st.text_input("Ödeme Şekli", value=default_odeme, disabled=True)
                aciklama = st.text_area("Açıklama")
                durum = st.selectbox("Durum", ["Beklemede", "İptal", "Faturası Kesildi", "Siparişe Dönüştü"])
                pdf_file = st.file_uploader("Proforma PDF", type="pdf")
                submitted = st.form_submit_button("Kaydet")
                pdf_link = ""
                if submitted:
                    if not proforma_no.strip() or not vade_gun.strip():
                        st.error("Proforma No ve Vade (gün) boş olamaz!")
                    else:
                        if pdf_file:
                            pdf_filename = f"{musteri_sec}_{tarih}_{proforma_no}.pdf"
                            temp_path = os.path.join(".", pdf_filename)
                            with open(temp_path, "wb") as f:
                                f.write(pdf_file.read())
                            gfile = drive.CreateFile({'title': pdf_filename, 'parents': [{'id': "17lPkdYcC4BdowLdCsiWxiq0H_6oVGXLs"}]})
                            gfile.SetContentFile(temp_path)
                            gfile.Upload()
                            pdf_link = f"https://drive.google.com/file/d/{gfile['id']}/view?usp=sharing"
                            try: os.remove(temp_path)
                            except: pass
                        # Sipariş Formu ve Siparişe Dönüştü ayrı formla ekleniyor!
                        new_row = {
                            "Müşteri Adı": musteri_sec,
                            "Tarih": tarih,
                            "Proforma No": proforma_no,
                            "Tutar": tutar,
                            "Vade (gün)": vade_gun,
                            "Ülke": default_ulke,
                            "Satış Temsilcisi": default_temsilci,
                            "Ödeme Şekli": default_odeme,
                            "Açıklama": aciklama,
                            "Durum": "Beklemede",
                            "PDF": pdf_link,
                            "Sipariş Formu": "",
                            "Sevk Durumu": ""
                        }
                        df_proforma = pd.concat([df_proforma, pd.DataFrame([new_row])], ignore_index=True)
                        update_excel()
                        st.success("Proforma eklendi!")
                        st.rerun()
        
        elif islem == "Eski Kayıt":
            eski_kayitlar = df_proforma[
                (df_proforma["Müşteri Adı"] == musteri_sec) &
                (df_proforma["Durum"] == "Beklemede")
            ]
            if eski_kayitlar.empty:
                st.info("Bu müşteriye ait siparişe dönüşmemiş proforma kaydı yok.")
            else:
                st.dataframe(
                    eski_kayitlar[
                        ["Müşteri Adı", "Proforma No", "Tarih", "Tutar", "Durum", "Vade (gün)", "Sevk Durumu"]
                    ],
                    use_container_width=True
                )

                sec_index = st.selectbox(
                    "Proforma Seç",
                    eski_kayitlar.index,
                    format_func=lambda i: f"{eski_kayitlar.at[i, 'Proforma No']} | {eski_kayitlar.at[i, 'Tarih']}"
                ) if not eski_kayitlar.empty else None

                if sec_index is not None:
                    kayit = eski_kayitlar.loc[sec_index]
                    if kayit["PDF"]:
                        st.markdown(f"**Proforma PDF:** [{kayit['Proforma No']}]({kayit['PDF']})", unsafe_allow_html=True)

                    # Esas form sadece güncelleme ve silme için
                    with st.form("edit_proforma"):
                        tarih_ = st.date_input("Tarih", value=pd.to_datetime(kayit["Tarih"]).date())
                        proforma_no_ = st.text_input("Proforma No", value=kayit["Proforma No"])
                        tutar_ = st.text_input("Tutar ($)", value=kayit["Tutar"])
                        vade_gun_ = st.text_input("Vade (gün)", value=str(kayit["Vade (gün)"]))
                        aciklama_ = st.text_area("Açıklama", value=kayit["Açıklama"])
                        durum_ = st.selectbox(
                            "Durum",
                            ["Beklemede", "Siparişe Dönüştü", "İptal", "Faturası Kesildi"],
                            index=["Beklemede", "Siparişe Dönüştü", "İptal", "Faturası Kesildi"].index(kayit["Durum"])
                            if kayit["Durum"] in ["Beklemede", "Siparişe Dönüştü", "İptal", "Faturası Kesildi"] else 0
                        )
                        guncelle = st.form_submit_button("Güncelle")
                        sil = st.form_submit_button("Sil")

                    # Siparişe Dönüştü ise ayrı form!
                    if durum_ == "Siparişe Dönüştü":
                        st.info("Lütfen sipariş formunu yükleyin ve ardından 'Sipariş Formunu Kaydet' butonuna basın.")
                        with st.form(f"siparis_formu_upload_{sec_index}"):
                            siparis_formu_file = st.file_uploader("Sipariş Formu PDF", type="pdf")
                            siparis_kaydet = st.form_submit_button("Sipariş Formunu Kaydet")

                        if siparis_kaydet:
                            if siparis_formu_file is None:
                                st.error("Sipariş formu yüklemelisiniz.")
                            else:
                                siparis_formu_fname = f"{musteri_sec}_{proforma_no_}_SiparisFormu_{datetime.datetime.now().strftime('%Y%m%d%H%M%S')}.pdf"
                                temp_path = os.path.join(".", siparis_formu_fname)
                                with open(temp_path, "wb") as f:
                                    f.write(siparis_formu_file.read())
                                gfile = drive.CreateFile({'title': siparis_formu_fname, 'parents': [{'id': "1xeTdhOE1Cc6ohJsRzPVlCMMraBIXWO9w"}]})
                                gfile.SetContentFile(temp_path)
                                gfile.Upload()
                                siparis_formu_url = f"https://drive.google.com/file/d/{gfile['id']}/view?usp=sharing"
                                try: os.remove(temp_path)
                                except: pass
                                # Hem sipariş formu hem durum burada güncellenir!
                                df_proforma.at[sec_index, "Sipariş Formu"] = siparis_formu_url
                                df_proforma.at[sec_index, "Durum"] = "Siparişe Dönüştü"
                                update_excel()
                                st.success("Sipariş formu kaydedildi ve durum güncellendi!")
                                st.rerun()

                    # Diğer alanlar için sadece güncelle!
                    if guncelle:
                        df_proforma.at[sec_index, "Tarih"] = tarih_
                        df_proforma.at[sec_index, "Proforma No"] = proforma_no_
                        df_proforma.at[sec_index, "Tutar"] = tutar_
                        df_proforma.at[sec_index, "Vade (gün)"] = vade_gun_
                        df_proforma.at[sec_index, "Açıklama"] = aciklama_
                        if durum_ != "Siparişe Dönüştü":
                            df_proforma.at[sec_index, "Durum"] = durum_
                        update_excel()
                        st.success("Proforma güncellendi!")
                        st.rerun()

                    if sil:
                        df_proforma = df_proforma.drop(sec_index).reset_index(drop=True)
                        update_excel()
                        st.success("Kayıt silindi!")
                        st.rerun()
                else:
                    st.warning("Lütfen bir proforma seçin.")

### ===========================
### --- GÜNCEL SİPARİŞ DURUMU ---
### ===========================

elif menu == "Güncel Sipariş Durumu":
    st.header("Güncel Sipariş Durumu")

    if "Sevk Durumu" not in df_proforma.columns:
        df_proforma["Sevk Durumu"] = ""
    siparisler = df_proforma[
        (df_proforma["Durum"] == "Siparişe Dönüştü") & (~df_proforma["Sevk Durumu"].isin(["Sevkedildi", "Ulaşıldı"]))
    ].copy()

    for col in ["Termin Tarihi", "Sipariş Formu", "Ülke", "Satış Temsilcisi", "Ödeme Şekli"]:
        if col not in siparisler.columns:
            siparisler[col] = ""

    if siparisler.empty:
        st.info("Henüz sevk edilmeyi bekleyen sipariş yok.")
    else:
        siparisler["Termin Tarihi Order"] = pd.to_datetime(siparisler["Termin Tarihi"], errors="coerce")
        siparisler = siparisler.sort_values("Termin Tarihi Order", ascending=True)
        if not siparisler.empty:
            siparisler["Tarih"] = pd.to_datetime(siparisler["Tarih"], errors="coerce").dt.strftime("%d/%m/%Y")
            siparisler["Termin Tarihi"] = pd.to_datetime(siparisler["Termin Tarihi"], errors="coerce").dt.strftime("%d/%m/%Y")

        tablo = siparisler[["Tarih", "Müşteri Adı", "Termin Tarihi", "Ülke", "Satış Temsilcisi", "Ödeme Şekli", "Proforma No", "Tutar", "Açıklama"]]
        st.markdown("<h4 style='color:#219A41; font-weight:bold;'>Tüm Siparişe Dönüşenler</h4>", unsafe_allow_html=True)
        st.dataframe(tablo, use_container_width=True)

        # Termin Tarihi Güncelleme
        st.markdown("#### Termin Tarihi Güncelle")
        sec_index = st.selectbox(
            "Termin Tarihi Girilecek Siparişi Seçin",
            options=sorted(siparisler.index),
            format_func=lambda i: f"{siparisler.at[i,'Müşteri Adı']} - {siparisler.at[i,'Proforma No']}"
        )
        mevcut_termin = df_proforma.at[sec_index, "Termin Tarihi"] if "Termin Tarihi" in df_proforma.columns else ""
        try:
            default_termin = pd.to_datetime(mevcut_termin, errors="coerce")
            if pd.isnull(default_termin):
                default_termin = datetime.date.today()
            else:
                default_termin = default_termin.date()
        except Exception:
            default_termin = datetime.date.today()

        yeni_termin = st.date_input("Termin Tarihi", value=default_termin, key="termin_input")
        if st.button("Termin Tarihini Kaydet"):
            df_proforma.at[sec_index, "Termin Tarihi"] = yeni_termin
            update_excel()
            st.success("Termin tarihi kaydedildi!")
            st.rerun()

        # Sevk Etme Butonu
        st.markdown("#### Sipariş Sevk Et")
        sevk_sec_index = st.selectbox(
            "Sevk Edilecek Siparişi Seçin",
            options=sorted(siparisler.index),
            format_func=lambda i: f"{siparisler.at[i,'Müşteri Adı']} - {siparisler.at[i,'Proforma No']}",
            key="sevk_sec"
        )
        if st.button("Sipariş Sevkedildi (ETA Takibine Gönder)"):
            yeni_eta = {
                "Müşteri Adı": siparisler.at[sevk_sec_index, "Müşteri Adı"],
                "Proforma No": siparisler.at[sevk_sec_index, "Proforma No"],
                "ETA Tarihi": "",
                "Açıklama": siparisler.at[sevk_sec_index, "Açıklama"]
            }
            for col in ["Müşteri Adı", "Proforma No", "ETA Tarihi", "Açıklama"]:
                if col not in df_eta.columns:
                    df_eta[col] = ""
            df_eta = pd.concat([df_eta, pd.DataFrame([yeni_eta])], ignore_index=True)
            df_proforma.at[sevk_sec_index, "Sevk Durumu"] = "Sevkedildi"
            update_excel()
            st.success("Sipariş sevkedildi ve ETA takibine gönderildi!")
            st.rerun()

        # --- YENİ EKLENECEK: Siparişi Beklemeye Al (Geri Çağır) ---
        st.markdown("#### Siparişi Beklemeye Al (Geri Çağır)")
        geri_index = st.selectbox(
            "Beklemeye Alınacak Siparişi Seçin",
            options=sorted(siparisler.index),
            format_func=lambda i: f"{siparisler.at[i,'Müşteri Adı']} - {siparisler.at[i,'Proforma No']}",
            key="geri_sec"
        )
        if st.button("Siparişi Beklemeye Al / Geri Çağır"):
            df_proforma.at[geri_index, "Durum"] = "Beklemede"
            df_proforma.at[geri_index, "Sevk Durumu"] = ""
            df_proforma.at[geri_index, "Termin Tarihi"] = ""
            update_excel()
            st.success("Sipariş tekrar bekleyen proformalar listesine alındı!")
            st.rerun()

        # Altında PDF bağlantıları ve toplam tutar
        st.markdown("#### Tıklanabilir Proforma ve Sipariş Formu Linkleri")
        for i, row in siparisler.iterrows():
            links = []
            if pd.notnull(row["PDF"]) and row["PDF"]:
                links.append(f"[Proforma PDF: {row['Proforma No']}]({row['PDF']})")
            if pd.notnull(row["Sipariş Formu"]) and row["Sipariş Formu"]:
                fname = f"{row['Müşteri Adı']}__{row['Proforma No']}__SiparisFormu"
                links.append(f"[Sipariş Formu: {fname}]({row['Sipariş Formu']})")
            if links:
                st.markdown(" - " + " | ".join(links), unsafe_allow_html=True)

        try:
            toplam = pd.to_numeric(siparisler["Tutar"], errors="coerce").sum()
        except Exception:
            toplam = 0
        st.markdown(f"<div style='color:#219A41; font-weight:bold;'>*Toplam Bekleyen Sevk: {toplam:,.2f} $*</div>", unsafe_allow_html=True)

### ===========================
### --- FATURA & İHRACAT EVRAKLARI MENÜSÜ ---
### ===========================

elif menu == "Fatura & İhracat Evrakları":
    st.markdown("<h2 style='color:#219A41; font-weight:bold;'>Fatura & İhracat Evrakları</h2>", unsafe_allow_html=True)

    for col in [
        "Proforma No", "Vade (gün)", "Vade Tarihi", "Ülke", "Satış Temsilcisi", "Ödeme Şekli",
        "Commercial Invoice", "Sağlık Sertifikası", "Packing List",
        "Konşimento", "İhracat Beyannamesi", "Fatura PDF", "Sipariş Formu",
        "Yük Resimleri", "EK Belgeler", "Ödendi"
    ]:
        if col not in df_evrak.columns:
            df_evrak[col] = "" if col != "Ödendi" else False

    musteri_secenek = sorted(df_proforma["Müşteri Adı"].dropna().unique().tolist())
    secilen_musteri = st.selectbox("Müşteri Seç", [""] + musteri_secenek)
    secilen_proformalar = df_proforma[df_proforma["Müşteri Adı"] == secilen_musteri] if secilen_musteri else pd.DataFrame()
    proforma_no_sec = ""
    if not secilen_proformalar.empty:
        proforma_no_sec = st.selectbox("Proforma No Seç", [""] + secilen_proformalar["Proforma No"].astype(str).tolist())
    else:
        proforma_no_sec = st.selectbox("Proforma No Seç", [""])

    musteri_info = df_musteri[df_musteri["Müşteri Adı"] == secilen_musteri]
    ulke = musteri_info["Ülke"].values[0] if not musteri_info.empty else ""
    temsilci = musteri_info["Satış Temsilcisi"].values[0] if not musteri_info.empty else ""
    odeme = musteri_info["Ödeme Şekli"].values[0] if not musteri_info.empty else ""

    # --- 1. Önceki evrakların linklerini çek ---
    onceki_evrak = df_evrak[
        (df_evrak["Müşteri Adı"] == secilen_musteri) &
        (df_evrak["Proforma No"] == proforma_no_sec)
    ]

    def file_link_html(label, url):
        if url:
            return f'<div style="margin-top:-6px;"><a href="{url}" target="_blank" style="color:#219A41;">[Daha önce yüklenmiş {label}]</a></div>'
        else:
            return f'<div style="margin-top:-6px; color:#b00020; font-size:0.95em;">(Daha önce yüklenmemiş)</div>'

    evrak_tipleri = [
        ("Commercial Invoice", "Commercial Invoice PDF"),
        ("Sağlık Sertifikası", "Sağlık Sertifikası PDF"),
        ("Packing List", "Packing List PDF"),
        ("Konşimento", "Konşimento PDF"),
        ("İhracat Beyannamesi", "İhracat Beyannamesi PDF"),
    ]

    with st.form("add_evrak"):
        fatura_no = st.text_input("Fatura No")
        fatura_tarih = st.date_input("Fatura Tarihi", value=datetime.date.today())
        tutar = st.text_input("Fatura Tutarı ($)")
        vade_gun = ""
        vade_tarihi = ""
        if secilen_musteri and proforma_no_sec:
            proforma_kayit = df_proforma[(df_proforma["Müşteri Adı"] == secilen_musteri) & (df_proforma["Proforma No"] == proforma_no_sec)]
            if not proforma_kayit.empty:
                vade_gun = proforma_kayit.iloc[0].get("Vade (gün)", "")
                try:
                    vade_gun_int = int(vade_gun)
                    vade_tarihi = fatura_tarih + datetime.timedelta(days=vade_gun_int)
                except:
                    vade_tarihi = ""
        st.text_input("Vade (gün)", value=vade_gun, key="vade_gun", disabled=True)
        st.date_input("Vade Tarihi", value=vade_tarihi if vade_tarihi else fatura_tarih, key="vade_tarihi", disabled=True)
        st.text_input("Ülke", value=ulke, disabled=True)
        st.text_input("Satış Temsilcisi", value=temsilci, disabled=True)
        st.text_input("Ödeme Şekli", value=odeme, disabled=True)
        
        # --- 2. Evrak yükleme alanları ve eski dosya linkleri ---
        uploaded_files = {}
        for col, label in evrak_tipleri:
            uploaded_files[col] = st.file_uploader(label, type="pdf", key=f"{col}_upload")
            prev_url = onceki_evrak.iloc[0][col] if not onceki_evrak.empty else ""
            st.markdown(file_link_html(label, prev_url), unsafe_allow_html=True)
        
        submitted = st.form_submit_button("Kaydet")

        if submitted:
            if not fatura_no.strip() or not tutar.strip():
                st.error("Fatura No ve Tutar boş olamaz!")
            else:
                # Dosya yükleme ve eski dosya kontrolü
                file_urls = {}
                for col, label in evrak_tipleri:
                    uploaded_file = uploaded_files[col]
                    # Önce yeni dosya yüklendiyse Drive'a yükle, yoksa eski dosya linkini al
                    if uploaded_file:
                        file_name = f"{col}_{datetime.datetime.now().strftime('%Y%m%d%H%M%S')}.pdf"
                        temp_path = os.path.join(".", file_name)
                        with open(temp_path, "wb") as f:
                            f.write(uploaded_file.read())
                        gfile = drive.CreateFile({'title': file_name, 'parents': [{'id': "your_folder_id"}]})
                        gfile.SetContentFile(temp_path)
                        gfile.Upload()
                        file_urls[col] = f"https://drive.google.com/file/d/{gfile['id']}/view?usp=sharing"
                        try:
                            os.remove(temp_path)
                        except:
                            pass
                    else:
                        file_urls[col] = onceki_evrak.iloc[0][col] if not onceki_evrak.empty else ""

                new_row = {
                    "Müşteri Adı": secilen_musteri,
                    "Proforma No": proforma_no_sec,
                    "Fatura No": fatura_no,
                    "Fatura Tarihi": fatura_tarih,
                    "Tutar": tutar,
                    "Vade (gün)": vade_gun,
                    "Vade Tarihi": vade_tarihi,
                    "Ülke": ulke,
                    "Satış Temsilcisi": temsilci,
                    "Ödeme Şekli": odeme,
                    "Commercial Invoice": file_urls.get("Commercial Invoice", ""),
                    "Sağlık Sertifikası": file_urls.get("Sağlık Sertifikası", ""),
                    "Packing List": file_urls.get("Packing List", ""),
                    "Konşimento": file_urls.get("Konşimento", ""),
                    "İhracat Beyannamesi": file_urls.get("İhracat Beyannamesi", ""),
                    "Fatura PDF": "",  # Gerekirse ekle
                    "Sipariş Formu": "",
                    "Yük Resimleri": "",
                    "EK Belgeler": "",
                    "Ödendi": False,
                }
                df_evrak = pd.concat([df_evrak, pd.DataFrame([new_row])], ignore_index=True)
                update_excel()
                st.success("Evrak eklendi!")
                st.rerun()

### ===========================
### --- VADE TAKİBİ MENÜSÜ ---
### ===========================

elif menu == "Vade Takibi":
    st.markdown("<h2 style='color:#219A41; font-weight:bold;'>Vade Takibi</h2>", unsafe_allow_html=True)

    # Eksikse yeni alanları ekle
    for col in ["Proforma No", "Vade (gün)", "Ödendi", "Ülke", "Satış Temsilcisi", "Ödeme Şekli"]:
        if col not in df_evrak.columns:
            df_evrak[col] = "" if col != "Ödendi" else False
    df_evrak["Ödendi"] = df_evrak["Ödendi"].fillna(False).astype(bool)

    if "Vade Tarihi" in df_evrak.columns:
        df_evrak["Vade Tarihi"] = pd.to_datetime(df_evrak["Vade Tarihi"], errors="coerce")

    today = pd.to_datetime(datetime.date.today())

    # Sadece ödenmeyen ve vadeli fatura kayıtları
    vade_df = df_evrak[df_evrak["Vade Tarihi"].notna() & (~df_evrak["Ödendi"])]
    vade_df = vade_df.reset_index()

    for i, row in vade_df.iterrows():
        kalan = (row["Vade Tarihi"] - today).days
        mesaj = f"{row['Müşteri Adı']} | {row.get('Ülke','')} | {row.get('Satış Temsilcisi','')} | Proforma No: {row.get('Proforma No','')} | Fatura No: {row['Fatura No']} | Vade Tarihi: {row['Vade Tarihi'].date()} | Ödeme: {row.get('Ödeme Şekli','')}"
        if kalan == 1:
            st.error(f"{mesaj} | **YARIN VADE DOLUYOR!**")
        elif kalan < 0:
            st.warning(f"{mesaj} | **{abs(kalan)} gün GECİKTİ!**")
        else:
            st.info(f"{mesaj} | {kalan} gün kaldı.")

        tick = st.checkbox(
            f"Ödendi: {row['Müşteri Adı']} - Proforma No: {row.get('Proforma No','')} - Fatura No: {row['Fatura No']}",
            key=f"odendi_{i}"
        )
        if tick:
            df_evrak.at[row['index'], "Ödendi"] = True
            update_excel()
            st.success("Kayıt ödendi olarak işaretlendi!")
            st.rerun()

    st.markdown("#### Açık Vade Kayıtları")
    st.dataframe(
        df_evrak[
            df_evrak["Vade Tarihi"].notna() & (~df_evrak["Ödendi"])
        ][["Müşteri Adı", "Ülke", "Satış Temsilcisi", "Ödeme Şekli", "Proforma No", "Fatura No", "Fatura Tarihi", "Vade (gün)", "Vade Tarihi", "Tutar"]],
        use_container_width=True
    )

### ===========================
### --- ETA TAKİBİ MENÜSÜ ---
### ===========================

elif menu == "ETA Takibi":
    st.markdown("<h2 style='color:#219A41; font-weight:bold;'>ETA Takibi</h2>", unsafe_allow_html=True)

    # Eksik sütunları ekle
    for col in ["Sevk Durumu", "Proforma No", "Sevk Tarihi", "Ulaşma Tarihi"]:
        if col not in df_proforma.columns:
            df_proforma[col] = ""

    # === SEVKEDİLENLER KISMI ===
    sevkedilenler = df_proforma[df_proforma["Sevk Durumu"] == "Sevkedildi"].copy()
    if sevkedilenler.empty:
        st.info("Sevkedilmiş sipariş bulunmuyor.")
    else:
        secenekler = sevkedilenler[["Müşteri Adı", "Proforma No"]].drop_duplicates()
        secenekler["sec_text"] = secenekler["Müşteri Adı"] + " - " + secenekler["Proforma No"]
        selected = st.selectbox("Sevkedilen Sipariş Seç", secenekler["sec_text"])
        selected_row = secenekler[secenekler["sec_text"] == selected].iloc[0]
        sec_musteri = selected_row["Müşteri Adı"]
        sec_proforma = selected_row["Proforma No"]

        # ETA DataFrame'inde eksik sütun ekle
        for col in ["Müşteri Adı", "Proforma No", "ETA Tarihi", "Açıklama"]:
            if col not in df_eta.columns:
                df_eta[col] = ""

        # Önceden ETA girilmiş mi?
        filtre = (df_eta["Müşteri Adı"] == sec_musteri) & (df_eta["Proforma No"] == sec_proforma)
        if filtre.any():
            mevcut_eta = df_eta.loc[filtre, "ETA Tarihi"].values[0]
            mevcut_aciklama = df_eta.loc[filtre, "Açıklama"].values[0]
        else:
            mevcut_eta = ""
            mevcut_aciklama = ""

        with st.form("edit_eta"):
            try:
                varsayilan_eta = pd.to_datetime(mevcut_eta).date() if mevcut_eta and pd.notnull(mevcut_eta) and str(mevcut_eta) != "NaT" else datetime.date.today()
            except Exception:
                varsayilan_eta = datetime.date.today()
            eta_tarih = st.date_input("ETA Tarihi", value=varsayilan_eta)
            aciklama = st.text_area("Açıklama", value=mevcut_aciklama)
            guncelle = st.form_submit_button("ETA'yı Kaydet/Güncelle")
            ulasti = st.form_submit_button("Ulaştı")
            geri_al = st.form_submit_button("Sevki Geri Al")

            if guncelle:
                if filtre.any():
                    df_eta.loc[filtre, "ETA Tarihi"] = eta_tarih
                    df_eta.loc[filtre, "Açıklama"] = aciklama
                else:
                    new_row = {
                        "Müşteri Adı": sec_musteri,
                        "Proforma No": sec_proforma,
                        "ETA Tarihi": eta_tarih,
                        "Açıklama": aciklama
                    }
                    df_eta = pd.concat([df_eta, pd.DataFrame([new_row])], ignore_index=True)
                update_excel()
                st.success("ETA kaydedildi/güncellendi!")
                st.rerun()

            if ulasti:
                # Ulaşıldı: ETA listesinden çıkar, proforma'da Sevk Durumu "Ulaşıldı" ve bugünün tarihi "Ulaşma Tarihi" olarak kaydet
                df_eta = df_eta[~((df_eta["Müşteri Adı"] == sec_musteri) & (df_eta["Proforma No"] == sec_proforma))]
                idx = df_proforma[(df_proforma["Müşteri Adı"] == sec_musteri) & (df_proforma["Proforma No"] == sec_proforma)].index
                if len(idx) > 0:
                    df_proforma.at[idx[0], "Sevk Durumu"] = "Ulaşıldı"
                    df_proforma.at[idx[0], "Ulaşma Tarihi"] = datetime.date.today()
                update_excel()
                st.success("Sipariş 'Ulaşıldı' olarak işaretlendi ve ETA takibinden çıkarıldı!")
                st.rerun()

            if geri_al:
                # Siparişi geri al: ETA'dan çıkar, Sevk Durumu'nu boş yap
                df_eta = df_eta[~((df_eta["Müşteri Adı"] == sec_musteri) & (df_eta["Proforma No"] == sec_proforma))]
                idx = df_proforma[(df_proforma["Müşteri Adı"] == sec_musteri) & (df_proforma["Proforma No"] == sec_proforma)].index
                if len(idx) > 0:
                    df_proforma.at[idx[0], "Sevk Durumu"] = ""
                update_excel()
                st.success("Sevkiyat geri alındı! Sipariş tekrar Güncel Sipariş Durumu'na gönderildi.")
                st.rerun()

    # === ETA Takip Listesi ===
    st.markdown("#### ETA Takip Listesi")
    for col in ["Proforma No", "ETA Tarihi"]:
        if col not in df_eta.columns:
            df_eta[col] = ""
    if not df_eta.empty:
        df_eta["ETA Tarihi"] = pd.to_datetime(df_eta["ETA Tarihi"], errors="coerce")
        today = pd.to_datetime(datetime.date.today())
        df_eta["Kalan Gün"] = (df_eta["ETA Tarihi"] - today).dt.days
        tablo = df_eta[["Müşteri Adı", "Proforma No", "ETA Tarihi", "Kalan Gün", "Açıklama"]].copy()
        tablo = tablo.sort_values("ETA Tarihi", ascending=True)
        st.dataframe(tablo, use_container_width=True)

        st.markdown("##### ETA Kaydı Sil")
        silinecekler = df_eta.index.tolist()
        sil_sec = st.selectbox("Silinecek Kaydı Seçin", options=silinecekler,
            format_func=lambda i: f"{df_eta.at[i, 'Müşteri Adı']} - {df_eta.at[i, 'Proforma No']}")
        if st.button("KAYDI SİL"):
            df_eta = df_eta.drop(sil_sec).reset_index(drop=True)
            update_excel()
            st.success("Seçilen ETA kaydı silindi!")
            st.rerun()
    else:
        st.info("Henüz ETA kaydı yok.")

    # === ULAŞANLAR (TESLİM EDİLENLER) KISMI ===
    ulasanlar = df_proforma[df_proforma["Sevk Durumu"] == "Ulaşıldı"].copy()

    # Teslim Edilenlerde Ulaşma Tarihi Güncelle
    if not ulasanlar.empty:
        ulasanlar["sec_text"] = ulasanlar["Müşteri Adı"] + " - " + ulasanlar["Proforma No"]
        st.markdown("#### Teslim Edilen Siparişlerde Ulaşma Tarihi Güncelle")
        selected_ulasan = st.selectbox("Sipariş Seçiniz", ulasanlar["sec_text"])
        row = ulasanlar[ulasanlar["sec_text"] == selected_ulasan].iloc[0]
        try:
            current_ulasma = pd.to_datetime(row["Ulaşma Tarihi"]).date()
            if pd.isnull(current_ulasma) or str(current_ulasma) == "NaT":
                current_ulasma = datetime.date.today()
        except Exception:
            current_ulasma = datetime.date.today()

        new_ulasma_tarih = st.date_input("Ulaşma Tarihi", value=current_ulasma, key="ulasan_guncelle")
        if st.button("Ulaşma Tarihini Kaydet"):
            idx = df_proforma[(df_proforma["Müşteri Adı"] == row["Müşteri Adı"]) & 
                            (df_proforma["Proforma No"] == row["Proforma No"])].index
            if len(idx) > 0:
                df_proforma.at[idx[0], "Ulaşma Tarihi"] = new_ulasma_tarih
                update_excel()
                st.success("Ulaşma Tarihi güncellendi!")
                st.rerun()

        # Ulaşanlar Tablosu
        st.markdown("#### Ulaşan (Teslim Edilmiş) Siparişler")
        if "Sevk Tarihi" in ulasanlar.columns:
            ulasanlar["Sevk Tarihi"] = pd.to_datetime(ulasanlar["Sevk Tarihi"], errors="coerce")
        else:
            ulasanlar["Sevk Tarihi"] = pd.NaT
        if "Termin Tarihi" in ulasanlar.columns:
            ulasanlar["Termin Tarihi"] = pd.to_datetime(ulasanlar["Termin Tarihi"], errors="coerce")
        else:
            ulasanlar["Termin Tarihi"] = pd.NaT
        ulasanlar["Ulaşma Tarihi"] = pd.to_datetime(ulasanlar["Ulaşma Tarihi"], errors="coerce")

        ulasanlar["Gün Farkı"] = (ulasanlar["Ulaşma Tarihi"] - ulasanlar["Termin Tarihi"]).dt.days
        ulasanlar["Sevk Tarihi"] = ulasanlar["Sevk Tarihi"].dt.strftime("%d/%m/%Y")
        ulasanlar["Termin Tarihi"] = ulasanlar["Termin Tarihi"].dt.strftime("%d/%m/%Y")
        ulasanlar["Ulaşma Tarihi"] = ulasanlar["Ulaşma Tarihi"].dt.strftime("%d/%m/%Y")

        tablo = ulasanlar[["Müşteri Adı", "Proforma No", "Termin Tarihi", "Sevk Tarihi", "Ulaşma Tarihi", "Gün Farkı", "Tutar", "Açıklama"]]
        st.dataframe(tablo, use_container_width=True)
    else:
        st.info("Henüz ulaşan sipariş yok.")

 

# ==============================
# FUAR MÜŞTERİ KAYITLARI MENÜSÜ
# ==============================

if menu == "Fuar Müşteri Kayıtları":
    st.markdown("<h2 style='color:#8e54e9; font-weight:bold; text-align:center;'>🎫 FUAR MÜŞTERİ KAYITLARI</h2>", unsafe_allow_html=True)
    st.info("Fuarlarda müşteri görüşmelerinizi hızlıca buraya ekleyin. Hem yeni kayıt oluşturabilir hem de mevcut kayıtlarınızı düzenleyebilirsiniz.")

    # --- Fuar Adı Girişi & Seçimi ---
    fuar_isimleri = list(df_fuar_musteri["Fuar Adı"].dropna().unique())
    yeni_fuar = st.text_input("Yeni Fuar Adı Ekleyin (Eklemek istemiyorsanız boş bırakın):")
    if yeni_fuar and yeni_fuar not in fuar_isimleri:
        fuar_isimleri.append(yeni_fuar)
        fuar_adi = yeni_fuar
    else:
        fuar_adi = st.selectbox("Fuar Seçiniz", ["- Fuar Seçiniz -"] + sorted(fuar_isimleri), index=0)
        if fuar_adi == "- Fuar Seçiniz -":
            fuar_adi = ""

    secim = st.radio("İşlem Seçiniz:", ["Yeni Kayıt", "Eski Kayıt"])

    # Ülke ve Satış Temsilcisi Listeleri
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

    temsilci_listesi = ["Hüseyin POLAT", "Kemal İlker Çelikkalkan", "Efe Yıldırım"]

    # --- YENİ KAYIT ---
    if secim == "Yeni Kayıt":
        st.markdown("#### Yeni Fuar Müşteri Kaydı Ekle")
        with st.form("fuar_musteri_ekle"):
            musteri_adi = st.text_input("Müşteri Adı")
            ulke = st.selectbox("Ülke Seçin", ulke_listesi)  # Ülke Seçimi
            tel = st.text_input("Telefon")
            email = st.text_input("E-mail")
            temsilci = st.selectbox("Satış Temsilcisi", temsilci_listesi)  # Satış Temsilcisi Seçimi
            aciklama = st.text_area("Açıklamalar")
            gorusme_kalitesi = st.slider("Görüşme Kalitesi (1=Kötü, 5=Çok İyi)", 1, 5, 3)
            tarih = st.date_input("Tarih", value=datetime.date.today())
            submitted = st.form_submit_button("Kaydet")
            if submitted:
                if not musteri_adi.strip() or not fuar_adi:
                    st.warning("Lütfen fuar seçin ve müşteri adı girin.")
                else:
                    new_row = {
                        "Fuar Adı": fuar_adi,
                        "Müşteri Adı": musteri_adi,
                        "Ülke": ulke,
                        "Telefon": tel,
                        "E-mail": email,
                        "Satış Temsilcisi": temsilci,
                        "Açıklamalar": aciklama,
                        "Görüşme Kalitesi": gorusme_kalitesi,
                        "Tarih": tarih
                    }
                    df_fuar_musteri = pd.concat([df_fuar_musteri, pd.DataFrame([new_row])], ignore_index=True)
                    update_excel()
                    st.success("Fuar müşterisi başarıyla eklendi!")
                    st.rerun()

    # --- ESKİ KAYIT DÜZENLE/SİL ---
    elif secim == "Eski Kayıt":
        kolonlar = ["Müşteri Adı", "Ülke", "Telefon", "E-mail", "Satış Temsilcisi", "Açıklamalar", "Görüşme Kalitesi", "Tarih"]
        musteri_df = df_fuar_musteri[df_fuar_musteri["Fuar Adı"] == fuar_adi].copy()
        if musteri_df.empty:
            st.info("Bu fuara ait müşteri kaydı bulunamadı.")
        else:
            st.markdown(f"<h4 style='color:#4776e6;'>{fuar_adi} Fuarındaki Müşteri Görüşme Kayıtları</h4>", unsafe_allow_html=True)
            secili_index = st.selectbox(
                "Düzenlemek/Silmek istediğiniz kaydı seçin:",
                musteri_df.index,
                format_func=lambda i: f"{musteri_df.at[i, 'Müşteri Adı']} ({musteri_df.at[i, 'Tarih']})"
            )
            # Kayıt görüntüle & düzenle
            with st.form("kayit_duzenle"):
                musteri_adi = st.text_input("Müşteri Adı", value=musteri_df.at[secili_index, "Müşteri Adı"])
                ulke = st.selectbox("Ülke", ulke_listesi, index=ulke_listesi.index(musteri_df.at[secili_index, "Ülke"]))
                temsilci = st.selectbox("Satış Temsilcisi", temsilci_listesi, index=temsilci_listesi.index(musteri_df.at[secili_index, "Satış Temsilcisi"]))
                tel = st.text_input("Telefon", value=musteri_df.at[secili_index, "Telefon"])
                email = st.text_input("E-mail", value=musteri_df.at[secili_index, "E-mail"])
                aciklama = st.text_area("Açıklamalar", value=musteri_df.at[secili_index, "Açıklamalar"])
                gorusme_kalitesi = st.slider(
                    "Görüşme Kalitesi (1=Kötü, 5=Çok İyi)", 1, 5,
                    int(musteri_df.at[secili_index, "Görüşme Kalitesi"]) if musteri_df.at[secili_index, "Görüşme Kalitesi"] else 3
                )
                tarih = st.date_input(
                    "Tarih",
                    value=pd.to_datetime(musteri_df.at[secili_index, "Tarih"]).date()
                    if musteri_df.at[secili_index, "Tarih"] else datetime.date.today()
                )
                guncelle = st.form_submit_button("Kaydı Güncelle")
                sil = st.form_submit_button("Kaydı Sil")
            if guncelle:
                for key, value in zip(kolonlar, [musteri_adi, ulke, tel, email, temsilci, aciklama, gorusme_kalitesi, tarih]):
                    df_fuar_musteri.at[secili_index, key] = value
                update_excel()
                st.success("Kayıt güncellendi!")
                st.rerun()
            if sil:
                df_fuar_musteri = df_fuar_musteri.drop(secili_index).reset_index(drop=True)
                update_excel()
                st.success("Kayıt silindi!")
                st.rerun()
            st.dataframe(musteri_df[kolonlar], use_container_width=True)

# ===========================
# === MEDYA ÇEKMECESİ MENÜSÜ ===
# ===========================

elif menu == "Medya Çekmecesi":
    st.markdown("<h2 style='color:#8e54e9; font-weight:bold;'>Medya Çekmecesi</h2>", unsafe_allow_html=True)
    st.info("Google Drive’daki medya, ürün görselleri ve kalite evraklarına aşağıdaki sekmelerden ulaşabilirsiniz.")

    # Klasör linkleri
    drive_folders = {
        "Genel Medya Klasörü": "https://drive.google.com/embeddedfolderview?id=1gFAaK-6v1e3346e-W0TsizOqSq43vHLY#list",
        "Ürün Görselleri": "https://drive.google.com/embeddedfolderview?id=18NNlmadm5NNFkI1Amzt_YMwB53j6AmbD#list",
        "Kalite Evrakları": "https://drive.google.com/embeddedfolderview?id=1pbArzYfA4Tp50zvdyTzSPF2ThrMWrGJc#list"
    }

    tab1, tab2, tab3 = st.tabs(list(drive_folders.keys()))

    with tab1:
        st.markdown(
            f"""
            <iframe src="{drive_folders['Genel Medya Klasörü']}" width="100%" height="600" frameborder="0" style="border:1px solid #eee; border-radius:12px; margin-top:10px;"></iframe>
            """,
            unsafe_allow_html=True
        )
        st.info("İlgili dosyanın üstüne çift tıklayarak yeni sekmede açabilir veya indirebilirsiniz.")

    with tab2:
        st.markdown(
            f"""
            <iframe src="{drive_folders['Ürün Görselleri']}" width="100%" height="600" frameborder="0" style="border:1px solid #eee; border-radius:12px; margin-top:10px;"></iframe>
            """,
            unsafe_allow_html=True
        )
        st.info("İlgili dosyanın üstüne çift tıklayarak yeni sekmede açabilir veya indirebilirsiniz.")

    with tab3:
        st.markdown(
            f"""
            <iframe src="{drive_folders['Kalite Evrakları']}" width="100%" height="600" frameborder="0" style="border:1px solid #eee; border-radius:12px; margin-top:10px;"></iframe>
            """,
            unsafe_allow_html=True
        )
        st.info("Kalite sertifikalarını ve ilgili dokümanları bu klasörden inceleyebilir ve indirebilirsiniz.")

    st.warning("Not: Klasörlerin paylaşım ayarlarının 'Bağlantıya sahip olan herkes görüntüleyebilir' olduğundan emin olun.")