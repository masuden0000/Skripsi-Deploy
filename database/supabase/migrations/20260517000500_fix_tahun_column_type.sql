-- Ubah kolom tahun dari date ke text (hanya simpan 4 digit tahun)
-- Alasan: App mengirim "2026", "2024" bukan full date "2026-01-01".
-- Menyimpan sebagai date menyebabkan type mismatch pada query eq("tahun", "2026")
-- yang bisa menghasilkan false match atau unhandled cast error.

-- Drop unique constraint dulu (tergantung pada kolom tahun)
ALTER TABLE public.projects DROP CONSTRAINT IF EXISTS projects_skema_tahun_key;

-- Ubah tipe kolom: ambil 4 karakter pertama dari representasi text-nya.
-- LEFT(tahun::text, 4) aman untuk kedua sumber:
--   date "2026-01-01" → cast text → "2026-01-01" → LEFT 4 → "2026"
--   text "2026"        → cast text → "2026"        → LEFT 4 → "2026"
ALTER TABLE public.projects
  ALTER COLUMN tahun TYPE text
  USING LEFT(tahun::text, 4);

-- Pasang kembali unique constraint
ALTER TABLE public.projects
  ADD CONSTRAINT projects_skema_tahun_key UNIQUE (skema, tahun);
