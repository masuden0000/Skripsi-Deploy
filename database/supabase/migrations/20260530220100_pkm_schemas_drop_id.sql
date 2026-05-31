-- =============================================================================
-- Migration: pkm_schemas — jadikan singkatan sebagai primary key, drop id
--
-- Alasan:
--   - Kolom id (uuid) tidak pernah dipakai di kode maupun sebagai FK
--   - singkatan sudah UNIQUE dan dipakai sebagai FK dari projects.skema
--   - Menjadikan singkatan sebagai PK menghilangkan kolom yang tidak perlu
-- =============================================================================


-- 1. Drop FK dari projects.skema (bergantung pada index UNIQUE singkatan)
ALTER TABLE public.projects
  DROP CONSTRAINT projects_skema_fkey;

-- 2. Drop PK lama (pada kolom id)
ALTER TABLE public.pkm_schemas
  DROP CONSTRAINT pkm_schemas_pkey;

-- 3. Drop UNIQUE constraint pada singkatan (sudah bebas dari dependensi FK)
ALTER TABLE public.pkm_schemas
  DROP CONSTRAINT pkm_schemas_singkatan_key;

-- 4. Drop kolom id
ALTER TABLE public.pkm_schemas
  DROP COLUMN id;

-- 5. Jadikan singkatan sebagai primary key
ALTER TABLE public.pkm_schemas
  ADD CONSTRAINT pkm_schemas_pkey PRIMARY KEY (singkatan);

-- 6. Tambah kembali FK dari projects.skema ke pkm_schemas.singkatan (kini PK)
ALTER TABLE public.projects
  ADD CONSTRAINT projects_skema_fkey
  FOREIGN KEY (skema)
  REFERENCES public.pkm_schemas (singkatan)
  ON UPDATE CASCADE;
