-- Add project_id foreign key to document_chunks
alter table public.document_chunks
add column project_id uuid references public.projects(id) on delete cascade;

create index idx_document_chunks_project_id on public.document_chunks(project_id);

comment on column public.document_chunks.project_id is
  'Project this chunk belongs to - enables isolation between proposals.';

-- Add project_id foreign key to document_metadata
alter table public.document_metadata
add column project_id uuid references public.projects(id) on delete cascade;

create index idx_document_metadata_project_id on public.document_metadata(project_id);

comment on column public.document_metadata.project_id is
  'Project this metadata belongs to - enables isolation between proposals.';