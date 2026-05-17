-- Migration: Tambah unique constraint (skema, tahun) di tabel projects
-- Alasan: Satu skema hanya boleh satu per tahun. Admin tunggal + async queue memastikan tidak ada race condition.
-- Constraint ini sebagai fail-safe database-level untuk mencegah duplikat.

-- Tambah unique constraint
ALTER TABLE projects ADD CONSTRAINT projects_skema_tahun_key UNIQUE (skema, tahun);