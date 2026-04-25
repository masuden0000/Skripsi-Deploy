create table if not exists public.document_metadata (
    id           uuid        primary key default gen_random_uuid(),
    source_doc   text        unique not null,
    extracted_at timestamptz not null default timezone('utc', now()),
    payload      jsonb       not null
);

comment on table public.document_metadata is
    'Metadata terstruktur hasil ekstraksi doc_extractor. Satu row per dokumen PDF.';
comment on column public.document_metadata.source_doc is
    'Nama file PDF sumber (contoh: file.pdf). Dipakai sebagai upsert key.';
comment on column public.document_metadata.payload is
    'Full DocumentMetadata as JSON, termasuk sources per field.';
