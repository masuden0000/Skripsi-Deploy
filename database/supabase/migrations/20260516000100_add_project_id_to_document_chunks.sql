-- Tambahkan kolom project_id ke document_chunks untuk relasi antar tabel
-- project_id menghubungkan chunk dengan project agar tidak tertukar antar input berbeda

alter table public.document_chunks
  add column if not exists project_id uuid references public.projects(id) on delete cascade;

-- Hapus unique constraint lama karena project_id sekarang part of uniqueness
alter table public.document_chunks drop constraint if exists document_chunks_source_file_chunk_index_key;

-- Unique constraint baru: source_file + chunk_index + project_id
alter table public.document_chunks add constraint document_chunks_source_file_chunk_index_project_key
  unique (source_file, chunk_index, project_id);

-- Index untuk query by project_id
create index if not exists document_chunks_project_id_idx on public.document_chunks (project_id);

comment on column public.document_chunks.project_id is
  'UUID project untuk mengikat chunk ke project yang sesuai.';


-- ============================================================
-- document_metadata: juga tambahkan project_id agar konsisten
-- ============================================================

alter table public.document_metadata
  add column if not exists project_id uuid references public.projects(id) on delete cascade;

-- Unique constraint baru dengan project_id
alter table public.document_metadata drop constraint if exists document_metadata_source_doc_key;
alter table public.document_metadata add constraint document_metadata_source_doc_project_key
  unique (source_doc, project_id);

create index if not exists document_metadata_project_id_idx on public.document_metadata (project_id);

comment on column public.document_metadata.project_id is
  'UUID project untuk mengikat metadata ke project yang sesuai.';