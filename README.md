# Eka Hospital Logbook Perawat

Aplikasi Flask untuk logbook kompetensi dan Nursing Career Ladder.

## Perbaikan versi ini
- Foto profil perawat: upload dari dashboard, validasi ekstensi, nama file unik, dan penghapusan foto lama.
- Ubah password untuk semua role dari dashboard. Password baru minimal 8 karakter.
- Badge level dibuat lebih besar dan lebih jelas.
- Admin dapat menambah, **mengedit**, **mengaktifkan/nonaktifkan**, dan **menghapus** data perawat.
- Saat perawat dinonaktifkan, akun user juga dinonaktifkan sehingga tidak dapat login. Sesi aktif akun nonaktif diputus pada request berikutnya.
- Admin dapat mengubah level secara manual.
- Progress logbook menggunakan target: sebuah keterampilan baru dianggap selesai jika jumlah verifikasi disetujui mencapai targetnya.
- Perawat tidak dapat mencatat task dari level lain atau membuat pencapaian baru ketika masih ada pencapaian yang menunggu verifikasi.
- Approval kenaikan level melakukan validasi ulang progress sebelum level dinaikkan.
- Folder/file duplikat dan `__pycache__` dibersihkan dari paket distribusi.

## Database
Project ini tetap menggunakan database yang sudah ada (`nursing_career`). Kolom `foto_profile` harus tersedia pada tabel `nurses`. Jika belum ada, jalankan isi `migration_foto_profile.sql` melalui phpMyAdmin/MySQL.

Tidak ada perubahan struktur database untuk fitur ubah password karena password sudah disimpan pada `users.password_hash`.

## Persiapan produksi (baru)
- Proteksi CSRF aktif di semua form (Flask-WTF).
- Konfigurasi `SECRET_KEY`, `DATABASE_URL`, dll dibaca dari file `.env` (lihat `.env.example`).
- Log aktivitas admin (tambah/edit/hapus/nonaktifkan perawat, reset password) tercatat di tabel `admin_activity_logs` — jalankan `migration_admin_activity_log.sql`, lalu lihat di menu "Log Aktivitas Admin".
- Scheduler pengecekan SIP/SPK-RKK kedaluwarsa bisa dimatikan lewat `ENABLE_SCHEDULER=0` di `.env` untuk deployment multi-worker (pakai cron sebagai gantinya).
- Panduan lengkap deploy ke server (Gunicorn + systemd + Nginx + cron): lihat `deploy/README_DEPLOY.md`.

## Menjalankan
```powershell
python -m venv venv
.\venv\Scripts\activate
pip install -r requirements.txt
python app.py
```

Buka `http://127.0.0.1:5000`.

Untuk produksi, ganti `SECRET_KEY` dan `DATABASE_URL` melalui environment variable.
