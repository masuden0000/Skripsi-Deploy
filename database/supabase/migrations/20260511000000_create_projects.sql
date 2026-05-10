create table public.projects (
  id              uuid        primary key default gen_random_uuid(),
  user_id         uuid        references public.profiles(id),
  skema           text        not null,
  tahun           date        not null,
  judul           text        not null,
  source_file     text,
  source_url     text,
  status          text        not null default 'pending',
  -- status: 'pending' | 'uploading' | 'extracting' | 'extracted' | 'generating' | 'completed' | 'failed'
  error_message   text,
  result_url      text,
  created_at      timestamptz not null default now(),
  updated_at      timestamptz not null default now()
);

comment on table public.projects is
  'Project isolation for PKM proposal generation - each project has its own chunks, metadata, and output.';

comment on column public.projects.skema is
  'PKM scheme: pkm-kc, pkm-re, pkm-penelitian, dll.';

comment on column public.projects.tahun is
  'Submission date/tahun for the proposal.';

comment on column public.projects.judul is
  'Proposal title.';

comment on column public.projects.status is
  'Pipeline status: pending -> uploading -> extracting -> extracted -> generating -> completed/failed';

comment on column public.projects.source_url is
  'Supabase Storage URL for uploaded source file.';

comment on column public.projects.result_url is
  'Supabase Storage URL for generated DOCX output.';

comment on column public.projects.error_message is
  'Error message if pipeline failed.';

create or replace function public.set_updated_at()
returns trigger
language plpgsql
as $$
begin
  new.updated_at = now();
  return new;
end;
$$;

create trigger set_projects_updated_at
before update on public.projects
for each row
execute function public.set_updated_at();

alter table public.projects enable row level security;

create policy "users can read own projects"
  on public.projects
  for select
  to authenticated
  using (auth.uid() = user_id);

create policy "users can create own projects"
  on public.projects
  for insert
  to authenticated
  with check (auth.uid() = user_id);

create policy "users can update own projects"
  on public.projects
  for update
  to authenticated
  using (auth.uid() = user_id);

create policy "users can delete own projects"
  on public.projects
  for delete
  to authenticated
  using (auth.uid() = user_id);