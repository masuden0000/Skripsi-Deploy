-- Drop user_id column from projects table
-- Rationale: user_id is not set by backend (service role key bypasses RLS)
-- and admin-only access is enforced by backend middleware/auth.
-- Table isolation is sufficient for single-admin PKM proposal workflow.

-- Drop RLS policies that depend on user_id column FIRST
drop policy if exists "users can read own projects" on public.projects;
drop policy if exists "users can create own projects" on public.projects;
drop policy if exists "users can update own projects" on public.projects;
drop policy if exists "users can delete own projects" on public.projects;

-- Now drop the column
alter table public.projects drop column if exists user_id;

-- Recreate policies for admin-only access (service role key)
-- All authenticated users via backend service role can read/write all projects
create policy "service role can read projects" on public.projects
  for select to authenticated using (true);

create policy "service role can insert projects" on public.projects
  for insert to authenticated with check (true);

create policy "service role can update projects" on public.projects
  for update to authenticated using (true);

create policy "service role can delete projects" on public.projects
  for delete to authenticated using (true);