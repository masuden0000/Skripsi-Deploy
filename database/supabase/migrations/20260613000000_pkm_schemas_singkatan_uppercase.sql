-- =============================================================================
-- Migration: Normalisasi singkatan ke UPPERCASE + CHECK constraint
--
-- Masalah yang diselesaikan:
--   Data inconsistency pada kolom pkm_schemas.singkatan — ada nilai yang
--   masih huruf kecil (mis. 'pkm-re') padahal konvensi yang benar adalah
--   HURUF KAPITAL semua (mis. 'PKM-RE').
--
--   Kondisi aktual di database: ada DUPLIKAT — satu baris lowercase DAN satu
--   baris uppercase untuk skema yang sama (mis. 'pkm-re' dan 'PKM-RE' keduanya
--   ada). Ini menyebabkan UPDATE biasa gagal karena PK conflict.
--
-- Urutan langkah (WAJIB berurutan karena ada dependensi FK):
--   1. Pindahkan projects.skema yang lowercase ke uppercase
--      → agar tidak ada project yang masih menunjuk ke baris lowercase
--        (jika ada project yang masih bergantung ke baris lowercase, FK akan
--         mencegah penghapusan di langkah 2)
--   2. Hapus baris lowercase yang sudah punya pasangan uppercase
--      → menghilangkan duplikat agar UPDATE di langkah 3 tidak konflik PK
--   3. Update sisa baris lowercase yang belum punya pasangan uppercase
--      → menyelesaikan normalisasi baris yang unik (tidak punya duplikat)
--   4. Pasang CHECK constraint agar di masa depan tidak bisa masuk lowercase
-- =============================================================================


-- -----------------------------------------------------------------------------
-- 1. Normalisasi projects.skema ke UPPERCASE lebih dulu
--
--    Alasan urutan ini: FK dari projects.skema ke pkm_schemas.singkatan
--    bersifat RESTRICT pada DELETE. Jika ada project yang masih referencing
--    'pkm-re' (lowercase), kita tidak bisa menghapus baris 'pkm-re' dari
--    pkm_schemas di langkah 2.
--    Dengan update projects dulu, semua referensi sudah aman ke baris uppercase.
-- -----------------------------------------------------------------------------
UPDATE public.projects
  SET skema = UPPER(skema)
  WHERE skema IS DISTINCT FROM UPPER(skema);


-- -----------------------------------------------------------------------------
-- 2. Hapus baris lowercase yang sudah punya pasangan uppercase (duplikat)
--
--    Kondisi: EXISTS baris lain dengan nilai UPPER() yang sama.
--    Contoh: hapus 'pkm-re' karena 'PKM-RE' sudah ada.
--    Setelah langkah 1, tidak ada project yang bergantung ke baris ini lagi.
-- -----------------------------------------------------------------------------
DELETE FROM public.pkm_schemas lc
  WHERE lc.singkatan IS DISTINCT FROM UPPER(lc.singkatan)
    AND EXISTS (
      SELECT 1 FROM public.pkm_schemas uc
      WHERE uc.singkatan = UPPER(lc.singkatan)
    );


-- -----------------------------------------------------------------------------
-- 3. Update sisa baris lowercase yang TIDAK punya pasangan uppercase
--
--    Baris yang tidak dihapus di langkah 2 = tidak ada duplikat uppercase-nya.
--    Contoh: jika hanya ada 'pkm-xyz' tanpa 'PKM-XYZ', cukup di-UPDATE.
--    ON UPDATE CASCADE akan merambat ke projects.skema secara otomatis.
-- -----------------------------------------------------------------------------
UPDATE public.pkm_schemas
  SET singkatan = UPPER(singkatan)
  WHERE singkatan IS DISTINCT FROM UPPER(singkatan);


-- -----------------------------------------------------------------------------
-- 4. Tambah CHECK constraint: singkatan WAJIB HURUF KAPITAL semua
--
--    PostgreSQL akan menolak INSERT atau UPDATE yang mengandung huruf kecil
--    pada kolom singkatan, dengan pesan error yang jelas.
--    DROP IF EXISTS dipakai agar migration aman dijalankan ulang (idempoten).
-- -----------------------------------------------------------------------------
ALTER TABLE public.pkm_schemas
  DROP CONSTRAINT IF EXISTS pkm_schemas_singkatan_uppercase;

ALTER TABLE public.pkm_schemas
  ADD CONSTRAINT pkm_schemas_singkatan_uppercase
  CHECK (singkatan = UPPER(singkatan));

COMMENT ON CONSTRAINT pkm_schemas_singkatan_uppercase ON public.pkm_schemas IS
  'Memastikan singkatan selalu disimpan dalam HURUF KAPITAL semua (mis. PKM-KC, bukan pkm-kc).';
