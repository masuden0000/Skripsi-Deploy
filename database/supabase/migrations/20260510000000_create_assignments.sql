create table public.assignments (
  id               uuid        primary key default gen_random_uuid(),
  period_id        uuid        not null references public.pkm_review_periods(id) on delete cascade,
  reviewer_id      uuid        not null references public.reviewer_profiles(id) on delete cascade,
  proposal_link    text,
  assessment_link  text,
  is_completed     boolean     not null default false,
  created_at       timestamptz not null default now(),
  updated_at       timestamptz not null default now(),

  constraint unique_reviewer_period unique (period_id, reviewer_id),
  constraint at_least_one_link check (
    proposal_link is not null or assessment_link is not null
  )
);

comment on table public.assignments is
  'Tugas penugasan reviewer untuk periode review PKM.';

comment on column public.assignments.period_id is
  'Relasi ke periode review yang berlaku.';

comment on column public.assignments.reviewer_id is
  'Relasi ke akun reviewer yang ditugaskan.';

comment on column public.assignments.proposal_link is
  'Link menuju dokumen proposal yang harus direview.';

comment on column public.assignments.assessment_link is
  'Link menuju dokumen atau halaman pengumpulan hasil penilaian.';

comment on column public.assignments.is_completed is
  'Status penugasan: apakah reviewer sudah mengkonfirmasi selesai atau belum.';

create index idx_assignments_period_id       on public.assignments(period_id);
create index idx_assignments_reviewer_id      on public.assignments(reviewer_id);
create index idx_assignments_is_completed     on public.assignments(is_completed);
create index idx_assignments_period_completed on public.assignments(period_id, is_completed);

create trigger set_assignments_updated_at
before update on public.assignments
for each row
execute function public.set_updated_at();

alter table public.assignments enable row level security;

create policy "authenticated users can read assignments"
  on public.assignments
  for select
  to authenticated
  using (true);

create policy "authenticated users can create assignments"
  on public.assignments
  for insert
  to authenticated
  with check (true);

create policy "authenticated users can update assignments"
  on public.assignments
  for update
  to authenticated
  using (true);