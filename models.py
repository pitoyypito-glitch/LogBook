"""
Model SQLAlchemy yang mapping langsung ke tabel-tabel di database.sql
(database: nursing_career). Tabel sudah dibuat lewat import database.sql,
jadi model di sini HANYA mendefinisikan mapping -- tidak perlu db.create_all()
kecuali Anda belum meng-import database.sql sama sekali.
"""

from datetime import date, datetime

from flask_login import UserMixin
from werkzeug.security import check_password_hash, generate_password_hash

from extensions import db


class User(db.Model, UserMixin):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.Enum("perawat", "supervisor", "admin", name="role_enum"), nullable=False)
    status = db.Column(db.Enum("active", "inactive", name="user_status_enum"), nullable=False, default="active")
    created_at = db.Column(db.TIMESTAMP, server_default=db.func.now())

    nurse = db.relationship("Nurse", backref="user", uselist=False, foreign_keys="Nurse.user_id")

    def set_password(self, password: str) -> None:
        self.password_hash = generate_password_hash(password)

    def check_password(self, password: str) -> bool:
        return check_password_hash(self.password_hash, password)

    def __repr__(self):
        return f"<User {self.username} ({self.role})>"


class AdminActivityLog(db.Model):
    """Jejak audit aksi admin (tambah/edit/hapus/nonaktifkan perawat, reset
    password, dll). Tabel dibuat lewat migration_admin_activity_log.sql.

    Dengan lebih dari satu admin yang memegang kontrol, log ini penting
    supaya setiap perubahan/penghapusan data bisa ditelusuri siapa
    pelakunya dan kapan.
    """

    __tablename__ = "admin_activity_logs"

    id = db.Column(db.Integer, primary_key=True)
    admin_user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)
    admin_username = db.Column(db.String(50), nullable=False)
    aksi = db.Column(db.String(50), nullable=False)  # mis. "hapus_perawat"
    target_type = db.Column(db.String(50), nullable=True)  # mis. "nurse"
    target_id = db.Column(db.Integer, nullable=True)
    target_label = db.Column(db.String(150), nullable=True)  # mis. nama perawat
    keterangan = db.Column(db.String(255), nullable=True)
    created_at = db.Column(db.TIMESTAMP, server_default=db.func.now())

    admin_user = db.relationship("User", foreign_keys=[admin_user_id])

    def __repr__(self):
        return f"<AdminActivityLog {self.aksi} oleh {self.admin_username}>"


def catat_aktivitas_admin(aksi, target_type=None, target_id=None, target_label=None, keterangan=None):
    """Helper untuk mencatat satu baris audit log aksi admin yang sedang
    login (current_user). Dipanggil dari routes/admin.py setelah aksi
    berhasil dilakukan, sebelum db.session.commit() -- masuk dalam
    transaksi yang sama.
    """
    from flask_login import current_user

    log = AdminActivityLog(
        admin_user_id=getattr(current_user, "id", None),
        admin_username=getattr(current_user, "username", "?"),
        aksi=aksi,
        target_type=target_type,
        target_id=target_id,
        target_label=target_label,
        keterangan=keterangan,
    )
    db.session.add(log)


class Level(db.Model):
    __tablename__ = "levels"

    id = db.Column(db.Integer, primary_key=True)
    nama_level = db.Column(db.String(50), nullable=False)
    urutan = db.Column(db.Integer, nullable=False)
    deskripsi = db.Column(db.String(255))

    competencies = db.relationship("Competency", backref="level", order_by="Competency.urutan")

    def __repr__(self):
        return f"<Level {self.nama_level}>"


class Department(db.Model):
    __tablename__ = "departments"

    id = db.Column(db.Integer, primary_key=True)
    nama_departemen = db.Column(db.String(50), nullable=False)
    urutan = db.Column(db.Integer, nullable=False)

    def __repr__(self):
        return f"<Department {self.nama_departemen}>"


class Nurse(db.Model):
    __tablename__ = "nurses"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    nama = db.Column(db.String(150), nullable=False)
    nik = db.Column(db.String(30))
    # Nama kolom di DB adalah "str", memakai atribut python str_ agar tidak
    # menimpa builtin str().
    str_ = db.Column("str", db.String(50))
    sip = db.Column(db.String(50))
    sip_expiry = db.Column(db.Date)  # SIP berlaku 5 tahun sejak terbit
    spk_rkk = db.Column(db.String(50))
    spk_rkk_expiry = db.Column(db.Date)  # SPK/RKK berlaku 3 tahun sejak terbit
    foto_profile = db.Column(db.String(255))
    current_level_id = db.Column(db.Integer, db.ForeignKey("levels.id"))
    department_id = db.Column(db.Integer, db.ForeignKey("departments.id"))
    status = db.Column(db.Enum("active", "inactive", name="nurse_status_enum"), nullable=False, default="active")
    created_at = db.Column(db.TIMESTAMP, server_default=db.func.now())

    level = db.relationship("Level", foreign_keys=[current_level_id])
    department = db.relationship("Department", foreign_keys=[department_id])
    progress_entries = db.relationship("LogbookProgress", backref="nurse", foreign_keys="LogbookProgress.nurse_id")
    level_requests = db.relationship("LevelRequest", backref="nurse", foreign_keys="LevelRequest.nurse_id")

    # Ambang batas (hari) untuk kategori peringatan kedaluwarsa dokumen.
    PERINGATAN_H = 90   # <=90 hari lagi -> "warning" (kuning)
    KRITIS_H = 30       # <=30 hari lagi -> "critical" (merah, belum expired)

    @staticmethod
    def _status_kedaluwarsa(tanggal_expiry):
        """Hitung status & sisa hari suatu tanggal kedaluwarsa (SIP/SPK-RKK).

        Return None jika tanggal belum diisi, atau dict:
        {"days_left": int, "level": "ok"|"warning"|"critical"|"expired"}
        """
        if not tanggal_expiry:
            return None
        days_left = (tanggal_expiry - date.today()).days
        if days_left < 0:
            level = "expired"
        elif days_left <= Nurse.KRITIS_H:
            level = "critical"
        elif days_left <= Nurse.PERINGATAN_H:
            level = "warning"
        else:
            level = "ok"
        return {"days_left": days_left, "level": level}

    @property
    def sip_status(self):
        return self._status_kedaluwarsa(self.sip_expiry)

    @property
    def spk_rkk_status(self):
        return self._status_kedaluwarsa(self.spk_rkk_expiry)

    @property
    def dokumen_kedaluwarsa(self):
        """True jika SIP atau SPK/RKK sudah lewat tanggal berlakunya."""
        today = date.today()
        if self.sip_expiry and self.sip_expiry < today:
            return True
        if self.spk_rkk_expiry and self.spk_rkk_expiry < today:
            return True
        return False

    def __repr__(self):
        return f"<Nurse {self.nama}>"


class Competency(db.Model):
    __tablename__ = "competencies"

    id = db.Column(db.Integer, primary_key=True)
    level_id = db.Column(db.Integer, db.ForeignKey("levels.id"), nullable=False)
    nama_kompetensi = db.Column(db.String(500), nullable=False)
    urutan = db.Column(db.Integer, nullable=False)

    tasks = db.relationship("LogbookTask", backref="competency", order_by="LogbookTask.nomor")

    def __repr__(self):
        return f"<Competency {self.nama_kompetensi[:40]}>"


class LogbookTask(db.Model):
    __tablename__ = "logbook_tasks"

    id = db.Column(db.Integer, primary_key=True)
    competency_id = db.Column(db.Integer, db.ForeignKey("competencies.id"), nullable=False)
    nomor = db.Column(db.Integer)
    nama_keterampilan = db.Column(db.Text, nullable=False)
    target = db.Column(db.Integer)
    satuan = db.Column(db.String(10))
    aktif = db.Column(db.Boolean, nullable=False, default=True)

    # parent_task_id: diisi pada sub-poin (mis. id 84-89) yang menunjuk ke
    # baris header-nya (mis. id 83 "Melakukan edukasi tentang:").
    # is_header: True untuk baris header itu sendiri -- baris ini tidak
    # pernah diisi manual oleh perawat (tidak ada LogbookProgress untuknya),
    # statusnya "selesai" dihitung dari status semua sub-poin turunannya.
    parent_task_id = db.Column(db.Integer, db.ForeignKey("logbook_tasks.id"))
    is_header = db.Column(db.Boolean, nullable=False, default=False)

    children = db.relationship(
        "LogbookTask",
        backref=db.backref("parent_task", remote_side=[id]),
        foreign_keys=[parent_task_id],
        order_by="LogbookTask.nomor",
    )

    def __repr__(self):
        return f"<LogbookTask {self.nama_keterampilan[:40]}>"


class LogbookProgress(db.Model):
    __tablename__ = "logbook_progress"
    __table_args__ = (
        db.UniqueConstraint("nurse_id", "task_id", "percobaan_ke", name="uq_progress_attempt"),
    )

    id = db.Column(db.Integer, primary_key=True)
    nurse_id = db.Column(db.Integer, db.ForeignKey("nurses.id"), nullable=False)
    task_id = db.Column(db.Integer, db.ForeignKey("logbook_tasks.id"), nullable=False)
    percobaan_ke = db.Column(db.Integer, nullable=False, default=1)

    status_o = db.Column(db.Boolean, nullable=False, default=False)
    status_spv = db.Column(db.Boolean, nullable=False, default=False)
    status_m = db.Column(db.Boolean, nullable=False, default=False)

    tanggal_o = db.Column(db.Date)
    tanggal_spv = db.Column(db.Date)
    tanggal_m = db.Column(db.Date)

    verifier_id = db.Column(db.Integer, db.ForeignKey("users.id"))
    catatan = db.Column(db.Text)

    verification_status = db.Column(
        db.Enum("belum_diperiksa", "disetujui", "ditolak", name="verification_status_enum"),
        nullable=False,
        default="belum_diperiksa",
    )
    verified_at = db.Column(db.TIMESTAMP)
    created_at = db.Column(db.TIMESTAMP, server_default=db.func.now())

    task = db.relationship("LogbookTask")
    verifier = db.relationship("User", foreign_keys=[verifier_id])

    def __repr__(self):
        return f"<LogbookProgress nurse={self.nurse_id} task={self.task_id} #{self.percobaan_ke}>"


class LevelRequest(db.Model):
    __tablename__ = "level_requests"

    id = db.Column(db.Integer, primary_key=True)
    nurse_id = db.Column(db.Integer, db.ForeignKey("nurses.id"), nullable=False)
    from_level_id = db.Column(db.Integer, db.ForeignKey("levels.id"), nullable=False)
    to_level_id = db.Column(db.Integer, db.ForeignKey("levels.id"), nullable=False)
    status = db.Column(
        db.Enum("pending", "approved", "rejected", name="level_request_status_enum"),
        nullable=False,
        default="pending",
    )
    submitted_at = db.Column(db.TIMESTAMP, server_default=db.func.now())
    reviewed_by = db.Column(db.Integer, db.ForeignKey("users.id"))
    reviewed_at = db.Column(db.TIMESTAMP)
    catatan = db.Column(db.Text)

    from_level = db.relationship("Level", foreign_keys=[from_level_id])
    to_level = db.relationship("Level", foreign_keys=[to_level_id])
    reviewer = db.relationship("User", foreign_keys=[reviewed_by])

    def __repr__(self):
        return f"<LevelRequest nurse={self.nurse_id} {self.from_level_id}->{self.to_level_id} {self.status}>"


class PasswordResetRequest(db.Model):
    """Pengajuan lupa password dari user (dikirim lewat form regist/lupa password).

    Admin meninjau pengajuan ini dan, jika disetujui, memasukkan password
    baru untuk akun terkait secara langsung (bukan self-service ganti
    password oleh user).
    """

    __tablename__ = "password_reset_requests"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    alasan = db.Column(db.String(255))
    status = db.Column(
        db.Enum("pending", "selesai", "ditolak", name="password_reset_status_enum"),
        nullable=False,
        default="pending",
    )
    submitted_at = db.Column(db.TIMESTAMP, server_default=db.func.now())
    reviewed_by = db.Column(db.Integer, db.ForeignKey("users.id"))
    reviewed_at = db.Column(db.TIMESTAMP)
    catatan = db.Column(db.Text)

    user = db.relationship("User", foreign_keys=[user_id])
    reviewer = db.relationship("User", foreign_keys=[reviewed_by])

    def __repr__(self):
        return f"<PasswordResetRequest user={self.user_id} {self.status}>"


"""
Tambahan model SQLAlchemy untuk modul Logbook OJT & PraPK.

Cara pakai:
1. Jalankan ojt_prapk_migration.sql pada database `nursing_career` terlebih
   dahulu (lewat phpMyAdmin/MySQL client), sama seperti migration_foto_profile.sql.
2. Tempelkan seluruh isi file ini ke bagian BAWAH models.py yang sudah ada
   (setelah class LevelRequest). Tidak perlu import tambahan karena `db`,
   `datetime`, dsb. sudah di-import di bagian atas models.py.

Catatan desain:
- OJT dan PraPK memakai STRUKTUR TABEL YANG SAMA (sesuai permintaan), tabel
  ojt_units / ojt_categories / ojt_items dipakai bersama oleh kedua jenis
  program. Pembedanya ada di kolom `jenis` pada OjtPrapkEnrollment
  ('OJT' atau 'PRAPK').
- Satu baris di kolom "Tgl / Paraf Pembimbing" pada Excel = satu baris di
  OjtPrapkProgress (percobaan_ke berjalan 1..target, sama seperti pola
  LogbookProgress.percobaan_ke yang sudah dipakai di modul Level/Competency).
- "Selesai/tercapai" untuk satu item = jumlah baris OjtPrapkProgress untuk
  (enrollment_id, item_id) tersebut >= target milik OjtItem.
"""


class OjtUnit(db.Model):
    __tablename__ = "ojt_units"

    id = db.Column(db.Integer, primary_key=True)
    kode_unit = db.Column(db.String(30), unique=True, nullable=False)
    nama_unit = db.Column(db.String(150), nullable=False)
    keterangan = db.Column(db.String(255))

    categories = db.relationship("OjtCategory", backref="unit", order_by="OjtCategory.urutan")

    def __repr__(self):
        return f"<OjtUnit {self.kode_unit}>"


class OjtCategory(db.Model):
    __tablename__ = "ojt_categories"
    __table_args__ = (
        db.UniqueConstraint("unit_id", "kode_kategori", name="uq_unit_kode"),
    )

    id = db.Column(db.Integer, primary_key=True)
    unit_id = db.Column(db.Integer, db.ForeignKey("ojt_units.id"), nullable=False)
    kode_kategori = db.Column(db.String(5), nullable=False)  # A, B, C, ...
    nama_kategori = db.Column(db.String(255), nullable=False)
    urutan = db.Column(db.Integer, nullable=False)

    items = db.relationship("OjtItem", backref="category", order_by="OjtItem.urutan")

    def __repr__(self):
        return f"<OjtCategory {self.kode_kategori} {self.nama_kategori[:30]}>"


class OjtItem(db.Model):
    __tablename__ = "ojt_items"

    id = db.Column(db.Integer, primary_key=True)
    category_id = db.Column(db.Integer, db.ForeignKey("ojt_categories.id"), nullable=False)
    nomor = db.Column(db.Integer, nullable=False)
    nama_materi = db.Column(db.String(500), nullable=False)
    target = db.Column(db.Integer, nullable=False, default=1)
    urutan = db.Column(db.Integer, nullable=False)
    aktif = db.Column(db.Boolean, nullable=False, default=True)

    def __repr__(self):
        return f"<OjtItem {self.nama_materi[:40]}>"


class OjtPrapkEnrollment(db.Model):
    """Pendaftaran seorang perawat ke program OJT atau PraPK di suatu unit."""

    __tablename__ = "ojt_prapk_enrollments"

    id = db.Column(db.Integer, primary_key=True)
    nurse_id = db.Column(db.Integer, db.ForeignKey("nurses.id"), nullable=False)
    unit_id = db.Column(db.Integer, db.ForeignKey("ojt_units.id"), nullable=False)
    jenis = db.Column(db.Enum("OJT", "PRAPK", name="ojt_prapk_jenis_enum"), nullable=False)
    pembimbing_id = db.Column(db.Integer, db.ForeignKey("users.id"))
    tanggal_masuk_kerja = db.Column(db.Date)
    tanggal_mulai = db.Column(db.Date)
    tanggal_selesai = db.Column(db.Date)
    status = db.Column(
        db.Enum("berjalan", "selesai", "dibatalkan", name="ojt_prapk_status_enum"),
        nullable=False,
        default="berjalan",
    )
    catatan = db.Column(db.Text)
    created_at = db.Column(db.TIMESTAMP, server_default=db.func.now())

    nurse = db.relationship("Nurse", foreign_keys=[nurse_id])
    unit = db.relationship("OjtUnit", foreign_keys=[unit_id])
    pembimbing = db.relationship("User", foreign_keys=[pembimbing_id])
    progress_entries = db.relationship(
        "OjtPrapkProgress", backref="enrollment", foreign_keys="OjtPrapkProgress.enrollment_id"
    )

    def __repr__(self):
        return f"<OjtPrapkEnrollment nurse={self.nurse_id} unit={self.unit_id} {self.jenis}>"


class OjtPrapkProgress(db.Model):
    """Satu baris 'Tgl / Paraf Pembimbing' pada logbook (satu percobaan)."""

    __tablename__ = "ojt_prapk_progress"
    __table_args__ = (
        db.UniqueConstraint("enrollment_id", "item_id", "percobaan_ke", name="uq_progress_attempt"),
    )

    id = db.Column(db.Integer, primary_key=True)
    enrollment_id = db.Column(db.Integer, db.ForeignKey("ojt_prapk_enrollments.id"), nullable=False)
    item_id = db.Column(db.Integer, db.ForeignKey("ojt_items.id"), nullable=False)
    percobaan_ke = db.Column(db.Integer, nullable=False, default=1)
    tanggal = db.Column(db.Date, nullable=False)
    pembimbing_id = db.Column(db.Integer, db.ForeignKey("users.id"))
    catatan = db.Column(db.Text)
    created_at = db.Column(db.TIMESTAMP, server_default=db.func.now())

    item = db.relationship("OjtItem")
    pembimbing = db.relationship("User", foreign_keys=[pembimbing_id])

    def __repr__(self):
        return f"<OjtPrapkProgress enrollment={self.enrollment_id} item={self.item_id} #{self.percobaan_ke}>"
