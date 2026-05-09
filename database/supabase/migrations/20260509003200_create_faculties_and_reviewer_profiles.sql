create table public.faculties (
  id uuid primary key default gen_random_uuid(),
  code text not null unique,
  name text not null unique,
  created_at timestamptz not null default now()
);

comment on table public.faculties is
  'Master data fakultas untuk identitas asal reviewer.';

comment on column public.faculties.code is
  'Kode singkat fakultas.';

comment on column public.faculties.name is
  'Nama fakultas yang ditampilkan di UI.';

create table public.reviewer_profiles (
  id uuid primary key references public.profiles(id) on delete cascade,
  faculty_id uuid not null references public.faculties(id),
  is_active boolean not null default true,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

comment on table public.reviewer_profiles is
  'Metadata khusus reviewer yang melengkapi tabel profiles.';

comment on column public.reviewer_profiles.faculty_id is
  'Relasi ke master fakultas reviewer.';

comment on column public.reviewer_profiles.is_active is
  'Menandai apakah reviewer boleh login dan mengakses sistem.';

create or replace function public.validate_reviewer_profile_role()
returns trigger
language plpgsql
as $$
declare
  profile_role public.app_role;
begin
  select role
  into profile_role
  from public.profiles
  where id = new.id;

  if profile_role is null then
    raise exception 'Profile untuk reviewer tidak ditemukan.';
  end if;

  if profile_role <> 'reviewer' then
    raise exception 'Hanya profile dengan role reviewer yang boleh memiliki reviewer_profiles.';
  end if;

  return new;
end;
$$;

create trigger validate_reviewer_profiles_role
before insert or update on public.reviewer_profiles
for each row
execute function public.validate_reviewer_profile_role();

create trigger set_reviewer_profiles_updated_at
before update on public.reviewer_profiles
for each row
execute function public.set_updated_at();

alter table public.faculties enable row level security;
alter table public.reviewer_profiles enable row level security;

create policy "authenticated users can read faculties"
  on public.faculties
  for select
  to authenticated
  using (true);

create policy "reviewers read own reviewer profile"
  on public.reviewer_profiles
  for select
  to authenticated
  using (auth.uid() = id);

insert into public.faculties (code, name)
values
  ('FILKOM', 'Fakultas Ilmu Komputer'),
  ('FT', 'Fakultas Teknik'),
  ('FST', 'Fakultas Sains dan Teknologi');
