-- Tabel untuk melacak status batch validasi dokumen (bulk upload).
-- Setiap submit "Validasi Semua" membuat satu baris di validation_jobs,
-- dan satu baris per dokumen di validation_job_items.

create table if not exists validation_jobs (
  id               uuid        primary key default gen_random_uuid(),
  status           text        not null default 'pending'
                               check (status in ('pending', 'processing', 'completed', 'failed')),
  total_items      integer     not null default 0,
  completed_items  integer     not null default 0,
  created_at       timestamptz not null default now(),
  updated_at       timestamptz not null default now()
);

create table if not exists validation_job_items (
  id             uuid        primary key default gen_random_uuid(),
  job_id         uuid        not null references validation_jobs(id) on delete cascade,
  position       integer     not null,
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

create index if not exists idx_vji_job_id       on validation_job_items(job_id);
create index if not exists idx_vji_job_position on validation_job_items(job_id, position);
