-- Migration: tambah kolom tanggal kedaluwarsa SIP & SPK/RKK pada tabel nurses.
--
-- SIP (Surat Izin Praktik) berlaku 5 tahun sejak terbit.
-- SPK/RKK (Surat Penugasan Klinis / Rincian Kewenangan Klinis) berlaku 3 tahun sejak terbit.
--
-- Jalankan file ini SEKALI lewat phpMyAdmin/MySQL client pada database
-- `nursing_career`, sama seperti migration_foto_profile.sql sebelumnya.
--
-- Setelah kolom ini terisi, sistem akan:
--   1. Menampilkan badge peringatan (H-90 kuning, H-30 merah) di dashboard
--      admin & dashboard perawat yang bersangkutan.
--   2. Menonaktifkan otomatis akun perawat (nurses.status & users.status
--      menjadi 'inactive') begitu salah satu tanggal kedaluwarsa terlewati.
--      Lihat job harian di jobs.py yang dijalankan oleh APScheduler (app.py)
--      atau lewat perintah `flask cek-kedaluwarsa`.

ALTER TABLE nurses
  ADD COLUMN sip_expiry DATE NULL COMMENT 'Tanggal kedaluwarsa SIP (masa berlaku 5 tahun)' AFTER sip,
  ADD COLUMN spk_rkk_expiry DATE NULL COMMENT 'Tanggal kedaluwarsa SPK/RKK (masa berlaku 3 tahun)' AFTER spk_rkk;

-- Opsional: jika Anda sudah tahu tanggal terbit SIP/SPK-RKK setiap perawat,
-- isi langsung tanggal kedaluwarsanya, misalnya:
-- UPDATE nurses SET sip_expiry = '2029-03-14' WHERE id = 1;
-- UPDATE nurses SET spk_rkk_expiry = '2027-03-14' WHERE id = 1;
