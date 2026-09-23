import os

from flask import Blueprint, abort, current_app, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from extensions import db
from models import Competency, LevelRequest, LogbookProgress, LogbookTask
from utils import allowed_photo, hapus_foto_profile, simpan_foto_profile

nurse_bp = Blueprint("nurse", __name__)


def hitung_progress_level(nurse):
    """Progress dihitung berdasarkan jumlah target yang sudah DISETUJUI."""
    if not nurse or not nurse.current_level_id:
        return {"total": 0, "selesai": 0, "persen": 0}

    tasks = (
        LogbookTask.query.join(Competency)
        .filter(Competency.level_id == nurse.current_level_id, LogbookTask.aktif.is_(True))
        .all()
    )
    total = len(tasks)
    if total == 0:
        return {"total": 0, "selesai": 0, "persen": 0}

    selesai = 0
    for task in tasks:
        approved = LogbookProgress.query.filter_by(
            nurse_id=nurse.id, task_id=task.id, verification_status="disetujui"
        ).count()
        target = max(task.target or 1, 1)
        if approved >= target:
            selesai += 1

    persen = round((selesai / total) * 100, 1)
    return {"total": total, "selesai": selesai, "persen": persen}


@nurse_bp.route("/dashboard")
@login_required
def dashboard():
    if current_user.role == "perawat":
        nurse = current_user.nurse
        summary = hitung_progress_level(nurse)
        pending_request = None
        if nurse:
            pending_request = LevelRequest.query.filter_by(nurse_id=nurse.id, status="pending").first()
        return render_template("dashboard.html", nurse=nurse, summary=summary, pending_request=pending_request)

    from jobs import daftar_dokumen_perlu_perhatian
    from models import Nurse

    total_nurses = Nurse.query.count()
    active_nurses = Nurse.query.filter_by(status="active").count()
    pending_requests = LevelRequest.query.filter_by(status="pending").count()
    pending_verifikasi = LogbookProgress.query.filter_by(verification_status="belum_diperiksa").count()
    perlu_perhatian = daftar_dokumen_perlu_perhatian()
    return render_template(
        "dashboard.html",
        total_nurses=total_nurses,
        active_nurses=active_nurses,
        pending_requests=pending_requests,
        pending_verifikasi=pending_verifikasi,
        perlu_perhatian=perlu_perhatian,
    )


@nurse_bp.route("/profil")
@login_required
def profil():
    if current_user.role != "perawat" or not current_user.nurse:
        abort(403)
    return render_template("profil.html", nurse=current_user.nurse)


@nurse_bp.route("/profil/update", methods=["POST"])
@login_required
def update_profil():
    """Perawat hanya dapat mengunggah/mengganti foto profil. Data diri lain
    (nama, NIK, SIP, SPK/RKK, level) bersifat baca-saja -- hanya diisi saat
    registrasi dan hanya dapat diubah oleh admin lewat Kelola Perawat."""
    if current_user.role != "perawat" or not current_user.nurse:
        abort(403)

    nurse = current_user.nurse

    photo = request.files.get("foto_profile")
    if photo and photo.filename:
        if not allowed_photo(photo.filename, current_app.config["ALLOWED_PHOTO_EXT"]):
            flash("Format foto harus PNG, JPG, JPEG, atau WEBP.", "danger")
            return redirect(url_for("nurse.profil"))
        old_photo = nurse.foto_profile
        new_photo = simpan_foto_profile(
            photo,
            current_app.config["UPLOAD_FOLDER"],
            current_app.config["ALLOWED_PHOTO_EXT"],
            nurse.id,
        )
        if not new_photo:
            flash("Foto profil gagal diupload.", "danger")
            return redirect(url_for("nurse.profil"))
        nurse.foto_profile = new_photo
        hapus_foto_profile(old_photo, current_app.config["UPLOAD_FOLDER"])
        db.session.commit()
        flash("Foto profil berhasil diperbarui.", "success")
    else:
        flash("Pilih foto terlebih dahulu.", "warning")

    return redirect(url_for("nurse.profil"))
