import os

try:
    from dotenv import load_dotenv

    load_dotenv()  # baca file .env jika ada (lihat .env.example)
except ImportError:
    pass

BASE_DIR = os.path.abspath(os.path.dirname(__file__))

_DEFAULT_SECRET_KEY = "ganti-secret-key-ini-sebelum-produksi"


class Config:
    """Konfigurasi utama aplikasi Nursing Career Ladder / Logbook Perawat."""

    # WAJIB di-set lewat environment variable (.env / systemd EnvironmentFile)
    # di server produksi. Nilai fallback di bawah HANYA untuk development lokal.
    SECRET_KEY = os.environ.get("SECRET_KEY", _DEFAULT_SECRET_KEY)

    # Sesuaikan user/password MySQL. Untuk produksi, WAJIB di-set lewat
    # environment variable DATABASE_URL (jangan pakai user root tanpa password).
    # Format: mysql+pymysql://<user>:<password>@<host>/<nama_database>
    SQLALCHEMY_DATABASE_URI = os.environ.get(
        "DATABASE_URL",
        "mysql+pymysql://root:@localhost/nursing_career",
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ENGINE_OPTIONS = {
        "pool_pre_ping": True,
        "pool_recycle": 280,
    }

    # Folder penyimpanan foto profil perawat (public via /static/uploads/...)
    UPLOAD_FOLDER = os.path.join(BASE_DIR, "static", "uploads")
    ALLOWED_PHOTO_EXT = {"png", "jpg", "jpeg", "webp"}
    MAX_CONTENT_LENGTH = 5 * 1024 * 1024  # batas upload 5MB

    # Password default untuk akun perawat yang baru didaftarkan (lewat halaman
    # registrasi mandiri maupun ditambahkan admin). Login memakai NIK sebagai
    # identitas (bukan username terpisah lagi). Perawat bisa mengganti
    # password sendiri lewat halaman Profil (butuh password lama); jika lupa
    # password lama, gunakan alur Lupa Password (diajukan ke admin).
    DEFAULT_PASSWORD = "Eka123!"

    # --- Keamanan session cookie ---------------------------------------
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"
    # Aktifkan otomatis kalau diakses lewat HTTPS (set FORCE_HTTPS=1 di .env
    # begitu domain produksi sudah pakai SSL/TLS).
    SESSION_COOKIE_SECURE = os.environ.get("FORCE_HTTPS", "0") == "1"

    # --- Scheduler APScheduler in-process --------------------------------
    # Kalau dijalankan dengan Gunicorn >1 worker, tiap worker akan mencoba
    # mendaftarkan scheduler-nya sendiri -> job harian bisa terpanggil dobel.
    # Set ENABLE_SCHEDULER=0 di .env kalau produksi memakai >1 worker, lalu
    # jadwalkan `flask cek-kedaluwarsa` lewat cron sekali sehari (lihat
    # deploy/README_DEPLOY.md).
    ENABLE_SCHEDULER = os.environ.get("ENABLE_SCHEDULER", "1") == "1"
