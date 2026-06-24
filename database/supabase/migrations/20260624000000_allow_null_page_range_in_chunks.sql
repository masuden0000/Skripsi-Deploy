-- Izinkan page_start dan page_end bernilai NULL pada document_chunks.
-- Halaman dengan penomoran romawi (halaman depan dokumen PKM) akan diingest
-- dengan nilai NULL pada kedua kolom ini karena nomor romawi bukan integer.
ALTER TABLE "public"."document_chunks"
    ALTER COLUMN "page_start" DROP NOT NULL,
    ALTER COLUMN "page_end" DROP NOT NULL;
