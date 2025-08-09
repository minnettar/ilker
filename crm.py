# test: klasörde listeleme (paylaşım var mı?)
try:
    r = drive_service.files().list(
        q=f"'{SIPARIS_FORMU_ID}' in parents and trashed=false",
        fields="files(id, name)", pageSize=1
    ).execute()
    print("Klasöre erişim OK, örnek:", r.get("files", []))
except Exception as e:
    print("Klasöre erişim YOK:", e)
