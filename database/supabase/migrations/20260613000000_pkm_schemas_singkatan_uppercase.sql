-- =============================================================================
-- Migration: Normalisasi singkatan ke UPPERCASE + CHECK constraint
--
-- Masalah yang diselesaikan:
--   Data inconsistency pada kolom pkm_schemas.singkatan — ada nilai yang
--   masih huruf kecil (mis. 'pkm-ai') padahal konvensi yang benar adalah
--   HURUF KAPITAL semua (mis. 'PKM-AI').
--
-- Langkah yang dilakukan:
--   1. Normalisasi: UPDATE semua nilai singkatan yang belum kapital → UPPER()
--      FK projects.skema punya ON UPDATE CASCADE, sehingga ikut terupdate
--      secara otomatis tanpa perlu query tambahan.
--   2. Defensive: Normalisasi projects.skema juga, untuk data yang mungkin
--      lolos dari migration sebelumnya (20260530220000).
--   3. Constraint: Tambah CHECK agar INSERT/UPDATE di masa depan wajib kapital.
-- =============================================================================


-- -----------------------------------------------------------------------------
-- 1. Normalisasi singkatan yang masih huruf kecil → HURUF KAPITAL
--
--    Contoh: 'pkm-ai' → 'PKM-AI', 'pkm-kc' → 'PKM-KC'
--
--    Karena singkatan adalah PRIMARY KEY dan projects.skema punya FK dengan
--    ON UPDATE CASCADE, perubahan di sini otomatis merambat ke tabel projects.
--    Tidak perlu UPDATE projects secara terpisah.
-- -----------------------------------------------------------------------------
UPDATE public.pkm_schemas
  SET singkatan = UPPER(singkatan)
  WHERE singkatan IS DISTINCT FROM UPPER(singkatan);


-- -----------------------------------------------------------------------------
-- 2. Normalisasi projects.skema (defensive — jaga-jaga data yang lolos)
--
--    Seharusnya sudah tertangani oleh migration 20260530220000, tapi kita
--    ulangi di sini agar kondisi awal benar-benar bersih sebelum constraint
--    FK aktif.
-- -----------------------------------------------------------------------------
UPDATE public.projects
  SET skema = UPPER(skema)
  WHERE skema IS DISTINCT FROM UPPER(skema);


-- -----------------------------------------------------------------------------
-- 3. Tambah CHECK constraint: singkatan WAJIB HURUF KAPITAL semua
--
--    Cara kerja: PostgreSQL akan menolak INSERT atau UPDATE yang mengandung
--    huruf kecil pada kolom singkatan, dengan pesan error yang jelas.
--
--    IF NOT EXISTS dipakai agar migration aman dijalankan ulang (idempoten).
-- -----------------------------------------------------------------------------
ALTER TABLE public.pkm_schemas
  DROP CONSTRAINT IF EXISTS pkm_schemas_singkatan_uppercase;

ALTER TABLE public.pkm_schemas
  ADD CONSTRAINT pkm_schemas_singkatan_uppercase
  CHECK (singkatan = UPPER(singkatan));

COMMENT ON CONSTRAINT pkm_schemas_singkatan_uppercase ON public.pkm_schemas IS
  'Memastikan singkatan selalu disimpan dalam HURUF KAPITAL semua (mis. PKM-KC, bukan pkm-kc).';
