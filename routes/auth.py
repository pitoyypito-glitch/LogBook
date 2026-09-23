from flask import Blueprint, current_app, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required, login_user, logout_user

from extensions import db
from models import Department, Level, Nurse, PasswordResetRequest, User

auth_bp = Blueprint("auth", __name__)

NIK_MAX_LEN = 8


def _nik_valid(nik: str) -> bool:
    """NIK sementara divalidasi: hanya angka, panjang 1-8 digit."""
    return bool(nik) and nik.isdigit() and len(nik) <= NIK_MAX_LEN


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("nurse.dashboard"))

    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        user = User.query.filter_by(username=username).first()

        if user is None or not user.check_password(password):
            flash("NIK atau password salah.", "danger")
            return render_template("login.html")
        if user.status != "active":
            flash("Akun Anda tidak aktif. Hubungi admin.", "danger")
            return render_template("login.html")

        login_user(user)
        display_name = user.nurse.nama if user.nurse else user.username
        flash(f"Selamat datang, {display_name}!", "success")
        return redirect(request.args.get("next") or url_for("nurse.dashboard"))

    return render_template("login.html")


@auth_bp.route("/logout")
@login_required
def logout():
    logout_user()
    flash("Anda telah logout.", "info")
    return redirect(url_for("auth.login"))


@auth_bp.route("/register", methods=["GET", "POST"])
def register():
    if current_user.is_authenticated:
        return redirect(url_for("nurse.dashboard"))

    levels = Level.query.order_by(Level.urutan).all()
    departments = Department.query.order_by(Department.urutan).all()

    if request.method == "POST":
        nama = request.form.get("nama", "").strip()
        nik = request.form.get("nik", "").strip()
        sip = request.form.get("sip", "").strip()
        spk_rkk = request.form.get("spk_rkk", "").strip()
        current_level_id = request.form.get("current_level_id", type=int)
        department_id = request.form.get("department_id", type=int)

        form_values = {
            "nama": nama, "nik": nik,
            "sip": sip, "spk_rkk": spk_rkk, "current_level_id": current_level_id,
            "department_id": department_id,
        }

        if not all([nama, nik, sip, spk_rkk, current_level_id, department_id]):
            flash("Semua data wajib diisi: nama lengkap, NIK, SIP, SPK/RKK, level, dan departemen.", "danger")
            return render_template("register.html", levels=levels, departments=departments, form_values=form_values)
        if not _nik_valid(nik):
            flash(f"NIK tidak valid. NIK harus berupa angka, maksimal {NIK_MAX_LEN} digit.", "danger")
            return render_template("register.html", levels=levels, departments=departments, form_values=form_values)
        if User.query.filter_by(username=nik).first():
            flash("NIK sudah terdaftar, silakan login atau gunakan fitur Lupa Password.", "danger")
            return render_template("register.html", levels=levels, departments=departments, form_values=form_values)
        if not db.session.get(Level, current_level_id):
            flash("Level yang dipilih tidak valid.", "danger")
            return render_template("register.html", levels=levels, departments=departments, form_values=form_values)
        if not db.session.get(Department, department_id):
            flash("Departemen yang dipilih tidak valid.", "danger")
            return render_template("register.html", levels=levels, departments=departments, form_values=form_values)

        user = User(username=nik, role="perawat", status="active")
        user.set_password(current_app.config["DEFAULT_PASSWORD"])
        db.session.add(user)
        db.session.flush()

        nurse = Nurse(
            user_id=user.id,
            nama=nama,
            nik=nik,
            sip=sip,
            spk_rkk=spk_rkk,
            current_level_id=current_level_id,
            department_id=department_id,
            status="active",
        )
        db.session.add(nurse)
        db.session.commit()

        flash(
            f"Pendaftaran berhasil! Login menggunakan NIK Anda ({nik}) dengan "
            f"password default \"{current_app.config['DEFAULT_PASSWORD']}\".",
            "success",
        )
        return redirect(url_for("auth.login"))

    return render_template("register.html", levels=levels, departments=departments, form_values={})


@auth_bp.route("/lupa-password", methods=["GET", "POST"])
def forgot_password():
    if current_user.is_authenticated:
        return redirect(url_for("nurse.dashboard"))

    if request.method == "POST":
        username = request.form.get("username", "").strip()
        alasan = request.form.get("alasan", "").strip() or None
        user = User.query.filter_by(username=username).first()

        if not user:
            flash("NIK tidak ditemukan.", "danger")
            return render_template("forgot_password.html", username=username)

        existing = PasswordResetRequest.query.filter_by(user_id=user.id, status="pending").first()
        if existing:
            flash("Anda sudah memiliki pengajuan lupa password yang masih menunggu diproses admin.", "warning")
            return redirect(url_for("auth.login"))

        db.session.add(PasswordResetRequest(user_id=user.id, alasan=alasan, status="pending"))
        db.session.commit()
        flash("Pengajuan lupa password berhasil dikirim. Admin akan menetapkan password baru untuk Anda.", "success")
        return redirect(url_for("auth.login"))

    return render_template("forgot_password.html", username="")


@auth_bp.route("/password", methods=["POST"])
@login_required
def change_password():
    # Perawat kembali ke halaman Profil, admin/supervisor kembali ke Dashboard.
    redirect_target = "nurse.profil" if current_user.role == "perawat" else "nurse.dashboard"

    old_password = request.form.get("old_password", "")
    new_password = request.form.get("new_password", "")
    confirm_password = request.form.get("confirm_password", "")

    if not current_user.check_password(old_password):
        flash("Password lama tidak sesuai.", "danger")
        return redirect(url_for(redirect_target))
    if len(new_password) < 8:
        flash("Password baru minimal 8 karakter.", "danger")
        return redirect(url_for(redirect_target))
    if new_password != confirm_password:
        flash("Konfirmasi password baru tidak cocok.", "danger")
        return redirect(url_for(redirect_target))
    if new_password == old_password:
        flash("Password baru harus berbeda dari password lama.", "warning")
        return redirect(url_for(redirect_target))

    current_user.set_password(new_password)
    db.session.commit()
    flash("Password berhasil diubah.", "success")
    return redirect(url_for(redirect_target))
