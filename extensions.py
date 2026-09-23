from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_wtf import CSRFProtect

db = SQLAlchemy()

login_manager = LoginManager()
login_manager.login_view = "auth.login"
login_manager.login_message = "Silakan login terlebih dahulu."
login_manager.login_message_category = "warning"

# Proteksi CSRF untuk semua form POST (form harus menyertakan
# {{ csrf_token() }} sebagai input hidden bernama csrf_token).
csrf = CSRFProtect()
