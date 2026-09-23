# Panduan Deploy Produksi — Eka Hospital Logbook

Ditujukan untuk penggunaan internal RS (±500 user, dikontrol oleh beberapa
admin) di server Linux (Ubuntu/Debian). Sesuaikan path/nama service kalau
server berbeda.

## 1. Siapkan server

```bash
sudo mkdir -p /opt/eka-hospital-logbook
sudo chown $USER:$USER /opt/eka-hospital-logbook
# salin isi project ke folder ini, lalu:
cd /opt/eka-hospital-logbook
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

## 2. Konfigurasi environment

```bash
cp .env.example .env
nano .env   # isi SECRET_KEY, DATABASE_URL, dll
```

- `SECRET_KEY`: generate dengan `python3 -c "import secrets; print(secrets.token_hex(32))"`.
- `DATABASE_URL`: buat user MySQL khusus (bukan root), beri akses hanya ke
  database `nursing_career`.
- `ENABLE_SCHEDULER`: set `0` kalau Gunicorn dijalankan >1 worker (lihat
  bagian Cron di bawah).

## 3. Migrasi database

Import `database.sql` awal (kalau server baru), lalu jalankan semua
`migration_*.sql` termasuk `migration_admin_activity_log.sql` yang baru,
lewat `mysql` CLI atau phpMyAdmin.

## 4. Jalankan lewat Gunicorn + systemd

Salin `deploy/eka-hospital-logbook.service` ke `/etc/systemd/system/`,
sesuaikan `User`, `WorkingDirectory`, dan path venv, lalu:

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now eka-hospital-logbook
sudo systemctl status eka-hospital-logbook
```

## 5. Reverse proxy Nginx

Salin `deploy/nginx.conf.example`, sesuaikan `server_name`, aktifkan
site-nya (lihat komentar di file tersebut). Nginx yang menerima trafik
dari user, lalu meneruskan ke Gunicorn di `127.0.0.1:8000`.

## 6. Cron untuk pengecekan SIP/SPK-RKK kedaluwarsa (kalau ENABLE_SCHEDULER=0)

```bash
sudo crontab -e
# tambahkan baris ini (jalan tiap hari jam 01:00):
0 1 * * * cd /opt/eka-hospital-logbook && venv/bin/flask cek-kedaluwarsa >> /var/log/eka-cek-kedaluwarsa.log 2>&1
```

## 7. Checklist sebelum go-live

- [ ] `SECRET_KEY` sudah diganti, bukan nilai default.
- [ ] `DATABASE_URL` pakai user MySQL khusus (bukan root tanpa password).
- [ ] `.env` tidak ikut ter-commit ke Git / tidak bisa diakses publik.
- [ ] Sudah jalan lewat Gunicorn (bukan `python app.py`).
- [ ] `ENABLE_SCHEDULER=0` + cron aktif kalau worker > 1.
- [ ] Backup database terjadwal (mis. `mysqldump` harian ke lokasi aman).
- [ ] Kalau sudah pasang HTTPS: set `FORCE_HTTPS=1` di `.env`.

## 8. Update/redeploy berikutnya

```bash
cd /opt/eka-hospital-logbook
git pull   # atau upload ulang file yang berubah
source venv/bin/activate
pip install -r requirements.txt
# jalankan migration_*.sql baru kalau ada
sudo systemctl restart eka-hospital-logbook
```
