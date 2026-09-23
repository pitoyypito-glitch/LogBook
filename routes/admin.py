from datetime import date, datetime

from flask import Blueprint, current_app, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from extensions import db
from models import (
    AdminActivityLog,
    Department,
    Level,
    LevelRequest,
    LogbookProgress,
    Nurse,
    PasswordResetRequest,
    User,
    catat_aktivitas_admin,
)
from utils import allowed_photo, hapus_foto_profile, role_required, simpan_foto_profile

admin_bp = Blueprint("admin", __name__, url_prefix="/admin")

NIK_MAX_LEN = 8


def _nik_valid(nik: str) -> bool:
    """NIK sementara divalidasi: hanya angka, panjang 1-8 digit."""
    return bool(nik) and nik.isdigit() and len(nik) <= NIK_MAX_LEN


def _parse_tanggal(nilai):
    """Parse input <input type=date> ('YYYY-MM-DD') jadi date, atau None."""
    nilai = (nilai or "").strip()
    if not nilai:
        return None
    try:
        return datetime.strptime(nilai, "%Y-%m-%d").date()
    except ValueError:
        return None


@admin_bp.route("/perawat")
@login_required
@role_required("admin")
def daftar_perawat():
    from jobs import daftar_dokumen_perlu_perhatian

    nurses = Nurse.query.order_by(Nurse.nama).all()
    levels = Level.query.order_by(Level.urutan).all()
    departments = Department.query.order_by(Department.urutan).all()
    reset_requests = (
        PasswordResetRequest.query.filter_by(status="pending")
        .order_by(PasswordResetRequest.submitted_at)
        .all()
    )
    perlu_perhatian = daftar_dokumen_perlu_perhatian()
    return render_template(
        "admin/nurses.html",
        nurses=nurses,
        levels=levels,
        departments=departments,
        reset_requests=reset_requests,
        perlu_perhatian=perlu_perhatian,
    )


@admin_bp.route("/perawat/tambah", methods=["POST"])
@login_required
@role_required("admin")
def tambah_perawat():
    nik = request.form.get("nik", "").strip()
    nama = request.form.get("nama", "").strip()
    current_level_id = request.form.get("current_level_id", type=int)
    department_id = request.form.get("department_id", type=int)

    if not nik or not nama:
        flash("NIK dan nama wajib diisi.", "danger")
        return redirect(url_for("admin.daftar_perawat"))
    if not _nik_valid(nik):
        flash(f"NIK tidak valid. NIK harus berupa angka, maksimal {NIK_MAX_LEN} digit.", "danger")
        return redirect(url_for("admin.daftar_perawat"))
    if User.query.filter_by(username=nik).first():
        flash("NIK sudah digunakan oleh akun lain.", "danger")
        return redirect(url_for("admin.daftar_perawat"))

    user = User(username=nik, role="perawat", status="active")
    user.set_password(current_app.config["DEFAULT_PASSWORD"])
    db.session.add(user)
    db.session.flush()

    nurse = Nurse(
        user_id=user.id,
        nama=nama,
        nik=nik,
        str_=request.form.get("str", "").strip() or None,
        sip=request.form.get("sip", "").strip() or None,
        sip_expiry=_parse_tanggal(request.form.get("sip_expiry")),
        spk_rkk=request.form.get("spk_rkk", "").strip() or None,
        spk_rkk_expiry=_parse_tanggal(request.form.get("spk_rkk_expiry")),
        current_level_id=current_level_id,
        department_id=department_id,
        status="active",
    )
    db.session.add(nurse)
    db.session.flush()
    catat_aktivitas_admin(
        "tambah_perawat", target_type="nurse", target_id=nurse.id, target_label=nama
    )
    db.session.commit()
    flash(
        f"Akun perawat '{nama}' berhasil dibuat. Login dengan NIK {nik} dan "
        f"password default \"{current_app.config['DEFAULT_PASSWORD']}\".",
        "success",
    )
    return redirect(url_for("admin.daftar_perawat"))


@admin_bp.route("/perawat/<int:nurse_id>/edit", methods=["GET", "POST"])
@login_required
@role_required("admin")
def edit_perawat(nurse_id):
    nurse = Nurse.query.get_or_404(nurse_id)
    levels = Level.query.order_by(Level.urutan).all()
    departments = Department.query.order_by(Department.urutan).all()

    if request.method == "POST":
        nik = request.form.get("nik", "").strip()
        nama = request.form.get("nama", "").strip()
        if not nik or not nama:
            flash("NIK dan nama wajib diisi.", "danger")
            return redirect(url_for("admin.edit_perawat", nurse_id=nurse.id))
        if not _nik_valid(nik):
            flash(f"NIK tidak valid. NIK harus berupa angka, maksimal {NIK_MAX_LEN} digit.", "danger")
            return redirect(url_for("admin.edit_perawat", nurse_id=nurse.id))

        duplicate = User.query.filter(User.username == nik, User.id != nurse.user_id).first()
        if duplicate:
            flash("NIK sudah digunakan oleh akun lain.", "danger")
            return redirect(url_for("admin.edit_perawat", nurse_id=nurse.id))

        nurse.user.username = nik
        nurse.nama = nama
        nurse.nik = nik
        nurse.str_ = request.form.get("str", "").strip() or None
        nurse.sip = request.form.get("sip", "").strip() or None
        nurse.sip_expiry = _parse_tanggal(request.form.get("sip_expiry"))
        nurse.spk_rkk = request.form.get("spk_rkk", "").strip() or None
        nurse.spk_rkk_expiry = _parse_tanggal(request.form.get("spk_rkk_expiry"))
        nurse.current_level_id = request.form.get("current_level_id", type=int) or None
        nurse.department_id = request.form.get("department_id", type=int) or None

        password_diubah = False
        new_password = request.form.get("password", "")
        if new_password:
            if len(new_password) < 8:
                flash("Password baru minimal 8 karakter.", "danger")
                return redirect(url_for("admin.edit_perawat", nurse_id=nurse.id))
            nurse.user.set_password(new_password)
            password_diubah = True

        photo = request.files.get("foto_profile")
        if photo and photo.filename:
            if not allowed_photo(photo.filename, current_app.config["ALLOWED_PHOTO_EXT"]):
                flash("Format foto harus PNG, JPG, JPEG, atau WEBP.", "danger")
                return redirect(url_for("admin.edit_perawat", nurse_id=nurse.id))
            old_photo = nurse.foto_profile
            new_photo = simpan_foto_profile(
                photo,
                current_app.config["UPLOAD_FOLDER"],
                current_app.config["ALLOWED_PHOTO_EXT"],
                nurse.id,
            )
            if new_photo:
                nurse.foto_profile = new_photo
                hapus_foto_profile(old_photo, current_app.config["UPLOAD_FOLDER"])

        catat_aktivitas_admin(
            "edit_perawat",
            target_type="nurse",
            target_id=nurse.id,
            target_label=nurse.nama,
            keterangan="password direset admin" if password_diubah else None,
        )
        db.session.commit()
        flash(f"Data perawat '{nurse.nama}' berhasil diperbarui.", "success")
        return redirect(url_for("admin.daftar_perawat"))

    return render_template("admin/edit_nurse.html", nurse=nurse, levels=levels, departments=departments)


@admin_bp.route("/perawat/<int:nurse_id>/status", methods=["POST"])
@login_required
@role_required("admin")
def toggle_status(nurse_id):
    nurse = Nurse.query.get_or_404(nurse_id)
    new_status = "inactive" if nurse.status == "active" else "active"

    if new_status == "active" and nurse.dokumen_kedaluwarsa:
        flash(
            f"Perhatian: SIP/SPK-RKK {nurse.nama} sudah lewat tanggal berlaku. "
            "Akun diaktifkan, tetapi akan otomatis dinonaktifkan lagi oleh sistem "
            "kecuali tanggal kedaluwarsanya diperbarui di halaman Edit.",
            "warning",
        )

    nurse.status = new_status
    nurse.user.status = new_status
    catat_aktivitas_admin(
        "aktifkan_perawat" if new_status == "active" else "nonaktifkan_perawat",
        target_type="nurse",
        target_id=nurse.id,
        target_label=nurse.nama,
    )
    db.session.commit()
    flash(f"Akun {nurse.nama} sekarang {'aktif' if new_status == 'active' else 'nonaktif'}.", "success")
    return redirect(url_for("admin.daftar_perawat"))


@admin_bp.route("/perawat/<int:nurse_id>/hapus", methods=["POST"])
@login_required
@role_required("admin")
def hapus_perawat(nurse_id):
    nurse = Nurse.query.get_or_404(nurse_id)
    if nurse.user_id == current_user.id:
        flash("Admin yang sedang login tidak dapat menghapus dirinya sendiri.", "danger")
        return redirect(url_for("admin.daftar_perawat"))

    user = nurse.user
    nurse_name = nurse.nama
    nurse_id_untuk_log = nurse.id
    old_photo = nurse.foto_profile
    # Catat sebelum baris dihapus (target_id tidak lagi merujuk baris yang
    # valid setelah delete, tapi tetap berguna untuk jejak historis).
    catat_aktivitas_admin(
        "hapus_perawat", target_type="nurse", target_id=nurse_id_untuk_log, target_label=nurse_name
    )
    # Hapus data anak terlebih dahulu agar aman terhadap foreign key MySQL.
    LogbookProgress.query.filter_by(nurse_id=nurse.id).delete(synchronize_session=False)
    LevelRequest.query.filter_by(nurse_id=nurse.id).delete(synchronize_session=False)
    db.session.delete(nurse)
    db.session.delete(user)
    db.session.commit()
    hapus_foto_profile(old_photo, current_app.config["UPLOAD_FOLDER"])
    flash(f"Data perawat '{nurse_name}' berhasil dihapus.", "success")
    return redirect(url_for("admin.daftar_perawat"))


@admin_bp.route("/perawat/<int:nurse_id>/level", methods=["POST"])
@login_required
@role_required("admin")
def ubah_level_manual(nurse_id):
    nurse = Nurse.query.get_or_404(nurse_id)
    level_id = request.form.get("current_level_id", type=int)
    if level_id and not db.session.get(Level, level_id):
        flash("Level tidak ditemukan.", "danger")
        return redirect(url_for("admin.daftar_perawat"))
    nurse.current_level_id = level_id
    catat_aktivitas_admin(
        "ubah_level_manual", target_type="nurse", target_id=nurse.id, target_label=nurse.nama
    )
    db.session.commit()
    flash(f"Level {nurse.nama} berhasil diperbarui.", "success")
    return redirect(url_for("admin.daftar_perawat"))


@admin_bp.route("/level-requests")
@login_required
@role_required("admin", "supervisor")
def level_requests():
    requests_ = LevelRequest.query.order_by(LevelRequest.submitted_at.desc()).all()
    return render_template("admin/level_requests.html", requests=requests_)


@admin_bp.route("/lupa-password/<int:request_id>/setujui", methods=["POST"])
@login_required
@role_required("admin")
def setujui_lupa_password(request_id):
    req = PasswordResetRequest.query.get_or_404(request_id)
    if req.status != "pending":
        flash("Pengajuan ini sudah diproses sebelumnya.", "warning")
        return redirect(url_for("admin.daftar_perawat"))

    new_password = request.form.get("new_password", "")
    if len(new_password) < 8:
        flash("Password baru minimal 8 karakter.", "danger")
        return redirect(url_for("admin.daftar_perawat"))

    req.user.set_password(new_password)
    req.status = "selesai"
    req.reviewed_by = current_user.id
    req.reviewed_at = datetime.utcnow()
    catat_aktivitas_admin(
        "setujui_lupa_password",
        target_type="user",
        target_id=req.user.id,
        target_label=req.user.username,
    )
    db.session.commit()
    flash(f"Password baru untuk '{req.user.username}' berhasil ditetapkan.", "success")
    return redirect(url_for("admin.daftar_perawat"))


@admin_bp.route("/lupa-password/<int:request_id>/tolak", methods=["POST"])
@login_required
@role_required("admin")
def tolak_lupa_password(request_id):
    req = PasswordResetRequest.query.get_or_404(request_id)
    if req.status != "pending":
        flash("Pengajuan ini sudah diproses sebelumnya.", "warning")
        return redirect(url_for("admin.daftar_perawat"))

    req.status = "ditolak"
    req.reviewed_by = current_user.id
    req.reviewed_at = datetime.utcnow()
    db.session.commit()
    flash("Pengajuan lupa password ditolak.", "info")
    return redirect(url_for("admin.daftar_perawat"))


@admin_bp.route("/log-aktivitas")
@login_required
@role_required("admin")
def activity_log():
    logs = (
        AdminActivityLog.query.order_by(AdminActivityLog.created_at.desc())
        .limit(300)
        .all()
    )
    return render_template("admin/activity_log.html", logs=logs)


@admin_bp.route("/verifikasi")
@login_required
@role_required("admin", "supervisor")
def verifikasi():
    entries = LogbookProgress.query.order_by(LogbookProgress.created_at.desc()).limit(300).all()
    return render_template("admin/verify_progress.html", entries=entries)
