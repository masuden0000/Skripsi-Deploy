-- Change tahun from DATE to TEXT since it stores only a year value (e.g., "2026")
ALTER TABLE public.projects ALTER COLUMN tahun TYPE TEXT USING tahun::text;
