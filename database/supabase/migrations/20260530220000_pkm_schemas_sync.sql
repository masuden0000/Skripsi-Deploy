-- =============================================================================
-- Migration: pkm_schemas sync
-- Tujuan:
--   1. Tambah kolom renderer_type ke pkm_schemas (membedakan Type A vs Type B)
--   2. Seed 10 skema PKM
--   3. Normalisasi projects.skema ke UPPERCASE
--   4. Tambah FK dari projects.skema ke pkm_schemas.singkatan
-- =============================================================================


-- -----------------------------------------------------------------------------
-- 1. Tambah kolom renderer_type
-- -----------------------------------------------------------------------------
ALTER TABLE public.pkm_schemas
  ADD COLUMN IF NOT EXISTS renderer_type text NOT NULL DEFAULT 'A'
    CONSTRAINT pkm_schemas_renderer_type_check CHECK (renderer_type IN ('A', 'B'));

COMMENT ON COLUMN public.pkm_schemas.renderer_type IS
  'Tipe renderer dokumen: A = proposal (semua skema kecuali PKM-AI), B = artikel ilmiah (PKM-AI).';


-- -----------------------------------------------------------------------------
-- 2. Seed 10 skema PKM
--    ON CONFLICT (singkatan) → update agar idempoten (aman dijalankan ulang)
-- -----------------------------------------------------------------------------
INSERT INTO public.pkm_schemas (singkatan, nama, renderer_type) VALUES
  ('PKM-KC',  'Karsa Cipta',                   'A'),
  ('PKM-RE',  'Riset Eksakta',                  'A'),
  ('PKM-RSH', 'Riset Sosial Humaniora',          'A'),
  ('PKM-K',   'Kewirausahaan',                  'A'),
  ('PKM-PM',  'Pengabdian Kepada Masyarakat',   'A'),
  ('PKM-PI',  'Penerapan Iptek',                'A'),
  ('PKM-KI',  'Karya Inovatif',                 'A'),
  ('PKM-VGK', 'Video Gagasan Konstruktif',      'A'),
  ('PKM-GFT', 'Gagasan Futuristik Tertulis',    'A'),
  ('PKM-AI',  'Artikel Ilmiah',                 'B')
ON CONFLICT (singkatan) DO UPDATE
  SET nama          = EXCLUDED.nama,
      renderer_type = EXCLUDED.renderer_type,
      updated_at    = now();


-- -----------------------------------------------------------------------------
-- 3. Normalisasi projects.skema ke UPPERCASE
--    Contoh: 'pkm-kc' → 'PKM-KC'
--    Aman untuk data yang sudah ada sebelum FK ditambahkan.
-- -----------------------------------------------------------------------------
UPDATE public.projects
  SET skema = UPPER(skema)
  WHERE skema IS DISTINCT FROM UPPER(skema);


-- -----------------------------------------------------------------------------
-- 4. Tambah FK dari projects.skema ke pkm_schemas.singkatan
--    ON UPDATE CASCADE: jika singkatan berubah, projects ikut terupdate.
--    Tidak pakai ON DELETE karena skema tidak boleh dihapus selama ada project.
-- -----------------------------------------------------------------------------
ALTER TABLE public.projects
  ADD CONSTRAINT projects_skema_fkey
  FOREIGN KEY (skema)
  REFERENCES public.pkm_schemas (singkatan)
  ON UPDATE CASCADE;
