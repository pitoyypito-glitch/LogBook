-- Migration: tabel audit log aksi admin (tambah/edit/hapus perawat, dll).
-- Jalankan lewat phpMyAdmin/MySQL pada database `nursing_career`.
-- Aman dijalankan berkali-kali (pakai CREATE TABLE IF NOT EXISTS).

CREATE TABLE IF NOT EXISTS admin_activity_logs (
    id INT AUTO_INCREMENT PRIMARY KEY,
    admin_user_id INT NULL,
    admin_username VARCHAR(50) NOT NULL,
    aksi VARCHAR(50) NOT NULL,
    target_type VARCHAR(50) NULL,
    target_id INT NULL,
    target_label VARCHAR(150) NULL,
    keterangan VARCHAR(255) NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_admin_activity_logs_user
        FOREIGN KEY (admin_user_id) REFERENCES users(id)
        ON DELETE SET NULL,
    INDEX idx_admin_activity_logs_created_at (created_at),
    INDEX idx_admin_activity_logs_admin_user (admin_user_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
