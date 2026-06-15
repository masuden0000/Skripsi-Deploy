ai/
├── manage.py                          ← CLI entry point (setup / extract / docx / validate)
├── model_ai/
│   ├── config.py                      ← Konfigurasi env, API key rotation
│   ├── metadata_repository.py         ← CRUD ke tabel document_metadata (Supabase)
│   ├── storage.py                     ← Upload file ke Supabase Storage
│   │
│   ├── loader/                        ── FASE 1: INGESTION
│   │   ├── pdf_extractor.py           ← PDF → Markdown
│   │   ├── chunk_builder.py           ← Markdown → Chunks (section-aware)
│   │   └── supabase_ingest.py         ← Embed chunks → simpan ke pgvector
│   │
│   ├── extractor/                     ── FASE 2: RETRIEVAL & EXTRACTION
│   │   ├── doc_extractor.py           ← Orkestrator RAG (retrieve → augment → generate)
│   │   ├── models.py                  ← Pydantic output schema tiap kategori
│   │   ├── prompts.py                 ← Registry prompt loader dari file .md
│   │   └── prompts/                   ← Template prompt + query semantik
│   │       ├── typography.md
│   │       ├── page_layout.md
│   │       ├── spacing.md
│   │       ├── numbering.md
│   │       ├── figures_and_tables.md
│   │       ├── page_count_limits.md
│   │       ├── document_structure_proposal.md
│   │       └── document_type.md
│   │
│   ├── validation/                    ── FASE 3: VALIDASI
│   │   ├── validator.py               ← Orkestrator validasi
│   │   ├── rule_validator.py          ← Komparasi expected vs actual
│   │   ├── docx_property_extractor.py ← Ekstrak properti fisik dari DOCX
│   │   └── models.py                  ← Pydantic schema hasil validasi
│   │
│   └── docx/                          ── FASE 4: GENERASI DOCX
│       ├── generator.py               ← Entry point generate DOCX
│       ├── docx_renderer.py           ← Render konten ke file DOCX
│       ├── metadata_loader.py         ← Load metadata dari Supabase
│       ├── chunk_loader.py            ← Load chunks dari Supabase
│       └── instructional_placeholder_builder.py ← Buat placeholder instruksional