# Document Metadata Extractor Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build an ingest-time pipeline (`manage.py extract`) that extracts structured document metadata from Supabase chunks using per-key `.md` prompt files and Pydantic models, saving results to `data/output.json` and a new Supabase `document_metadata` table.

**Architecture:** For each of 9 metadata keys, the extractor reads a `.md` prompt file (frontmatter contains the embedding query string), retrieves top-K chunks via Supabase vector RPC, renders the prompt with chunk context, calls Gemini LLM with `with_structured_output()` against an `*Extracted` Pydantic model (no `sources` field), then builds `Source` citations from retrieved chunk metadata and merges them into the final `*Info` model. All results assemble into a root `DocumentMetadata` and persist to JSON + Supabase.

**Tech Stack:** Python 3.11+, Pydantic v2, `langchain-google-genai`, `supabase-py`, `python-frontmatter`

---

## File Map

**Create:**
- `experiments/pymupdf4llm/model_ai/extractor/__init__.py`
- `experiments/pymupdf4llm/model_ai/extractor/models.py`
- `experiments/pymupdf4llm/model_ai/extractor/doc_extractor.py`
- `experiments/pymupdf4llm/model_ai/extractor/prompts/typography.md`
- `experiments/pymupdf4llm/model_ai/extractor/prompts/page_layout.md`
- `experiments/pymupdf4llm/model_ai/extractor/prompts/spacing.md`
- `experiments/pymupdf4llm/model_ai/extractor/prompts/document_structure_proposal.md`
- `experiments/pymupdf4llm/model_ai/extractor/prompts/document_structure_laporan_kemajuan.md`
- `experiments/pymupdf4llm/model_ai/extractor/prompts/document_structure_laporan_akhir.md`
- `experiments/pymupdf4llm/model_ai/extractor/prompts/numbering.md`
- `experiments/pymupdf4llm/model_ai/extractor/prompts/figures_and_tables.md`
- `experiments/pymupdf4llm/model_ai/extractor/prompts/page_count_limits.md`
- `experiments/pymupdf4llm/infra/supabase_metadata.sql`
- `experiments/pymupdf4llm/tests/__init__.py`
- `experiments/pymupdf4llm/tests/extractor/__init__.py`
- `experiments/pymupdf4llm/tests/extractor/test_models.py`
- `experiments/pymupdf4llm/tests/extractor/test_doc_extractor.py`

**Modify:**
- `experiments/pymupdf4llm/requirements.txt` — add `python-frontmatter`
- `experiments/pymupdf4llm/manage.py` — add `extract` command

---

## Task 1: Add dependency + create extractor package skeleton

**Files:**
- Modify: `experiments/pymupdf4llm/requirements.txt`
- Create: `experiments/pymupdf4llm/model_ai/extractor/__init__.py`
- Create: `experiments/pymupdf4llm/model_ai/extractor/prompts/` (directory only)

- [ ] **Step 1: Add python-frontmatter to requirements.txt**

Tambahkan baris berikut setelah baris `pymupdf4llm` di `requirements.txt`:

```
python-frontmatter>=1.0.0,<2.0.0
```

- [ ] **Step 2: Install dependency**

```bash
cd experiments/pymupdf4llm
pip install python-frontmatter
```

Expected: `Successfully installed python-frontmatter-...`

- [ ] **Step 3: Create extractor package**

Buat file `experiments/pymupdf4llm/model_ai/extractor/__init__.py` dengan isi:

```python
```

(file kosong — hanya package marker)

- [ ] **Step 4: Create prompts directory**

```bash
mkdir -p experiments/pymupdf4llm/model_ai/extractor/prompts
```

- [ ] **Step 5: Commit**

```bash
git add experiments/pymupdf4llm/requirements.txt experiments/pymupdf4llm/model_ai/extractor/__init__.py
git commit -m "feat: add python-frontmatter dependency and extractor package skeleton"
```

---

## Task 2: Pydantic models (`models.py`)

**Files:**
- Create: `experiments/pymupdf4llm/model_ai/extractor/models.py`
- Create: `experiments/pymupdf4llm/tests/__init__.py`
- Create: `experiments/pymupdf4llm/tests/extractor/__init__.py`
- Create: `experiments/pymupdf4llm/tests/extractor/test_models.py`

- [ ] **Step 1: Create test files (package markers)**

Buat `experiments/pymupdf4llm/tests/__init__.py` (kosong) dan `experiments/pymupdf4llm/tests/extractor/__init__.py` (kosong).

- [ ] **Step 2: Write failing tests**

Buat `experiments/pymupdf4llm/tests/extractor/test_models.py`:

```python
import pytest
from pydantic import ValidationError

from model_ai.extractor.models import (
    BabItem,
    DocumentMetadata,
    DocumentStructureExtracted,
    DocumentStructureInfo,
    FiguresTablesExtracted,
    FiguresTablesInfo,
    NumberingExtracted,
    NumberingInfo,
    PageCountExtracted,
    PageCountInfo,
    PageLayoutExtracted,
    PageLayoutInfo,
    Source,
    SpacingExtracted,
    SpacingInfo,
    TypographyExtracted,
    TypographyInfo,
)


def test_source_stores_all_citation_fields():
    s = Source(
        chunk_index=5,
        page_start=2,
        page_end=3,
        header="Format Penulisan",
        snippet="Times New Roman 12pt",
    )
    assert s.chunk_index == 5
    assert s.page_start == 2
    assert s.page_end == 3
    assert s.header == "Format Penulisan"
    assert s.snippet == "Times New Roman 12pt"


def test_typography_extracted_all_fields_optional():
    t = TypographyExtracted()
    assert t.font_family is None
    assert t.font_size_body_pt is None


def test_typography_info_merges_extracted_and_sources():
    src = Source(chunk_index=1, page_start=1, page_end=1, header="H", snippet="s")
    extracted = TypographyExtracted(font_family="Times New Roman", font_size_body_pt=12)
    info = TypographyInfo(**extracted.model_dump(), sources=[src])
    assert info.font_family == "Times New Roman"
    assert info.font_size_body_pt == 12
    assert len(info.sources) == 1
    assert info.sources[0].chunk_index == 1


def test_bab_item_fields():
    bab = BabItem(bab_number="BAB 1", title="PENDAHULUAN")
    assert bab.bab_number == "BAB 1"
    assert bab.title == "PENDAHULUAN"


def test_document_structure_info_has_bab_list_and_sources():
    src = Source(chunk_index=2, page_start=1, page_end=1, header="H", snippet="s")
    bab = BabItem(bab_number="BAB 1", title="PENDAHULUAN")
    extracted = DocumentStructureExtracted(bab_list=[bab])
    info = DocumentStructureInfo(**extracted.model_dump(), sources=[src])
    assert len(info.bab_list) == 1
    assert info.bab_list[0].title == "PENDAHULUAN"
    assert len(info.sources) == 1


def test_document_metadata_instantiates_with_all_sub_models():
    empty_src: list[Source] = []
    meta = DocumentMetadata(
        typography=TypographyInfo(sources=empty_src),
        page_layout=PageLayoutInfo(sources=empty_src),
        spacing=SpacingInfo(sources=empty_src),
        document_structure_proposal=DocumentStructureInfo(bab_list=[], sources=empty_src),
        document_structure_laporan_kemajuan=DocumentStructureInfo(bab_list=[], sources=empty_src),
        document_structure_laporan_akhir=DocumentStructureInfo(bab_list=[], sources=empty_src),
        numbering=NumberingInfo(sources=empty_src),
        figures_and_tables=FiguresTablesInfo(sources=empty_src),
        page_count_limits=PageCountInfo(sources=empty_src),
    )
    assert meta.typography.font_family is None
    assert meta.source_document is None


def test_document_metadata_serializes_to_dict():
    empty_src: list[Source] = []
    meta = DocumentMetadata(
        typography=TypographyInfo(sources=empty_src),
        page_layout=PageLayoutInfo(sources=empty_src),
        spacing=SpacingInfo(sources=empty_src),
        document_structure_proposal=DocumentStructureInfo(bab_list=[], sources=empty_src),
        document_structure_laporan_kemajuan=DocumentStructureInfo(bab_list=[], sources=empty_src),
        document_structure_laporan_akhir=DocumentStructureInfo(bab_list=[], sources=empty_src),
        numbering=NumberingInfo(sources=empty_src),
        figures_and_tables=FiguresTablesInfo(sources=empty_src),
        page_count_limits=PageCountInfo(sources=empty_src),
    )
    d = meta.model_dump()
    assert "typography" in d
    assert "sources" in d["typography"]
```

- [ ] **Step 3: Run tests to verify they fail**

```bash
cd experiments/pymupdf4llm
python -m pytest tests/extractor/test_models.py -v
```

Expected: `ModuleNotFoundError: No module named 'model_ai.extractor.models'`

- [ ] **Step 4: Implement `models.py`**

Buat `experiments/pymupdf4llm/model_ai/extractor/models.py`:

```python
from pydantic import BaseModel


class Source(BaseModel):
    chunk_index: int
    page_start: int
    page_end: int
    header: str
    snippet: str


# --- Typography ---

class TypographyExtracted(BaseModel):
    font_family: str | None = None
    font_size_body_pt: int | None = None
    font_size_heading_pt: str | None = None
    heading_style: str | None = None
    heading_capitalization: str | None = None


class TypographyInfo(TypographyExtracted):
    sources: list[Source] = []


# --- Page Layout ---

class PageLayoutExtracted(BaseModel):
    margin_top_cm: float | None = None
    margin_bottom_cm: float | None = None
    margin_left_cm: float | None = None
    margin_right_cm: float | None = None
    paper_size: str | None = None
    orientation: str | None = None
    columns: int | None = None


class PageLayoutInfo(PageLayoutExtracted):
    sources: list[Source] = []


# --- Spacing ---

class SpacingExtracted(BaseModel):
    line_spacing_body: float | None = None
    paragraph_alignment: str | None = None
    paragraph_first_indent: str | None = None
    hanging_indent_references: str | None = None


class SpacingInfo(SpacingExtracted):
    sources: list[Source] = []


# --- Document Structure ---

class BabItem(BaseModel):
    bab_number: str
    title: str


class DocumentStructureExtracted(BaseModel):
    halaman_sampul: bool | None = None
    halaman_pengesahan: bool | None = None
    ringkasan: bool | None = None
    daftar_isi: bool | None = None
    daftar_gambar: str | None = None
    daftar_tabel: str | None = None
    daftar_lampiran: str | None = None
    bab_list: list[BabItem] = []
    daftar_pustaka: bool | None = None
    lampiran: bool | None = None
    max_halaman_inti: int | None = None
    format_nama_file: str | None = None


class DocumentStructureInfo(DocumentStructureExtracted):
    sources: list[Source] = []


# --- Numbering ---

class NumberingExtracted(BaseModel):
    preliminary_page_format: str | None = None
    preliminary_page_position: str | None = None
    preliminary_page_start_from: str | None = None
    content_page_format: str | None = None
    content_page_position: str | None = None
    content_page_start_from: str | None = None
    chapter_numbering_format: str | None = None
    sub_chapter_format: str | None = None
    figure_numbering_format: str | None = None
    table_numbering_format: str | None = None


class NumberingInfo(NumberingExtracted):
    sources: list[Source] = []


# --- Figures & Tables ---

class FiguresTablesExtracted(BaseModel):
    table_caption_position: str | None = None
    figure_caption_position: str | None = None
    caption_format_figure: str | None = None
    caption_format_table: str | None = None
    source_required_if_not_own: bool | None = None
    max_width_constraint: str | None = None


class FiguresTablesInfo(FiguresTablesExtracted):
    sources: list[Source] = []


# --- Page Count Limits ---

class PageCountExtracted(BaseModel):
    proposal_halaman_inti_maks: int | None = None
    laporan_kemajuan_halaman_inti_maks: int | None = None
    laporan_akhir_halaman_inti_maks: int | None = None
    catatan: str | None = None


class PageCountInfo(PageCountExtracted):
    sources: list[Source] = []


# --- Root Model ---

class DocumentMetadata(BaseModel):
    document_type: str | None = None
    source_document: str | None = None
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

- [ ] **Step 5: Run tests to verify they pass**

```bash
cd experiments/pymupdf4llm
python -m pytest tests/extractor/test_models.py -v
```

Expected: `9 passed`

- [ ] **Step 6: Commit**

```bash
git add model_ai/extractor/models.py tests/
git commit -m "feat: add Pydantic models for document metadata extraction with source citations"
```

---

## Task 3: Prompt files (9 file `.md`)

**Files:**
- Create: semua file di `experiments/pymupdf4llm/model_ai/extractor/prompts/`

- [ ] **Step 1: Buat `typography.md`**

```markdown
---
query: "font huruf ukuran tipografi heading body Times New Roman"
---

# Extraction Task: Typography

## Context
{context}

## Task
Ekstrak informasi tipografi dokumen dari konteks di atas.
Jika informasi tidak ditemukan dalam konteks, gunakan null.
Jangan gunakan pengetahuan umum — hanya berdasarkan konteks yang diberikan.

## Output Fields
- font_family: nama font utama dokumen (contoh: "Times New Roman")
- font_size_body_pt: ukuran font body dalam satuan pt sebagai integer (contoh: 12)
- font_size_heading_pt: ukuran font heading — boleh string jika ada keterangan tambahan
- heading_style: gaya penulisan heading (contoh: "Bold")
- heading_capitalization: aturan kapitalisasi judul BAB (contoh: "ALL CAPS untuk judul BAB")
```

- [ ] **Step 2: Buat `page_layout.md`**

```markdown
---
query: "margin halaman ukuran kertas A4 portrait landscape kolom batas tepi"
---

# Extraction Task: Page Layout

## Context
{context}

## Task
Ekstrak informasi tata letak halaman dari konteks di atas.
Jika tidak ditemukan, gunakan null.

## Output Fields
- margin_top_cm: margin atas dalam cm (float)
- margin_bottom_cm: margin bawah dalam cm (float)
- margin_left_cm: margin kiri dalam cm (float)
- margin_right_cm: margin kanan dalam cm (float)
- paper_size: ukuran kertas (contoh: "A4")
- orientation: orientasi halaman (contoh: "Portrait")
- columns: jumlah kolom teks (integer)
```

- [ ] **Step 3: Buat `spacing.md`**

```markdown
---
query: "spasi baris paragraf rata kanan kiri justify indentasi menjorok"
---

# Extraction Task: Spacing

## Context
{context}

## Task
Ekstrak informasi spasi dan format paragraf dari konteks di atas.
Jika tidak ditemukan, gunakan null.

## Output Fields
- line_spacing_body: spasi antar baris body (float, contoh: 1.15)
- paragraph_alignment: rata paragraf (contoh: "Justify (rata kiri dan kanan)")
- paragraph_first_indent: indentasi awal paragraf jika ada, null jika tidak ada
- hanging_indent_references: aturan hanging indent untuk daftar pustaka
```

- [ ] **Step 4: Buat `document_structure_proposal.md`**

```markdown
---
query: "struktur proposal BAB pendahuluan tinjauan pustaka lampiran halaman inti sistematika"
---

# Extraction Task: Document Structure (Proposal PKM)

## Context
{context}

## Task
Ekstrak struktur dokumen khusus untuk jenis PROPOSAL PKM dari konteks di atas.
Isi bab_list dengan semua BAB yang tercantum beserta judulnya (dalam urutan).
Gunakan null untuk field yang tidak disebutkan, false jika eksplisit tidak ada.

## Output Fields
- halaman_sampul: apakah ada halaman sampul (bool)
- halaman_pengesahan: apakah ada halaman pengesahan (bool)
- ringkasan: apakah ada ringkasan atau abstrak (bool)
- daftar_isi: apakah ada daftar isi (bool)
- daftar_gambar: keterangan daftar gambar (string atau null)
- daftar_tabel: keterangan daftar tabel (string atau null)
- daftar_lampiran: keterangan daftar lampiran (string atau null)
- bab_list: daftar BAB dalam format [{bab_number, title}]
- daftar_pustaka: apakah ada daftar pustaka (bool)
- lampiran: apakah ada lampiran (bool)
- max_halaman_inti: batas maksimum halaman inti (integer)
- format_nama_file: format nama file untuk pengumpulan (string)
```

- [ ] **Step 5: Buat `document_structure_laporan_kemajuan.md`**

```markdown
---
query: "struktur laporan kemajuan BAB target luaran hasil potensi rencana tahapan"
---

# Extraction Task: Document Structure (Laporan Kemajuan PKM)

## Context
{context}

## Task
Ekstrak struktur dokumen khusus untuk jenis LAPORAN KEMAJUAN dari konteks di atas.
Isi bab_list dengan semua BAB yang tercantum beserta judulnya (dalam urutan).
Gunakan null untuk field yang tidak disebutkan.

## Output Fields
- halaman_sampul: apakah ada halaman sampul (bool)
- halaman_pengesahan: apakah ada halaman pengesahan (bool)
- ringkasan: apakah ada ringkasan atau abstrak (bool)
- daftar_isi: apakah ada daftar isi (bool)
- daftar_gambar: keterangan daftar gambar (string atau null)
- daftar_tabel: keterangan daftar tabel (string atau null)
- daftar_lampiran: keterangan daftar lampiran (string atau null)
- bab_list: daftar BAB dalam format [{bab_number, title}]
- daftar_pustaka: apakah ada daftar pustaka (bool)
- lampiran: apakah ada lampiran (bool)
- max_halaman_inti: batas maksimum halaman inti (integer)
- format_nama_file: format nama file untuk pengumpulan (string)
```

- [ ] **Step 6: Buat `document_structure_laporan_akhir.md`**

```markdown
---
query: "struktur laporan akhir BAB tinjauan pustaka hasil dicapai potensi khusus penutup"
---

# Extraction Task: Document Structure (Laporan Akhir PKM)

## Context
{context}

## Task
Ekstrak struktur dokumen khusus untuk jenis LAPORAN AKHIR dari konteks di atas.
Isi bab_list dengan semua BAB yang tercantum beserta judulnya (dalam urutan).
Gunakan null untuk field yang tidak disebutkan.

## Output Fields
- halaman_sampul: apakah ada halaman sampul (bool)
- halaman_pengesahan: apakah ada halaman pengesahan (bool)
- ringkasan: apakah ada ringkasan atau abstrak (bool)
- daftar_isi: apakah ada daftar isi (bool)
- daftar_gambar: keterangan daftar gambar (string atau null)
- daftar_tabel: keterangan daftar tabel (string atau null)
- daftar_lampiran: keterangan daftar lampiran (string atau null)
- bab_list: daftar BAB dalam format [{bab_number, title}]
- daftar_pustaka: apakah ada daftar pustaka (bool)
- lampiran: apakah ada lampiran (bool)
- max_halaman_inti: batas maksimum halaman inti (integer)
- format_nama_file: format nama file untuk pengumpulan (string)
```

- [ ] **Step 7: Buat `numbering.md`**

```markdown
---
query: "penomoran halaman romawi arab sudut posisi format BAB sub-bab gambar tabel"
---

# Extraction Task: Numbering

## Context
{context}

## Task
Ekstrak informasi sistem penomoran halaman, bab, gambar, dan tabel dari konteks di atas.
Jika tidak ditemukan, gunakan null.

## Output Fields
- preliminary_page_format: format nomor halaman awal (contoh: "Romawi kecil (i, ii, iii, ...)")
- preliminary_page_position: posisi nomor halaman awal (contoh: "Sudut kanan bawah")
- preliminary_page_start_from: mulai dari halaman mana penomoran awal (contoh: "Daftar Isi (halaman i)")
- content_page_format: format nomor halaman isi (contoh: "Angka Arab (1, 2, 3, ...)")
- content_page_position: posisi nomor halaman isi (contoh: "Sudut kanan atas")
- content_page_start_from: mulai dari halaman mana penomoran isi
- chapter_numbering_format: format penomoran BAB (contoh: "BAB 1, BAB 2, BAB 3, ...")
- sub_chapter_format: format sub-bab (contoh: "4.1, 4.2, dst.")
- figure_numbering_format: format penomoran gambar (contoh: "Gambar 1., Gambar 2., dst.")
- table_numbering_format: format penomoran tabel (contoh: "Tabel 4.1, Tabel 1., dst.")
```

- [ ] **Step 8: Buat `figures_and_tables.md`**

```markdown
---
query: "keterangan gambar tabel caption di atas di bawah format sumber margin lebar"
---

# Extraction Task: Figures and Tables

## Context
{context}

## Task
Ekstrak aturan penulisan keterangan gambar dan tabel dari konteks di atas.
Jika tidak ditemukan, gunakan null.

## Output Fields
- table_caption_position: posisi keterangan tabel (contoh: "Di atas tabel")
- figure_caption_position: posisi keterangan gambar (contoh: "Di bawah gambar")
- caption_format_figure: format keterangan gambar (contoh: "Gambar [N]. [Judul Gambar] ([Sumber jika ada])")
- caption_format_table: format keterangan tabel (contoh: "Tabel [N.N] [Judul Tabel]")
- source_required_if_not_own: apakah sumber wajib dicantumkan jika bukan karya sendiri (bool)
- max_width_constraint: batasan lebar gambar/tabel
```

- [ ] **Step 9: Buat `page_count_limits.md`**

```markdown
---
query: "maksimum halaman inti batas halaman proposal laporan kemajuan akhir lampiran"
---

# Extraction Task: Page Count Limits

## Context
{context}

## Task
Ekstrak batas maksimum halaman untuk setiap jenis dokumen PKM dari konteks di atas.
Jika tidak ditemukan, gunakan null.

## Output Fields
- proposal_halaman_inti_maks: batas halaman inti untuk proposal (integer)
- laporan_kemajuan_halaman_inti_maks: batas halaman inti untuk laporan kemajuan (integer)
- laporan_akhir_halaman_inti_maks: batas halaman inti untuk laporan akhir (integer)
- catatan: catatan tambahan tentang penghitungan halaman inti
```

- [ ] **Step 10: Commit**

```bash
git add model_ai/extractor/prompts/
git commit -m "feat: add 9 extraction prompt files with frontmatter query strings"
```

---

## Task 4: Implement `doc_extractor.py` dengan unit tests

**Files:**
- Create: `experiments/pymupdf4llm/model_ai/extractor/doc_extractor.py`
- Create: `experiments/pymupdf4llm/tests/extractor/test_doc_extractor.py`

- [ ] **Step 1: Write failing tests**

Buat `experiments/pymupdf4llm/tests/extractor/test_doc_extractor.py`:

```python
import textwrap
from pathlib import Path

import pytest

from model_ai.extractor.doc_extractor import build_sources, load_prompt, render_prompt
from model_ai.extractor.models import Source


SAMPLE_CHUNKS = [
    {
        "chunk_index": 3,
        "page_start": 2,
        "page_end": 3,
        "chunk_parent": "Format Penulisan",
        "content": "Dokumen menggunakan font Times New Roman ukuran 12pt untuk body text dan heading.",
        "similarity": 0.91,
    }
]


def test_build_sources_maps_chunk_fields_to_source():
    sources = build_sources(SAMPLE_CHUNKS)
    assert len(sources) == 1
    s = sources[0]
    assert s.chunk_index == 3
    assert s.page_start == 2
    assert s.page_end == 3
    assert s.header == "Format Penulisan"
    assert "Times New Roman" in s.snippet


def test_build_sources_snippet_truncated_to_100_chars():
    long_chunks = [
        {
            "chunk_index": 1,
            "page_start": 1,
            "page_end": 1,
            "chunk_parent": "H",
            "content": "A" * 200,
            "similarity": 0.8,
        }
    ]
    sources = build_sources(long_chunks)
    assert len(sources[0].snippet) <= 100


def test_build_sources_empty_chunks_returns_empty_list():
    assert build_sources([]) == []


def test_load_prompt_extracts_query_and_template(tmp_path: Path):
    prompt_file = tmp_path / "test.md"
    prompt_file.write_text(
        textwrap.dedent("""\
            ---
            query: "font huruf ukuran tipografi"
            ---

            # Task

            ## Context
            {context}

            ## Output
            Ekstrak font.
        """)
    )
    query, template = load_prompt(prompt_file)
    assert query == "font huruf ukuran tipografi"
    assert "{context}" in template
    assert "# Task" in template


def test_render_prompt_joins_chunk_contents():
    template = "## Context\n{context}\n"
    chunks = [
        {"content": "Chunk satu."},
        {"content": "Chunk dua."},
    ]
    result = render_prompt(template, chunks)
    assert "Chunk satu." in result
    assert "Chunk dua." in result
    assert "---" in result  # separator antara chunks


def test_render_prompt_with_no_chunks_yields_empty_context():
    template = "## Context\n{context}\n"
    result = render_prompt(template, [])
    assert "{context}" not in result
    assert result == "## Context\n\n"
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd experiments/pymupdf4llm
python -m pytest tests/extractor/test_doc_extractor.py -v
```

Expected: `ModuleNotFoundError: No module named 'model_ai.extractor.doc_extractor'`

- [ ] **Step 3: Implement `doc_extractor.py`**

Buat `experiments/pymupdf4llm/model_ai/extractor/doc_extractor.py`:

```python
import json
import os
from pathlib import Path
from typing import Any, Type

import frontmatter
from langchain_google_genai import ChatGoogleGenerativeAI, GoogleGenerativeAIEmbeddings
from pydantic import BaseModel
from supabase import create_client

from model_ai.extractor.models import (
    DocumentMetadata,
    DocumentStructureExtracted,
    DocumentStructureInfo,
    FiguresTablesExtracted,
    FiguresTablesInfo,
    NumberingExtracted,
    NumberingInfo,
    PageCountExtracted,
    PageCountInfo,
    PageLayoutExtracted,
    PageLayoutInfo,
    Source,
    SpacingExtracted,
    SpacingInfo,
    TypographyExtracted,
    TypographyInfo,
)

APP_DIR = Path(__file__).resolve().parents[2]
PROMPTS_DIR = Path(__file__).resolve().parent / "prompts"
OUTPUT_PATH = APP_DIR / "data" / "output.json"
LLM_MODEL = "gemini-2.0-flash"

KEY_REGISTRY: list[tuple[str, Type[BaseModel], Type[BaseModel]]] = [
    ("typography", TypographyExtracted, TypographyInfo),
    ("page_layout", PageLayoutExtracted, PageLayoutInfo),
    ("spacing", SpacingExtracted, SpacingInfo),
    ("document_structure_proposal", DocumentStructureExtracted, DocumentStructureInfo),
    ("document_structure_laporan_kemajuan", DocumentStructureExtracted, DocumentStructureInfo),
    ("document_structure_laporan_akhir", DocumentStructureExtracted, DocumentStructureInfo),
    ("numbering", NumberingExtracted, NumberingInfo),
    ("figures_and_tables", FiguresTablesExtracted, FiguresTablesInfo),
    ("page_count_limits", PageCountExtracted, PageCountInfo),
]


def build_sources(chunks: list[dict]) -> list[Source]:
    return [
        Source(
            chunk_index=c["chunk_index"],
            page_start=c["page_start"],
            page_end=c["page_end"],
            header=c["chunk_parent"],
            snippet=c["content"][:100],
        )
        for c in chunks
    ]


def load_prompt(prompt_path: Path) -> tuple[str, str]:
    """Parse frontmatter YAML dari .md file. Return (query_string, template_body)."""
    post = frontmatter.load(str(prompt_path))
    query: str = post["query"]
    template: str = post.content
    return query, template


def render_prompt(template: str, chunks: list[dict]) -> str:
    """Ganti {context} di template dengan gabungan teks chunks."""
    context = "\n\n---\n\n".join(c["content"] for c in chunks)
    return template.replace("{context}", context)


def _retrieve_chunks(query: str) -> list[dict]:
    """Embed query lalu retrieve top-K chunks dari Supabase via vector RPC."""
    google_api_key = os.environ["GOOGLE_API_KEY"]
    embedding_model = os.environ.get("EMBEDDING_MODEL_NAME", "models/text-embedding-004")
    top_k = int(os.environ.get("RAG_TOP_K", "5"))

    embeddings = GoogleGenerativeAIEmbeddings(
        model=embedding_model,
        google_api_key=google_api_key,
    )
    vector = embeddings.embed_query(query)

    supabase = create_client(os.environ["SUPABASE_URL"], os.environ["SUPABASE_KEY"])
    result = supabase.rpc(
        "match_document_chunks",
        {"query_embedding": vector, "match_count": top_k},
    ).execute()
    return result.data or []


def _extract_key(
    prompt_path: Path,
    extracted_cls: Type[BaseModel],
    info_cls: Type[BaseModel],
) -> Any:
    """Jalankan satu siklus ekstraksi: retrieve → prompt → LLM → merge sources."""
    query, template = load_prompt(prompt_path)
    chunks = _retrieve_chunks(query)
    prompt = render_prompt(template, chunks)

    llm = ChatGoogleGenerativeAI(
        model=LLM_MODEL,
        google_api_key=os.environ["GOOGLE_API_KEY"],
    )
    chain = llm.with_structured_output(extracted_cls)
    extracted = chain.invoke(prompt)

    sources = build_sources(chunks)
    return info_cls(**extracted.model_dump(), sources=sources)


def extract_document_metadata() -> DocumentMetadata:
    results: dict[str, Any] = {}
    for key, extracted_cls, info_cls in KEY_REGISTRY:
        print(f"[extract] Memproses: {key} ...")
        results[key] = _extract_key(PROMPTS_DIR / f"{key}.md", extracted_cls, info_cls)
        print(f"[extract] Selesai:   {key}")

    results["source_document"] = Path(APP_DIR.parent / "file.pdf").name
    return DocumentMetadata(**results)


def save_to_json(metadata: DocumentMetadata) -> None:
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(metadata.model_dump(), f, ensure_ascii=False, indent=4)
    print(f"[extract] JSON disimpan: {OUTPUT_PATH}")


def save_to_supabase(metadata: DocumentMetadata) -> None:
    supabase = create_client(os.environ["SUPABASE_URL"], os.environ["SUPABASE_KEY"])
    payload = metadata.model_dump()
    source_doc = payload.get("source_document") or "unknown"
    supabase.table("document_metadata").upsert(
        {"source_doc": source_doc, "payload": payload},
        on_conflict="source_doc",
    ).execute()
    print(f"[extract] Supabase upsert: source_doc={source_doc}")


def run_extraction() -> None:
    metadata = extract_document_metadata()
    save_to_json(metadata)
    save_to_supabase(metadata)
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
cd experiments/pymupdf4llm
python -m pytest tests/extractor/test_doc_extractor.py -v
```

Expected: `6 passed`

- [ ] **Step 5: Run all tests (regression check)**

```bash
python -m pytest tests/ -v
```

Expected: `15 passed` (9 dari test_models + 6 dari test_doc_extractor)

- [ ] **Step 6: Commit**

```bash
git add model_ai/extractor/doc_extractor.py tests/extractor/test_doc_extractor.py
git commit -m "feat: implement doc_extractor orchestrator with helper functions"
```

---

## Task 5: Supabase migration — tabel `document_metadata`

**Files:**
- Create: `experiments/pymupdf4llm/infra/supabase_metadata.sql`

- [ ] **Step 1: Buat file migration SQL**

Buat `experiments/pymupdf4llm/infra/supabase_metadata.sql`:

```sql
create table if not exists public.document_metadata (
    id           uuid        primary key default gen_random_uuid(),
    source_doc   text        unique not null,
    extracted_at timestamptz not null default timezone('utc', now()),
    payload      jsonb       not null
);

comment on table public.document_metadata is
    'Metadata terstruktur hasil ekstraksi doc_extractor. Satu row per dokumen PDF.';
comment on column public.document_metadata.source_doc is
    'Nama file PDF sumber (contoh: file.pdf). Dipakai sebagai upsert key.';
comment on column public.document_metadata.payload is
    'Full DocumentMetadata as JSON, termasuk sources per field.';
```

- [ ] **Step 2: Jalankan migration di Supabase**

Buka Supabase Dashboard → SQL Editor → paste isi file `supabase_metadata.sql` → Run.

Verifikasi: tabel `document_metadata` muncul di Table Editor.

- [ ] **Step 3: Commit**

```bash
git add infra/supabase_metadata.sql
git commit -m "feat: add document_metadata Supabase table migration"
```

---

## Task 6: Tambahkan command `extract` ke `manage.py`

**Files:**
- Modify: `experiments/pymupdf4llm/manage.py`

- [ ] **Step 1: Tambahkan wrapper function `run_extract()`**

Tambahkan setelah fungsi `run_setup()` (sebelum `def main()`):

```python
def run_extract() -> None:
    from model_ai.extractor.doc_extractor import run_extraction

    run_extraction()
```

- [ ] **Step 2: Tambahkan subparser `extract`**

Di dalam `main()`, setelah blok `subparsers.add_parser("ui", ...)`:

```python
    subparsers.add_parser(
        "extract",
        help="Ekstrak metadata terstruktur dari chunks Supabase dan simpan ke output.json.",
    )
```

- [ ] **Step 3: Tambahkan handler `extract`**

Di dalam `main()`, setelah blok `if args.command == "ui":`:

```python
    if args.command == "extract":
        run_extract()
        return
```

- [ ] **Step 4: Verifikasi help output**

```bash
cd experiments/pymupdf4llm
python manage.py --help
```

Expected output berisi:
```
  extract     Ekstrak metadata terstruktur dari chunks Supabase dan simpan ke output.json.
```

- [ ] **Step 5: Commit**

```bash
git add manage.py
git commit -m "feat: add extract command to manage.py CLI"
```

---

## Task 7: Smoke test end-to-end

> **Prasyarat:** `manage.py setup` sudah dijalankan sebelumnya sehingga chunks ada di Supabase. File `.env` berisi `GOOGLE_API_KEY`, `SUPABASE_URL`, `SUPABASE_KEY`.

- [ ] **Step 1: Jalankan extraction**

```bash
cd experiments/pymupdf4llm
python manage.py extract
```

Expected output (per key):
```
[extract] Memproses: typography ...
[extract] Selesai:   typography
[extract] Memproses: page_layout ...
...
[extract] JSON disimpan: .../data/output.json
[extract] Supabase upsert: source_doc=file.pdf
```

- [ ] **Step 2: Verifikasi output.json**

```bash
python -c "
import json
data = json.load(open('data/output.json'))
print('Keys:', list(data.keys()))
print('Typography font:', data['typography']['font_family'])
print('Sources count:', len(data['typography']['sources']))
"
```

Expected:
- `Keys:` berisi semua 11 key (`document_type`, `source_document`, dan 9 sub-model)
- `Typography font:` bukan `None` (misal: `Times New Roman`)
- `Sources count:` >= 1

- [ ] **Step 3: Verifikasi Supabase**

Buka Supabase Dashboard → Table Editor → `document_metadata`. Pastikan ada satu row dengan `source_doc = "file.pdf"` dan `payload` berisi JSON lengkap.

- [ ] **Step 4: Commit final**

```bash
git add .
git commit -m "chore: verify doc_extractor smoke test passes end-to-end"
```
