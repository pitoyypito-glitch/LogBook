-- Migrasi: dukungan baris "header" pada logbook_tasks (mis. id 83
-- "Melakukan edukasi tentang:" yang punya 6 sub-poin id 84-89 di bawahnya).
-- Jalankan query ini di phpMyAdmin (atau client MySQL lain) pada
-- database `nursing_career` SEBELUM menjalankan aplikasi versi terbaru.
--
-- Catatan: jika kolom ini sudah pernah dibuat manual sebelumnya, migrasi
-- ini boleh dilewati / dijalankan ulang dengan IF NOT EXISTS sesuai versi
-- MySQL/MariaDB yang dipakai.

ALTER TABLE logbook_tasks
  ADD COLUMN parent_task_id INT(11) DEFAULT NULL AFTER competency_id,
  ADD COLUMN is_header TINYINT(1) NOT NULL DEFAULT 0 AFTER aktif;

ALTER TABLE logbook_tasks
  ADD CONSTRAINT fk_logbook_tasks_parent
  FOREIGN KEY (parent_task_id) REFERENCES logbook_tasks(id);

-- Tandai id 83 sebagai header, dan kaitkan sub-poin 84-89 ke id 83.
UPDATE logbook_tasks SET is_header = 1 WHERE id = 83;
UPDATE logbook_tasks SET parent_task_id = 83 WHERE id IN (84, 85, 86, 87, 88, 89);
