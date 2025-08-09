# ======================
# 1) IMPORTLAR VE AYARLAR
# ======================
import os
import io
import datetime
import pandas as pd
import streamlit as st
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from google.oauth2 import service_account
import numpy as np
import smtplib
from email.message import EmailMessage

# ======================
# 2) ÜLKE ve TEMSİLCİ LİSTELERİ
# ======================
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

# ======================
# 3) GOOGLE SHEETS & DRIVE BAĞLANTILARI
# ======================
from googleapiclient.http import MediaFileUpload

SHEET_ID = "1nKuBKJPzpYC5TxNvc4G2OgI7miytuLBQE0n31I3yue0"

FIYAT_TEKLIFI_ID        = "1TNjwx-xhmlxNRI3ggCJA7jaCAu9Lt_65"
PROFORMA_PDF_KLASOR_ID  = "17lPkdYcC4BdowLdCsiWxiq0H_6oVGXLs"
SIPARIS_FORMU_ID = "1xeTdhOE1Cc6ohJsRzPVlCMMraBIXWO9w"
EVRAK_KLASOR_ID         = "14FTE1oSeIeJ6Y_7C0oQyZPKC8dK8hr1J"

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive.file",
    # İstersen: "https://www.googleapis.com/auth/drive"  # klasör izinleri/okuma için geniş kapsam
]

creds = service_account.Credentials.from_service_account_info(
    st.secrets["gcp_service_account"],
    scopes=SCOPES
)

sheets_service = build("sheets", "v4", credentials=creds)
sheet = sheets_service.spreadsheets()
drive_service = build("drive", "v3", credentials=creds)

def _safe_str(x):
    # DataFrame -> Sheets güvenli string
    if pd.isna(x):
        return ""
    if isinstance(x, (pd.Timestamp, datetime.datetime, datetime.date)):
        try:
            return pd.to_datetime(x).strftime("%Y-%m-%d")
        except Exception:
            return str(x)
    return str(x)

def df_to_values(df: pd.DataFrame):
    if df is None or df.empty:
        # Boşsa sadece başlıkları yazalım; başlık yoksa boş bir satır döndürme
        cols = df.columns.tolist() if isinstance(df, pd.DataFrame) else []
        return [cols] if cols else [[]]
    clean = df.copy()
    for c in clean.columns:
        clean[c] = clean[c].map(_safe_str)
    return [clean.columns.tolist()] + clean.values.tolist()

def write_df(sheet_name: str, df: pd.DataFrame):
    try:
        values = df_to_values(df)
        # İlk önce temizle
        sheet.values().clear(spreadsheetId=SHEET_ID, range=sheet_name).execute()
        # Sonra yaz
        sheet.values().update(
            spreadsheetId=SHEET_ID,
            range=sheet_name,
            valueInputOption="RAW",
            body={"values": values}
        ).execute()
    except Exception as e:
        # Konsola/loga bas; UI’da gürültü yapmamak için raise etmiyoruz
        print(f"'{sheet_name}' yazılırken hata: {e}")

def update_google_sheets():
    write_df("Sayfa1",       df_musteri)
    write_df("Kayıtlar",     df_kayit)
    write_df("Teklifler",    df_teklif)
    write_df("Proformalar",  df_proforma)
    write_df("Evraklar",     df_evrak)
    write_df("ETA",          df_eta)
    write_df("FuarMusteri",  df_fuar_musteri)

def _guess_mime_by_ext(filename: str) -> str:
    ext = os.path.splitext(filename.lower())[1]
    # Sık kullanılanlar
    return {
        ".pdf":  "application/pdf",
        ".jpg":  "image/jpeg",
        ".jpeg": "image/jpeg",
        ".png":  "image/png",
        ".csv":  "text/csv",
        ".xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        ".xls":  "application/vnd.ms-excel",
        ".txt":  "text/plain",
    }.get(ext, "application/octet-stream")

def _sanitize_filename(name: str) -> str:
    # Drive sorun çıkarmasın diye basit temizlik
    keep = "-_.() "
    return "".join(ch if ch.isalnum() or ch in keep else "_" for ch in str(name))[:180]

def upload_file_to_drive(folder_id: str, local_path: str, filename: str) -> str:
    from googleapiclient.http import MediaFileUpload
    meta = {"name": filename, "parents": [folder_id]} if folder_id else {"name": filename}
    media = MediaFileUpload(local_path, mimetype="application/pdf", resumable=False)
    created = drive_service.files().create(body=meta, media_body=media, fields="id").execute()
    fid = created["id"]
    try:
        drive_service.permissions().create(
            fileId=fid,
            body={"role": "reader", "type": "anyone"},
            fields="id"
        ).execute()
    except Exception:
        pass
    return f"https://drive.google.com/file/d/{fid}/view?usp=sharing"

# ======================
# 3b) SHEETS -> DATAFRAME YÜKLEME
# ======================

def load_sheet_as_df(sheet_name, columns):
    try:
        ws = sheet.values().get(spreadsheetId=SHEET_ID, range=sheet_name).execute()
        values = ws.get("values", [])
        if not values:
            return pd.DataFrame(columns=columns)

        header = values[0]
        data_rows = values[1:]

        # Sadece ETA’da şemayı sabitle
        if sheet_name == "ETA":
            header = columns

        df = pd.DataFrame(data_rows, columns=header)

        # Eksik sütun varsa ekle (diğer sayfalarda kırılmaz)
        for col in columns:
            if col not in df.columns:
                df[col] = ""

        return df
    except Exception as e:
        print(f"'{sheet_name}' sayfası yüklenirken hata: {e}")
        return pd.DataFrame(columns=columns)
        
# --- tüm sayfaları yükle ---
df_musteri = load_sheet_as_df("Sayfa1", [
    "Müşteri Adı","Telefon","E-posta","Adres","Ülke",
    "Satış Temsilcisi","Kategori","Durum","Vade (Gün)","Ödeme Şekli",
    "Para Birimi","DT Seçimi"
])

df_kayit = load_sheet_as_df("Kayıtlar", [
    "Müşteri Adı","Tarih","Tip","Açıklama"
])

df_teklif = load_sheet_as_df("Teklifler", [
    "Müşteri Adı","Tarih","Teklif No","Tutar",
    "Ürün/Hizmet","Açıklama","Durum","PDF"
])

df_proforma = load_sheet_as_df("Proformalar", [
    "Müşteri Adı","Tarih","Proforma No","Tutar","Açıklama",
    "Durum","PDF","Sipariş Formu","Vade (gün)","Sevk Durumu",
    "Ülke","Satış Temsilcisi","Ödeme Şekli","Termin Tarihi",
    "Sevk Tarihi","Ulaşma Tarihi"
])

df_evrak = load_sheet_as_df("Evraklar", [
    "Müşteri Adı","Proforma No","Fatura No","Fatura Tarihi","Vade (gün)","Vade Tarihi","Tutar",
    "Ülke","Satış Temsilcisi","Ödeme Şekli",
    "Commercial Invoice","Sağlık Sertifikası","Packing List","Konşimento","İhracat Beyannamesi",
    "Fatura PDF","Sipariş Formu","Yük Resimleri","EK Belgeler","Ödendi"
])

df_eta = load_sheet_as_df("ETA", [
    "Müşteri Adı","Proforma No","ETA Tarihi","Açıklama"
])

df_fuar_musteri = load_sheet_as_df("FuarMusteri", [
    "Fuar Adı","Müşteri Adı","Ülke","Telefon","E-mail","Satış Temsilcisi",
    "Açıklamalar","Görüşme Kalitesi","Tarih"
])

# ======================
# 4) MENÜ LİSTESİ & YETKİ KONTROLÜ
# ======================

MENULER = [
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

# Boss sadece özet görsün; diğerleri tüm menüler
allowed_menus = [("Özet Ekran", "menu-ozet", "📊")] if st.session_state.get("user") == "Boss" else MENULER

# mevcut seçim yoksa veya izinli listede değilse ilk menüye al
if "menu_state" not in st.session_state or st.session_state.menu_state not in [m[0] for m in allowed_menus]:
    st.session_state.menu_state = allowed_menus[0][0]

# Sidebar stilleri
st.sidebar.markdown("""
<style>
.menu-btn {display:block;width:100%;padding:1em;margin-bottom:10px;border:none;border-radius:10px;
font-size:1.05em;font-weight:600;color:white;cursor:pointer;transition:filter .2s;}
.menu-ozet {background: linear-gradient(90deg,#43cea2,#185a9d);}
.menu-cari {background: linear-gradient(90deg,#43cea2,#185a9d);}
.menu-musteri {background: linear-gradient(90deg,#ffb347,#ffcc33);}
.menu-gorusme {background: linear-gradient(90deg,#ff5e62,#ff9966);}
.menu-teklif {background: linear-gradient(90deg,#8e54e9,#4776e6);}
.menu-proforma {background: linear-gradient(90deg,#11998e,#38ef7d);}
.menu-siparis {background: linear-gradient(90deg,#f7971e,#ffd200);}
.menu-evrak {background: linear-gradient(90deg,#f953c6,#b91d73);}
.menu-vade {background: linear-gradient(90deg,#43e97b,#38f9d7);}
.menu-eta {background: linear-gradient(90deg,#f857a6,#ff5858);}
.menu-fuar {background: linear-gradient(90deg,#6a11cb,#2575fc);}
.menu-medya {background: linear-gradient(90deg,#232526,#414345);}
.menu-btn:hover {filter:brightness(1.15);}
</style>
""", unsafe_allow_html=True)

# Sidebar butonları
for i, (isim, css, ikon) in enumerate(allowed_menus):
    if st.sidebar.button(f"{ikon} {isim}", key=f"menu_{i}", help=isim):
        st.session_state.menu_state = isim

menu = st.session_state.menu_state

# ======================
# 5) ÖZET EKRAN
# ======================

if menu == "Özet Ekran":
    st.markdown("<h2 style='color:#219A41; font-weight:bold;'>ŞEKEROĞLU İHRACAT CRM - Özet Ekran</h2>", unsafe_allow_html=True)

    # --- Bekleyen Teklifler ---
    st.markdown("### 💰 Bekleyen Teklifler")
    bekleyen_teklifler = df_teklif[df_teklif.get("Durum","") == "Açık"].copy()
    if not bekleyen_teklifler.empty and "Tarih" in bekleyen_teklifler:
        bekleyen_teklifler["Tarih"] = pd.to_datetime(bekleyen_teklifler["Tarih"], errors="coerce").dt.strftime("%d/%m/%Y")
    toplam_teklif = pd.to_numeric(bekleyen_teklifler.get("Tutar", pd.Series(dtype=float)), errors="coerce").sum() if not bekleyen_teklifler.empty else 0
    st.markdown(f"<div style='font-size:1.1em; color:#11998e; font-weight:bold;'>Toplam: {toplam_teklif:,.2f} $</div>", unsafe_allow_html=True)
    st.dataframe(
        bekleyen_teklifler[["Müşteri Adı","Tarih","Teklif No","Tutar","Ürün/Hizmet","Açıklama"]] if not bekleyen_teklifler.empty else pd.DataFrame(columns=["Müşteri Adı","Tarih","Teklif No","Tutar","Ürün/Hizmet","Açıklama"]),
        use_container_width=True
    )

    # --- Bekleyen Proformalar ---
    st.markdown("### 📄 Bekleyen Proformalar")
    bekleyen_proformalar = df_proforma[df_proforma.get("Durum","") == "Beklemede"].copy()
    if not bekleyen_proformalar.empty and "Tarih" in bekleyen_proformalar:
        bekleyen_proformalar["Tarih"] = pd.to_datetime(bekleyen_proformalar["Tarih"], errors="coerce").dt.strftime("%d/%m/%Y")
    toplam_proforma = pd.to_numeric(bekleyen_proformalar.get("Tutar", pd.Series(dtype=float)), errors="coerce").sum() if not bekleyen_proformalar.empty else 0
    st.markdown(f"<div style='font-size:1.1em; color:#f7971e; font-weight:bold;'>Toplam: {toplam_proforma:,.2f} $</div>", unsafe_allow_html=True)
    st.dataframe(
        bekleyen_proformalar[["Müşteri Adı","Proforma No","Tarih","Tutar","Açıklama"]] if not bekleyen_proformalar.empty else pd.DataFrame(columns=["Müşteri Adı","Proforma No","Tarih","Tutar","Açıklama"]),
        use_container_width=True
    )

    # --- Siparişe Dönüşen (Sevk Bekleyen) ---
    st.markdown("### 🚚 Siparişe Dönüşen (Sevk Bekleyen) Siparişler")
    for c in ["Sevk Durumu","Termin Tarihi","Satış Temsilcisi","Ödeme Şekli","Ülke"]: 
        if c not in df_proforma.columns: df_proforma[c] = ""
    siparisler = df_proforma[(df_proforma["Durum"] == "Siparişe Dönüştü") & (~df_proforma["Sevk Durumu"].isin(["Sevkedildi","Ulaşıldı"]))].copy()
    siparisler["Termin Tarihi Order"] = pd.to_datetime(siparisler["Termin Tarihi"], errors="coerce")
    siparisler = siparisler.sort_values("Termin Tarihi Order", ascending=True)
    if not siparisler.empty:
        siparisler["Tarih"] = pd.to_datetime(siparisler["Tarih"], errors="coerce").dt.strftime("%d/%m/%Y")
        siparisler["Termin Tarihi"] = pd.to_datetime(siparisler["Termin Tarihi"], errors="coerce").dt.strftime("%d/%m/%Y")
    st.dataframe(
        siparisler[["Tarih","Müşteri Adı","Termin Tarihi","Ülke","Satış Temsilcisi","Ödeme Şekli","Proforma No","Tutar","Açıklama"]] if not siparisler.empty else pd.DataFrame(columns=["Tarih","Müşteri Adı","Termin Tarihi","Ülke","Satış Temsilcisi","Ödeme Şekli","Proforma No","Tutar","Açıklama"]),
        use_container_width=True
    )
    toplam_bekleyen_sevk = pd.to_numeric(siparisler.get("Tutar", pd.Series(dtype=float)), errors="coerce").sum() if not siparisler.empty else 0
    st.markdown(f"<div style='color:#219A41; font-weight:bold;'>*Toplam Bekleyen Sevk: {toplam_bekleyen_sevk:,.2f} $*</div>", unsafe_allow_html=True)

    # --- Yolda Olan (ETA) ---
    st.markdown("### ⏳ Yolda Olan (ETA Takibi) Siparişler")
    eta_yolda = df_proforma[(df_proforma.get("Sevk Durumu","") == "Sevkedildi") & (df_proforma.get("Sevk Durumu","") != "Ulaşıldı")].copy()
    toplam_eta = pd.to_numeric(eta_yolda.get("Tutar", pd.Series(dtype=float)), errors="coerce").sum() if not eta_yolda.empty else 0
    st.markdown(f"<div style='font-size:1.1em; color:#c471f5; font-weight:bold;'>Toplam: {toplam_eta:,.2f} $</div>", unsafe_allow_html=True)
    st.dataframe(
        eta_yolda[["Müşteri Adı","Ülke","Proforma No","Tarih","Tutar","Termin Tarihi","Açıklama"]] if not eta_yolda.empty else pd.DataFrame(columns=["Müşteri Adı","Ülke","Proforma No","Tarih","Tutar","Termin Tarihi","Açıklama"]),
        use_container_width=True
    )

    # --- Son Teslim Edilen 5 Sipariş ---
    st.markdown("### ✅ Son Teslim Edilen (Ulaşıldı) 5 Sipariş")
    if "Sevk Durumu" in df_proforma.columns:
        teslim_edilenler = df_proforma[df_proforma["Sevk Durumu"] == "Ulaşıldı"].copy()
        if not teslim_edilenler.empty:
            teslim_edilenler = teslim_edilenler.sort_values(by="Tarih", ascending=False).head(5)
            teslim_edilenler["Tarih"] = pd.to_datetime(teslim_edilenler["Tarih"], errors="coerce").dt.strftime("%d/%m/%Y")
            teslim_edilenler["Termin Tarihi"] = pd.to_datetime(teslim_edilenler["Termin Tarihi"], errors="coerce").dt.strftime("%d/%m/%Y")
            st.dataframe(
                teslim_edilenler[["Müşteri Adı","Ülke","Proforma No","Tarih","Tutar","Termin Tarihi","Açıklama"]],
                use_container_width=True
            )
        else:
            st.info("Teslim edilmiş sipariş yok.")
    else:
        st.info("Teslim edilmiş sipariş yok.")

    # --- Boss için Vade Özeti ---
    if st.session_state.get("user") == "Boss":
        st.markdown("### 💸 Vadeli Fatura ve Tahsilat Takibi")
        for c in ["Proforma No","Vade (gün)","Ödendi","Ülke","Satış Temsilcisi","Ödeme Şekli"]:
            if c not in df_evrak.columns: df_evrak[c] = "" if c != "Ödendi" else False
        df_evrak["Ödendi"] = df_evrak["Ödendi"].fillna(False).astype(bool)
        vade_df = df_evrak[df_evrak["Vade Tarihi"].notna() & (~df_evrak["Ödendi"])].copy()
        if not vade_df.empty:
            vade_df["Vade Tarihi"] = pd.to_datetime(vade_df["Vade Tarihi"], errors="coerce")
            vade_df["Kalan Gün"] = (vade_df["Vade Tarihi"] - pd.to_datetime(datetime.date.today())).dt.days
            st.dataframe(vade_df[["Müşteri Adı","Ülke","Fatura No","Vade Tarihi","Tutar","Kalan Gün"]], use_container_width=True)
        else:
            st.info("Açık vade kaydı yok.")

    st.markdown("<hr>", unsafe_allow_html=True)
    st.info("Detaylı işlem için sol menüden ilgili bölüme geçebilirsiniz.")

# ======================
# 6) CARİ EKLEME
# ======================

def yeni_cari_txt_olustur(cari_dict: dict, file_path="yeni_cari.txt"):
    with open(file_path, "w", encoding="utf-8") as f:
        f.write(
            f"Müşteri Adı: {cari_dict.get('Müşteri Adı','')}\n"
            f"Telefon: {cari_dict.get('Telefon','')}\n"
            f"E-posta: {cari_dict.get('E-posta','')}\n"
            f"Adres: {cari_dict.get('Adres','')}\n"
            f"Ülke: {cari_dict.get('Ülke','')}\n"
            f"Satış Temsilcisi: {cari_dict.get('Satış Temsilcisi','')}\n"
            f"Kategori: {cari_dict.get('Kategori','')}\n"
            f"Durum: {cari_dict.get('Durum','')}\n"
            f"Vade (Gün): {cari_dict.get('Vade (Gün)','')}\n"
            f"Ödeme Şekli: {cari_dict.get('Ödeme Şekli','')}\n"
            f"Para Birimi: {cari_dict.get('Para Birimi','')}\n"
            f"DT Seçimi: {cari_dict.get('DT Seçimi','')}\n"
        )

def send_email_with_txt(to_email: list[str], subject: str, body: str, file_path: str):
    from_email = "todo@sekeroglugroup.com"
    password   = "vbgvforwwbcpzhxf"  # Gmail uygulama şifresi
    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = from_email
    msg["To"] = ", ".join(to_email)
    msg.set_content(body)
    with open(file_path, "rb") as f:
        msg.add_attachment(f.read(), maintype="text", subtype="plain", filename="yeni_cari.txt")
    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as smtp:
        smtp.login(from_email, password)
        smtp.send_message(msg)

if menu == "Cari Ekleme":
    st.markdown("<h2 style='color:#219A41; font-weight:bold;'>Yeni Müşteri Ekle</h2>", unsafe_allow_html=True)
    with st.form("add_customer"):
        name = st.text_input("Müşteri Adı")
        phone = st.text_input("Telefon")
        email = st.text_input("E-posta")
        address = st.text_area("Adres")
        ulke = st.selectbox("Ülke", ulke_listesi)
        temsilci = st.selectbox("Satış Temsilcisi", temsilci_listesi)
        kategori = st.selectbox("Kategori", ["Avrupa bayi","bayi","müşteri","yeni müşteri"])
        aktif_pasif = st.selectbox("Durum", ["Aktif","Pasif"])
        vade_gun = st.number_input("Vade (Gün Sayısı)", min_value=0, max_value=365, value=0, step=1)
        odeme_sekli = st.selectbox("Ödeme Şekli", ["Peşin","Mal Mukabili","Vesaik Mukabili","Akreditif","Diğer"])
        para_birimi = st.selectbox("Para Birimi", ["EURO","USD","TL","RUBLE"])
        dt_secim = st.selectbox("DT Seçin", ["DT-1","DT-2","DT-3","DT-4"])
        submitted = st.form_submit_button("Kaydet")

    if submitted:
        if not name.strip():
            st.error("Müşteri adı boş olamaz!")
        else:
            new_row = {
                "Müşteri Adı": name, "Telefon": phone, "E-posta": email, "Adres": address,
                "Ülke": ulke, "Satış Temsilcisi": temsilci, "Kategori": kategori, "Durum": aktif_pasif,
                "Vade (Gün)": vade_gun, "Ödeme Şekli": odeme_sekli, "Para Birimi": para_birimi, "DT Seçimi": dt_secim
            }
            df_musteri = pd.concat([df_musteri, pd.DataFrame([new_row])], ignore_index=True)
            update_google_sheets()  # <- senin mevcut fonksiyonun
            yeni_cari_txt_olustur(new_row)
            try:
                send_email_with_txt(
                    to_email=["muhasebe@sekeroglugroup.com","h.boy@sekeroglugroup.com"],
                    subject="Yeni Cari Açılışı",
                    body="Muhasebe için yeni cari açılışı ekte gönderilmiştir.",
                    file_path="yeni_cari.txt"
                )
                st.success("Müşteri eklendi ve e-posta ile muhasebeye gönderildi!")
            except Exception as e:
                st.warning(f"Müşteri eklendi fakat e-posta gönderilemedi: {e}")
            st.rerun()

# ======================
# 7) MÜŞTERİ LİSTESİ
# ======================

if menu == "Müşteri Listesi":
    st.markdown("<h2 style='color:#219A41; font-weight:bold;'>Müşteri Listesi</h2>", unsafe_allow_html=True)

    # Eksik kolonlar
    for c in ["Vade (Gün)","Ülke","Satış Temsilcisi","Ödeme Şekli","Kategori","Durum"]:
        if c not in df_musteri.columns: df_musteri[c] = ""

    if df_musteri.empty:
        st.markdown("<div style='color:#b00020; font-weight:bold; font-size:1.1em;'>Henüz müşteri kaydı yok.</div>", unsafe_allow_html=True)
    else:
        # Sadece aktif müşteriler
        aktif_df = df_musteri[df_musteri["Durum"]=="Aktif"].copy()
        aktif_df = aktif_df.sort_values("Müşteri Adı").reset_index(drop=True)
        st.dataframe(aktif_df.replace({np.nan:"Eksik bilgi, lütfen tamamlayın","":"Eksik bilgi, lütfen tamamlayın"}), use_container_width=True)

        st.markdown("<h4 style='margin-top:22px;'>Müşteri Düzenle</h4>", unsafe_allow_html=True)
        df_sorted = df_musteri.sort_values("Müşteri Adı").reset_index(drop=True)
        sec_idx = st.selectbox(
            "Düzenlenecek Müşteri",
            options=df_sorted.index.tolist(),
            format_func=lambda i: f"{df_sorted.at[i,'Müşteri Adı']} ({df_sorted.at[i,'Kategori']})"
        )

        with st.form("edit_customer"):
            name = st.text_input("Müşteri Adı", value=df_sorted.at[sec_idx,"Müşteri Adı"])
            phone = st.text_input("Telefon", value=df_sorted.at[sec_idx,"Telefon"])
            email = st.text_input("E-posta", value=df_sorted.at[sec_idx,"E-posta"])
            address = st.text_area("Adres", value=df_sorted.at[sec_idx,"Adres"])
            ulke = st.selectbox("Ülke", ulke_listesi, index=ulke_listesi.index(df_sorted.at[sec_idx,"Ülke"]) if df_sorted.at[sec_idx,"Ülke"] in ulke_listesi else 0)
            temsilci = st.selectbox("Satış Temsilcisi", temsilci_listesi, index=temsilci_listesi.index(df_sorted.at[sec_idx,"Satış Temsilcisi"]) if df_sorted.at[sec_idx,"Satış Temsilcisi"] in temsilci_listesi else 0)
            kategori = st.selectbox("Kategori", ["Avrupa bayi","bayi","müşteri","yeni müşteri"], index=(["Avrupa bayi","bayi","müşteri","yeni müşteri"].index(df_sorted.at[sec_idx,"Kategori"]) if df_sorted.at[sec_idx,"Kategori"] in ["Avrupa bayi","bayi","müşteri","yeni müşteri"] else 0))
            durum = st.selectbox("Durum", ["Aktif","Pasif"], index=(0 if df_sorted.at[sec_idx,"Durum"]=="Aktif" else 1))
            vade = st.text_input("Vade (Gün)", value=str(df_sorted.at[sec_idx,"Vade (Gün)"]))
            odeme = st.selectbox("Ödeme Şekli", ["Peşin","Mal Mukabili","Vesaik Mukabili","Akreditif","Diğer"],
                                 index=(["Peşin","Mal Mukabili","Vesaik Mukabili","Akreditif","Diğer"].index(df_sorted.at[sec_idx,"Ödeme Şekli"]) if df_sorted.at[sec_idx,"Ödeme Şekli"] in ["Peşin","Mal Mukabili","Vesaik Mukabili","Akreditif","Diğer"] else 0))
            guncelle = st.form_submit_button("Güncelle")
        if guncelle:
            orj_idx = df_musteri[df_musteri["Müşteri Adı"]==df_sorted.at[sec_idx,"Müşteri Adı"]].index
            if len(orj_idx):
                i = orj_idx[0]
                df_musteri.at[i,"Müşteri Adı"]=name; df_musteri.at[i,"Telefon"]=phone; df_musteri.at[i,"E-posta"]=email
                df_musteri.at[i,"Adres"]=address; df_musteri.at[i,"Ülke"]=ulke; df_musteri.at[i,"Satış Temsilcisi"]=temsilci
                df_musteri.at[i,"Kategori"]=kategori; df_musteri.at[i,"Durum"]=durum; df_musteri.at[i,"Vade (Gün)"]=vade
                df_musteri.at[i,"Ödeme Şekli"]=odeme
                update_google_sheets()
                st.success("Müşteri güncellendi!")
                st.rerun()

        st.markdown("<h4 style='margin-top:12px;'>Müşteri Sil</h4>", unsafe_allow_html=True)
        if st.button("Seçili Müşteriyi Sil"):
            orj_idx = df_musteri[df_musteri["Müşteri Adı"]==df_sorted.at[sec_idx,"Müşteri Adı"]].index
            if len(orj_idx):
                df_musteri = df_musteri.drop(orj_idx[0]).reset_index(drop=True)
                update_google_sheets()
                st.success("Müşteri silindi!")
                st.rerun()

# =========================================
# 8) GÖRÜŞME / ARAMA / ZİYARET KAYITLARI
# =========================================

elif menu == "Görüşme / Arama / Ziyaret Kayıtları":
    st.markdown("<h2 style='color:#219A41; font-weight:bold;'>Görüşme / Arama / Ziyaret Kayıtları</h2>", unsafe_allow_html=True)

    # Müşteri listesi (boş seçenek başta)
    musteri_options = [""] + sorted([m for m in df_musteri["Müşteri Adı"].dropna().unique() if str(m).strip()!=""])

    secim = st.radio("İşlem Seçin:", ["Yeni Kayıt", "Eski Kayıt", "Tarih Aralığı ile Kayıtlar"], horizontal=True)

    # Yeni Kayıt
    if secim == "Yeni Kayıt":
        with st.form("add_kayit"):
            musteri_sec = st.selectbox("Müşteri Seç", musteri_options, index=0)
            tarih = st.date_input("Tarih", value=datetime.date.today(), format="DD/MM/YYYY")
            tip = st.selectbox("Tip", ["Arama","Görüşme","Ziyaret"])
            aciklama = st.text_area("Açıklama")
            submitted = st.form_submit_button("Kaydet")
        if submitted:
            if not musteri_sec:
                st.error("Lütfen müşteri seçiniz.")
            else:
                df_kayit = pd.concat([df_kayit, pd.DataFrame([{
                    "Müşteri Adı": musteri_sec, "Tarih": tarih, "Tip": tip, "Açıklama": aciklama
                }])], ignore_index=True)
                update_google_sheets()
                st.success("Kayıt eklendi!")
                st.rerun()

    # Eski Kayıt
    elif secim == "Eski Kayıt":
        musteri_sec = st.selectbox("Müşteri Seç", musteri_options, index=0, key="eski_musteri")
        if musteri_sec:
            kayitlar = df_kayit[df_kayit["Müşteri Adı"]==musteri_sec].sort_values("Tarih", ascending=False).copy()
            if not kayitlar.empty:
                kayitlar["Tarih"] = pd.to_datetime(kayitlar["Tarih"], errors="coerce").dt.strftime("%d/%m/%Y")
                st.dataframe(kayitlar, use_container_width=True)
            else:
                st.info("Seçili müşteri için kayıt yok.")
        else:
            st.info("Lütfen müşteri seçin.")

    # Tarih Aralığı
    else:
        col1,col2 = st.columns(2)
        with col1: bas = st.date_input("Başlangıç", value=datetime.date.today()-datetime.timedelta(days=7), format="DD/MM/YYYY")
        with col2: bit = st.date_input("Bitiş", value=datetime.date.today(), format="DD/MM/YYYY")
        tarih_arasi = df_kayit[(pd.to_datetime(df_kayit["Tarih"], errors="coerce")>=pd.to_datetime(bas)) &
                               (pd.to_datetime(df_kayit["Tarih"], errors="coerce")<=pd.to_datetime(bit))].copy()
        if not tarih_arasi.empty:
            tarih_arasi["Tarih"] = pd.to_datetime(tarih_arasi["Tarih"], errors="coerce").dt.strftime("%d/%m/%Y")
            st.dataframe(tarih_arasi.sort_values("Tarih", ascending=False), use_container_width=True)
        else:
            st.info("Bu tarihler arasında kayıt yok.")

# ======================
# 9) FİYAT TEKLİFLERİ
# ======================

FIYAT_TEKLIFI_ID   = "1TNjwx-xhmlxNRI3ggCJA7jaCAu9Lt_65"   # <- senin verdiğin
PROFORMA_PDF_ID    = "17lPkdYcC4BdowLdCsiWxiq0H_6oVGXLs"   # <- daha önce kullandığımız
SIPARIS_FORMU_ID   = "1xeTdhOE1Cc6ohJsRzPVlCMMraBIXWO9w"   # <- daha önce kullandığımız
EVRAK_KLASOR_ID    = "14FTE1oSeIeJ6Y_7C0oQyZPKC8dK8hr1J"   # <- senin verdiğin

if menu == "Fiyat Teklifleri":
    st.markdown("<h2 style='color:#219A41; font-weight:bold;'>Fiyat Teklifleri</h2>", unsafe_allow_html=True)

    # Teklif No oluşturucu
    def otomatik_teklif_no():
        if df_teklif.empty or "Teklif No" not in df_teklif.columns:
            return "TKF-0001"
        mevcut = pd.to_numeric(
            df_teklif["Teklif No"].astype(str).str.extract(r"(\d+)$")[0],
            errors="coerce"
        ).dropna().astype(int)
        return f"TKF-{(mevcut.max()+1 if not mevcut.empty else 1):04d}"

    # Açık teklifler özeti
    goster = df_teklif.copy()
    if not goster.empty and "Tarih" in goster.columns:
        goster["Tarih"] = pd.to_datetime(goster["Tarih"], errors="coerce").dt.strftime("%d/%m/%Y")

    if "Durum" in goster.columns:
        acik = goster[goster["Durum"] == "Açık"].sort_values(["Müşteri Adı","Teklif No"])
    else:
        acik = pd.DataFrame(columns=["Müşteri Adı","Tarih","Teklif No","Tutar","Ürün/Hizmet","Açıklama"])

    toplam = pd.to_numeric(acik["Tutar"], errors="coerce").sum() if not acik.empty else 0
    st.markdown(
        f"<div style='font-size:1.05em; color:#11998e; font-weight:bold;'>Toplam: {toplam:,.2f} $ | Açık Teklif: {len(acik)} adet</div>",
        unsafe_allow_html=True
    )
    st.dataframe(
        acik[["Müşteri Adı","Tarih","Teklif No","Tutar","Ürün/Hizmet","Açıklama"]]
        if not acik.empty else
        pd.DataFrame(columns=["Müşteri Adı","Tarih","Teklif No","Tutar","Ürün/Hizmet","Açıklama"]),
        use_container_width=True
    )

    col1, col2 = st.columns(2)
    with col1: yeni_btn = st.button("Yeni Teklif")
    with col2: eski_btn = st.button("Eski Teklif")

    if "teklif_view" not in st.session_state:
        st.session_state.teklif_view = None
    if yeni_btn:
        st.session_state.teklif_view = "yeni"
    if eski_btn:
        st.session_state.teklif_view = "eski"

    # Yeni Teklif
    if st.session_state.teklif_view == "yeni":
        must_list = [""] + sorted(df_musteri["Müşteri Adı"].dropna().unique().tolist())
        with st.form("add_teklif"):
            st.subheader("Yeni Teklif Ekle")
            musteri_sec = st.selectbox("Müşteri", must_list, index=0, key="yeni_teklif_musteri")
            tarih = st.date_input("Tarih", value=datetime.date.today(), format="DD/MM/YYYY")
            teklif_no = st.text_input("Teklif No", value=otomatik_teklif_no())
            tutar = st.text_input("Tutar ($)")
            urun = st.text_input("Ürün/Hizmet")
            aciklama = st.text_area("Açıklama")
            durum = st.selectbox("Durum", ["Açık","Sonuçlandı","Beklemede"], index=0)
            pdf = st.file_uploader("Teklif PDF", type="pdf")
            kaydet = st.form_submit_button("Kaydet")

        if kaydet:
            if not teklif_no.strip() or not musteri_sec:
                st.error("Teklif No ve Müşteri zorunlu.")
            else:
                pdf_link = ""
                if pdf:
                    temiz_m = "".join(ch if ch.isalnum() else "_" for ch in str(musteri_sec))
                    temiz_t = str(tarih).replace("-","")
                    fname = f"{temiz_m}__{temiz_t}__{teklif_no}.pdf"
                    tmp = os.path.join(".", fname)
                    with open(tmp, "wb") as f:
                        f.write(pdf.read())

                    # >>> PyDrive yerine ortak helper:
                    pdf_link = upload_file_to_drive(
                        FIYAT_TEKLIFI_ID,
                        tmp,
                        fname
                    )
                    try:
                        os.remove(tmp)
                    except Exception:
                        pass

                df_teklif = pd.concat([df_teklif, pd.DataFrame([{
                    "Müşteri Adı": musteri_sec,
                    "Tarih": tarih,
                    "Teklif No": teklif_no,
                    "Tutar": tutar,
                    "Ürün/Hizmet": urun,
                    "Açıklama": aciklama,
                    "Durum": durum,
                    "PDF": pdf_link
                }])], ignore_index=True)

                update_google_sheets()
                st.success("Teklif eklendi!")
                st.session_state.teklif_view = None
                st.rerun()

    # Eski Teklif
    if st.session_state.teklif_view == "eski":
        st.subheader("Eski Teklifler")
        musteri_listesi = [""] + sorted(df_teklif["Müşteri Adı"].dropna().unique().tolist())
        sec_mus = st.selectbox("Müşteri Seç", musteri_listesi, key="eski_teklif_mus")
        if sec_mus:
            tlf = df_teklif[df_teklif["Müşteri Adı"] == sec_mus].sort_values("Tarih", ascending=False)
            if tlf.empty:
                st.info("Bu müşteriye ait teklif yok.")
            else:
                sec_i = st.selectbox(
                    "Teklif Seç",
                    tlf.index,
                    format_func=lambda i: f"{tlf.at[i,'Teklif No']} | {tlf.at[i,'Tarih']}"
                )
                kayit = tlf.loc[sec_i]
                if str(kayit.get("PDF","")).strip():
                    st.markdown(f"**Teklif PDF:** [{kayit['Teklif No']}]({kayit['PDF']})", unsafe_allow_html=True)
                st.table({
                    "Müşteri Adı":[kayit["Müşteri Adı"]],
                    "Tarih":[kayit["Tarih"]],
                    "Teklif No":[kayit["Teklif No"]],
                    "Tutar":[kayit["Tutar"]],
                    "Ürün/Hizmet":[kayit["Ürün/Hizmet"]],
                    "Açıklama":[kayit["Açıklama"]],
                    "Durum":[kayit["Durum"]]
                })

# ======================
# 10) PROFORMA TAKİBİ
# ======================

elif menu == "Proforma Takibi":
    st.markdown("<h2 style='color:#219A41; font-weight:bold;'>Proforma Takibi</h2>", unsafe_allow_html=True)

    # Eksik kolonlar
    for col in ["Vade (gün)", "Sipariş Formu", "Durum", "PDF", "Sevk Durumu",
                "Ülke", "Satış Temsilcisi", "Ödeme Şekli", "Termin Tarihi", "Sevk Tarihi", "Ulaşma Tarihi"]:
        if col not in df_proforma.columns:
            df_proforma[col] = ""

    # Beklemede özet
    beklemede = df_proforma[df_proforma["Durum"] == "Beklemede"]
    if not beklemede.empty:
        st.subheader("Bekleyen Proformalar")
        st.dataframe(
            beklemede[["Müşteri Adı", "Proforma No", "Tarih", "Tutar", "Durum", "Vade (gün)", "Sevk Durumu"]],
            use_container_width=True
        )

    musteri_list = sorted(
        [x for x in df_musteri["Müşteri Adı"].dropna().unique() if isinstance(x, str) and x.strip() != ""]
    ) if not df_musteri.empty else []
    musteri_sec = st.selectbox("Müşteri Seç", [""] + musteri_list)

    if musteri_sec:
        islem = st.radio("İşlem", ["Yeni Kayıt", "Eski Kayıt"], horizontal=True)

        # --- YENİ KAYIT ---
        if islem == "Yeni Kayıt":
            mi = df_musteri[df_musteri["Müşteri Adı"] == musteri_sec]
            def_ulke = mi["Ülke"].values[0] if not mi.empty else ""
            def_rep  = mi["Satış Temsilcisi"].values[0] if not mi.empty else ""
            def_pay  = mi["Ödeme Şekli"].values[0] if not mi.empty else ""

            with st.form("add_proforma"):
                tarih = st.date_input("Tarih", value=datetime.date.today())
                proforma_no = st.text_input("Proforma No")
                tutar = st.text_input("Tutar ($)")
                vade_gun = st.text_input("Vade (gün)")
                ulke = st.text_input("Ülke", value=def_ulke, disabled=True)
                temsilci = st.text_input("Satış Temsilcisi", value=def_rep, disabled=True)
                odeme = st.text_input("Ödeme Şekli", value=def_pay, disabled=True)
                aciklama = st.text_area("Açıklama")
                durum = st.selectbox("Durum", ["Beklemede", "İptal", "Faturası Kesildi", "Siparişe Dönüştü"], index=0)
                pdf_file = st.file_uploader("Proforma PDF", type="pdf")
                kaydet = st.form_submit_button("Kaydet")

            pdf_link = ""
            if kaydet:
                if not proforma_no.strip() or not vade_gun.strip():
                    st.error("Proforma No ve Vade (gün) zorunlu!")
                else:
                    # Proforma PDF -> Google Drive
                    if pdf_file:
                        fname = f"{musteri_sec}_{tarih}_{proforma_no}.pdf"
                        tmp = os.path.join(".", fname)
                        with open(tmp, "wb") as f:
                            f.write(pdf_file.read())
                        try:
                            pdf_link = upload_file_to_drive(PROFORMA_PDF_ID, tmp, fname)
                        finally:
                            try:
                                os.remove(tmp)
                            except:
                                pass

                    new_row = {
                        "Müşteri Adı": musteri_sec,
                        "Tarih": tarih,
                        "Proforma No": proforma_no,
                        "Tutar": tutar,
                        "Vade (gün)": vade_gun,
                        "Ülke": def_ulke,
                        "Satış Temsilcisi": def_rep,
                        "Ödeme Şekli": def_pay,
                        "Açıklama": aciklama,
                        "Durum": "Beklemede",        # sipariş formu ayrı adımda
                        "PDF": pdf_link,
                        "Sipariş Formu": "",
                        "Sevk Durumu": ""
                    }
                    df_proforma = pd.concat([df_proforma, pd.DataFrame([new_row])], ignore_index=True)
                    update_google_sheets()
                    st.success("Proforma eklendi!")
                    st.rerun()

        # --- ESKİ KAYIT ---
        elif islem == "Eski Kayıt":
            kayitlar = df_proforma[
                (df_proforma["Müşteri Adı"] == musteri_sec) & (df_proforma["Durum"] == "Beklemede")
            ]
            if kayitlar.empty:
                st.info("Bu müşteriye ait bekleyen proforma yok.")
            else:
                st.dataframe(
                    kayitlar[["Müşteri Adı", "Proforma No", "Tarih", "Tutar", "Durum", "Vade (gün)", "Sevk Durumu"]],
                    use_container_width=True
                )

                sec_index = st.selectbox(
                    "Proforma Seç",
                    kayitlar.index,
                    format_func=lambda i: f"{kayitlar.at[i, 'Proforma No']} | {kayitlar.at[i, 'Tarih']}"
                )

                if sec_index is not None:
                    row = kayitlar.loc[sec_index]
                    if str(row.get("PDF", "")).strip():
                        st.markdown(f"**Proforma PDF:** [{row['Proforma No']}]({row['PDF']})", unsafe_allow_html=True)

                    with st.form("edit_proforma"):
                        tarih_ = st.date_input("Tarih", value=pd.to_datetime(row["Tarih"]).date())
                        proforma_no_ = st.text_input("Proforma No", value=row["Proforma No"])
                        tutar_ = st.text_input("Tutar ($)", value=row["Tutar"])
                        vade_gun_ = st.text_input("Vade (gün)", value=str(row["Vade (gün)"]))
                        aciklama_ = st.text_area("Açıklama", value=row["Açıklama"])
                        durum_ = st.selectbox(
                            "Durum",
                            ["Beklemede", "Siparişe Dönüştü", "İptal", "Faturası Kesildi"],
                            index=["Beklemede", "Siparişe Dönüştü", "İptal", "Faturası Kesildi"].index(row["Durum"])
                            if row["Durum"] in ["Beklemede", "Siparişe Dönüştü", "İptal", "Faturası Kesildi"] else 0
                        )
                        guncelle = st.form_submit_button("Güncelle")
                        sil = st.form_submit_button("Sil")

                    # --- Siparişe Dönüştü ise SİPARİŞ FORMU yükleme ---
                    if durum_ == "Siparişe Dönüştü":
                        st.info("Lütfen sipariş formunu yükleyin ve ardından 'Sipariş Formunu Kaydet' butonuna basın.")
                        with st.form(f"siparis_formu_upload_{sec_index}"):
                            siparis_formu_file = st.file_uploader("Sipariş Formu PDF", type="pdf")
                            siparis_kaydet = st.form_submit_button("Sipariş Formunu Kaydet")

                        if siparis_kaydet:
                            if siparis_formu_file is None:
                                st.error("Sipariş formu yüklemelisiniz.")
                            else:
                                sname = f"{musteri_sec}_{proforma_no_}_SiparisFormu_{datetime.datetime.now().strftime('%Y%m%d%H%M%S')}.pdf"
                                tmp_path = os.path.join(".", sname)
                                with open(tmp_path, "wb") as f:
                                    f.write(siparis_formu_file.read())

                                try:
                                    siparis_formu_url = upload_file_to_drive(SIPARIS_FORMU_ID, tmp_path, sname)
                                finally:
                                    try:
                                        os.remove(tmp_path)
                                    except:
                                        pass

                                # Link + Durum güncelle
                                df_proforma.at[sec_index, "Sipariş Formu"] = siparis_formu_url
                                df_proforma.at[sec_index, "Durum"] = "Siparişe Dönüştü"
                                update_google_sheets()
                                st.success("Sipariş formu kaydedildi ve durum güncellendi!")
                                st.rerun()

                    # --- Diğer alanlar — Güncelle ---
                    if guncelle:
                        df_proforma.at[sec_index, "Tarih"] = tarih_
                        df_proforma.at[sec_index, "Proforma No"] = proforma_no_
                        df_proforma.at[sec_index, "Tutar"] = tutar_
                        df_proforma.at[sec_index, "Vade (gün)"] = vade_gun_
                        df_proforma.at[sec_index, "Açıklama"] = aciklama_
                        if durum_ != "Siparişe Dönüştü":
                            df_proforma.at[sec_index, "Durum"] = durum_
                        update_google_sheets()
                        st.success("Proforma güncellendi!")
                        st.rerun()

                    # --- Sil ---
                    if sil:
                        df_proforma = df_proforma.drop(sec_index).reset_index(drop=True)
                        update_google_sheets()
                        st.success("Kayıt silindi!")
                        st.rerun()

# ==============================
# 11) GÜNCEL SİPARİŞ DURUMU
# ==============================

elif menu == "Güncel Sipariş Durumu":
    st.header("Güncel Sipariş Durumu")

    for c in ["Sevk Durumu","Termin Tarihi","Sipariş Formu","Ülke","Satış Temsilcisi","Ödeme Şekli"]:
        if c not in df_proforma.columns: df_proforma[c] = ""

    sip = df_proforma[(df_proforma["Durum"]=="Siparişe Dönüştü") &
                      (~df_proforma["Sevk Durumu"].isin(["Sevkedildi","Ulaşıldı"]))].copy()

    sip["Termin Tarihi Order"] = pd.to_datetime(sip["Termin Tarihi"], errors="coerce")
    sip = sip.sort_values("Termin Tarihi Order", ascending=True)

    if sip.empty:
        st.info("Sevk bekleyen sipariş yok.")
    else:
        sip["Tarih"] = pd.to_datetime(sip["Tarih"], errors="coerce").dt.strftime("%d/%m/%Y")
        sip["Termin Tarihi"] = pd.to_datetime(sip["Termin Tarihi"], errors="coerce").dt.strftime("%d/%m/%Y")
        tablo = sip[["Tarih","Müşteri Adı","Termin Tarihi","Ülke","Satış Temsilcisi","Ödeme Şekli","Proforma No","Tutar","Açıklama"]]
        st.dataframe(tablo, use_container_width=True)

        # Termin güncelle
        st.markdown("#### Termin Tarihi Güncelle")
        sec_i = st.selectbox("Sipariş Seç", options=sip.index,
                             format_func=lambda i: f"{sip.at[i,'Müşteri Adı']} - {sip.at[i,'Proforma No']}")
        mevcut = df_proforma.at[sec_i,"Termin Tarihi"]
        try:
            default = pd.to_datetime(mevcut, errors="coerce").date() if mevcut else datetime.date.today()
        except:
            default = datetime.date.today()
        yeni_termin = st.date_input("Termin Tarihi", value=default, key="termin_input")
        if st.button("Termin Tarihini Kaydet"):
            df_proforma.at[sec_i,"Termin Tarihi"] = yeni_termin
            update_google_sheets()
            st.success("Termin kaydedildi!")
            st.rerun()

        # Sevk et (ETA’ya gönder)
        st.markdown("#### Siparişi Sevk Et (ETA Takibi)")
        sevk_i = st.selectbox("Sevk Edilecek Sipariş", options=sip.index,
                              format_func=lambda i: f"{sip.at[i,'Müşteri Adı']} - {sip.at[i,'Proforma No']}", key="sevk_sec")
        if st.button("Sevkedildi (ETA'ya gönder)"):
            # df_eta'ya ekle
            for c in ["Müşteri Adı","Proforma No","ETA Tarihi","Açıklama"]:
                if c not in df_eta.columns: df_eta[c] = ""
            df_eta = pd.concat([df_eta, pd.DataFrame([{
                "Müşteri Adı": sip.at[sevk_i,"Müşteri Adı"],
                "Proforma No": sip.at[sevk_i,"Proforma No"],
                "ETA Tarihi": "",
                "Açıklama": sip.at[sevk_i,"Açıklama"],
            }])], ignore_index=True)
            df_proforma.at[sevk_i,"Sevk Durumu"] = "Sevkedildi"
            update_google_sheets()
            st.success("Sevk edildi ve ETA'ya eklendi!")
            st.rerun()

        # Beklemeye al (geri çağır)
        st.markdown("#### Siparişi Beklemeye Al (Geri Çağır)")
        geri_i = st.selectbox("Beklemeye Alınacak Sipariş", options=sip.index,
                              format_func=lambda i: f"{sip.at[i,'Müşteri Adı']} - {sip.at[i,'Proforma No']}", key="geri_sec")
        if st.button("Beklemeye Al / Geri Çağır"):
            df_proforma.at[geri_i,"Durum"] = "Beklemede"
            df_proforma.at[geri_i,"Sevk Durumu"] = ""
            df_proforma.at[geri_i,"Termin Tarihi"] = ""
            update_google_sheets()
            st.success("Sipariş beklemeye alındı!")
            st.rerun()

        # PDF linkleri + toplam
        st.markdown("#### Proforma / Sipariş Formu Linkleri")
        for i,r in sip.iterrows():
            links=[]
            if str(r.get("PDF","")).strip():
                links.append(f"[Proforma PDF: {r['Proforma No']}]({r['PDF']})")
            if str(r.get("Sipariş Formu","")).strip():
                links.append(f"[Sipariş Formu]({r['Sipariş Formu']})")
            if links: st.markdown(" - " + " | ".join(links), unsafe_allow_html=True)

        toplam = pd.to_numeric(sip["Tutar"], errors="coerce").sum() if not sip.empty else 0
        st.markdown(f"<div style='color:#219A41; font-weight:bold;'>*Toplam Bekleyen Sevk: {toplam:,.2f} $*</div>", unsafe_allow_html=True)

# =========================================
# 12) FATURA & İHRACAT EVRAKLARI
# =========================================

elif menu == "Fatura & İhracat Evrakları":
    st.markdown("<h2 style='color:#219A41; font-weight:bold;'>Fatura & İhracat Evrakları</h2>", unsafe_allow_html=True)

    for col in ["Proforma No","Vade (gün)","Vade Tarihi","Ülke","Satış Temsilcisi","Ödeme Şekli",
                "Commercial Invoice","Sağlık Sertifikası","Packing List","Konşimento","İhracat Beyannamesi",
                "Fatura PDF","Sipariş Formu","Yük Resimleri","EK Belgeler","Ödendi"]:
        if col not in df_evrak.columns:
            df_evrak[col] = "" if col!="Ödendi" else False

    mus_opts = sorted(df_proforma["Müşteri Adı"].dropna().unique().tolist())
    sec_mus = st.selectbox("Müşteri Seç", [""]+mus_opts)
    if sec_mus:
        pf_opts = df_proforma[df_proforma["Müşteri Adı"]==sec_mus]["Proforma No"].astype(str).tolist()
        sec_pf = st.selectbox("Proforma No Seç", [""]+pf_opts)
    else:
        sec_pf = st.selectbox("Proforma No Seç", [""])

    mi = df_musteri[df_musteri["Müşteri Adı"]==sec_mus]
    ulke = mi["Ülke"].values[0] if not mi.empty else ""
    rep  = mi["Satış Temsilcisi"].values[0] if not mi.empty else ""
    pay  = mi["Ödeme Şekli"].values[0] if not mi.empty else ""

    # Önceki evraklar
    onceki = df_evrak[(df_evrak["Müşteri Adı"]==sec_mus) & (df_evrak["Proforma No"]==sec_pf)]

    def prev_html(label, url):
        return (f'<div style="margin-top:-6px;"><a href="{url}" target="_blank" style="color:#219A41;">[Eski {label}]</a></div>'
                if url else '<div style="margin-top:-6px; color:#b00020; font-size:0.95em;">(Daha önce yüklenmemiş)</div>')

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
        vade_tarih = ""
        pf_row = df_proforma[(df_proforma["Müşteri Adı"]==sec_mus) & (df_proforma["Proforma No"]==sec_pf)]
        if not pf_row.empty:
            vade_gun = pf_row.iloc[0].get("Vade (gün)","")
            try:
                vade_gun_int = int(vade_gun)
                vade_tarih = fatura_tarih + datetime.timedelta(days=vade_gun_int)
            except:
                vade_tarih = ""

        st.text_input("Vade (gün)", value=vade_gun, disabled=True)
        st.date_input("Vade Tarihi", value=vade_tarih if vade_tarih else fatura_tarih, disabled=True)
        st.text_input("Ülke", value=ulke, disabled=True)
        st.text_input("Satış Temsilcisi", value=rep, disabled=True)
        st.text_input("Ödeme Şekli", value=pay, disabled=True)

        # Upload alanları + eski linkler
        uploaded = {}
        for col,label in evrak_tipleri:
            uploaded[col] = st.file_uploader(label, type="pdf", key=f"{col}_upload")
            prev_url = onceki.iloc[0][col] if not onceki.empty else ""
            st.markdown(prev_html(label, prev_url), unsafe_allow_html=True)

        kaydet = st.form_submit_button("Kaydet")

    if kaydet:
        if not fatura_no.strip() or not tutar.strip():
            st.error("Fatura No ve Tutar zorunlu!")
        else:
            file_urls = {}
            for col,label in evrak_tipleri:
                up = uploaded[col]
                if up:
                    fname = f"{col}_{datetime.datetime.now().strftime('%Y%m%d%H%M%S')}.pdf"
                    tmp = os.path.join(".", fname)
                    with open(tmp,"wb") as f: f.write(up.read())
                    g = drive.CreateFile({'title': fname, 'parents':[{'id': EVRAK_KLASOR_ID}]})
                    g.SetContentFile(tmp); g.Upload()
                    file_urls[col] = f"https://drive.google.com/file/d/{g['id']}/view?usp=sharing"
                    try: os.remove(tmp)
                    except: pass
                else:
                    file_urls[col] = onceki.iloc[0][col] if not onceki.empty else ""

            new_row = {
                "Müşteri Adı": sec_mus, "Proforma No": sec_pf,
                "Fatura No": fatura_no, "Fatura Tarihi": fatura_tarih, "Tutar": tutar,
                "Vade (gün)": vade_gun, "Vade Tarihi": vade_tarih,
                "Ülke": ulke, "Satış Temsilcisi": rep, "Ödeme Şekli": pay,
                "Commercial Invoice": file_urls.get("Commercial Invoice",""),
                "Sağlık Sertifikası": file_urls.get("Sağlık Sertifikası",""),
                "Packing List": file_urls.get("Packing List",""),
                "Konşimento": file_urls.get("Konşimento",""),
                "İhracat Beyannamesi": file_urls.get("İhracat Beyannamesi",""),
                "Fatura PDF": "", "Sipariş Formu": "", "Yük Resimleri":"", "EK Belgeler":"", "Ödendi": False
            }
            df_evrak = pd.concat([df_evrak, pd.DataFrame([new_row])], ignore_index=True)
            update_google_sheets()
            st.success("Evraklar kaydedildi!")
            st.rerun()

# ======================
# 13) VADE TAKİBİ
# ======================

elif menu == "Vade Takibi":
    st.markdown("<h2 style='color:#219A41; font-weight:bold;'>Vade Takibi</h2>", unsafe_allow_html=True)

    for c in ["Proforma No","Vade (gün)","Ödendi","Ülke","Satış Temsilcisi","Ödeme Şekli"]:
        if c not in df_evrak.columns: df_evrak[c] = "" if c!="Ödendi" else False
    df_evrak["Ödendi"] = df_evrak["Ödendi"].fillna(False).astype(bool)

    if "Vade Tarihi" in df_evrak.columns:
        df_evrak["Vade Tarihi"] = pd.to_datetime(df_evrak["Vade Tarihi"], errors="coerce")

    today = pd.to_datetime(datetime.date.today())
    vade_df = df_evrak[df_evrak["Vade Tarihi"].notna() & (~df_evrak["Ödendi"])].reset_index()

    for i,row in vade_df.iterrows():
        kalan = (row["Vade Tarihi"] - today).days
        msg = f"{row['Müşteri Adı']} | {row.get('Ülke','')} | {row.get('Satış Temsilcisi','')} | PF: {row.get('Proforma No','')} | Fatura: {row['Fatura No']} | Vade: {row['Vade Tarihi'].date()} | Ödeme: {row.get('Ödeme Şekli','')}"
        if kalan == 1:
            st.error(f"{msg} | **YARIN VADE DOLUYOR!**")
        elif kalan < 0:
            st.warning(f"{msg} | **{abs(kalan)} gün GECİKTİ!**")
        else:
            st.info(f"{msg} | {kalan} gün kaldı.")

        tick = st.checkbox(f"Ödendi: {row['Müşteri Adı']} - PF: {row.get('Proforma No','')} - Fatura: {row['Fatura No']}",
                           key=f"odendi_{i}")
        if tick:
            df_evrak.at[row["index"], "Ödendi"] = True
            update_google_sheets()
            st.success("Ödendi olarak işaretlendi!")
            st.rerun()

    st.markdown("#### Açık Vade Kayıtları")
    st.dataframe(
        df_evrak[df_evrak["Vade Tarihi"].notna() & (~df_evrak["Ödendi"])][
            ["Müşteri Adı","Ülke","Satış Temsilcisi","Ödeme Şekli","Proforma No","Fatura No","Fatura Tarihi","Vade (gün)","Vade Tarihi","Tutar"]
        ],
        use_container_width=True
    )

# ======================
# 14) ETA TAKİBİ
# ======================

elif menu == "ETA Takibi":
    st.markdown("<h2 style='color:#219A41; font-weight:bold;'>ETA Takibi</h2>", unsafe_allow_html=True)

    for c in ["Sevk Durumu","Proforma No","Sevk Tarihi","Ulaşma Tarihi","Termin Tarihi"]:
        if c not in df_proforma.columns: df_proforma[c] = ""

    # Sevkedilenler
    sevkedilen = df_proforma[df_proforma["Sevk Durumu"]=="Sevkedildi"].copy()
    if sevkedilen.empty:
        st.info("Sevk edilmiş sipariş bulunmuyor.")
    else:
        opts = sevkedilen[["Müşteri Adı","Proforma No"]].drop_duplicates()
        opts["sec_text"] = opts["Müşteri Adı"] + " - " + opts["Proforma No"]
        selected = st.selectbox("Sevkedilen Sipariş Seç", opts["sec_text"])
        row = opts[opts["sec_text"]==selected].iloc[0]
        sm, sp = row["Müşteri Adı"], row["Proforma No"]

        for c in ["Müşteri Adı","Proforma No","ETA Tarihi","Açıklama"]:
            if c not in df_eta.columns: df_eta[c] = ""

        filt = (df_eta["Müşteri Adı"]==sm) & (df_eta["Proforma No"]==sp)
        mevcut_eta = df_eta.loc[filt, "ETA Tarihi"].values[0] if filt.any() else ""
        mevcut_acik = df_eta.loc[filt, "Açıklama"].values[0] if filt.any() else ""

        with st.form("edit_eta"):
            try:
                def_eta = pd.to_datetime(mevcut_eta).date() if mevcut_eta and str(mevcut_eta)!="NaT" else datetime.date.today()
            except:
                def_eta = datetime.date.today()
            eta_tarih = st.date_input("ETA Tarihi", value=def_eta)
            aciklama = st.text_area("Açıklama", value=mevcut_acik)
            guncelle = st.form_submit_button("ETA'yı Kaydet/Güncelle")
            ulasti = st.form_submit_button("Ulaştı")
            geri_al = st.form_submit_button("Sevki Geri Al")

        if guncelle:
            if filt.any():
                df_eta.loc[filt, "ETA Tarihi"] = eta_tarih
                df_eta.loc[filt, "Açıklama"] = aciklama
            else:
                df_eta = pd.concat([df_eta, pd.DataFrame([{
                    "Müşteri Adı": sm, "Proforma No": sp, "ETA Tarihi": eta_tarih, "Açıklama": aciklama
                }])], ignore_index=True)
            update_google_sheets()
            st.success("ETA kaydedildi/güncellendi!")
            st.rerun()

        if ulasti:
            # ETA’dan çıkar, proforma’da Sevk Durumu=Ulaşıldı ve Ulaşma Tarihi=bugün
            df_eta = df_eta[~((df_eta["Müşteri Adı"]==sm) & (df_eta["Proforma No"]==sp))]
            idx = df_proforma[(df_proforma["Müşteri Adı"]==sm) & (df_proforma["Proforma No"]==sp)].index
            if len(idx)>0:
                df_proforma.at[idx[0],"Sevk Durumu"] = "Ulaşıldı"
                df_proforma.at[idx[0],"Ulaşma Tarihi"] = datetime.date.today()
            update_google_sheets()
            st.success("Ulaşıldı olarak işaretlendi ve ETA'dan çıkarıldı!")
            st.rerun()

        if geri_al:
            # Sevki geri al: ETA’dan çıkar, Sevk Durumu’nu boş yap (Güncel Sipariş Durumu’na döner)
            df_eta = df_eta[~((df_eta["Müşteri Adı"]==sm) & (df_eta["Proforma No"]==sp))]
            idx = df_proforma[(df_proforma["Müşteri Adı"]==sm) & (df_proforma["Proforma No"]==sp)].index
            if len(idx)>0:
                df_proforma.at[idx[0],"Sevk Durumu"] = ""
            update_google_sheets()
            st.success("Sevkiyat geri alındı, sipariş bekleyenlere döndü.")
            st.rerun()

    # ETA listesi
    st.markdown("#### ETA Takip Listesi")
    for c in ["Proforma No","ETA Tarihi"]:
        if c not in df_eta.columns: df_eta[c] = ""
    if not df_eta.empty:
        df_eta["ETA Tarihi"] = pd.to_datetime(df_eta["ETA Tarihi"], errors="coerce")
        today = pd.to_datetime(datetime.date.today())
        df_eta["Kalan Gün"] = (df_eta["ETA Tarihi"] - today).dt.days
        tablo = df_eta[["Müşteri Adı","Proforma No","ETA Tarihi","Kalan Gün","Açıklama"]].sort_values("ETA Tarihi", ascending=True)
        st.dataframe(tablo, use_container_width=True)

        st.markdown("##### ETA Kaydı Sil")
        sil_opts = df_eta.index.tolist()
        sil_sec = st.selectbox("Silinecek ETA Kaydı", sil_opts,
                               format_func=lambda i: f"{df_eta.at[i,'Müşteri Adı']} - {df_eta.at[i,'Proforma No']}")
        if st.button("KAYDI SİL"):
            df_eta = df_eta.drop(sil_sec).reset_index(drop=True)
            update_google_sheets()
            st.success("ETA kaydı silindi!")
            st.rerun()
    else:
        st.info("Henüz ETA kaydı yok.")

    # Ulaşanlar (teslim edilenler) — Ulaşma tarihi güncelle
    ulasan = df_proforma[df_proforma["Sevk Durumu"]=="Ulaşıldı"].copy()
    if not ulasan.empty:
        ulasan["sec_text"] = ulasan["Müşteri Adı"] + " - " + ulasan["Proforma No"]
        st.markdown("#### Teslim Edilenlerde Ulaşma Tarihi Güncelle")
        sel = st.selectbox("Sipariş Seçiniz", ulasan["sec_text"])
        r = ulasan[ulasan["sec_text"]==sel].iloc[0]
        try:
            cur = pd.to_datetime(r["Ulaşma Tarihi"]).date()
            if str(cur)=="NaT": cur = datetime.date.today()
        except:
            cur = datetime.date.today()
        new_dt = st.date_input("Ulaşma Tarihi", value=cur, key="ulasan_guncelle")
        if st.button("Ulaşma Tarihini Kaydet"):
            idx = df_proforma[(df_proforma["Müşteri Adı"]==r["Müşteri Adı"]) & (df_proforma["Proforma No"]==r["Proforma No"])].index
            if len(idx)>0:
                df_proforma.at[idx[0],"Ulaşma Tarihi"] = new_dt
                update_google_sheets()
                st.success("Ulaşma Tarihi güncellendi!")
                st.rerun()

        # Tablo
        ulasan["Sevk Tarihi"] = pd.to_datetime(ulasan.get("Sevk Tarihi", pd.NaT), errors="coerce")
        ulasan["Termin Tarihi"] = pd.to_datetime(ulasan.get("Termin Tarihi", pd.NaT), errors="coerce")
        ulasan["Ulaşma Tarihi"] = pd.to_datetime(ulasan.get("Ulaşma Tarihi", pd.NaT), errors="coerce")
        ulasan["Gün Farkı"] = (ulasan["Ulaşma Tarihi"] - ulasan["Termin Tarihi"]).dt.days
        for c in ["Sevk Tarihi","Termin Tarihi","Ulaşma Tarihi"]:
            ulasan[c] = ulasan[c].dt.strftime("%d/%m/%Y")
        t = ulasan[["Müşteri Adı","Proforma No","Termin Tarihi","Sevk Tarihi","Ulaşma Tarihi","Gün Farkı","Tutar","Açıklama"]]
        st.dataframe(t, use_container_width=True)
    else:
        st.info("Henüz 'Ulaşıldı' sipariş yok.")

# ==============================
# FUAR MÜŞTERİ KAYITLARI MENÜSÜ
# ==============================

elif menu == "Fuar Müşteri Kayıtları":
    st.markdown("<h2 style='color:#8e54e9; font-weight:bold;'>🎫 FUAR MÜŞTERİ KAYITLARI</h2>", unsafe_allow_html=True)
    st.info("Fuarlarda görüştüğünüz müşterileri hızlıca ekleyin, düzenleyin veya silin.")

    # Sabit listeler (genelde dosyanın üstünde tanımlı—gerekirse burada da dursun)
    ulke_listesi = ulke_listesi  # (üstteki uzun listeyi kullanıyoruz)
    temsilci_listesi = ["HÜSEYİN POLAT", "KEMAL İLKER ÇELİKKALKAN", "EFE YILDIRIM", "FERHAT ŞEKEROĞLU"]

    # Var olan fuarlar
    mevcut_fuarlar = sorted([x for x in df_fuar_musteri["Fuar Adı"].dropna().unique() if str(x).strip()])

    # Fuar seçimi / yeni fuar
    colA, colB = st.columns([3,2])
    with colA:
        fuar_adi = st.selectbox("Fuar Seçiniz", ["- Fuar Seçiniz -"] + mevcut_fuarlar, index=0)
        if fuar_adi == "- Fuar Seçiniz -":
            fuar_adi = ""
    with colB:
        yeni_fuar = st.text_input("Yeni Fuar Adı (opsiyonel)")
        if st.button("Yeni Fuarı Ekle"):
            if yeni_fuar.strip():
                fuar_adi = yeni_fuar.strip()
                st.success(f"'{fuar_adi}' eklendi ve seçildi.")
            else:
                st.warning("Fuar adı boş olamaz.")

    secim = st.radio("İşlem Seçiniz", ["Yeni Kayıt", "Eski Kayıt"], horizontal=True)

    # --- YENİ KAYIT ---
    if secim == "Yeni Kayıt":
        with st.form("fuar_musteri_ekle"):
            musteri_adi = st.text_input("Müşteri Adı")
            ulke = st.selectbox("Ülke", ulke_listesi)
            tel = st.text_input("Telefon")
            email = st.text_input("E-mail")
            temsilci = st.selectbox("Satış Temsilcisi", temsilci_listesi)
            aciklama = st.text_area("Açıklamalar")
            gorusme_kalitesi = st.slider("Görüşme Kalitesi (1=Kötü, 5=Çok İyi)", 1, 5, 3)
            tarih = st.date_input("Tarih", value=datetime.date.today())
            kaydet = st.form_submit_button("Kaydet")

        if kaydet:
            if not fuar_adi or not musteri_adi.strip():
                st.warning("Lütfen fuar seçiniz ve müşteri adını giriniz.")
            else:
                new_row = {
                    "Fuar Adı": fuar_adi,
                    "Müşteri Adı": musteri_adi.strip(),
                    "Ülke": ulke,
                    "Telefon": tel,
                    "E-mail": email,
                    "Satış Temsilcisi": temsilci,
                    "Açıklamalar": aciklama,
                    "Görüşme Kalitesi": gorusme_kalitesi,
                    "Tarih": tarih
                }
                df_fuar_musteri = pd.concat([df_fuar_musteri, pd.DataFrame([new_row])], ignore_index=True)
                update_google_sheets()
                st.success("Fuar müşterisi eklendi!")
                st.rerun()

    # --- ESKİ KAYIT ---
    elif secim == "Eski Kayıt":
        if not fuar_adi:
            st.info("Lütfen bir fuar seçin.")
        else:
            kolonlar = ["Müşteri Adı","Ülke","Telefon","E-mail","Satış Temsilcisi","Açıklamalar","Görüşme Kalitesi","Tarih"]
            fuar_df = df_fuar_musteri[df_fuar_musteri["Fuar Adı"] == fuar_adi].copy()

            if fuar_df.empty:
                st.info("Bu fuara ait müşteri kaydı yok.")
            else:
                st.markdown(f"**{fuar_adi}** fuarındaki kayıtlar:")
                st.dataframe(fuar_df[kolonlar], use_container_width=True)

                sec_index = st.selectbox(
                    "Düzenlenecek/Silinecek Kayıt",
                    fuar_df.index,
                    format_func=lambda i: f"{fuar_df.at[i,'Müşteri Adı']} ({fuar_df.at[i,'Tarih']})"
                )

                with st.form("fuar_kayit_duzenle"):
                    musteri_adi = st.text_input("Müşteri Adı", value=fuar_df.at[sec_index, "Müşteri Adı"])
                    ulke = st.selectbox("Ülke", ulke_listesi,
                                        index=ulke_listesi.index(fuar_df.at[sec_index, "Ülke"]) if fuar_df.at[sec_index, "Ülke"] in ulke_listesi else len(ulke_listesi)-1)
                    temsilci = st.selectbox("Satış Temsilcisi", temsilci_listesi,
                                            index=temsilci_listesi.index(fuar_df.at[sec_index, "Satış Temsilcisi"]) if fuar_df.at[sec_index, "Satış Temsilcisi"] in temsilci_listesi else 0)
                    tel = st.text_input("Telefon", value=fuar_df.at[sec_index, "Telefon"])
                    email = st.text_input("E-mail", value=fuar_df.at[sec_index, "E-mail"])
                    aciklama = st.text_area("Açıklamalar", value=fuar_df.at[sec_index, "Açıklamalar"])
                    gk_raw = fuar_df.at[sec_index, "Görüşme Kalitesi"]
                    gk_default = int(gk_raw) if str(gk_raw).isdigit() else 3
                    gorusme_kalitesi = st.slider("Görüşme Kalitesi", 1, 5, gk_default)
                    try:
                        t_default = pd.to_datetime(fuar_df.at[sec_index, "Tarih"]).date()
                    except Exception:
                        t_default = datetime.date.today()
                    tarih = st.date_input("Tarih", value=t_default)

                    guncelle = st.form_submit_button("Güncelle")
                    sil = st.form_submit_button("Sil")

                if guncelle:
                    df_fuar_musteri.at[sec_index, "Müşteri Adı"] = musteri_adi
                    df_fuar_musteri.at[sec_index, "Ülke"] = ulke
                    df_fuar_musteri.at[sec_index, "Telefon"] = tel
                    df_fuar_musteri.at[sec_index, "E-mail"] = email
                    df_fuar_musteri.at[sec_index, "Satış Temsilcisi"] = temsilci
                    df_fuar_musteri.at[sec_index, "Açıklamalar"] = aciklama
                    df_fuar_musteri.at[sec_index, "Görüşme Kalitesi"] = gorusme_kalitesi
                    df_fuar_musteri.at[sec_index, "Tarih"] = tarih
                    update_google_sheets()
                    st.success("Kayıt güncellendi!")
                    st.rerun()

                if sil:
                    df_fuar_musteri = df_fuar_musteri.drop(sec_index).reset_index(drop=True)
                    update_google_sheets()
                    st.success("Kayıt silindi!")
                    st.rerun()

# ===========================
# === MEDYA ÇEKMECESİ MENÜSÜ ===
# ===========================

elif menu == "Medya Çekmecesi":
    st.markdown("<h2 style='color:#8e54e9; font-weight:bold;'>Medya Çekmecesi</h2>", unsafe_allow_html=True)
    st.info("Google Drive’daki medya, ürün görselleri ve kalite evraklarına aşağıdaki sekmelerden ulaşabilirsiniz.")

    # --- Klasör ID'leri (gerekirse yukarıda sabitler bölümüne taşıyabilirsin) ---
    GENEL_MEDYA_ID   = "1gFAaK-6v1e3346e-W0TsizOqSq43vHLY"
    URUN_GORSEL_ID   = "18NNlmadm5NNFkI1Amzt_YMwB53j6AmbD"
    KALITE_EVRAGI_ID = "1pbArzYfA4Tp50zvdyTzSPF2ThrMWrGJc"

    def embed_url(folder_id: str) -> str:
        return f"https://drive.google.com/embeddedfolderview?id={folder_id}#list"

    drive_tabs = {
        "Genel Medya Klasörü": embed_url(GENEL_MEDYA_ID),
        "Ürün Görselleri": embed_url(URUN_GORSEL_ID),
        "Kalite Evrakları": embed_url(KALITE_EVRAGI_ID),
    }

    tab1, tab2, tab3 = st.tabs(list(drive_tabs.keys()))

    with tab1:
        st.markdown(
            f'<iframe src="{drive_tabs["Genel Medya Klasörü"]}" width="100%" height="620" frameborder="0" style="border:1px solid #eee; border-radius:12px;"></iframe>',
            unsafe_allow_html=True
        )
        st.info("Dosyayı yeni sekmede açmak için çift tıklayın (Drive üzerindeki paylaşım herkese açık olmalı).")

    with tab2:
        st.markdown(
            f'<iframe src="{drive_tabs["Ürün Görselleri"]}" width="100%" height="620" frameborder="0" style="border:1px solid #eee; border-radius:12px;"></iframe>',
            unsafe_allow_html=True
        )
        st.info("Ürün görsellerini buradan inceleyebilir veya indirebilirsiniz.")

    with tab3:
        st.markdown(
            f'<iframe src="{drive_tabs["Kalite Evrakları"]}" width="100%" height="620" frameborder="0" style="border:1px solid #eee; border-radius:12px;"></iframe>',
            unsafe_allow_html=True
        )
        st.info("Kalite sertifikaları ve dokümanlar burada listelenir.")

    st.warning("Not: Klasörlerin paylaşım ayarlarını 'Bağlantıya sahip olan herkes görüntüleyebilir' olarak ayarlamayı unutmayın.")
