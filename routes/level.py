from datetime import datetime

from flask import Blueprint, abort, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from extensions import db
from models import Competency, Level, LevelRequest, LogbookProgress, LogbookTask

level_bp = Blueprint("level", __name__, url_prefix="/level")


def cek_eligibility(nurse):
    """Eligible jika setiap keterampilan aktif mencapai target approval."""
    if not nurse or not nurse.current_level_id:
        return False, 0, 0

    tasks = (
        LogbookTask.query.join(Competency)
        .filter(Competency.level_id == nurse.current_level_id, LogbookTask.aktif.is_(True))
        .all()
    )
    total = len(tasks)
    if total == 0:
        return False, 0, 0

    selesai = 0
    for task in tasks:
        approved = LogbookProgress.query.filter_by(
            nurse_id=nurse.id, task_id=task.id, verification_status="disetujui"
        ).count()
        if approved >= max(task.target or 1, 1):
            selesai += 1

    return selesai == total, selesai, total


@level_bp.route("/")
@login_required
def index():
    if current_user.role == "perawat":
        nurse = current_user.nurse
        eligible, selesai, total = cek_eligibility(nurse)
        riwayat = (
            LevelRequest.query.filter_by(nurse_id=nurse.id)
            .order_by(LevelRequest.submitted_at.desc()).all() if nurse else []
        )
        next_level = None
        if nurse and nurse.level:
            next_level = Level.query.filter_by(urutan=nurse.level.urutan + 1).first()
        return render_template(
            "level/request.html", nurse=nurse, eligible=eligible, selesai=selesai,
            total=total, riwayat=riwayat, next_level=next_level,
        )

    requests_ = LevelRequest.query.filter_by(status="pending").order_by(LevelRequest.submitted_at).all()
    return render_template("level/request.html", requests=requests_, is_reviewer=True)


@level_bp.route("/ajukan", methods=["POST"])
@login_required
def ajukan():
    if current_user.role != "perawat":
        abort(403)
    nurse = current_user.nurse
    if not nurse or nurse.status != "active":
        flash("Akun perawat tidak aktif atau profil belum tersedia.", "danger")
        return redirect(url_for("level.index"))

    eligible, _, _ = cek_eligibility(nurse)
    if not eligible:
        flash("Logbook level saat ini belum memenuhi target 100%.", "danger")
        return redirect(url_for("level.index"))

    if LevelRequest.query.filter_by(nurse_id=nurse.id, status="pending").first():
        flash("Sudah ada pengajuan yang masih menunggu review.", "warning")
        return redirect(url_for("level.index"))

    next_level = Level.query.filter_by(urutan=nurse.level.urutan + 1).first()
    if not next_level:
        flash("Perawat sudah berada di level tertinggi.", "info")
        return redirect(url_for("level.index"))

    db.session.add(LevelRequest(
        nurse_id=nurse.id, from_level_id=nurse.current_level_id,
        to_level_id=next_level.id, status="pending"
    ))
    db.session.commit()
    flash("Pengajuan kenaikan level berhasil dikirim.", "success")
    return redirect(url_for("level.index"))


@level_bp.route("/review/<int:request_id>", methods=["POST"])
@login_required
def review(request_id):
    if current_user.role not in ("supervisor", "admin"):
        abort(403)

    req = LevelRequest.query.get_or_404(request_id)
    if req.status != "pending":
        flash("Pengajuan ini sudah diproses sebelumnya.", "warning")
        return redirect(url_for("level.index"))

    action = request.form.get("action")
    catatan = request.form.get("catatan", "").strip() or None

    if action == "approve":
        # Validasi ulang sebelum menaikkan level.
        eligible, _, _ = cek_eligibility(req.nurse)
        if req.nurse.current_level_id != req.from_level_id or not eligible:
            req.status = "rejected"
            req.catatan = catatan or "Pengajuan tidak memenuhi validasi ulang progress level."
            req.reviewed_by = current_user.id
            req.reviewed_at = datetime.utcnow()
            db.session.commit()
            flash("Pengajuan tidak dapat disetujui karena progress/level berubah.", "danger")
            return redirect(url_for("level.index"))
        req.status = "approved"
        req.nurse.current_level_id = req.to_level_id
    elif action == "reject":
        req.status = "rejected"
    else:
        abort(400)

    req.reviewed_by = current_user.id
    req.reviewed_at = datetime.utcnow()
    req.catatan = catatan
    db.session.commit()
    flash("Keputusan review berhasil disimpan.", "success")
    return redirect(url_for("level.index"))
