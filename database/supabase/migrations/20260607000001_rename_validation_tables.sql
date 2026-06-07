-- Rename validation_jobs → validation_sessions
-- Rename validation_job_items → validation_results
--
-- "Session" lebih netral dan general daripada "job" (istilah teknis queue).
-- "Results" mendeskripsikan isi tabel secara semantik (setiap baris = satu hasil validasi dokumen).
-- session_id di validation_results bersifat nullable agar ke depan bisa dipakai
-- untuk menyimpan hasil validasi dokumen tunggal tanpa perlu session.

-- Hapus tabel lama (tidak ada data produksi)
drop table if exists validation_job_items;
drop table if exists validation_jobs;

-- ── validation_sessions ────────────────────────────────────────────────────────
-- Satu baris per sesi validasi (bulk upload).
-- Menyimpan status keseluruhan sesi dan jumlah dokumen yang diproses.
create table if not exists validation_sessions (
  id              uuid        primary key default gen_random_uuid(),
  type            text        not null default 'bulk'
                              check (type in ('single', 'bulk')),
  status          text        not null default 'pending'
                              check (status in ('pending', 'processing', 'completed', 'failed')),
  total_items     integer     not null default 0,
  completed_items integer     not null default 0,
  created_at      timestamptz not null default now(),
  updated_at      timestamptz not null default now()
);

-- ── validation_results ─────────────────────────────────────────────────────────
-- Satu baris per dokumen yang divalidasi.
-- session_id nullable: NULL untuk validasi tunggal, diisi untuk validasi bulk.
create table if not exists validation_results (
  id             uuid        primary key default gen_random_uuid(),
  session_id     uuid        references validation_sessions(id) on delete cascade,
  position       integer     not null default 0,
  file_name      text        not null,
  schema_id      text        not null,
  tahun          text        not null,
  status         text        not null default 'pending'
                             check (status in ('pending', 'processing', 'completed', 'failed')),
  result         jsonb,
  error_message  text,
  created_at     timestamptz not null default now(),
  updated_at     timestamptz not null default now()
);

create index if not exists idx_vr_session_id       on validation_results(session_id);
create index if not exists idx_vr_session_position on validation_results(session_id, position);
