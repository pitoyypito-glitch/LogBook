from datetime import date, datetime

from flask import Blueprint, abort, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from extensions import db
from models import Nurse, OjtCategory, OjtItem, OjtPrapkEnrollment, OjtPrapkProgress, OjtUnit, User

ojt_prapk_bp = Blueprint("ojt_prapk", __name__, url_prefix="/ojt-prapk")


def _parse_date(value):
    if not value:
        return None
    try:
        return datetime.strptime(value, "%Y-%m-%d").date()
    except ValueError:
        return None


@ojt_prapk_bp.route("/")
@login_required
def index():
    if current_user.role == "perawat":
        nurse = current_user.nurse
        enrollments = (
            OjtPrapkEnrollment.query.filter_by(nurse_id=nurse.id).order_by(OjtPrapkEnrollment.created_at.desc()).all()
            if nurse else []
        )
        return render_template("ojt_prapk/list.html", enrollments=enrollments)

    enrollments = OjtPrapkEnrollment.query.order_by(OjtPrapkEnrollment.created_at.desc()).all()
    units = OjtUnit.query.order_by(OjtUnit.nama_unit).all()
    nurses = Nurse.query.filter_by(status="active").order_by(Nurse.nama).all()
    pembimbing_options = User.query.filter(User.role.in_(("supervisor", "admin"))).order_by(User.username).all()
    return render_template(
        "ojt_prapk/list.html",
        enrollments=enrollments,
        is_reviewer=True,
        units=units,
        nurses=nurses,
        pembimbing_options=pembimbing_options,
    )


@ojt_prapk_bp.route("/enroll", methods=["POST"])
@login_required
def enroll():
    if current_user.role != "admin":
        abort(403)

    nurse_id = request.form.get("nurse_id", type=int)
    unit_id = request.form.get("unit_id", type=int)
    jenis = request.form.get("jenis")
    pembimbing_id = request.form.get("pembimbing_id", type=int)
    tanggal_masuk_kerja = _parse_date(request.form.get("tanggal_masuk_kerja"))
    tanggal_mulai = _parse_date(request.form.get("tanggal_mulai")) or date.today()

    if not (nurse_id and unit_id and jenis in ("OJT", "PRAPK")):
        flash("Perawat, unit, dan jenis program wajib diisi.", "warning")
        return redirect(url_for("ojt_prapk.index"))

    nurse = Nurse.query.get_or_404(nurse_id)
    unit = OjtUnit.query.get_or_404(unit_id)

    existing = OjtPrapkEnrollment.query.filter_by(
        nurse_id=nurse.id, unit_id=unit.id, jenis=jenis, status="berjalan"
    ).first()
    if existing:
        flash(f"{nurse.nama} sudah memiliki program {jenis} yang sedang berjalan di unit {unit.nama_unit}.", "warning")
        return redirect(url_for("ojt_prapk.index"))

    enrollment = OjtPrapkEnrollment(
        nurse_id=nurse.id,
        unit_id=unit.id,
        jenis=jenis,
        pembimbing_id=pembimbing_id or None,
        tanggal_masuk_kerja=tanggal_masuk_kerja,
        tanggal_mulai=tanggal_mulai,
        status="berjalan",
    )
    db.session.add(enrollment)
    db.session.commit()
    flash(f"Program {jenis} untuk {nurse.nama} di unit {unit.nama_unit} berhasil dibuat.", "success")
    return redirect(url_for("ojt_prapk.detail", enrollment_id=enrollment.id))


@ojt_prapk_bp.route("/enrollment/<int:enrollment_id>")
@login_required
def detail(enrollment_id):
    enrollment = OjtPrapkEnrollment.query.get_or_404(enrollment_id)

    if current_user.role == "perawat":
        nurse = current_user.nurse
        if not nurse or enrollment.nurse_id != nurse.id:
            abort(403)

    categories = (
        OjtCategory.query.filter_by(unit_id=enrollment.unit_id).order_by(OjtCategory.urutan).all()
    )
    progress_map = {}
    total_items = 0
    total_selesai = 0
    for cat in categories:
        for item in cat.items:
            entries = (
                OjtPrapkProgress.query.filter_by(enrollment_id=enrollment.id, item_id=item.id)
                .order_by(OjtPrapkProgress.percobaan_ke)
                .all()
            )
            progress_map[item.id] = entries
            total_items += 1
            if len(entries) >= (item.target or 1):
                total_selesai += 1

    can_input = current_user.role in ("supervisor", "admin")
    persen = round((total_selesai / total_items) * 100) if total_items else 0

    return render_template(
        "ojt_prapk/detail.html",
        enrollment=enrollment,
        categories=categories,
        progress_map=progress_map,
        can_input=can_input,
        total_items=total_items,
        total_selesai=total_selesai,
        persen=persen,
        today=date.today().isoformat(),
    )


@ojt_prapk_bp.route("/enrollment/<int:enrollment_id>/item/<int:item_id>/progress", methods=["POST"])
@login_required
def add_progress(enrollment_id, item_id):
    if current_user.role not in ("supervisor", "admin"):
        abort(403)

    enrollment = OjtPrapkEnrollment.query.get_or_404(enrollment_id)
    item = OjtItem.query.get_or_404(item_id)
    if item.category.unit_id != enrollment.unit_id:
        abort(400)

    if enrollment.status != "berjalan":
        flash("Program ini sudah tidak berjalan (selesai/dibatalkan).", "warning")
        return redirect(url_for("ojt_prapk.detail", enrollment_id=enrollment.id))

    count = OjtPrapkProgress.query.filter_by(enrollment_id=enrollment.id, item_id=item.id).count()
    target = item.target or 1
    if count >= target:
        flash("Target materi ini sudah tercapai.", "warning")
        return redirect(url_for("ojt_prapk.detail", enrollment_id=enrollment.id))

    tanggal = _parse_date(request.form.get("tanggal")) or date.today()
    catatan = request.form.get("catatan", "").strip() or None

    db.session.add(OjtPrapkProgress(
        enrollment_id=enrollment.id,
        item_id=item.id,
        percobaan_ke=count + 1,
        tanggal=tanggal,
        pembimbing_id=current_user.id,
        catatan=catatan,
    ))
    db.session.commit()
    flash(f"Paraf ke-{count + 1} untuk '{item.nama_materi}' berhasil disimpan.", "success")
    return redirect(url_for("ojt_prapk.detail", enrollment_id=enrollment.id))


@ojt_prapk_bp.route("/enrollment/<int:enrollment_id>/progress/<int:progress_id>/delete", methods=["POST"])
@login_required
def delete_progress(enrollment_id, progress_id):
    if current_user.role not in ("supervisor", "admin"):
        abort(403)
    entry = OjtPrapkProgress.query.get_or_404(progress_id)
    if entry.enrollment_id != enrollment_id:
        abort(400)
    db.session.delete(entry)
    db.session.commit()
    flash("Paraf dibatalkan.", "success")
    return redirect(url_for("ojt_prapk.detail", enrollment_id=enrollment_id))


@ojt_prapk_bp.route("/enrollment/<int:enrollment_id>/status", methods=["POST"])
@login_required
def update_status(enrollment_id):
    if current_user.role != "admin":
        abort(403)
    enrollment = OjtPrapkEnrollment.query.get_or_404(enrollment_id)
    status = request.form.get("status")
    if status not in ("berjalan", "selesai", "dibatalkan"):
        abort(400)
    enrollment.status = status
    if status == "selesai" and not enrollment.tanggal_selesai:
        enrollment.tanggal_selesai = date.today()
    db.session.commit()
    flash("Status program berhasil diperbarui.", "success")
    return redirect(url_for("ojt_prapk.detail", enrollment_id=enrollment.id))
