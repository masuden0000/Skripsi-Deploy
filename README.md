# Skripsi Dummy Project 1 (AI)

Repository ini berisi pipeline end-to-end untuk:

- ekstraksi PDF menjadi markdown + chunks,
- ingest chunks ke Supabase (dengan embedding),
- ekstraksi metadata dokumen berbasis RAG + LLM,
- schema diff (structured vs free extraction),
- translasi style ke python-docx dan generator DOCX proposal.

## Struktur Project

Project sekarang dipisah menjadi empat area utama:

- `ai/`: pipeline AI, extractor, DOCX generator, dan data runtime lokal.
- `database/`: schema SQL, config CLI, dan migration Supabase.
- `backend/`: disiapkan untuk backend aplikasi.
- `frontend/`: disiapkan untuk frontend aplikasi.

## Quick Start

1. Buat virtual environment dan aktifkan:

```bash
python -m venv .venv
source .venv/Scripts/activate
```

2. Install dependency:

```bash
pip install -r ai/requirements.txt
```

3. Siapkan environment per area project:

```text
ai/.env
frontend/.env.local
```

- `ai/.env` untuk runtime pipeline AI, termasuk akses service-role ke Supabase.
- `frontend/.env.local` untuk Supabase URL + anon key yang aman dipakai aplikasi Next.js.
- Root `.env` tidak dipakai sebagai source environment aktif.

4. Jalankan pipeline utama:

```bash
python ai/manage.py setup
python ai/manage.py extract
python ai/manage.py docx --type proposal --source-doc file.pdf
```

## Command CLI

Semua command utama bisa dijalankan dari root repo:

- `python ai/manage.py setup`
	- Ekstrak PDF -> `output.md` + `output_chunks.json`, lalu ingest ke Supabase.
- `python ai/manage.py setup --skip-ingest`
	- Hanya build chunk lokal tanpa upsert ke Supabase.
- `python ai/manage.py extract`
	- Ekstraksi metadata terstruktur lalu upsert ke `document_metadata.payload`.
- `python ai/manage.py docx --type proposal --source-doc file.pdf`
	- Generate dokumen DOCX proposal dari metadata Supabase + chunks lokal.
- `python ai/manage.py docx-style-map --source-doc file.pdf`
	- Jalankan pipeline mapping style DOCX (catalog, retrieval, candidate, validasi, apply plan).

## Supabase Migration

Schema Supabase tidak perlu lagi di-copy manual ke SQL Editor. Migration utama sekarang ada di `database/supabase/migrations/`.

```powershell
Set-Location -LiteralPath .\database\supabase
npx supabase login
npx supabase link --project-ref <PROJECT_REF>
npx supabase db push --dry-run
npx supabase db push
```

Di mesin ini `supabase` global belum tersedia, tapi `npx supabase` sudah bisa dipakai.

```powershell
npx supabase --version
```

## Pembagian Environment

- `ai/.env`
	- `GROQ_API_KEY`
	- `GOOGLE_API_KEY`
	- `MODEL_NAME`
	- `TEMPERATURE`
	- `EMBEDDING_MODEL_NAME`
	- `SUPABASE_URL`
	- `SUPABASE_SERVICE_ROLE_KEY`
	- `CHAT_HOST`
	- `CHAT_PORT`
	- `RAG_TOP_K`
	- `RAG_MIN_CONTEXT_SIMILARITY`
- `frontend/.env.local`
	- `NEXT_PUBLIC_SUPABASE_URL`
	- `NEXT_PUBLIC_SUPABASE_ANON_KEY`
- `database/`
	- tidak butuh file env khusus untuk workflow migration standar; `npx supabase link` dan `npx supabase db push` memakai konfigurasi di `database/supabase/`
- `backend/`
	- belum memakai env karena folder masih placeholder

## Struktur Ringkas

```text
ai/
|-- data/
|   |-- output.md
|   |-- output_chunks.json
|   `-- docx_mapping_*.json
|-- model_ai/
|   |-- loader/
|   |-- extractor/
|   |-- docx/
|   `-- visualisasi/
|-- testing ekstraksi/
|-- manage.py
`-- requirements.txt
database/
|-- supabase_setup.sql
|-- supabase_metadata.sql
|-- README.md
`-- supabase/
    |-- config.toml
    `-- migrations/
backend/
frontend/
```

## Catatan Perubahan Terbaru

- Prompt extractor sudah dipusatkan ke `model_ai/extractor/prompts/*.md` via registry di `model_ai/extractor/prompts.py`.
- Pipeline DOCX diperkuat dengan:
	- `model_ai/docx/generator.py`,
	- `model_ai/docx/metadata_loader.py`,
	- `model_ai/docx/style_mapping_pipeline.py`,
	- `model_ai/docx/instructional_placeholder_builder.py`.
- Ditambahkan utilitas evaluasi translasi di folder `testing ekstraksi/`.
- Ditambahkan halaman visualisasi pipeline di `model_ai/visualisasi/`.
Test Upload