from datetime import date, datetime

from flask import Blueprint, abort, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from extensions import db
from models import Competency, LogbookProgress, LogbookTask

logbook_bp = Blueprint("logbook", __name__, url_prefix="/logbook")


def task_milik_level(task, level_id):
    return bool(task.competency and task.competency.level_id == level_id and task.aktif)


@logbook_bp.route("/")
@login_required
def index():
    if current_user.role == "perawat":
        nurse = current_user.nurse
        if not nurse or not nurse.current_level_id:
            flash("Profil perawat atau level belum diatur oleh admin.", "warning")
            return render_template("logbook/list.html", competencies=[])

        competencies = Competency.query.filter_by(level_id=nurse.current_level_id).order_by(Competency.urutan).all()
        progress_map = {}
        for comp in competencies:
            for task in comp.tasks:
                if task.is_header:
                    # Baris header tidak diisi manual -- statusnya dihitung
                    # belakangan dari sub-poin (children), lihat di bawah.
                    continue
                entries = LogbookProgress.query.filter_by(nurse_id=nurse.id, task_id=task.id).order_by(LogbookProgress.percobaan_ke).all()
                approved = sum(e.verification_status == "disetujui" for e in entries)
                progress_map[task.id] = {"entries": entries, "approved": approved}

        # Status header = selesai hanya jika SEMUA sub-poin (children) sudah
        # mencapai target masing-masing. Dihitung dari progress_map yang
        # sudah ada di atas, tanpa perlu row LogbookProgress untuk header itu sendiri.
        for comp in competencies:
            for task in comp.tasks:
                if not task.is_header:
                    continue
                children = task.children
                total = len(children)
                selesai = 0
                for child in children:
                    info = progress_map.get(child.id)
                    if info and child.target and info["approved"] >= child.target:
                        selesai += 1
                progress_map[task.id] = {
                    "entries": [],
                    "approved": selesai,
                    "is_header_summary": True,
                    "total_children": total,
                    "children_selesai": selesai,
                }
        return render_template("logbook/list.html", competencies=competencies, nurse=nurse, progress_map=progress_map)

    pending = (
        LogbookProgress.query.filter_by(verification_status="belum_diperiksa")
        .join(LogbookTask).order_by(LogbookProgress.created_at).all()
    )
    return render_template("logbook/list.html", pending=pending, is_reviewer=True)


@logbook_bp.route("/task/<int:task_id>", methods=["GET", "POST"])
@login_required
def task_detail(task_id):
    task = LogbookTask.query.get_or_404(task_id)

    if task.is_header:
        # Baris header (mis. id 83) tidak punya progress sendiri -- statusnya
        # turunan dari sub-poin (children). Tidak boleh diakses sebagai task
        # biasa untuk diisi/verifikasi.
        abort(404)

    if current_user.role == "perawat":
        nurse = current_user.nurse
        if not nurse or nurse.status != "active" or not task_milik_level(task, nurse.current_level_id):
            abort(403)

        if request.method == "POST":
            target = max(task.target or 1, 1)
            approved_count = LogbookProgress.query.filter_by(
                nurse_id=nurse.id, task_id=task.id, verification_status="disetujui"
            ).count()
            if approved_count >= target:
                flash("Target keterampilan ini sudah terpenuhi.", "warning")
                return redirect(url_for("logbook.task_detail", task_id=task.id))

            pending = LogbookProgress.query.filter_by(
                nurse_id=nurse.id, task_id=task.id, verification_status="belum_diperiksa"
            ).first()
            if pending:
                flash("Masih ada pencapaian yang menunggu verifikasi.", "warning")
                return redirect(url_for("logbook.task_detail", task_id=task.id))

            last_entry = LogbookProgress.query.filter_by(nurse_id=nurse.id, task_id=task.id).order_by(LogbookProgress.percobaan_ke.desc()).first()
            percobaan_ke = (last_entry.percobaan_ke + 1) if last_entry else 1
            status_o = "status_o" in request.form
            status_spv = "status_spv" in request.form
            status_m = "status_m" in request.form
            if not (status_o or status_spv or status_m):
                flash("Pilih minimal satu pencapaian: O, SPV, atau M.", "warning")
                return redirect(url_for("logbook.task_detail", task_id=task.id))

            db.session.add(LogbookProgress(
                nurse_id=nurse.id, task_id=task.id, percobaan_ke=percobaan_ke,
                status_o=status_o, status_spv=status_spv, status_m=status_m,
                tanggal_o=date.today() if status_o else None,
                tanggal_spv=date.today() if status_spv else None,
                tanggal_m=date.today() if status_m else None,
                catatan=request.form.get("catatan", "").strip() or None,
            ))
            db.session.commit()
            flash(f"Pencapaian ke-{percobaan_ke} berhasil disimpan dan menunggu verifikasi.", "success")
            return redirect(url_for("logbook.task_detail", task_id=task.id))

        entries = LogbookProgress.query.filter_by(nurse_id=nurse.id, task_id=task.id).order_by(LogbookProgress.percobaan_ke).all()
        return render_template("logbook/detail.html", task=task, entries=entries)

    nurse_id = request.args.get("nurse_id", type=int)
    query = LogbookProgress.query.filter_by(task_id=task.id)
    if nurse_id:
        query = query.filter_by(nurse_id=nurse_id)
    entries = query.order_by(LogbookProgress.created_at).all()
    return render_template("logbook/detail.html", task=task, entries=entries, is_reviewer=True)


@logbook_bp.route("/progress/<int:progress_id>/verify", methods=["POST"])
@login_required
def verify_progress(progress_id):
    if current_user.role not in ("supervisor", "admin"):
        abort(403)
    entry = LogbookProgress.query.get_or_404(progress_id)
    if entry.verification_status != "belum_diperiksa":
        flash("Pencapaian ini sudah diverifikasi.", "warning")
        return redirect(request.referrer or url_for("logbook.index"))

    action = request.form.get("action")
    if action == "approve":
        entry.verification_status = "disetujui"
    elif action == "reject":
        entry.verification_status = "ditolak"
    else:
        abort(400)

    entry.verifier_id = current_user.id
    entry.verified_at = datetime.utcnow()
    catatan = request.form.get("catatan", "").strip()
    if catatan:
        entry.catatan = catatan
    db.session.commit()
    flash("Verifikasi berhasil disimpan.", "success")
    return redirect(request.referrer or url_for("logbook.index"))
