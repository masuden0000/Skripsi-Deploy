# PyMuPDF4LLM Experiment

Eksperimen ini memuat pipeline ekstraksi PDF, chunking markdown, embedding ke Supabase, dan ekstraksi metadata dokumen PKM.

## Ringkasan Alur

1. File sumber dibaca dari `file.pdf` di root repo.
2. `model_ai/loader/pdf_extractor.py` mengekstrak PDF ke markdown per halaman.
3. `model_ai/loader/chunk_builder.py` membentuk section dan chunk final.
4. Hasil disimpan ke `data/output.md` dan `data/output_chunks.json`.
5. `model_ai/loader/supabase_ingest.py` membuat embedding lalu upsert ke tabel `document_chunks`.
6. `model_ai/extractor/doc_extractor.py` melakukan retrieval + grounding untuk ekstraksi metadata terstruktur lalu upsert ke `document_metadata`.
7. Consumer metadata seperti `docx`, `docx-style-map`, dan `schema-diff` membaca ulang metadata dari `document_metadata.payload` memakai selector `source_doc`.

## Struktur Folder

```text
ai/
|-- data/
|   |-- output.md
|   `-- output_chunks.json
|-- model_ai/
|   |-- loader/
|   |   |-- chunk_builder.py
|   |   |-- pdf_extractor.py
|   |   `-- supabase_ingest.py
|   |-- extractor/
|   |   `-- doc_extractor.py
|   `-- docx/
|       `-- style_mapping_pipeline.py
|-- .env.example
|-- manage.py
`-- requirements.txt
```

Schema Supabase berada di root folder `database/`.

## Kebutuhan Environment

- Python `3.11`, `3.12`, atau `3.13`
- Groq API key
- Google API key untuk embedding Gemini
- Project Supabase dengan tabel dan RPC yang sesuai

Salin `ai/.env.example` menjadi `ai/.env`, lalu isi semua nilai yang diperlukan.

Root `.env` tidak dipakai oleh runtime AI. File yang dibaca kode adalah `ai/.env`.

## Menjalankan Project

Install dependency dari root repo:

```bash
pip install -r ai/requirements.txt
```

Jalankan pipeline ekstraksi dan ingest:

```bash
python ai/manage.py setup
```

Hanya bangun file chunk tanpa kirim ke Supabase:

```bash
python ai/manage.py setup --skip-ingest
```

Ekstrak metadata terstruktur ke Supabase:

```bash
python ai/manage.py extract
```

Generate DOCX dari metadata yang sudah tersimpan:

```bash
python ai/manage.py docx --type proposal --source-doc file.pdf
```

## Variabel `ai/.env`

Nilai yang saat ini dipakai oleh kode:

- `GROQ_API_KEY`
- `GOOGLE_API_KEY`
- `MODEL_NAME`
- `TEMPERATURE`
- `EMBEDDING_MODEL_NAME`
- `SUPABASE_URL`
- `SUPABASE_SERVICE_ROLE_KEY`
- `RAG_TOP_K`
- `RAG_MIN_CONTEXT_SIMILARITY`

Catatan:

- Model untuk ekstraksi (`doc_extractor.py`, `schema_differ.py`) dan pipeline mapping DOCX memakai Groq via `langchain-groq`.
- Embedding untuk retrieval dan ingest Supabase masih memakai Gemini embedding (`langchain-google-genai`).
- `SUPABASE_SERVICE_ROLE_KEY` hanya untuk runtime server-side AI, bukan untuk frontend.

## Output Penting

- `ai/data/output.md`: gabungan markdown hasil ekstraksi PDF
- `ai/data/output_chunks.json`: payload chunk final untuk ingest dan debugging
- `public.document_metadata.payload`: source of truth metadata terstruktur hasil extractor

## Perubahan Struktur Terbaru

- Pengelompokan modul `model_ai` sekarang dipisah berdasarkan tanggung jawab: `loader`, `extractor`, `docx`, dan `dev`
- Nama folder `loader` menggantikan pengelompokan lama yang lebih umum
- Import di `manage.py` dan skrip debug sudah disesuaikan ke struktur baru
- `__pycache__` dan file bytecode Python sekarang diabaikan lewat `.gitignore` lokal
