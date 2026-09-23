-- Migration: tambah tabel `departments` dan kolom `department_id` pada `nurses`.
-- Jalankan file ini pada database `nursing_career` (lewat phpMyAdmin/MySQL client),
-- sama seperti migration_foto_profile.sql / migration_expiry_dates.sql.

CREATE TABLE IF NOT EXISTS departments (
    id INT AUTO_INCREMENT PRIMARY KEY,
    nama_departemen VARCHAR(50) NOT NULL,
    urutan INT NOT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

INSERT INTO departments (nama_departemen, urutan) VALUES
    ('Rawat Inap', 1),
    ('Rawat Jalan', 2),
    ('Emergency', 3),
    ('ICU', 4),
    ('Perina - NICU', 5),
    ('Maternity', 6),
    ('Anastesi', 7),
    ('Bedah', 8);

ALTER TABLE nurses
    ADD COLUMN department_id INT NULL AFTER current_level_id,
    ADD CONSTRAINT fk_nurses_department
        FOREIGN KEY (department_id) REFERENCES departments(id);
