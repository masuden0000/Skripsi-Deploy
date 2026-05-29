CREATE OR REPLACE FUNCTION "public"."match_document_chunks"(
    "query_embedding" "public"."vector",
    "match_count" integer DEFAULT 5,
    "filter_project_id" "uuid" DEFAULT NULL::"uuid",
    "min_similarity" double precision DEFAULT 0.0,
    "excluded_parents" text[] DEFAULT NULL
)
RETURNS TABLE(
    "chunk_index" integer,
    "content" "text",
    "chunk_parent" "text",
    "source_file" "text",
    "project_id" "uuid",
    "page_start" integer,
    "page_end" integer,
    "similarity" double precision
)
LANGUAGE "sql" STABLE
AS $$
    SELECT
        document_chunks.chunk_index,
        document_chunks.content,
        document_chunks.chunk_parent,
        document_chunks.source_file,
        document_chunks.project_id,
        document_chunks.page_start,
        document_chunks.page_end,
        1 - (document_chunks.embedding <=> query_embedding) AS similarity
    FROM public.document_chunks
    WHERE
        (filter_project_id IS NULL OR document_chunks.project_id = filter_project_id)
        AND (1 - (document_chunks.embedding <=> query_embedding)) >= min_similarity
        AND (excluded_parents IS NULL OR document_chunks.chunk_parent != ALL(excluded_parents))
    ORDER BY document_chunks.embedding <=> query_embedding
    LIMIT match_count;
$$;

ALTER FUNCTION "public"."match_document_chunks"(
    "public"."vector", integer, "uuid", double precision, text[]
) OWNER TO "postgres";
