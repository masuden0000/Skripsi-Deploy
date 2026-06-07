-- RLS untuk validation_sessions dan validation_results.
--
-- Hanya user dengan role 'reviewer' di tabel profiles yang dapat melakukan
-- SELECT, INSERT, UPDATE, DELETE pada kedua tabel ini.
--
-- Catatan: backend (FastAPI) menggunakan service_role key yang secara otomatis
-- bypass RLS, sehingga proses insert/update dari background task tidak terpengaruh.

-- ── validation_sessions ────────────────────────────────────────────────────────
alter table public.validation_sessions enable row level security;

create policy "reviewer full access on validation_sessions"
  on public.validation_sessions
  for all
  to authenticated
  using (
    exists (
      select 1 from public.profiles
      where id = auth.uid()
        and role = 'reviewer'
    )
  )
  with check (
    exists (
      select 1 from public.profiles
      where id = auth.uid()
        and role = 'reviewer'
    )
  );

-- ── validation_results ─────────────────────────────────────────────────────────
alter table public.validation_results enable row level security;

create policy "reviewer full access on validation_results"
  on public.validation_results
  for all
  to authenticated
  using (
    exists (
      select 1 from public.profiles
      where id = auth.uid()
        and role = 'reviewer'
    )
  )
  with check (
    exists (
      select 1 from public.profiles
      where id = auth.uid()
        and role = 'reviewer'
    )
  );
