insert into public.faculties (code, name)
values
  ('FEB', 'Fakultas Ekonomi dan Bisnis'),
  ('FISIP', 'Fakultas Ilmu Sosial dan Ilmu Politik'),
  ('FILKOM', 'Fakultas Ilmu Komputer'),
  ('FH', 'Fakultas Hukum'),
  ('FK', 'Fakultas Kedokteran'),
  ('FT', 'Fakultas Teknik'),
  ('FIKES', 'Fakultas Ilmu Kesehatan')
on conflict (code) do update
set name = excluded.name;
