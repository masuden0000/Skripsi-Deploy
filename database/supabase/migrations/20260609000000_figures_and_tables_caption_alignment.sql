-- Migration: Tambah field alignment caption ke document_metadata.payload.figures_and_tables
--
-- Perubahan ini bersifat logis (JSONB), tidak memerlukan ALTER TABLE.
-- Field baru yang didukung oleh renderer docx_A_renderer.py:
--
--   document_metadata.payload.figures_and_tables.caption_alignment_figure
--     Alignment keterangan gambar: CENTER | LEFT | RIGHT | JUSTIFY
--     Default saat null: CENTER
--
--   document_metadata.payload.figures_and_tables.caption_alignment_table
--     Alignment keterangan tabel: CENTER | LEFT | RIGHT | JUSTIFY
--     Default saat null: CENTER
--
--   document_metadata.payload.figures_and_tables.caption_alignment_lampiran
--     Alignment heading lampiran: CENTER | LEFT | RIGHT | JUSTIFY
--     Default saat null: CENTER
--
-- Field disimpan bersama field lain di dalam kolom JSONB payload.figures_and_tables
-- dan dikirim ke renderer via document_metadata.payload saat generate DOCX.
--
-- Backward-compatible: dokumen lama yang belum punya field ini akan menggunakan
-- default CENTER (sama dengan perilaku sebelumnya yang hardcode).

-- Tambah check constraint untuk memvalidasi nilai alignment yang valid
-- di level database agar konsisten dengan enum di frontend dan renderer.
ALTER TABLE document_metadata
  ADD CONSTRAINT chk_caption_alignment_figure CHECK (
    payload->'figures_and_tables'->>'caption_alignment_figure' IS NULL
    OR payload->'figures_and_tables'->>'caption_alignment_figure' IN ('CENTER', 'LEFT', 'RIGHT', 'JUSTIFY')
  );

ALTER TABLE document_metadata
  ADD CONSTRAINT chk_caption_alignment_table CHECK (
    payload->'figures_and_tables'->>'caption_alignment_table' IS NULL
    OR payload->'figures_and_tables'->>'caption_alignment_table' IN ('CENTER', 'LEFT', 'RIGHT', 'JUSTIFY')
  );

ALTER TABLE document_metadata
  ADD CONSTRAINT chk_caption_alignment_lampiran CHECK (
    payload->'figures_and_tables'->>'caption_alignment_lampiran' IS NULL
    OR payload->'figures_and_tables'->>'caption_alignment_lampiran' IN ('CENTER', 'LEFT', 'RIGHT', 'JUSTIFY')
  );
