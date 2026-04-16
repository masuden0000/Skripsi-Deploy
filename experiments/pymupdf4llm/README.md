# PyMuPDF4LLM Experiment

Eksperimen ini memuat pipeline ekstraksi PDF, chunking markdown, embedding ke Supabase, dan chat UI sederhana untuk RAG dokumen PKM.

## Ringkasan Alur

1. File sumber dibaca dari `file.pdf` di root repo.
2. `model_ai/loader/pdf_extractor.py` mengekstrak PDF ke markdown per halaman.
3. `model_ai/loader/chunk_builder.py` membentuk section dan chunk final.
4. Hasil disimpan ke `data/output.md` dan `data/output_chunks.json`.
5. `model_ai/loader/supabase_ingest.py` membuat embedding lalu upsert ke tabel `document_chunks`.
6. `model_ai/rag/rag_service.py` mengambil chunk relevan dari Supabase dan membangun jawaban terstruktur.
7. `model_ai/ui/chat_server.py` menyajikan frontend chat sederhana dari folder `frontend/`.

## Struktur Folder

```text
experiments/pymupdf4llm/
|-- data/
|   |-- output.md
|   `-- output_chunks.json
|-- frontend/
|-- infra/
|   `-- supabase_setup.sql
|-- model_ai/
|   |-- dev/
|   |   `-- inspect_page_chunks.py
|   |-- loader/
|   |   |-- chunk_builder.py
|   |   |-- pdf_extractor.py
|   |   `-- supabase_ingest.py
|   |-- rag/
|   |   |-- rag_service.py
|   |   `-- simple_llm.py
|   `-- ui/
|       `-- chat_server.py
|-- .env.example
|-- manage.py
`-- requirements.txt
```

## Kebutuhan Environment

- Python `3.11`, `3.12`, atau `3.13`
- Google API key untuk Gemini
- Project Supabase dengan tabel dan RPC yang sesuai

Salin `.env.example` menjadi `.env`, lalu isi semua nilai yang diperlukan.

## Menjalankan Project

Install dependency:

```bash
pip install -r experiments/pymupdf4llm/requirements.txt
```

Jalankan pipeline ekstraksi dan ingest:

```bash
python experiments/pymupdf4llm/manage.py setup
```

Hanya bangun file chunk tanpa kirim ke Supabase:

```bash
python experiments/pymupdf4llm/manage.py setup --skip-ingest
```

Jalankan chat UI:

```bash
python experiments/pymupdf4llm/manage.py ui
```

## Variabel `.env`

Nilai yang saat ini dipakai oleh kode:

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

## Output Penting

- `data/output.md`: gabungan markdown hasil ekstraksi PDF
- `data/output_chunks.json`: payload chunk final untuk ingest dan debugging

## Perubahan Struktur Terbaru

- Pengelompokan modul `model_ai` sekarang dipisah berdasarkan tanggung jawab: `loader`, `rag`, `ui`, dan `dev`
- Nama folder `loader` menggantikan pengelompokan lama yang lebih umum
- Import di `manage.py` dan skrip debug sudah disesuaikan ke struktur baru
- `__pycache__` dan file bytecode Python sekarang diabaikan lewat `.gitignore` lokal
