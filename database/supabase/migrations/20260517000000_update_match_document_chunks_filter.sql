-- Update match_document_chunks to support optional source_file filter
-- Enables per-project chunk isolation during RAG extraction
create or replace function public.match_document_chunks(
    query_embedding vector(768),
    match_count integer default 5,
    filter_source_file text default null
)
returns table (
    chunk_index integer,
    content text,
    chunk_parent text,
    source_file text,
    page_start integer,
    page_end integer,
    similarity double precision
)
language sql
stable
as $$
    select
        document_chunks.chunk_index,
        document_chunks.content,
        document_chunks.chunk_parent,
        document_chunks.source_file,
        document_chunks.page_start,
        document_chunks.page_end,
        1 - (document_chunks.embedding <=> query_embedding) as similarity
    from public.document_chunks
    where (filter_source_file is null or document_chunks.source_file = filter_source_file)
    order by document_chunks.embedding <=> query_embedding
    limit match_count;
$$;
