-- Migration: Tambah unique constraint project_id + drop source_doc di document_metadata
-- Alasan: project_id sudah cukup sebagai unique key. source_doc dihapus karena tidak lagi needed.
-- Run ini SETELAH migration document_chunks.

-- Tambah unique constraint pada project_id
ALTER TABLE document_metadata ADD CONSTRAINT document_metadata_project_id_key UNIQUE (project_id);

-- Drop kolom source_doc (tidak lagi needed sebagai unique key)
ALTER TABLE document_metadata DROP COLUMN IF EXISTS source_doc;