create type public.app_role as enum ('admin', 'reviewer');

create table public.profiles (
  id         uuid primary key references auth.users(id) on delete cascade,
  role       public.app_role not null,
  full_name  text,
  created_at timestamptz not null default now()
);

alter table public.profiles enable row level security;

create policy "users read own profile"
  on public.profiles
  for select
  using (auth.uid() = id);
