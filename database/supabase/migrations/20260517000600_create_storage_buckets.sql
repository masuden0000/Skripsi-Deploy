-- Buat storage bucket untuk file sumber (PDF panduan PKM) dan output (DOCX proposal)
-- ON CONFLICT DO NOTHING: aman dijalankan ulang jika bucket sudah ada

INSERT INTO storage.buckets (id, name, public, file_size_limit)
VALUES
  ('ai-source-files', 'ai-source-files', true, 104857600),
  ('ai-output-files', 'ai-output-files', true, 104857600)
ON CONFLICT (id) DO NOTHING;
