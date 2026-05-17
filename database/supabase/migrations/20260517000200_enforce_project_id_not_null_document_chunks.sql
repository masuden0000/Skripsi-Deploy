-- Pastikan tidak ada row lama dengan project_id NULL sebelum enforce NOT NULL.
-- Jalankan query ini terlebih dahulu untuk memeriksa: SELECT COUNT(*) FROM document_chunks WHERE project_id IS NULL;
ALTER TABLE public.document_chunks
  ALTER COLUMN project_id SET NOT NULL;
