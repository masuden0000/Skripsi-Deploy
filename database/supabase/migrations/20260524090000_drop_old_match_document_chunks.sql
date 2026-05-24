-- Hapus overload lama match_document_chunks (3 param, tanpa min_similarity)
-- agar PostgreSQL tidak bingung memilih antara dua overload saat dipanggil dengan 3 param.
-- Fungsi pengganti (4 param dengan min_similarity DEFAULT 0.0) sudah ada dari migration sebelumnya.

DROP FUNCTION IF EXISTS "public"."match_document_chunks"(
    "query_embedding" "public"."vector",
    "match_count" integer,
    "filter_project_id" "uuid"
);
