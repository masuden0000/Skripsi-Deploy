-- =============================================================================
-- Migration: Hapus kolom renderer_type dari pkm_schemas
--
-- Alasan:
--   Logika penentuan renderer dipindahkan sepenuhnya ke kode Python (hardcode).
--   Fungsi is_type_b() di shared.py kini menjadi satu-satunya sumber kebenaran.
--   Kolom ini tidak lagi dibaca oleh kode manapun sehingga tidak perlu ada di DB.
--
-- Dampak yang sudah diverifikasi sebelum migration ini:
--   - shared.py     : get_renderer_type() diganti is_type_b(), tidak ada DB query
--   - generator.py  : pemanggil diperbarui ke is_type_b()
--   - prompts.py    : pemanggil diperbarui ke is_type_b()
--   - pkm.py        : query SELECT sudah tidak menyertakan renderer_type
--   - pkm.ts        : field renderer_type sudah nullable().optional() di frontend
--                     dan tidak digunakan di UI manapun — aman dihilangkan
-- =============================================================================

ALTER TABLE public.pkm_schemas
  DROP COLUMN IF EXISTS renderer_type;
