# Design Spec: Document Metadata Extractor (`doc_extractor`)

**Date:** 2026-04-20
**Project:** experiments/pymupdf4llm
**Status:** Approved

---

## 1. Overview

Pipeline ekstraksi metadata terstruktur dari dokumen PDF. Dijalankan satu kali saat ingest, setelah chunks tersimpan di Supabase. Output berupa `DocumentMetadata` (Pydantic model) yang disimpan ke file JSON lokal dan tabel Supabase.

Pipeline ini **terpisah** dari `rag_service.py` (Q&A chat). Keduanya hanya berbagi infrastruktur yang sama: Supabase vector store dan Gemini embedding.

---

## 2. Posisi dalam Ingest Pipeline

```
manage.py setup   →  pdf_extractor.py     (PDF → chunks → output_chunks.json)
                  →  supabase_ingest.py   (chunks → Supabase document_chunks)
manage.py extract →  doc_extractor.py     (Supabase → DocumentMetadata → output.json + Supabase)
```

`doc_extractor` wajib dijalankan **setelah** `supabase_ingest` karena retrieval dilakukan via Supabase vector search.

---

## 3. Struktur Modul Baru

```
experiments/pymupdf4llm/model_ai/
└── extractor/
    ├── __init__.py
    ├── doc_extractor.py        # orchestrator utama
    ├── models.py               # semua Pydantic models
    └── prompts/                # satu .md per top-level key
        ├── typography.md
        ├── page_layout.md
        ├── spacing.md
        ├── document_structure_proposal.md
        ├── document_structure_laporan_kemajuan.md
        ├── document_structure_laporan_akhir.md
        ├── numbering.md
        ├── figures_and_tables.md
        └── page_count_limits.md
```

---

## 4. Pydantic Models (`models.py`)

### 4.1 Source Citation

```python
class Source(BaseModel):
    chunk_id: str
    page_start: int
    page_end: int
    header: str       # nilai chunk_parent dari Supabase
    snippet: str      # ±100 karakter teks relevan dari chunk
```

### 4.2 Sub-Models (satu per key)

Setiap sub-model merepresentasikan satu top-level key dari `output.json`. Semua menyertakan field `sources: list[Source]`.

```python
class TypographyInfo(BaseModel):
    font_family: str | None
    font_size_body_pt: int | None
    font_size_heading_pt: str | None
    heading_style: str | None
    heading_capitalization: str | None
    sources: list[Source]

class PageLayoutInfo(BaseModel):
    margin_top_cm: float | None
    margin_bottom_cm: float | None
    margin_left_cm: float | None
    margin_right_cm: float | None
    paper_size: str | None
    orientation: str | None
    columns: int | None
    sources: list[Source]

class SpacingInfo(BaseModel):
    line_spacing_body: float | None
    paragraph_alignment: str | None
    paragraph_first_indent: str | None
    hanging_indent_references: str | None
    sources: list[Source]

class BabItem(BaseModel):
    bab_number: str
    title: str

class DocumentStructureInfo(BaseModel):
    halaman_sampul: bool | None
    halaman_pengesahan: bool | None
    ringkasan: bool | None
    daftar_isi: bool | None
    daftar_gambar: str | None
    daftar_tabel: str | None
    daftar_lampiran: str | None
    bab_list: list[BabItem]
    daftar_pustaka: bool | None
    lampiran: bool | None
    max_halaman_inti: int | None
    format_nama_file: str | None
    sources: list[Source]

class NumberingInfo(BaseModel):
    preliminary_page_format: str | None
    preliminary_page_position: str | None
    preliminary_page_start_from: str | None
    content_page_format: str | None
    content_page_position: str | None
    content_page_start_from: str | None
    chapter_numbering_format: str | None
    sub_chapter_format: str | None
    figure_numbering_format: str | None
    table_numbering_format: str | None
    sources: list[Source]

class FiguresTablesInfo(BaseModel):
    table_caption_position: str | None
    figure_caption_position: str | None
    caption_format_figure: str | None
    caption_format_table: str | None
    source_required_if_not_own: bool | None
    max_width_constraint: str | None
    sources: list[Source]

class PageCountInfo(BaseModel):
    proposal_halaman_inti_maks: int | None
    laporan_kemajuan_halaman_inti_maks: int | None
    laporan_akhir_halaman_inti_maks: int | None
    catatan: str | None
    sources: list[Source]
```

### 4.3 Root Model

```python
class DocumentMetadata(BaseModel):
    document_type: str | None
    source_document: str | None
    typography: TypographyInfo
    page_layout: PageLayoutInfo
    spacing: SpacingInfo
    document_structure_proposal: DocumentStructureInfo
    document_structure_laporan_kemajuan: DocumentStructureInfo
    document_structure_laporan_akhir: DocumentStructureInfo
    numbering: NumberingInfo
    figures_and_tables: FiguresTablesInfo
    page_count_limits: PageCountInfo
```

---

## 5. Prompt File Format (`prompts/<key>.md`)

Setiap file prompt menggunakan frontmatter YAML untuk menyimpan query string embedding:

```markdown
---
query: "font huruf ukuran tipografi heading body Times New Roman"
---

# Extraction Task: Typography

## Context
{context}

## Task
Ekstrak informasi tipografi dokumen dari konteks di atas.
Isi field sesuai informasi yang ditemukan. Jika tidak ditemukan, gunakan null.
Jawab berdasarkan konteks saja — jangan gunakan pengetahuan umum.

## Output Fields
- font_family: nama font yang digunakan (contoh: "Times New Roman")
- font_size_body_pt: ukuran font body dalam pt (integer)
- font_size_heading_pt: ukuran font heading (string, karena bisa berisi keterangan)
- heading_style: gaya heading (contoh: "Bold")
- heading_capitalization: aturan kapitalisasi heading
```

Template `{context}` diisi runtime dengan teks chunk yang di-retrieve dari Supabase.

---

## 6. Alur Kerja `doc_extractor.py`

```
untuk setiap (key, prompt_file, SubModel) dalam KEY_REGISTRY:
  1. baca prompts/<key>.md → parse frontmatter → ambil query string
  2. embed query string via Gemini embedding-001 (768 dim)
  3. Supabase RPC match_document_chunks → top-K chunks
  4. format {context} dari teks chunks yang di-retrieve
  5. render prompt template dengan {context}
  6. LLM.with_structured_output(SubModel) → instance Pydantic
  7. build sources[] dari metadata chunks (chunk_id, page, header, snippet)
  8. inject sources ke instance Pydantic

gabungkan semua sub-model → DocumentMetadata

simpan:
  - data/output.json (overwrite)
  - Supabase tabel document_metadata (upsert by source_document)
```

### KEY_REGISTRY (urutan eksekusi)

```python
KEY_REGISTRY = [
    ("typography",                          "prompts/typography.md",                         TypographyInfo),
    ("page_layout",                         "prompts/page_layout.md",                        PageLayoutInfo),
    ("spacing",                             "prompts/spacing.md",                            SpacingInfo),
    ("document_structure_proposal",         "prompts/document_structure_proposal.md",        DocumentStructureInfo),
    ("document_structure_laporan_kemajuan", "prompts/document_structure_laporan_kemajuan.md",DocumentStructureInfo),
    ("document_structure_laporan_akhir",    "prompts/document_structure_laporan_akhir.md",   DocumentStructureInfo),
    ("numbering",                           "prompts/numbering.md",                          NumberingInfo),
    ("figures_and_tables",                  "prompts/figures_and_tables.md",                 FiguresTablesInfo),
    ("page_count_limits",                   "prompts/page_count_limits.md",                  PageCountInfo),
]
```

---

## 7. Storage

### 7.1 Local JSON (`data/output.json`)

Output `DocumentMetadata.model_dump()` ditulis ke `data/output.json`. File ini di-overwrite setiap kali `manage.py extract` dijalankan.

### 7.2 Supabase Tabel `document_metadata`

```sql
create table document_metadata (
    id            uuid        primary key default gen_random_uuid(),
    source_doc    text        unique not null,
    extracted_at  timestamptz not null default now(),
    payload       jsonb       not null
);
```

Satu row per dokumen. `payload` berisi full `DocumentMetadata` sebagai JSONB. Upsert by `source_doc` — re-extract tidak membuat duplikat.

---

## 8. Entry Point (`manage.py`)

Command baru:

```
python manage.py extract
```

Memanggil `doc_extractor.py`, mencetak progress per key, dan melaporkan path output file.

---

## 9. Dependencies & Environment

Tidak ada dependency baru — pipeline menggunakan:
- `langchain-google-genai` (sudah ada, untuk embedding + LLM)
- `supabase` (sudah ada)
- `pydantic` (sudah ada, dipakai `rag_service.py`)
- `python-frontmatter` (**baru**) — untuk parse frontmatter YAML dari file `.md`

Tambahkan `python-frontmatter` ke `requirements.txt`.

---

## 10. Out of Scope

- Runtime extraction (dipanggil saat user bertanya)
- Integrasi output `document_metadata` ke dalam chat RAG pipeline
- Multi-dokumen extraction dalam satu run
- Re-extract per-key selektif (extract ulang satu key tanpa re-run semua)
