-- Mengembalikan RLS policy SELECT untuk reviewer di validation_sessions &
-- validation_results.
--
-- Konteks: Migrasi 20260607000003 menghapus semua policy reviewer pada kedua
-- tabel ini dengan asumsi tidak ada akses browser langsung. Asumsi tersebut
-- KELIRU untuk skenario Supabase Realtime: subscription via anon/authenticated
-- key menghormati RLS, sehingga tanpa policy SELECT, server tidak mem-broadcast
-- event UPDATE/INSERT ke client meski publikasi sudah aktif.
--
-- Backend (FastAPI) tetap memakai service_role yang bypass RLS, jadi tidak
-- terpengaruh oleh policy ini.

-- ── validation_sessions ───────────────────────────────────────────────────────
create policy "reviewer can read validation_sessions"
  on public.validation_sessions
  for select
  to authenticated
  using (
    exists (
      select 1 from public.profiles
      where id = auth.uid()
        and role = 'reviewer'
    )
  );

-- ── validation_results ────────────────────────────────────────────────────────
create policy "reviewer can read validation_results"
  on public.validation_results
  for select
  to authenticated
  using (
    exists (
      select 1 from public.profiles
      where id = auth.uid()
        and role = 'reviewer'
    )
  );
