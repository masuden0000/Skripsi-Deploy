-- Tabel master skema/jenis PKM
create table if not exists public.pkm_schemas (
  id          uuid primary key default gen_random_uuid(),
  nama        text not null,
  singkatan   text not null unique,
  created_at  timestamptz not null default now(),
  updated_at  timestamptz not null default now()
);

-- Trigger updated_at
create or replace function public.set_updated_at()
returns trigger language plpgsql as $$
begin
  new.updated_at = now();
  return new;
end;
$$;

create trigger pkm_schemas_updated_at
  before update on public.pkm_schemas
  for each row execute function public.set_updated_at();

-- RLS: baca publik, tulis hanya service role
alter table public.pkm_schemas enable row level security;

create policy "pkm_schemas_select" on public.pkm_schemas
  for select using (true);

-- Seed data jenis PKM
insert into public.pkm_schemas (nama, singkatan) values
  ('Riset Eksakta',                  'PKM-RE'),
  ('Riset Sosial Humaniora',         'PKM-RSH'),
  ('Kewirausahaan',                  'PKM-K'),
  ('Pengabdian Masyarakat',          'PKM-PM'),
  ('Penerapan Iptek',                'PKM-PI'),
  ('Karsa Cipta',                    'PKM-KC'),
  ('Gagasan Futuristik Tertulis',    'PKM-GFT'),
  ('Video Gagasan Konstruktif',      'PKM-VGK')
on conflict (singkatan) do nothing;
