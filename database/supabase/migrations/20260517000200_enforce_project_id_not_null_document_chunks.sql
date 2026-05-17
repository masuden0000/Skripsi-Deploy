-- Migration: Ubah unique constraint + enforce NOT NULL di document_chunks
-- Alasan: Setiap project_id = satu kombinasi skema+tahun, jadi project_id sudah cukup sebagai unique key.
-- Data lama dengan project_id NULL diabaikan (user decision: ignore old data).

-- Drop constraint lama
ALTER TABLE document_chunks DROP CONSTRAINT IF EXISTS document_chunks_source_file_chunk_index_key;

-- Tambah constraint baru dengan project_id
ALTER TABLE document_chunks ADD CONSTRAINT document_chunks_project_id_chunk_idx_key UNIQUE (project_id, chunk_index);

-- Ensure no old rows with NULL project_id before enforcing NOT NULL
ALTER TABLE public.document_chunks
  ALTER COLUMN project_id SET NOT NULL;
