create extension if not exists vector;

create table if not exists public.document_chunks (
    id bigserial primary key,
    source_file text not null,
    chunk_index integer not null,
    content text not null,
    chunk_parent text not null,
    chunk_prev integer null,
    chunk_next integer null,
    page_start integer not null,
    page_end integer not null,
    embedding vector(768) not null,
    created_at timestamptz not null default timezone('utc', now()),
    unique (source_file, chunk_index)
);

create index if not exists document_chunks_embedding_idx
on public.document_chunks
using ivfflat (embedding vector_cosine_ops)
with (lists = 100);

create or replace function public.match_document_chunks(
    query_embedding vector(768),
    match_count integer default 5
)
returns table (
    chunk_index integer,
    content text,
    chunk_parent text,
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
        document_chunks.page_start,
        document_chunks.page_end,
        1 - (document_chunks.embedding <=> query_embedding) as similarity
    from public.document_chunks
    order by document_chunks.embedding <=> query_embedding
    limit match_count;
$$;
