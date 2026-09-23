-- Migrasi untuk fitur registrasi mandiri & lupa password.
-- Jalankan pada database `nursing_career` melalui phpMyAdmin/MySQL client,
-- sama seperti migration_foto_profile.sql dan migration_task_header.sql.
--
-- Catatan:
-- 1. Registrasi mandiri TIDAK memerlukan tabel baru. User yang mendaftar
--    sendiri lewat form regist akan langsung dibuatkan baris di `users`
--    dan `nurses` dengan status = 'inactive' (menunggu diaktifkan admin
--    lewat halaman Kelola Perawat, tombol "Aktifkan" yang sudah ada).
-- 2. Fitur "Lupa Password" memerlukan tabel baru di bawah ini untuk
--    menyimpan pengajuan user ke admin.

CREATE TABLE IF NOT EXISTS password_reset_requests (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    alasan VARCHAR(255) NULL,
    status ENUM('pending', 'selesai', 'ditolak') NOT NULL DEFAULT 'pending',
    submitted_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    reviewed_by INT NULL,
    reviewed_at TIMESTAMP NULL,
    catatan TEXT NULL,
    CONSTRAINT fk_prr_user FOREIGN KEY (user_id) REFERENCES users(id),
    CONSTRAINT fk_prr_reviewer FOREIGN KEY (reviewed_by) REFERENCES users(id)
);
