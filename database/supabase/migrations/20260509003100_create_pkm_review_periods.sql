create or replace function public.set_updated_at()
returns trigger
language plpgsql
as $$
begin
  new.updated_at = now();
  return new;
end;
$$;

create table public.pkm_review_periods (
  id uuid primary key default gen_random_uuid(),
  nama text not null,
  tanggal_mulai date not null,
  tanggal_selesai date not null,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  constraint pkm_review_periods_date_check check (tanggal_selesai >= tanggal_mulai)
);

comment on table public.pkm_review_periods is
  'Daftar periode review PKM yang dikelola admin dashboard.';

comment on column public.pkm_review_periods.nama is
  'Nama periode review yang ditampilkan pada menu admin.';

comment on column public.pkm_review_periods.tanggal_mulai is
  'Tanggal mulai periode review PKM.';

comment on column public.pkm_review_periods.tanggal_selesai is
  'Tanggal selesai periode review PKM.';

create trigger set_pkm_review_periods_updated_at
before update on public.pkm_review_periods
for each row
execute function public.set_updated_at();

alter table public.pkm_review_periods enable row level security;

create policy "authenticated users can read pkm review periods"
  on public.pkm_review_periods
  for select
  to authenticated
  using (true);

insert into public.pkm_review_periods (nama, tanggal_mulai, tanggal_selesai)
values
  ('Periode Review PKM 2026/I', date '2026-04-01', date '2026-07-31'),
  ('Periode Review PKM 2025/II', date '2025-08-01', date '2025-11-30'),
  ('Periode Review PKM 2025/I', date '2025-02-01', date '2025-06-30'),
  ('Periode Review PKM 2024/II', date '2024-08-01', date '2024-11-30');
