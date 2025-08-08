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

# === Blok-2: Tüm Sayfaları DataFrame olarak Yükle ===

COLUMNS_MUSTERI = [
    "Müşteri Adı", "Telefon", "E-posta", "Adres", "Ülke",
    "Satış Temsilcisi", "Kategori", "Durum", "Vade (Gün)", "Ödeme Şekli",
    "Para Birimi", "DT Seçimi"
]

COLUMNS_KAYIT = ["Müşteri Adı", "Tarih", "Tip", "Açıklama"]

COLUMNS_TEKLIF = [
    "Müşteri Adı", "Tarih", "Teklif No", "Tutar",
    "Ürün/Hizmet", "Açıklama", "Durum", "PDF"
]

COLUMNS_PROFORMA = [
    "Müşteri Adı", "Tarih", "Proforma No", "Tutar", "Açıklama",
    "Durum", "PDF", "Sipariş Formu", "Vade (gün)", "Sevk Durumu",
    "Termin Tarihi", "Sevk Tarihi", "Ulaşma Tarihi",
    "Ülke", "Satış Temsilcisi", "Ödeme Şekli"
]

COLUMNS_EVRAK = [
    "Müşteri Adı", "Fatura No", "Fatura Tarihi", "Vade Tarihi", "Tutar",
    "Commercial Invoice", "Sağlık Sertifikası", "Packing List",
    "Konşimento", "İhracat Beyannamesi", "Fatura PDF", "Sipariş Formu",
    "Yük Resimleri", "EK Belgeler",
    "Proforma No", "Vade (gün)", "Ülke", "Satış Temsilcisi", "Ödeme Şekli",
    "Ödendi"
]

COLUMNS_ETA = ["Müşteri Adı", "Proforma No", "ETA Tarihi", "Açıklama"]

COLUMNS_FUAR = [
    "Fuar Adı", "Müşteri Adı", "Ülke", "Telefon", "E-mail",
    "Satış Temsilcisi", "Açıklamalar", "Görüşme Kalitesi", "Tarih"
]

df_musteri      = load_sheet_as_df("Sayfa1",       COLUMNS_MUSTERI)
df_kayit        = load_sheet_as_df("Kayıtlar",     COLUMNS_KAYIT)
df_teklif       = load_sheet_as_df("Teklifler",    COLUMNS_TEKLIF)
df_proforma     = load_sheet_as_df("Proformalar",  COLUMNS_PROFORMA)
df_evrak        = load_sheet_as_df("Evraklar",     COLUMNS_EVRAK)
df_eta          = load_sheet_as_df("ETA",          COLUMNS_ETA)
df_fuar_musteri = load_sheet_as_df("FuarMusteri",  COLUMNS_FUAR)

# === Blok-3: DataFrame'leri Google Sheets'e Yaz ===

def update_google_sheets():
    """
    Bütün DataFrame’leri ilgili sayfalara yazar.
    (Başlık dahil, sayfayı temizleyip komple günceller.)
    """
    try:
        df_to_sheet("Sayfa1",      df_musteri)
        df_to_sheet("Kayıtlar",    df_kayit)
        df_to_sheet("Teklifler",   df_teklif)
        df_to_sheet("Proformalar", df_proforma)
        df_to_sheet("Evraklar",    df_evrak)
        df_to_sheet("ETA",         df_eta)
        df_to_sheet("FuarMusteri", df_fuar_musteri)
        st.success("Google Sheets güncellendi.")
    except Exception as e:
        st.error(f"Google Sheets'e yazarken hata oluştu: {e}")

# === Menü tanımları ===
MENULER = [
    ("Özet Ekran", "📊"),
    ("Cari Ekleme", "🧑‍💼"),
    ("Müşteri Listesi", "📒"),
    ("Görüşme / Arama / Ziyaret Kayıtları", "☎️"),
    ("Fiyat Teklifleri", "💰"),
    ("Proforma Takibi", "📄"),
    ("Güncel Sipariş Durumu", "🚚"),
    ("Fatura & İhracat Evrakları", "📑"),
    ("Vade Takibi", "⏰"),
    ("ETA Takibi", "🛳️"),
    ("Fuar Müşteri Kayıtları", "🎫"),
    ("Medya Çekmecesi", "🗂️"),
]

# Boss sadece özet görsün diyorsan:
allowed_menus = MENULER if st.session_state.user != "Boss" else [MENULER[0]]

if "menu_state" not in st.session_state:
    st.session_state.menu_state = allowed_menus[0][0]

st.sidebar.markdown("## Menü")
for ad, ikon in allowed_menus:
    if st.sidebar.button(f"{ikon} {ad}", key=f"menu_{ad}"):
        st.session_state.menu_state = ad

menu = st.session_state.menu_state


# --- Ülke ve Temsilci Listeleri (global) ---
ulke_listesi = sorted([
    "Afganistan","Almanya","Amerika Birleşik Devletleri","Andorra","Angola","Antigua ve Barbuda","Arjantin",
    "Arnavutluk","Avustralya","Avusturya","Azerbaycan","Bahamalar","Bahreyn","Bangladeş","Barbados","Belçika",
    "Belize","Benin","Beyaz Rusya","Bhutan","Birleşik Arap Emirlikleri","Birleşik Krallık","Bolivya",
    "Bosna-Hersek","Botsvana","Brezilya","Brunei","Bulgaristan","Burkina Faso","Burundi","Butan",
    "Cezayir","Çad","Çekya","Çin","Danimarka","Doğu Timor","Dominik Cumhuriyeti","Dominika","Ekvador",
    "Ekvator Ginesi","El Salvador","Endonezya","Eritre","Ermenistan","Estonya","Etiyopya","Fas",
    "Fiji","Fildişi Sahili","Filipinler","Filistin","Finlandiya","Fransa","Gabon","Gambia",
    "Gana","Gine","Gine-Bissau","Grenada","Guatemala","Guyana","Güney Afrika","Güney Kore",
    "Güney Sudan","Gürcistan","Haiti","Hindistan","Hırvatistan","Hollanda","Honduras","Hong Kong",
    "Irak","İran","İrlanda","İspanya","İsrail","İsveç","İsviçre","İtalya","İzlanda","Jamaika",
    "Japonya","Kamboçya","Kamerun","Kanada","Karadağ","Katar","Kazakistan","Kenya","Kırgızistan",
    "Kiribati","Kolombiya","Komorlar","Kongo","Kongo Demokratik Cumhuriyeti","Kostarika","Küba",
    "Kuveyt","Kuzey Kore","Kuzey Makedonya","Laos","Lesotho","Letonya","Liberya","Libya",
    "Liechtenstein","Litvanya","Lübnan","Lüksemburg","Macaristan","Madagaskar","Malavi","Maldivler",
    "Malezya","Mali","Malta","Marshall Adaları","Meksika","Mısır","Mikronezya","Moğolistan","Moldova",
    "Monako","Morityus","Mozambik","Myanmar","Namibya","Nauru","Nepal","Nijer","Nijerya",
    "Nikaragua","Norveç","Orta Afrika Cumhuriyeti","Özbekistan","Pakistan","Palau","Panama","Papua Yeni Gine",
    "Paraguay","Peru","Polonya","Portekiz","Romanya","Ruanda","Rusya","Saint Kitts ve Nevis",
    "Saint Lucia","Saint Vincent ve Grenadinler","Samoa","San Marino","Sao Tome ve Principe","Senegal",
    "Seyşeller","Sırbistan","Sierra Leone","Singapur","Slovakya","Slovenya","Solomon Adaları","Somali",
    "Sri Lanka","Sudan","Surinam","Suriye","Suudi Arabistan","Svaziland","Şili","Tacikistan","Tanzanya",
    "Tayland","Tayvan","Togo","Tonga","Trinidad ve Tobago","Tunus","Tuvalu","Türkiye","Türkmenistan",
    "Uganda","Ukrayna","Umman","Uruguay","Ürdün","Vanuatu","Vatikan","Venezuela","Vietnam",
    "Yemen","Yeni Zelanda","Yunanistan","Zambiya","Zimbabve"
]) + ["Diğer"]

temsilci_listesi = [
    "KEMAL İLKER ÇELİKKALKAN",
    "HÜSEYİN POLAT",
    "EFE YILDIRIM",
    "FERHAT ŞEKEROĞLU"
]
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
                # DataFrame'e ekle
                df_musteri = pd.concat([df_musteri, pd.DataFrame([new_row])], ignore_index=True)

                # Google Sheets'e yaz
                update_google_sheets()

                # (Opsiyonel) muhasebeye TXT + mail
                try:
                    yeni_cari_txt_olustur(new_row, "yeni_cari.txt")
                    send_email_with_txt(
                        to_email=["kemal.ilker27@gmail.com"],
                        subject="Yeni Cari Açılışı",
                        body="Muhasebe için yeni cari açılışı ekte gönderilmiştir.",
                        file_path="yeni_cari.txt"
                    )
                    st.success("Müşteri eklendi ve e-posta ile muhasebeye gönderildi!")
                except Exception as e:
                    st.warning(f"Müşteri eklendi ama e-posta gönderilemedi: {e}")

                st.rerun()

# =============== ÖZET EKRAN ===============
if menu == "Özet Ekran":
    st.markdown("<h2 style='color:#219A41; font-weight:bold;'>ŞEKEROĞLU İHRACAT CRM - Özet Ekran</h2>", unsafe_allow_html=True)

    # ----- Bekleyen Teklifler -----
    for col in ["Durum", "Tutar", "Tarih", "Müşteri Adı", "Teklif No", "Ürün/Hizmet", "Açıklama"]:
        if col not in df_teklif.columns:
            df_teklif[col] = ""

    st.markdown("### 💰 Bekleyen Teklifler")
    bekleyen_teklifler = df_teklif[df_teklif["Durum"] == "Açık"].copy()
    if not bekleyen_teklifler.empty:
        bekleyen_teklifler["Tarih"] = pd.to_datetime(bekleyen_teklifler["Tarih"], errors="coerce").dt.strftime("%d/%m/%Y")
    toplam_teklif = pd.to_numeric(bekleyen_teklifler["Tutar"], errors="coerce").fillna(0).sum() if not bekleyen_teklifler.empty else 0.0
    st.markdown(f"<div style='font-size:1.1em; color:#11998e; font-weight:bold;'>Toplam: {toplam_teklif:,.2f} $</div>", unsafe_allow_html=True)
    if bekleyen_teklifler.empty:
        st.info("Bekleyen teklif yok.")
    else:
        st.dataframe(
            bekleyen_teklifler[["Müşteri Adı", "Tarih", "Teklif No", "Tutar", "Ürün/Hizmet", "Açıklama"]],
            use_container_width=True
        )

    # ----- Bekleyen Proformalar -----
    for col in ["Durum", "Tutar", "Tarih", "Müşteri Adı", "Proforma No", "Açıklama"]:
        if col not in df_proforma.columns:
            df_proforma[col] = ""

    st.markdown("### 📄 Bekleyen Proformalar")
    bekleyen_proformalar = df_proforma[df_proforma["Durum"] == "Beklemede"].copy()
    if not bekleyen_proformalar.empty:
        bekleyen_proformalar["Tarih"] = pd.to_datetime(bekleyen_proformalar["Tarih"], errors="coerce").dt.strftime("%d/%m/%Y")
    toplam_proforma = pd.to_numeric(bekleyen_proformalar["Tutar"], errors="coerce").fillna(0).sum() if not bekleyen_proformalar.empty else 0.0
    st.markdown(f"<div style='font-size:1.1em; color:#f7971e; font-weight:bold;'>Toplam: {toplam_proforma:,.2f} $</div>", unsafe_allow_html=True)
    if bekleyen_proformalar.empty:
        st.info("Bekleyen proforma yok.")
    else:
        st.dataframe(
            bekleyen_proformalar[["Müşteri Adı", "Proforma No", "Tarih", "Tutar", "Açıklama"]],
            use_container_width=True
        )

    # ----- Siparişe Dönüşen (Sevk Bekleyen) -----
    for col in ["Sevk Durumu", "Termin Tarihi", "Satış Temsilcisi", "Ödeme Şekli", "Ülke", "Tarih", "Açıklama", "Tutar"]:
        if col not in df_proforma.columns:
            df_proforma[col] = ""

    st.markdown("### 🚚 Siparişe Dönüşen (Sevk Bekleyen) Siparişler")
    siparisler = df_proforma[
        (df_proforma["Durum"] == "Siparişe Dönüştü") &
        (~df_proforma["Sevk Durumu"].isin(["Sevkedildi", "Ulaşıldı"]))
    ].copy()

    if siparisler.empty:
        st.info("Henüz sevk edilmeyi bekleyen sipariş yok.")
    else:
        siparisler["Termin Tarihi Order"] = pd.to_datetime(siparisler["Termin Tarihi"], errors="coerce")
        siparisler["Tarih"] = pd.to_datetime(siparisler["Tarih"], errors="coerce").dt.strftime("%d/%m/%Y")
        siparisler["Termin Tarihi"] = pd.to_datetime(siparisler["Termin Tarihi"], errors="coerce").dt.strftime("%d/%m/%Y")
        siparisler = siparisler.sort_values("Termin Tarihi Order", ascending=True)
        st.dataframe(
            siparisler[["Tarih", "Müşteri Adı", "Termin Tarihi", "Ülke", "Satış Temsilcisi", "Ödeme Şekli", "Proforma No", "Tutar", "Açıklama"]],
            use_container_width=True
        )
        toplam_bekleyen_sevk = pd.to_numeric(siparisler["Tutar"], errors="coerce").fillna(0).sum()
        st.markdown(f"<div style='color:#219A41; font-weight:bold;'>*Toplam Bekleyen Sevk: {toplam_bekleyen_sevk:,.2f} $*</div>", unsafe_allow_html=True)

    # ----- Yolda Olan (Sevkedildi) / ETA -----
    for col in ["Sevk Durumu", "Müşteri Adı", "Ülke", "Proforma No", "Tarih", "Tutar", "Termin Tarihi", "Açıklama"]:
        if col not in df_proforma.columns:
            df_proforma[col] = ""

    st.markdown("### ⏳ Yolda Olan (ETA Takibi) Siparişler")
    eta_yolda = df_proforma[(df_proforma["Sevk Durumu"] == "Sevkedildi")].copy()
    if eta_yolda.empty:
        st.info("Yolda olan (sevk edilmiş) sipariş yok.")
    else:
        eta_yolda["Tarih"] = pd.to_datetime(eta_yolda["Tarih"], errors="coerce").dt.strftime("%d/%m/%Y")
        eta_yolda["Termin Tarihi"] = pd.to_datetime(eta_yolda["Termin Tarihi"], errors="coerce").dt.strftime("%d/%m/%Y")
        st.dataframe(
            eta_yolda[["Müşteri Adı", "Ülke", "Proforma No", "Tarih", "Tutar", "Termin Tarihi", "Açıklama"]],
            use_container_width=True
        )
        toplam_eta = pd.to_numeric(eta_yolda["Tutar"], errors="coerce").fillna(0).sum()
        st.markdown(f"<div style='font-size:1.1em; color:#c471f5; font-weight:bold;'>Toplam: {toplam_eta:,.2f} $</div>", unsafe_allow_html=True)

    # ----- Son Teslim Edilen 5 Sipariş (Ulaşıldı) -----
    st.markdown("### ✅ Son Teslim Edilen (Ulaşıldı) 5 Sipariş")
    ulasan = df_proforma[df_proforma["Sevk Durumu"] == "Ulaşıldı"].copy()
    if ulasan.empty:
        st.info("Teslim edilmiş sipariş yok.")
    else:
        for col in ["Tarih", "Termin Tarihi"]:
            if col not in ulasan.columns:
                ulasan[col] = ""
        ulasan = ulasan.sort_values(by="Tarih", ascending=False).head(5)
        ulasan["Tarih"] = pd.to_datetime(ulasan["Tarih"], errors="coerce").dt.strftime("%d/%m/%Y")
        ulasan["Termin Tarihi"] = pd.to_datetime(ulasan["Termin Tarihi"], errors="coerce").dt.strftime("%d/%m/%Y")
        st.dataframe(
            ulasan[["Müşteri Adı", "Ülke", "Proforma No", "Tarih", "Tutar", "Termin Tarihi", "Açıklama"]],
            use_container_width=True
        )

    # ----- Vade Takibi (Boss görünür) -----
    if st.session_state.user == "Boss":
        st.markdown("### 💸 Vadeli Fatura ve Tahsilat Takibi")
        # eksikleri tamamla
        for col in ["Vade Tarihi", "Ödendi", "Müşteri Adı", "Ülke", "Fatura No", "Tutar"]:
            if col not in df_evrak.columns:
                df_evrak[col] = "" if col != "Ödendi" else False

        if df_evrak.empty or df_evrak["Vade Tarihi"].isna().all():
            st.info("Açık vade kaydı yok.")
        else:
            df_vade = df_evrak.copy()
            df_vade["Ödendi"] = df_vade["Ödendi"].fillna(False).astype(bool)
            df_vade["Vade Tarihi"] = pd.to_datetime(df_vade["Vade Tarihi"], errors="coerce")
            vade_df = df_vade[df_vade["Vade Tarihi"].notna() & (~df_vade["Ödendi"])].copy()
            if vade_df.empty:
                st.info("Açık vade kaydı yok.")
            else:
                vade_df["Kalan Gün"] = (vade_df["Vade Tarihi"] - pd.to_datetime(datetime.date.today())).dt.days
                tablo = vade_df[["Müşteri Adı", "Ülke", "Fatura No", "Vade Tarihi", "Tutar", "Kalan Gün"]].copy()
                tablo["Vade Tarihi"] = pd.to_datetime(tablo["Vade Tarihi"], errors="coerce").dt.strftime("%d/%m/%Y")
                st.dataframe(tablo.sort_values("Vade Tarihi"), use_container_width=True)

    st.markdown("<hr>", unsafe_allow_html=True)
    st.info("Detaylı işlem için sol menüden ilgili bölümü seçebilirsiniz.")
