-- Migration: NIK menggantikan Username sebagai identitas login perawat.
-- Jalankan SETELAH migration_departemen.sql, pada database `nursing_career`.
--
-- Catatan penting:
-- Kolom `users.username` TETAP DIPAKAI di database (tidak dihapus) karena
-- akun admin/supervisor masih login dengan username biasa. Untuk akun
-- PERAWAT, aplikasi sekarang otomatis mengisi `users.username` dengan nilai
-- NIK perawat tersebut -- jadi login perawat cukup pakai NIK & password,
-- tanpa perlu username terpisah.
--
-- Password default akun perawat baru (baik daftar mandiri maupun dibuat
-- admin) adalah: Eka123!

-- 1) Sinkronkan data lama: isi users.username = nik untuk akun perawat yang
--    sudah ada, supaya bisa langsung login pakai NIK setelah update ini.
--    (Lewati baris yang NIK-nya kosong atau sudah dipakai user lain, agar
--    tidak melanggar constraint UNIQUE pada users.username.)
UPDATE nurses n
JOIN users u ON u.id = n.user_id
SET u.username = n.nik
WHERE n.nik IS NOT NULL
  AND n.nik <> ''
  AND NOT EXISTS (
    SELECT 1 FROM users u2
    WHERE u2.username = n.nik AND u2.id <> u.id
  );

-- 2) (Opsional tapi disarankan) pastikan kolom nik tidak boleh kosong ke
--    depannya, karena sekarang menjadi identitas login perawat.
ALTER TABLE nurses
    MODIFY COLUMN nik VARCHAR(30) NOT NULL;
