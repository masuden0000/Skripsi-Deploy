-- Selaraskan singkatan dengan slug yang dipakai di projects.skema (lowercase, mis. "pkm-re")
-- dan tambahkan dua skema yang sebelumnya belum ada (pkm-ki, pkm-ai).

update public.pkm_schemas set singkatan = 'pkm-re'  where singkatan = 'PKM-RE';
update public.pkm_schemas set singkatan = 'pkm-rsh' where singkatan = 'PKM-RSH';
update public.pkm_schemas set singkatan = 'pkm-k'   where singkatan = 'PKM-K';
update public.pkm_schemas set singkatan = 'pkm-pm'  where singkatan = 'PKM-PM';
update public.pkm_schemas set singkatan = 'pkm-pi'  where singkatan = 'PKM-PI';
update public.pkm_schemas set singkatan = 'pkm-kc'  where singkatan = 'PKM-KC';
update public.pkm_schemas set singkatan = 'pkm-vgk' where singkatan = 'PKM-VGK';
update public.pkm_schemas set singkatan = 'pkm-gft' where singkatan = 'PKM-GFT';

insert into public.pkm_schemas (nama, singkatan) values
  ('Karya Inovatif',  'pkm-ki'),
  ('Artikel Ilmiah',  'pkm-ai')
on conflict (singkatan) do nothing;
