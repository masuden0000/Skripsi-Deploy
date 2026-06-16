-- Mendaftarkan tabel validation_sessions & validation_results ke publication
-- supabase_realtime supaya client dapat menerima event INSERT/UPDATE/DELETE
-- via Supabase Realtime (postgres_changes). Tanpa baris ini, subscription
-- terbentuk tapi server tidak pernah mem-broadcast perubahan.

alter publication supabase_realtime add table public.validation_sessions;
alter publication supabase_realtime add table public.validation_results;

-- REPLICA IDENTITY FULL agar payload UPDATE menyertakan kolom lama+baru,
-- sehingga klien dapat mendeteksi transisi status (pending → processing → completed).
alter table public.validation_sessions replica identity full;
alter table public.validation_results  replica identity full;
