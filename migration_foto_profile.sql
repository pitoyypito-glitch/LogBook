-- Migrasi: tambah kolom foto_profile ke tabel nurses
-- Jalankan query ini di phpMyAdmin (atau client MySQL lain) pada
-- database `nursing_career` SEBELUM menjalankan aplikasi versi terbaru.

ALTER TABLE nurses
  ADD COLUMN foto_profile VARCHAR(255) NULL AFTER spk_rkk;
