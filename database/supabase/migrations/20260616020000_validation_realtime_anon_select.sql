-- Memperbaiki RLS policy SELECT untuk validation_sessions & validation_results
-- supaya Supabase Realtime dapat mem-broadcast event ke browser client.
--
-- Konteks penting:
--   Browser pakai supabase-js dengan ANON key tanpa setSession (aplikasi ini
--   memakai auth Express berbasis cookie, BUKAN Supabase Auth). Akibatnya
--   role untuk Realtime adalah `anon`, bukan `authenticated`.
--
--   Policy `to authenticated` di migrasi 20260616010000 tidak match → Realtime
--   tetap silent meski publikasi sudah aktif (root cause: status bulk upload
--   tidak update sampai user refresh manual).
--
-- Yang dilakukan:
--   1. Drop policy `to authenticated` yang tidak fungsional
--   2. Buat policy SELECT terbuka untuk `anon, authenticated` (USING true)
--
-- Risk: validation_sessions/results berisi metadata proses validasi
-- (file_name, status, schema_id, hasil). Tidak ada PII sensitif; data ini
-- nantinya memang ditampilkan ke reviewer yang membuat sesi. Write tetap
-- via service_role (FastAPI), jadi tidak ada risiko tampering dari browser.

drop policy if exists "reviewer can read validation_sessions" on public.validation_sessions;
drop policy if exists "reviewer can read validation_results"  on public.validation_results;

create policy "anon can read validation_sessions"
  on public.validation_sessions
  for select
  to anon, authenticated
  using (true);

create policy "anon can read validation_results"
  on public.validation_results
  for select
  to anon, authenticated
  using (true);
