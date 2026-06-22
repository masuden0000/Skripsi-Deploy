-- Add review_status column to assignments table
-- Replaces boolean is_completed as the primary state tracker.
-- States: NULL = belum selesai, 'menunggu_validasi' = menunggu validasi admin, 'selesai' = divalidasi selesai

ALTER TABLE assignments
  ADD COLUMN IF NOT EXISTS review_status TEXT DEFAULT NULL
  CONSTRAINT assignments_review_status_check
    CHECK (review_status IN ('menunggu_validasi', 'selesai'));

-- Sync existing completed assignments
UPDATE assignments
  SET review_status = 'selesai'
  WHERE is_completed = true
    AND review_status IS NULL;
