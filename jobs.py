"""Job terjadwal (harian) untuk mengecek masa berlaku SIP & SPK/RKK perawat.

Aturan bisnis:
- SIP berlaku 5 tahun, SPK/RKK berlaku 3 tahun sejak terbit. Tanggal
  kedaluwarsa masing-masing disimpan di kolom nurses.sip_expiry dan
  nurses.spk_rkk_expiry (diisi manual oleh admin saat SIP/SPK-RKK terbit).
- Peringatan (badge kuning/merah) ditampilkan di dashboard admin & dashboard
  perawat yang bersangkutan mulai H-90 dan H-30 -- lihat Nurse._status_kedaluwarsa
  di models.py. Ini murni tampilan, tidak perlu job terpisah.
- Begitu tanggal kedaluwarsa TERLEWATI (H+1), fungsi di bawah ini akan
  menonaktifkan otomatis akun perawat tsb (nurses.status = 'inactive' dan
  users.status = 'inactive'), sehingga perawat tidak bisa login lagi sampai
  admin memperbarui tanggal kedaluwarsa (setelah SIP/SPK-RKK diperpanjang)
  dan mengaktifkan kembali akunnya lewat halaman Kelola Perawat.
- Fungsi ini idempotent: aman dipanggil berkali-kali (nurse yang sudah
  inactive tidak akan diproses ulang / tidak akan menimpa nonaktif manual).

Cara menjalankan job ini di produksi (pilih salah satu):
1. Otomatis, selama aplikasi Flask berjalan: sudah didaftarkan lewat
   APScheduler di app.py (jalan tiap hari jam 01:00 + sekali saat start).
   Cocok untuk deployment yang menjalankan `python app.py` terus-menerus.
2. Cron/​Task Scheduler asli di server, memanggil perintah CLI:
       flask cek-kedaluwarsa
   Cocok untuk deployment produksi yang lebih andal (tidak tergantung
   proses Flask tetap hidup), misal cron Linux jam 01:00 setiap hari:
       0 1 * * * cd /path/ke/app && /path/ke/venv/bin/flask cek-kedaluwarsa
"""

from datetime import date

from extensions import db
from models import Nurse


def cek_dan_nonaktifkan_dokumen_kedaluwarsa():
    """Nonaktifkan akun perawat yang SIP atau SPK/RKK-nya sudah kedaluwarsa.

    Return: list berisi objek Nurse yang baru dinonaktifkan pada pemanggilan ini.
    """
    today = date.today()

    kandidat = (
        Nurse.query.filter(
            Nurse.status == "active",
            db.or_(
                Nurse.sip_expiry.isnot(None) & (Nurse.sip_expiry < today),
                Nurse.spk_rkk_expiry.isnot(None) & (Nurse.spk_rkk_expiry < today),
            ),
        ).all()
    )

    dinonaktifkan = []
    for nurse in kandidat:
        nurse.status = "inactive"
        if nurse.user:
            nurse.user.status = "inactive"
        dinonaktifkan.append(nurse)

    if dinonaktifkan:
        db.session.commit()

    return dinonaktifkan


def daftar_dokumen_perlu_perhatian():
    """Untuk banner/ringkasan admin: perawat aktif yang dokumennya sudah
    kedaluwarsa atau akan kedaluwarsa dalam waktu dekat (<= PERINGATAN_H hari).
    """
    hasil = {"expired": [], "critical": [], "warning": []}
    nurses = Nurse.query.filter(
        Nurse.status == "active",
        db.or_(Nurse.sip_expiry.isnot(None), Nurse.spk_rkk_expiry.isnot(None)),
    ).all()

    for nurse in nurses:
        levels_terpakai = set()
        for status_info in (nurse.sip_status, nurse.spk_rkk_status):
            if status_info and status_info["level"] != "ok":
                levels_terpakai.add(status_info["level"])
        if "expired" in levels_terpakai:
            hasil["expired"].append(nurse)
        elif "critical" in levels_terpakai:
            hasil["critical"].append(nurse)
        elif "warning" in levels_terpakai:
            hasil["warning"].append(nurse)

    return hasil
