import os

from flask import Flask, redirect, url_for
from flask_login import current_user, logout_user

from config import Config, _DEFAULT_SECRET_KEY
from extensions import csrf, db, login_manager
from models import User


def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)

    import os
    os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)

    if app.config.get("SECRET_KEY") == _DEFAULT_SECRET_KEY:
        app.logger.warning(
            "PERINGATAN: SECRET_KEY masih memakai nilai default contoh. "
            "Set environment variable SECRET_KEY dengan string acak yang "
            "aman sebelum dipakai di produksi (lihat .env.example)."
        )

    db.init_app(app)
    login_manager.init_app(app)
    csrf.init_app(app)

    from routes.admin import admin_bp
    from routes.auth import auth_bp
    from routes.level import level_bp
    from routes.logbook import logbook_bp
    from routes.nurse import nurse_bp
    from routes.ojt_prapk import ojt_prapk_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(nurse_bp)
    app.register_blueprint(logbook_bp)
    app.register_blueprint(level_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(ojt_prapk_bp)

    @app.before_request
    def ensure_active_account():
        # Jika admin menonaktifkan akun yang sedang login, sesi aktif
        # tidak boleh tetap dapat digunakan.
        if current_user.is_authenticated and getattr(current_user, "status", None) != "active":
            logout_user()
            return redirect(url_for("auth.login"))

    @app.route("/")
    def index():
        if current_user.is_authenticated:
            return redirect(url_for("nurse.dashboard"))
        return redirect(url_for("auth.login"))

    # --- Perintah CLI: pengecekan SIP/SPK-RKK kedaluwarsa -----------------
    # Bisa dipanggil manual (flask cek-kedaluwarsa) atau dijadwalkan lewat
    # cron/Task Scheduler di server produksi, sebagai alternatif dari
    # APScheduler in-process yang didaftarkan di bawah.
    @app.cli.command("cek-kedaluwarsa")
    def cek_kedaluwarsa_command():
        """Nonaktifkan akun perawat yang SIP/SPK-RKK-nya sudah kedaluwarsa."""
        from jobs import cek_dan_nonaktifkan_dokumen_kedaluwarsa

        dinonaktifkan = cek_dan_nonaktifkan_dokumen_kedaluwarsa()
        if dinonaktifkan:
            nama = ", ".join(n.nama for n in dinonaktifkan)
            print(f"{len(dinonaktifkan)} akun dinonaktifkan otomatis: {nama}")
        else:
            print("Tidak ada akun yang perlu dinonaktifkan hari ini.")

    _mulai_scheduler_kedaluwarsa(app)

    return app


def _mulai_scheduler_kedaluwarsa(app):
    """Daftarkan job harian (APScheduler) yang mengecek & menonaktifkan
    otomatis akun perawat dengan SIP/SPK-RKK kedaluwarsa.

    Ini adalah jaring pengaman in-process untuk deployment yang hanya
    menjalankan `python app.py` tanpa cron terpisah. Untuk produksi yang
    lebih andal, tetap disarankan menjadwalkan `flask cek-kedaluwarsa`
    lewat cron/Task Scheduler asli di server (lihat jobs.py).
    """
    # Nonaktifkan lewat ENABLE_SCHEDULER=0 di .env kalau produksi memakai
    # Gunicorn dengan >1 worker (supaya job harian tidak terpanggil dobel
    # per worker) dan jadwalkan `flask cek-kedaluwarsa` lewat cron.
    if not app.config.get("ENABLE_SCHEDULER", True):
        app.logger.info(
            "ENABLE_SCHEDULER=0: scheduler in-process dimatikan. "
            "Pastikan `flask cek-kedaluwarsa` dijadwalkan lewat cron."
        )
        return

    # Saat debug reloader aktif, Flask menjalankan proses dua kali. Hanya
    # daftarkan scheduler di proses utama agar job tidak dobel.
    if app.debug and os.environ.get("WERKZEUG_RUN_MAIN") != "true":
        return

    try:
        from apscheduler.schedulers.background import BackgroundScheduler
    except ImportError:
        app.logger.warning(
            "APScheduler belum terpasang (pip install -r requirements.txt); "
            "pengecekan kedaluwarsa SIP/SPK-RKK otomatis tidak berjalan. "
            "Jalankan manual/cron lewat `flask cek-kedaluwarsa`."
        )
        return

    def _job():
        with app.app_context():
            try:
                from jobs import cek_dan_nonaktifkan_dokumen_kedaluwarsa

                dinonaktifkan = cek_dan_nonaktifkan_dokumen_kedaluwarsa()
                if dinonaktifkan:
                    nama = ", ".join(n.nama for n in dinonaktifkan)
                    app.logger.info(
                        "%s akun perawat dinonaktifkan otomatis (SIP/SPK-RKK kedaluwarsa): %s",
                        len(dinonaktifkan),
                        nama,
                    )
            except Exception:  # noqa: BLE001 - jangan sampai job harian menjatuhkan app
                app.logger.exception("Gagal menjalankan pengecekan kedaluwarsa SIP/SPK-RKK.")

    scheduler = BackgroundScheduler(daemon=True, timezone="Asia/Jakarta")
    scheduler.add_job(_job, "cron", hour=1, minute=0, id="cek_kedaluwarsa_harian")
    scheduler.start()

    # Jalankan sekali saat startup juga, supaya perubahan tidak menunggu
    # sampai jam 01:00 pertama setelah server dinyalakan. Dijalankan di
    # thread terpisah agar tidak memblokir/menggagalkan startup aplikasi
    # jika database belum siap (mis. saat migrasi belum dijalankan).
    scheduler.add_job(_job, "date")


app = create_app()


@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))


if __name__ == "__main__":
    # Database sudah dibuat lewat import database.sql ke phpMyAdmin/XAMPP.
    # Jalankan: python app.py
    app.run(debug=True, host="0.0.0.0", port=5000)
