create table if not exists public.user_logs (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references auth.users(id) on delete cascade,
  email text not null,
  role text not null,
  action text not null check (action in ('login', 'logout')),
  created_at timestamptz not null default timezone('utc'::text, now())
);

alter table public.user_logs enable row level security;

create policy "Users can view own logs"
  on public.user_logs
  for select
  using (auth.uid() = user_id);

create policy "Users can insert own logs"
  on public.user_logs
  for insert
  with check (auth.uid() = user_id);
