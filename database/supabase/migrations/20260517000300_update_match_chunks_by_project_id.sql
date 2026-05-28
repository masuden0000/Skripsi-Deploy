-- Update match_document_chunks to filter by project_id instead of source_file
-- project_id = satu kombinasi skema+tahun (one record per scheme+year)
create or replace function public.match_document_chunks(
    query_embedding vector(768),
    match_count integer default 5,
    filter_project_id uuid default null
)
returns table (
    chunk_index integer,
    content text,
    chunk_parent text,
    source_file text,
    project_id uuid,
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
        document_chunks.project_id,
        document_chunks.page_start,
        document_chunks.page_end,
        1 - (document_chunks.embedding <=> query_embedding) as similarity
    from public.document_chunks
    where (filter_project_id is null or document_chunks.project_id = filter_project_id)
    order by document_chunks.embedding <=> query_embedding
    limit match_count;
$$;