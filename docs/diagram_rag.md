╔══════════════════════════════════════════════════════════════╗
║                    FASE 1: INGESTION                         ║
║              (perintah: python manage.py setup)              ║
╚══════════════════════════════════════════════════════════════╝

  [File PDF: source.pdf]
        │
        ▼
┌─────────────────────────────────────────────────────┐
│  pdf_extractor.py                                   │
│  Fungsi: extract_chunks()                           │
│  Library: pymupdf4llm.to_markdown(page_chunks=True) │
│  Output: Markdown per halaman + metadata halaman    │
└─────────────────────────────────────────────────────┘
        │
        │  output.md (disimpan di data/{project_id}/output.md)
        ▼
┌─────────────────────────────────────────────────────┐
│  chunk_builder.py                                   │
│  Fungsi: build_sections() → build_payload()         │
│  Library: LangChain MarkdownTextSplitter            │
│  Proses:                                            │
│    1. Kelompokkan teks per seksi/BAB (header)       │
│    2. Filter heading OCR noise                      │
│    3. Split tiap seksi: chunk_size=1000, overlap=150│
│    4. Map tiap chunk ke range halaman PDF           │
│    5. Link chunk_prev & chunk_next dalam seksi      │
│  Output: list of chunks dengan metadata             │
└─────────────────────────────────────────────────────┘
        │
        │  output_chunks.json (data/{project_id}/output_chunks.json)
        ▼
┌─────────────────────────────────────────────────────┐
│  supabase_ingest.py                                 │
│  Fungsi: ingest_chunks()                            │
│  Library: GoogleGenerativeAIEmbeddings              │
│  Model: gemini-embedding-001 (768 dimensi)          │
│  Proses:                                            │
│    1. Batch 20 chunk per request                    │
│    2. Embed teks → vektor 768 dimensi               │
│    3. Upsert ke tabel document_chunks (Supabase)    │
│    4. Rate limit: rotasi 5 API key Google           │
└─────────────────────────────────────────────────────┘
        │
        ▼
  [Supabase: tabel document_chunks]
  ┌─────────────────────────────────┐
  │ project_id                      │
  │ chunk_index                     │
  │ content      (teks chunk)       │
  │ chunk_parent (nama seksi/BAB)   │
  │ chunk_prev / chunk_next         │
  │ page_start / page_end           │
  │ embedding    vector(768)  ◄──── │ pgvector
  └─────────────────────────────────┘


╔══════════════════════════════════════════════════════════════╗
║                FASE 2: RETRIEVAL & EXTRACTION                ║
║             (perintah: python manage.py extract)             ║
╚══════════════════════════════════════════════════════════════╝

  [prompts/*.md]
  ┌───────────────────────────────────────┐
  │ YAML frontmatter:                     │
  │   queries: [list query semantik]      │
  │   top_k: 5                            │
  │ Body: template prompt + {context}     │
  └───────────────────────────────────────┘
        │
        ▼ prompts.py (load & parse file .md)
        │
        ▼
┌─────────────────────────────────────────────────────┐
│  doc_extractor.py — untuk TIAP kategori ekstraksi:  │
│  (typography, page_layout, spacing, numbering,      │
│   figures_and_tables, page_count_limits,            │
│   document_structure_proposal, document_type)       │
│                                                     │
│  STEP 1 — RETRIEVE                                  │
│  _retrieve_chunks_multi(queries)                    │
│    ├── Embed setiap query → vektor 768 dim          │
│    │   (GoogleGenerativeAIEmbeddings)               │
│    └── Panggil Supabase RPC:                        │
│        match_document_chunks(                       │
│          query_embedding,                           │
│          match_count = top_k,                       │
│          filter_project_id                          │
│        )  ← cosine similarity search                │
│                                                     │
│  STEP 2 — EXPAND                                    │
│  _expand_to_full_headers(chunks)                    │
│    └── Ambil semua chunk dalam seksi yang sama      │
│        (chunk_parent = nama BAB)                    │
│        agar konteks tidak terpotong                 │
│                                                     │
│  STEP 3 — AUGMENT                                   │
│  render_prompt(chunks, template)                    │
│    └── Gabungkan chunks → string context            │
│        Inject ke {context} dalam template prompt    │
│                                                     │
│  STEP 4 — GENERATE                                  │
│  LLM call:                                          │
│    Primary : ChatGroq (LLaMA-3.3-70b-versatile)    │
│    Fallback: ChatGoogleGenerativeAI (Gemini Flash)  │
│    Output  : JSON terstruktur (with_structured_output)│
│                                                     │
│  STEP 5 — VALIDATE & STORE                          │
│  Parse → Pydantic model (models.py)                 │
│  Tiap field punya sources: [chunk_index, page, snip]│
└─────────────────────────────────────────────────────┘
        │
        ▼
  [Supabase: tabel document_metadata]
  ┌──────────────────────────────────┐
  │ project_id                       │
  │ payload (JSONB):                 │
  │   typography: {..., sources:[]}  │
  │   page_layout: {...}             │
  │   spacing: {...}                 │
  │   numbering: {...}               │
  │   figures_and_tables: {...}      │
  │   page_count_limits: {...}       │
  │   document_structure: {...}      │
  │ extracted_at                     │
  └──────────────────────────────────┘


╔══════════════════════════════════════════════════════════════╗
║                    FASE 3: VALIDASI                          ║
║           (perintah: python manage.py validate)              ║
╚══════════════════════════════════════════════════════════════╝

  [File DOCX mahasiswa] + [document_metadata dari Supabase]
        │
        ▼
┌─────────────────────────────────────────────────────┐
│  docx_property_extractor.py                         │
│  Ekstrak properti fisik DOCX:                       │
│  font, ukuran, margin, spasi, dll.                  │
└─────────────────────────────────────────────────────┘
        │
        ▼
┌─────────────────────────────────────────────────────┐
│  rule_validator.py                                  │
│  Bandingkan: expected (dari metadata) vs actual     │
│  Output: pass/fail per rule + pesan kesalahan       │
└─────────────────────────────────────────────────────┘
        │
        ▼
┌─────────────────────────────────────────────────────┐
│  validator.py                                       │
│  Orkestrator: kumpulkan semua hasil → ValidationResult│
│  Kembalikan ke ai-backend → frontend               │
└─────────────────────────────────────────────────────┘


╔══════════════════════════════════════════════════════════════╗
║                  FASE 4: GENERASI DOCX                       ║
║             (perintah: python manage.py docx)                ║
╚══════════════════════════════════════════════════════════════╝

  [document_metadata] + [document_chunks]
        │
        ▼
┌─────────────────────────────────────────────────────┐
│  generator.py → docx_renderer.py                    │
│  Render template DOCX dengan:                       │
│  - Isi bab dari chunks                              │
│  - Format sesuai metadata (font, margin, spasi)     │
│  - Placeholder instruksional dari                   │
│    instructional_placeholder_builder.py             │
└─────────────────────────────────────────────────────┘
        │
        ▼
  [File output .docx] → upload via storage.py → Supabase Storage