# DOCX Generator Pipeline Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Refactor `model_ai/docx/` menjadi pipeline 10-modul yang memisahkan formatting spec (`DocxFormatSpec`) dari content rendering, dengan validator fail-fast dan audit post-generation.

**Architecture:** Spec layer (`loader → resolver → validator`) menghasilkan `DocxFormatSpec` yang menjadi satu-satunya interface ke python-docx. Document layer (`docx_adapter + content_model + renderer + builder`) hanya mengenal `DocxFormatSpec`, tidak pernah menyentuh `DocumentMetadata`. Refactor bertahap — pipeline tetap jalan di setiap tahap.

**Tech Stack:** Python 3.11+, python-docx, Pydantic v2, pytest

**Working directory for all commands:** `experiments/pymupdf4llm/`

**Baseline:** `python -m pytest tests/ -q` harus 33 passed sebelum memulai.

---

## File Map

### Files to Create
| File | Tanggung jawab |
|---|---|
| `model_ai/docx/schema.py` | `DocxFormatSpec` Pydantic model |
| `model_ai/docx/resolver.py` | `DocumentMetadata → DocxFormatSpec`, normalisasi string→enum |
| `model_ai/docx/validator.py` | Business rule validation, collect-all-violations |
| `model_ai/docx/ooxml_helper.py` | Pure OOXML functions (PAGE field, section break, dll) |
| `model_ai/docx/docx_adapter.py` | Apply page layout + styles ke `Document` object |
| `model_ai/docx/content_model.py` | `HeadingBlock`, `ParagraphBlock`, `Chapter`, `ProposalDocument` |
| `model_ai/docx/renderer.py` | Render satu `ContentBlock` → DOCX element |
| `model_ai/docx/loader.py` | Load JSON → `DocumentMetadata` (gantikan `metadata_loader.py`) |
| `model_ai/docx/builder.py` | Orkestrator: spec + chunks → `.docx` file |
| `model_ai/docx/audit.py` | Baca ulang DOCX, verifikasi terhadap `DocxFormatSpec` |
| `tests/docx/test_schema.py` | Unit tests untuk `DocxFormatSpec` |
| `tests/docx/test_resolver.py` | Unit tests untuk `resolver.py` |
| `tests/docx/test_validator.py` | Unit tests untuk `validator.py` |
| `tests/docx/test_ooxml_helper.py` | Unit tests untuk `ooxml_helper.py` |
| `tests/docx/test_docx_adapter.py` | Unit tests untuk `docx_adapter.py` |
| `tests/docx/test_content_model.py` | Unit tests untuk `content_model.py` |
| `tests/docx/test_renderer.py` | Unit tests untuk `renderer.py` |
| `tests/docx/test_builder.py` | Integration test untuk `builder.py` |
| `tests/docx/test_audit.py` | Unit tests untuk `audit.py` |

### Files to Modify
| File | Perubahan |
|---|---|
| `model_ai/docx/docx_renderer.py` | Task 4: import dari `ooxml_helper`; Task 5: import dari `docx_adapter` |
| `manage.py` | Task 8: route `docx` command ke `builder.py`; Task 9: tambah `--audit` flag |

### Files to Delete (Task 8)
- `model_ai/docx/generator.py`
- `model_ai/docx/docx_renderer.py`
- `model_ai/docx/metadata_loader.py`
- `model_ai/docx/style_translator_llm.py`
- `tests/docx/test_docx_generator.py`
- `tests/docx/test_style_translator_llm.py`

---

## Task 1: `schema.py` — DocxFormatSpec

**Files:**
- Create: `model_ai/docx/schema.py`
- Create: `tests/docx/test_schema.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/docx/test_schema.py
import pytest
from pydantic import ValidationError
from model_ai.docx.schema import DocxFormatSpec


def _minimal_spec_data() -> dict:
    return {
        "font_family": "Times New Roman",
        "font_size_body_pt": 12,
        "font_size_heading_pt": 12,
        "heading_bold": True,
        "heading_all_caps": True,
        "margin_top_cm": 3.0,
        "margin_bottom_cm": 3.0,
        "margin_left_cm": 4.0,
        "margin_right_cm": 3.0,
        "paper_size": "A4",
        "orientation": "PORTRAIT",
        "columns": 1,
        "line_spacing": 1.15,
        "line_spacing_rule": "MULTIPLE",
        "paragraph_alignment": "JUSTIFY",
        "first_line_indent_cm": None,
        "page_number_prelim_location": "footer",
        "page_number_prelim_alignment": "RIGHT",
        "page_number_prelim_format": "lowerRoman",
        "page_number_content_location": "header",
        "page_number_content_alignment": "RIGHT",
        "page_number_content_format": "decimal",
        "chapter_format": "BAB {n}",
        "sub_chapter_format": "{bab}.{sub}",
        "figure_format": "Gambar {n}.",
        "table_format": "Tabel {bab}.{n}",
        "table_caption_position": "ABOVE",
        "figure_caption_position": "BELOW",
        "caption_format_figure": "Gambar {n}. {title} ({source})",
        "caption_format_table": "Tabel {bab}.{n} {title}",
        "source_required_if_not_own": True,
        "proposal_sections": [],
        "proposal_max_halaman_inti": None,
        "laporan_kemajuan_sections": [],
        "laporan_akhir_sections": [],
    }


def test_docx_format_spec_instantiates_with_valid_data():
    spec = DocxFormatSpec.model_validate(_minimal_spec_data())
    assert spec.font_family == "Times New Roman"
    assert spec.font_size_body_pt == 12
    assert spec.heading_bold is True
    assert spec.first_line_indent_cm is None
    assert spec.proposal_sections == []


def test_docx_format_spec_accepts_sections_with_bab():
    from model_ai.extractor.models import SectionItem
    data = _minimal_spec_data()
    data["proposal_sections"] = [
        {"type": "bab", "number": 1, "title": "PENDAHULUAN"}
    ]
    spec = DocxFormatSpec.model_validate(data)
    assert spec.proposal_sections[0].type == "bab"
    assert spec.proposal_sections[0].number == 1


def test_docx_format_spec_rejects_missing_required_field():
    data = _minimal_spec_data()
    del data["font_family"]
    with pytest.raises(ValidationError):
        DocxFormatSpec.model_validate(data)


def test_docx_format_spec_first_line_indent_accepts_none():
    data = _minimal_spec_data()
    data["first_line_indent_cm"] = None
    spec = DocxFormatSpec.model_validate(data)
    assert spec.first_line_indent_cm is None


def test_docx_format_spec_first_line_indent_accepts_float():
    data = _minimal_spec_data()
    data["first_line_indent_cm"] = 1.27
    spec = DocxFormatSpec.model_validate(data)
    assert spec.first_line_indent_cm == 1.27
```

- [ ] **Step 2: Run test to verify it fails**

```bash
python -m pytest tests/docx/test_schema.py -v
```
Expected: `ModuleNotFoundError: No module named 'model_ai.docx.schema'`

- [ ] **Step 3: Create `model_ai/docx/schema.py`**

```python
from __future__ import annotations

from pydantic import BaseModel

from model_ai.extractor.models import SectionItem


class DocxFormatSpec(BaseModel):
    # Typography
    font_family: str
    font_size_body_pt: int
    font_size_heading_pt: int
    heading_bold: bool
    heading_all_caps: bool

    # Page layout
    margin_top_cm: float
    margin_bottom_cm: float
    margin_left_cm: float
    margin_right_cm: float
    paper_size: str
    orientation: str
    columns: int

    # Spacing
    line_spacing: float
    line_spacing_rule: str
    paragraph_alignment: str
    first_line_indent_cm: float | None

    # Page numbering
    page_number_prelim_location: str
    page_number_prelim_alignment: str
    page_number_prelim_format: str
    page_number_content_location: str
    page_number_content_alignment: str
    page_number_content_format: str

    # Numbering formats
    chapter_format: str
    sub_chapter_format: str
    figure_format: str
    table_format: str

    # Figures & tables
    table_caption_position: str
    figure_caption_position: str
    caption_format_figure: str
    caption_format_table: str
    source_required_if_not_own: bool

    # Document structure
    proposal_sections: list[SectionItem]
    proposal_max_halaman_inti: int | None
    laporan_kemajuan_sections: list[SectionItem]
    laporan_akhir_sections: list[SectionItem]
```

- [ ] **Step 4: Run test to verify it passes**

```bash
python -m pytest tests/docx/test_schema.py -v
```
Expected: 5 passed

- [ ] **Step 5: Commit**

```bash
git add model_ai/docx/schema.py tests/docx/test_schema.py
git commit -m "feat: add DocxFormatSpec schema for docx pipeline"
```

---

## Task 2: `resolver.py` — DocumentMetadata → DocxFormatSpec

**Files:**
- Create: `model_ai/docx/resolver.py`
- Create: `tests/docx/test_resolver.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/docx/test_resolver.py
import pytest
from model_ai.docx.resolver import resolve_spec, ResolutionError
from model_ai.extractor.models import DocumentMetadata


def _sample_metadata() -> DocumentMetadata:
    return DocumentMetadata.model_validate({
        "document_type": "Panduan PKM-KC",
        "source_document": "file.pdf",
        "typography": {
            "font_family": "Times New Roman",
            "font_size_body_pt": 12,
            "font_size_heading_pt": 12,
            "heading_bold": True,
            "heading_all_caps": True,
            "sources": [],
        },
        "page_layout": {
            "margin_top_cm": 3.0,
            "margin_bottom_cm": 3.0,
            "margin_left_cm": 4.0,
            "margin_right_cm": 3.0,
            "paper_size": "A4",
            "orientation": "PORTRAIT",
            "columns": 1,
            "sources": [],
        },
        "spacing": {
            "line_spacing": 1.15,
            "line_spacing_rule": "MULTIPLE",
            "paragraph_alignment": "JUSTIFY",
            "sources": [],
        },
        "document_structure_proposal": {
            "sections": [
                {"type": "daftar_isi", "required": True},
                {"type": "bab", "number": 1, "title": "PENDAHULUAN"},
            ],
            "sources": [],
        },
        "document_structure_laporan_kemajuan": {"sections": [], "sources": []},
        "document_structure_laporan_akhir": {"sections": [], "sources": []},
        "numbering": {
            "preliminary": {
                "format": "lowerRoman",
                "location": "FOOTER",
                "alignment": "RIGHT",
            },
            "content": {
                "format": "decimal",
                "location": "HEADER",
                "alignment": "RIGHT",
            },
            "sources": [],
        },
        "figures_and_tables": {
            "table_caption_position": "ABOVE",
            "figure_caption_position": "BELOW",
            "caption_format_figure": "Gambar {n}. {title} ({source})",
            "caption_format_table": "Tabel {bab}.{n} {title}",
            "source_required_if_not_own": True,
            "sources": [],
        },
        "page_count_limits": {"sources": []},
    })


def test_resolve_spec_maps_typography_fields():
    spec = resolve_spec(_sample_metadata())
    assert spec.font_family == "Times New Roman"
    assert spec.font_size_body_pt == 12
    assert spec.font_size_heading_pt == 12
    assert spec.heading_bold is True
    assert spec.heading_all_caps is True


def test_resolve_spec_maps_page_layout():
    spec = resolve_spec(_sample_metadata())
    assert spec.margin_top_cm == 3.0
    assert spec.margin_left_cm == 4.0
    assert spec.orientation == "PORTRAIT"
    assert spec.columns == 1


def test_resolve_spec_maps_spacing():
    spec = resolve_spec(_sample_metadata())
    assert spec.line_spacing == 1.15
    assert spec.paragraph_alignment == "JUSTIFY"


def test_resolve_spec_normalizes_alignment_lowercase():
    metadata = _sample_metadata()
    metadata.spacing.paragraph_alignment = "justify"
    spec = resolve_spec(metadata)
    assert spec.paragraph_alignment == "JUSTIFY"


def test_resolve_spec_normalizes_orientation_lowercase():
    metadata = _sample_metadata()
    metadata.page_layout.orientation = "portrait"
    spec = resolve_spec(metadata)
    assert spec.orientation == "PORTRAIT"


def test_resolve_spec_maps_page_numbering():
    spec = resolve_spec(_sample_metadata())
    assert spec.page_number_prelim_location == "footer"
    assert spec.page_number_prelim_alignment == "RIGHT"
    assert spec.page_number_prelim_format == "lowerRoman"
    assert spec.page_number_content_location == "header"
    assert spec.page_number_content_alignment == "RIGHT"
    assert spec.page_number_content_format == "decimal"


def test_resolve_spec_uses_defaults_when_numbering_is_null():
    metadata = _sample_metadata()
    metadata.numbering.preliminary = None
    metadata.numbering.content = None
    spec = resolve_spec(metadata)
    assert spec.page_number_prelim_location == "footer"
    assert spec.page_number_prelim_format == "lowerRoman"
    assert spec.page_number_content_location == "header"
    assert spec.page_number_content_format == "decimal"


def test_resolve_spec_uses_defaults_for_null_font_family():
    metadata = _sample_metadata()
    metadata.typography.font_family = None
    spec = resolve_spec(metadata)
    assert spec.font_family == "Times New Roman"


def test_resolve_spec_maps_proposal_sections():
    spec = resolve_spec(_sample_metadata())
    assert len(spec.proposal_sections) == 2
    assert spec.proposal_sections[0].type == "daftar_isi"
    assert spec.proposal_sections[1].type == "bab"


def test_resolve_spec_maps_figures_and_tables():
    spec = resolve_spec(_sample_metadata())
    assert spec.table_caption_position == "ABOVE"
    assert spec.figure_caption_position == "BELOW"
    assert spec.source_required_if_not_own is True


def test_resolution_error_message_contains_field_name():
    err = ResolutionError("font_family", None)
    assert "font_family" in str(err)
```

- [ ] **Step 2: Run test to verify it fails**

```bash
python -m pytest tests/docx/test_resolver.py -v
```
Expected: `ModuleNotFoundError: No module named 'model_ai.docx.resolver'`

- [ ] **Step 3: Create `model_ai/docx/resolver.py`**

```python
from __future__ import annotations

from typing import Any

from model_ai.docx.schema import DocxFormatSpec
from model_ai.extractor.models import DocumentMetadata

_DEFAULTS: dict[str, Any] = {
    "font_family": "Times New Roman",
    "font_size_body_pt": 12,
    "margin_top_cm": 3.0,
    "margin_bottom_cm": 3.0,
    "margin_left_cm": 4.0,
    "margin_right_cm": 3.0,
    "paper_size": "A4",
    "line_spacing": 1.15,
    "line_spacing_rule": "MULTIPLE",
    "paragraph_alignment": "JUSTIFY",
    "page_number_prelim_location": "footer",
    "page_number_prelim_alignment": "RIGHT",
    "page_number_prelim_format": "lowerRoman",
    "page_number_content_location": "header",
    "page_number_content_alignment": "RIGHT",
    "page_number_content_format": "decimal",
    "columns": 1,
    "chapter_format": "BAB {n}",
    "sub_chapter_format": "{bab}.{sub}",
    "figure_format": "Gambar {n}.",
    "table_format": "Tabel {bab}.{n}",
    "table_caption_position": "ABOVE",
    "figure_caption_position": "BELOW",
    "caption_format_figure": "Gambar {n}. {title} ({source})",
    "caption_format_table": "Tabel {bab}.{n} {title}",
    "source_required_if_not_own": True,
    "heading_bold": True,
    "heading_all_caps": False,
}


class ResolutionError(ValueError):
    def __init__(self, field: str, raw_value: Any) -> None:
        self.field = field
        self.raw_value = raw_value
        super().__init__(
            f"Cannot resolve required field '{field}': got {raw_value!r}"
        )


def resolve_spec(metadata: DocumentMetadata) -> DocxFormatSpec:
    typ = metadata.typography
    layout = metadata.page_layout
    spacing = metadata.spacing
    num = metadata.numbering
    fig = metadata.figures_and_tables
    prelim = num.preliminary
    content_num = num.content

    def _opt(field: str, value: Any) -> Any:
        return value if value is not None else _DEFAULTS.get(field)

    font_size_body = _opt("font_size_body_pt", typ.font_size_body_pt)
    font_size_heading = (
        _opt("font_size_heading_pt", typ.font_size_heading_pt) or font_size_body
    )

    return DocxFormatSpec(
        font_family=_opt("font_family", typ.font_family),
        font_size_body_pt=font_size_body,
        font_size_heading_pt=font_size_heading,
        heading_bold=_opt("heading_bold", typ.heading_bold),
        heading_all_caps=_opt("heading_all_caps", typ.heading_all_caps),
        margin_top_cm=_opt("margin_top_cm", layout.margin_top_cm),
        margin_bottom_cm=_opt("margin_bottom_cm", layout.margin_bottom_cm),
        margin_left_cm=_opt("margin_left_cm", layout.margin_left_cm),
        margin_right_cm=_opt("margin_right_cm", layout.margin_right_cm),
        paper_size=_opt("paper_size", layout.paper_size),
        orientation=_resolve_orientation(layout.orientation),
        columns=_opt("columns", layout.columns),
        line_spacing=_opt("line_spacing", spacing.line_spacing),
        line_spacing_rule=_opt("line_spacing_rule", spacing.line_spacing_rule),
        paragraph_alignment=_resolve_alignment(spacing.paragraph_alignment),
        first_line_indent_cm=spacing.first_line_indent_cm,
        page_number_prelim_location=_resolve_location(
            prelim.location if prelim else None, "page_number_prelim_location"
        ),
        page_number_prelim_alignment=_resolve_alignment_short(
            prelim.alignment if prelim else None, "page_number_prelim_alignment"
        ),
        page_number_prelim_format=_opt(
            "page_number_prelim_format", prelim.format if prelim else None
        ),
        page_number_content_location=_resolve_location(
            content_num.location if content_num else None, "page_number_content_location"
        ),
        page_number_content_alignment=_resolve_alignment_short(
            content_num.alignment if content_num else None, "page_number_content_alignment"
        ),
        page_number_content_format=_opt(
            "page_number_content_format", content_num.format if content_num else None
        ),
        chapter_format=_opt("chapter_format", num.chapter_format),
        sub_chapter_format=_opt("sub_chapter_format", num.sub_chapter_format),
        figure_format=_opt("figure_format", num.figure_format),
        table_format=_opt("table_format", num.table_format),
        table_caption_position=_opt(
            "table_caption_position", fig.table_caption_position
        ),
        figure_caption_position=_opt(
            "figure_caption_position", fig.figure_caption_position
        ),
        caption_format_figure=_opt(
            "caption_format_figure", fig.caption_format_figure
        ),
        caption_format_table=_opt(
            "caption_format_table", fig.caption_format_table
        ),
        source_required_if_not_own=_opt(
            "source_required_if_not_own", fig.source_required_if_not_own
        ),
        proposal_sections=metadata.document_structure_proposal.sections,
        proposal_max_halaman_inti=metadata.document_structure_proposal.max_halaman_inti,
        laporan_kemajuan_sections=metadata.document_structure_laporan_kemajuan.sections,
        laporan_akhir_sections=metadata.document_structure_laporan_akhir.sections,
    )


def _resolve_alignment(raw: str | None) -> str:
    val = (raw or "").strip().upper()
    return val if val in ("LEFT", "CENTER", "RIGHT", "JUSTIFY") else _DEFAULTS["paragraph_alignment"]


def _resolve_alignment_short(raw: str | None, field: str) -> str:
    val = (raw or "").strip().upper()
    return val if val in ("LEFT", "CENTER", "RIGHT") else _DEFAULTS[field]


def _resolve_orientation(raw: str | None) -> str:
    val = (raw or "").strip().upper()
    return val if val in ("PORTRAIT", "LANDSCAPE") else "PORTRAIT"


def _resolve_location(raw: str | None, field: str) -> str:
    val = (raw or "").strip().lower()
    return val if val in ("header", "footer") else _DEFAULTS[field]
```

- [ ] **Step 4: Run test to verify it passes**

```bash
python -m pytest tests/docx/test_resolver.py -v
```
Expected: 11 passed

- [ ] **Step 5: Commit**

```bash
git add model_ai/docx/resolver.py tests/docx/test_resolver.py
git commit -m "feat: add resolver to convert DocumentMetadata to DocxFormatSpec"
```

---

## Task 3: `validator.py` — Business Rule Validation

**Files:**
- Create: `model_ai/docx/validator.py`
- Create: `tests/docx/test_validator.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/docx/test_validator.py
import pytest
from model_ai.docx.validator import validate_spec, SpecValidationError
from model_ai.docx.schema import DocxFormatSpec
from model_ai.extractor.models import SectionItem


def _valid_spec() -> DocxFormatSpec:
    return DocxFormatSpec(
        font_family="Times New Roman",
        font_size_body_pt=12,
        font_size_heading_pt=12,
        heading_bold=True,
        heading_all_caps=True,
        margin_top_cm=3.0,
        margin_bottom_cm=3.0,
        margin_left_cm=4.0,
        margin_right_cm=3.0,
        paper_size="A4",
        orientation="PORTRAIT",
        columns=1,
        line_spacing=1.15,
        line_spacing_rule="MULTIPLE",
        paragraph_alignment="JUSTIFY",
        first_line_indent_cm=None,
        page_number_prelim_location="footer",
        page_number_prelim_alignment="RIGHT",
        page_number_prelim_format="lowerRoman",
        page_number_content_location="header",
        page_number_content_alignment="RIGHT",
        page_number_content_format="decimal",
        chapter_format="BAB {n}",
        sub_chapter_format="{bab}.{sub}",
        figure_format="Gambar {n}.",
        table_format="Tabel {bab}.{n}",
        table_caption_position="ABOVE",
        figure_caption_position="BELOW",
        caption_format_figure="Gambar {n}. {title} ({source})",
        caption_format_table="Tabel {bab}.{n} {title}",
        source_required_if_not_own=True,
        proposal_sections=[SectionItem(type="bab", number=1, title="PENDAHULUAN")],
        proposal_max_halaman_inti=10,
        laporan_kemajuan_sections=[],
        laporan_akhir_sections=[],
    )


def test_validate_spec_passes_for_valid_spec():
    validate_spec(_valid_spec())  # no exception raised


def test_validate_spec_fails_if_heading_smaller_than_body():
    spec = _valid_spec().model_copy(
        update={"font_size_heading_pt": 10, "font_size_body_pt": 12}
    )
    with pytest.raises(SpecValidationError) as exc_info:
        validate_spec(spec)
    assert "font_size_heading_pt" in str(exc_info.value)


def test_validate_spec_fails_if_proposal_sections_empty():
    spec = _valid_spec().model_copy(update={"proposal_sections": []})
    with pytest.raises(SpecValidationError) as exc_info:
        validate_spec(spec)
    assert "proposal_sections" in str(exc_info.value)


def test_validate_spec_fails_if_bab_missing_number():
    bad = SectionItem(type="bab", number=None, title="PENDAHULUAN")
    spec = _valid_spec().model_copy(update={"proposal_sections": [bad]})
    with pytest.raises(SpecValidationError) as exc_info:
        validate_spec(spec)
    assert "number" in str(exc_info.value)


def test_validate_spec_fails_if_bab_missing_title():
    bad = SectionItem(type="bab", number=1, title=None)
    spec = _valid_spec().model_copy(update={"proposal_sections": [bad]})
    with pytest.raises(SpecValidationError) as exc_info:
        validate_spec(spec)
    assert "title" in str(exc_info.value)


def test_validate_spec_collects_all_violations_at_once():
    bad = SectionItem(type="bab", number=None, title=None)
    spec = _valid_spec().model_copy(update={
        "proposal_sections": [bad],
        "font_size_heading_pt": 8,
        "font_size_body_pt": 12,
    })
    with pytest.raises(SpecValidationError) as exc_info:
        validate_spec(spec)
    assert len(exc_info.value.violations) >= 2


def test_validate_spec_fails_for_zero_line_spacing():
    spec = _valid_spec().model_copy(update={"line_spacing": 0.0})
    with pytest.raises(SpecValidationError) as exc_info:
        validate_spec(spec)
    assert "line_spacing" in str(exc_info.value)
```

- [ ] **Step 2: Run test to verify it fails**

```bash
python -m pytest tests/docx/test_validator.py -v
```
Expected: `ModuleNotFoundError: No module named 'model_ai.docx.validator'`

- [ ] **Step 3: Create `model_ai/docx/validator.py`**

```python
from model_ai.docx.schema import DocxFormatSpec


class SpecValidationError(ValueError):
    def __init__(self, violations: list[str]) -> None:
        self.violations = violations
        formatted = "\n".join(f"  - {v}" for v in violations)
        super().__init__(
            f"Spec validation failed with {len(violations)} violation(s):\n{formatted}"
        )


def validate_spec(spec: DocxFormatSpec) -> None:
    """Collect all violations, then raise once. Never raises on first violation only."""
    violations: list[str] = []

    if spec.font_size_heading_pt < spec.font_size_body_pt:
        violations.append(
            f"font_size_heading_pt ({spec.font_size_heading_pt}) < "
            f"font_size_body_pt ({spec.font_size_body_pt})"
        )

    if not spec.proposal_sections:
        violations.append("proposal_sections is empty")

    for i, section in enumerate(spec.proposal_sections):
        if section.type == "bab":
            if section.number is None:
                violations.append(
                    f"proposal_sections[{i}] type=bab missing 'number'"
                )
            if section.title is None:
                violations.append(
                    f"proposal_sections[{i}] type=bab missing 'title'"
                )

    if spec.line_spacing <= 0:
        violations.append(f"line_spacing must be > 0, got {spec.line_spacing}")

    if violations:
        raise SpecValidationError(violations)
```

- [ ] **Step 4: Run test to verify it passes**

```bash
python -m pytest tests/docx/test_validator.py -v
```
Expected: 7 passed

- [ ] **Step 5: Verify all existing tests still pass**

```bash
python -m pytest tests/ -q
```
Expected: 33 + new tests passed, 0 failed

- [ ] **Step 6: Commit**

```bash
git add model_ai/docx/validator.py tests/docx/test_validator.py
git commit -m "feat: add spec validator with collect-all-violations behavior"
```

---

## Task 4: `ooxml_helper.py` — Extract OOXML Functions

**Files:**
- Create: `model_ai/docx/ooxml_helper.py`
- Create: `tests/docx/test_ooxml_helper.py`
- Modify: `model_ai/docx/docx_renderer.py` (replace inline functions with imports)

- [ ] **Step 1: Write the failing test**

```python
# tests/docx/test_ooxml_helper.py
import pytest

pytest.importorskip("docx")

from docx import Document
from docx.oxml.ns import qn

from model_ai.docx.ooxml_helper import (
    append_field,
    clear_paragraph,
    set_page_number_type,
)


def test_append_field_inserts_fldchar_begin_and_end():
    doc = Document()
    para = doc.add_paragraph()
    append_field(para, " PAGE ")
    xml = para._p.xml
    assert "fldChar" in xml
    assert "instrText" in xml
    assert "PAGE" in xml


def test_append_field_separate_element_present():
    doc = Document()
    para = doc.add_paragraph()
    append_field(para, " SEQ Figure \\* ARABIC ")
    xml = para._p.xml
    assert "separate" in xml
    assert "SEQ" in xml


def test_clear_paragraph_removes_all_run_text():
    doc = Document()
    para = doc.add_paragraph("hello world")
    assert para.text == "hello world"
    clear_paragraph(para)
    assert para.text == ""


def test_set_page_number_type_sets_fmt_and_start():
    doc = Document()
    section = doc.sections[0]
    set_page_number_type(section, fmt="lowerRoman", start=1)
    sect_pr = section._sectPr
    pg_num = sect_pr.find(qn("w:pgNumType"))
    assert pg_num is not None
    assert pg_num.get(qn("w:fmt")) == "lowerRoman"
    assert pg_num.get(qn("w:start")) == "1"


def test_set_page_number_type_idempotent():
    doc = Document()
    section = doc.sections[0]
    set_page_number_type(section, fmt="lowerRoman", start=1)
    set_page_number_type(section, fmt="decimal", start=1)
    sect_pr = section._sectPr
    matches = sect_pr.findall(qn("w:pgNumType"))
    assert len(matches) == 1
    assert matches[0].get(qn("w:fmt")) == "decimal"
```

- [ ] **Step 2: Run test to verify it fails**

```bash
python -m pytest tests/docx/test_ooxml_helper.py -v
```
Expected: `ModuleNotFoundError: No module named 'model_ai.docx.ooxml_helper'`

- [ ] **Step 3: Create `model_ai/docx/ooxml_helper.py`**

Copy the five private functions from `docx_renderer.py` and make them public:

```python
from docx.oxml import OxmlElement
from docx.oxml.ns import qn


def append_field(paragraph, instruction: str) -> None:
    """Insert a Word field (PAGE, SEQ, TOC, etc.) into a paragraph."""
    run = paragraph.add_run()
    begin = OxmlElement("w:fldChar")
    begin.set(qn("w:fldCharType"), "begin")

    instr = OxmlElement("w:instrText")
    instr.set(qn("xml:space"), "preserve")
    instr.text = instruction

    separate = OxmlElement("w:fldChar")
    separate.set(qn("w:fldCharType"), "separate")
    text = OxmlElement("w:t")
    text.text = "1"

    end = OxmlElement("w:fldChar")
    end.set(qn("w:fldCharType"), "end")

    run._r.append(begin)
    run._r.append(instr)
    run._r.append(separate)
    run._r.append(text)
    run._r.append(end)


def set_page_number_type(section, fmt: str, start: int) -> None:
    """Set the page number format and start value for a section."""
    sect_pr = section._sectPr
    pg_num_type = sect_pr.find(qn("w:pgNumType"))
    if pg_num_type is None:
        pg_num_type = OxmlElement("w:pgNumType")
        sect_pr.append(pg_num_type)
    pg_num_type.set(qn("w:fmt"), fmt)
    pg_num_type.set(qn("w:start"), str(start))


def clear_paragraph(paragraph) -> None:
    """Remove all text from all runs in a paragraph."""
    for run in paragraph.runs:
        run.clear()
```

- [ ] **Step 4: Update `model_ai/docx/docx_renderer.py`** — replace the three identical private functions with imports

At the top of `docx_renderer.py`, add:
```python
from model_ai.docx.ooxml_helper import append_field, clear_paragraph, set_page_number_type
```

Then delete these four functions from `docx_renderer.py` (they are now in ooxml_helper):
- `_append_field`
- `_set_page_number_type`
- `_clear_paragraph`

Update all call sites in `docx_renderer.py`:
- `_append_field(` → `append_field(`
- `_set_page_number_type(` → `set_page_number_type(`
- `_clear_paragraph(` → `clear_paragraph(`

- [ ] **Step 5: Run all tests to verify pipeline still works**

```bash
python -m pytest tests/ -q
```
Expected: all tests pass (33 + 5 new = 38)

- [ ] **Step 6: Commit**

```bash
git add model_ai/docx/ooxml_helper.py model_ai/docx/docx_renderer.py tests/docx/test_ooxml_helper.py
git commit -m "refactor: extract ooxml_helper.py from docx_renderer"
```

---

## Task 5: `docx_adapter.py` — Page Layout + Styles Adapter

**Files:**
- Create: `model_ai/docx/docx_adapter.py`
- Create: `tests/docx/test_docx_adapter.py`
- Modify: `model_ai/docx/docx_renderer.py` (replace layout/style functions with imports)

- [ ] **Step 1: Write the failing test**

```python
# tests/docx/test_docx_adapter.py
import pytest

pytest.importorskip("docx")

from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.shared import Cm, Pt

from model_ai.docx.docx_adapter import apply_base_styles, apply_page_layout
from model_ai.docx.schema import DocxFormatSpec
from model_ai.extractor.models import SectionItem


def _sample_spec() -> DocxFormatSpec:
    return DocxFormatSpec(
        font_family="Times New Roman",
        font_size_body_pt=12,
        font_size_heading_pt=14,
        heading_bold=True,
        heading_all_caps=True,
        margin_top_cm=3.0,
        margin_bottom_cm=3.0,
        margin_left_cm=4.0,
        margin_right_cm=3.0,
        paper_size="A4",
        orientation="PORTRAIT",
        columns=1,
        line_spacing=1.15,
        line_spacing_rule="MULTIPLE",
        paragraph_alignment="JUSTIFY",
        first_line_indent_cm=None,
        page_number_prelim_location="footer",
        page_number_prelim_alignment="RIGHT",
        page_number_prelim_format="lowerRoman",
        page_number_content_location="header",
        page_number_content_alignment="RIGHT",
        page_number_content_format="decimal",
        chapter_format="BAB {n}",
        sub_chapter_format="{bab}.{sub}",
        figure_format="Gambar {n}.",
        table_format="Tabel {bab}.{n}",
        table_caption_position="ABOVE",
        figure_caption_position="BELOW",
        caption_format_figure="Gambar {n}. {title} ({source})",
        caption_format_table="Tabel {bab}.{n} {title}",
        source_required_if_not_own=True,
        proposal_sections=[SectionItem(type="bab", number=1, title="PENDAHULUAN")],
        proposal_max_halaman_inti=None,
        laporan_kemajuan_sections=[],
        laporan_akhir_sections=[],
    )


def test_apply_page_layout_sets_top_margin():
    doc = Document()
    apply_page_layout(doc.sections[0], _sample_spec())
    assert abs(doc.sections[0].top_margin - Cm(3.0)) < 10_000  # EMU tolerance


def test_apply_page_layout_sets_left_margin():
    doc = Document()
    apply_page_layout(doc.sections[0], _sample_spec())
    assert abs(doc.sections[0].left_margin - Cm(4.0)) < 10_000


def test_apply_page_layout_sets_portrait_dimensions():
    doc = Document()
    apply_page_layout(doc.sections[0], _sample_spec())
    from docx.shared import Mm
    assert abs(doc.sections[0].page_width - Mm(210)) < 10_000
    assert abs(doc.sections[0].page_height - Mm(297)) < 10_000


def test_apply_base_styles_sets_font_name_on_normal():
    doc = Document()
    apply_base_styles(doc, _sample_spec())
    assert doc.styles["Normal"].font.name == "Times New Roman"


def test_apply_base_styles_sets_body_font_size():
    doc = Document()
    apply_base_styles(doc, _sample_spec())
    assert doc.styles["Normal"].font.size == Pt(12)


def test_apply_base_styles_sets_heading_bold():
    doc = Document()
    apply_base_styles(doc, _sample_spec())
    assert doc.styles["Heading 1"].font.bold is True


def test_apply_base_styles_sets_heading_all_caps():
    doc = Document()
    apply_base_styles(doc, _sample_spec())
    assert doc.styles["Heading 1"].font.all_caps is True


def test_apply_base_styles_sets_heading_font_size():
    doc = Document()
    apply_base_styles(doc, _sample_spec())
    assert doc.styles["Heading 1"].font.size == Pt(14)
```

- [ ] **Step 2: Run test to verify it fails**

```bash
python -m pytest tests/docx/test_docx_adapter.py -v
```
Expected: `ModuleNotFoundError: No module named 'model_ai.docx.docx_adapter'`

- [ ] **Step 3: Create `model_ai/docx/docx_adapter.py`**

```python
from docx import Document
from docx.enum.section import WD_ORIENT
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml.ns import qn
from docx.shared import Cm, Mm, Pt

from model_ai.docx.ooxml_helper import set_page_number_type, append_field, clear_paragraph
from model_ai.docx.schema import DocxFormatSpec


def apply_page_layout(section, spec: DocxFormatSpec) -> None:
    """Apply paper size, orientation, and margins from spec to a section."""
    if spec.orientation == "LANDSCAPE":
        section.orientation = WD_ORIENT.LANDSCAPE
        section.page_width = Mm(297)
        section.page_height = Mm(210)
    else:
        section.orientation = WD_ORIENT.PORTRAIT
        section.page_width = Mm(210)
        section.page_height = Mm(297)

    section.top_margin = Cm(spec.margin_top_cm)
    section.bottom_margin = Cm(spec.margin_bottom_cm)
    section.left_margin = Cm(spec.margin_left_cm)
    section.right_margin = Cm(spec.margin_right_cm)


def apply_base_styles(document: Document, spec: DocxFormatSpec) -> None:
    """Apply font, size, spacing, and heading styles to document-level styles."""
    normal_style = document.styles["Normal"]
    normal_style.font.name = spec.font_family
    normal_style.font.size = Pt(spec.font_size_body_pt)
    normal_style._element.rPr.rFonts.set(qn("w:ascii"), spec.font_family)
    normal_style._element.rPr.rFonts.set(qn("w:hAnsi"), spec.font_family)
    normal_style.paragraph_format.line_spacing = spec.line_spacing
    normal_style.paragraph_format.alignment = _map_alignment(spec.paragraph_alignment)

    for style_name in ("Heading 1", "Heading 2"):
        heading_style = document.styles[style_name]
        heading_style.font.name = spec.font_family
        heading_style.font.size = Pt(spec.font_size_heading_pt)
        heading_style.font.bold = spec.heading_bold
        heading_style.font.all_caps = spec.heading_all_caps
        heading_style._element.rPr.rFonts.set(qn("w:ascii"), spec.font_family)
        heading_style._element.rPr.rFonts.set(qn("w:hAnsi"), spec.font_family)


def apply_page_numbering(
    section,
    location: str,
    alignment: str,
    fmt: str,
    start: int,
) -> None:
    """Configure page number field in header or footer of a section."""
    section.header.is_linked_to_previous = False
    section.footer.is_linked_to_previous = False

    target = section.header if location == "header" else section.footer
    para = target.paragraphs[0] if target.paragraphs else target.add_paragraph()
    para.alignment = _map_alignment(alignment)
    clear_paragraph(para)
    append_field(para, " PAGE ")
    set_page_number_type(section, fmt=fmt, start=start)


def _map_alignment(value: str) -> WD_ALIGN_PARAGRAPH:
    mapping = {
        "LEFT": WD_ALIGN_PARAGRAPH.LEFT,
        "CENTER": WD_ALIGN_PARAGRAPH.CENTER,
        "RIGHT": WD_ALIGN_PARAGRAPH.RIGHT,
        "JUSTIFY": WD_ALIGN_PARAGRAPH.JUSTIFY,
    }
    return mapping.get(value.upper(), WD_ALIGN_PARAGRAPH.JUSTIFY)
```

- [ ] **Step 4: Update `model_ai/docx/docx_renderer.py`** — replace layout/style functions with adapter imports

At the top of `docx_renderer.py`, add:
```python
from model_ai.docx.docx_adapter import apply_page_layout, apply_base_styles, apply_page_numbering
```

Delete these three private functions from `docx_renderer.py`:
- `_configure_page_layout`
- `_apply_base_styles`
- `_apply_page_numbering`
- `_map_alignment`
- `_position_alignment`

Update call sites in `docx_renderer.py`:
- `_configure_page_layout(first_section, metadata)` → `apply_page_layout(first_section, _metadata_to_adapter_args(metadata))` — wait, `docx_renderer.py` uses `DocumentMetadata`, not `DocxFormatSpec`. Since we're doing a gradual refactor, the renderer still uses `DocumentMetadata`. So we DON'T change the renderer's signature in this task.

Instead, keep `docx_renderer.py`'s internal functions as private wrappers that call through:

Actually, the cleanest approach for the gradual refactor:
- In Task 5, only create `docx_adapter.py` and its tests
- Do NOT yet modify `docx_renderer.py` to use it (that would require converting metadata to spec first)
- `docx_renderer.py` still uses its own internal functions
- `docx_adapter.py` is tested independently
- `docx_renderer.py` will be deleted in Task 8 when builder.py takes over

Update Step 4 to:

- [ ] **Step 4: (no changes to docx_renderer.py in this task)**

The adapter is tested standalone. `docx_renderer.py` will continue to use its own private functions until it's deleted in Task 8.

- [ ] **Step 5: Run all tests to verify nothing broke**

```bash
python -m pytest tests/ -q
```
Expected: all tests pass

- [ ] **Step 6: Commit**

```bash
git add model_ai/docx/docx_adapter.py tests/docx/test_docx_adapter.py
git commit -m "feat: add docx_adapter for page layout and style application"
```

---

## Task 6: `content_model.py` — Content Block Models

**Files:**
- Create: `model_ai/docx/content_model.py`
- Create: `tests/docx/test_content_model.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/docx/test_content_model.py
from model_ai.docx.content_model import (
    Chapter,
    FigureBlock,
    HeadingBlock,
    ParagraphBlock,
    ProposalDocument,
    TableBlock,
)


def test_heading_block_stores_text_and_level():
    block = HeadingBlock(level=1, text="BAB 1 PENDAHULUAN", source_chunk_index=3)
    assert block.level == 1
    assert block.text == "BAB 1 PENDAHULUAN"
    assert block.source_chunk_index == 3


def test_heading_block_source_chunk_index_optional():
    block = HeadingBlock(level=2, text="1.1 Latar Belakang")
    assert block.source_chunk_index is None


def test_paragraph_block_stores_text():
    block = ParagraphBlock(text="Isi paragraf.", source_chunk_index=5)
    assert block.text == "Isi paragraf."


def test_table_block_stores_caption_and_placeholder():
    block = TableBlock(
        caption="Tabel 1.1 Jadwal Kegiatan",
        placeholder="[PLACEHOLDER_TABEL]",
        source_chunk_index=None,
    )
    assert block.caption == "Tabel 1.1 Jadwal Kegiatan"
    assert block.placeholder == "[PLACEHOLDER_TABEL]"


def test_figure_block_stores_caption_and_placeholder():
    block = FigureBlock(
        caption="Gambar 1. Diagram Alir",
        placeholder="[PLACEHOLDER_GAMBAR]",
        source_chunk_index=None,
    )
    assert block.placeholder == "[PLACEHOLDER_GAMBAR]"


def test_chapter_stores_bab_number_title_and_blocks():
    heading = HeadingBlock(level=1, text="BAB 1 PENDAHULUAN")
    para = ParagraphBlock(text="Latar belakang penelitian ini...")
    chapter = Chapter(bab_number=1, title="PENDAHULUAN", blocks=[heading, para])
    assert chapter.bab_number == 1
    assert chapter.title == "PENDAHULUAN"
    assert len(chapter.blocks) == 2


def test_proposal_document_stores_all_sections():
    doc = ProposalDocument(
        preliminary_sections=["DAFTAR ISI", "DAFTAR GAMBAR"],
        chapters=[Chapter(bab_number=1, title="PENDAHULUAN", blocks=[])],
        has_daftar_pustaka=True,
        has_lampiran=True,
    )
    assert doc.preliminary_sections == ["DAFTAR ISI", "DAFTAR GAMBAR"]
    assert len(doc.chapters) == 1
    assert doc.has_daftar_pustaka is True
```

- [ ] **Step 2: Run test to verify it fails**

```bash
python -m pytest tests/docx/test_content_model.py -v
```
Expected: `ModuleNotFoundError: No module named 'model_ai.docx.content_model'`

- [ ] **Step 3: Create `model_ai/docx/content_model.py`**

```python
from __future__ import annotations

from pydantic import BaseModel


class HeadingBlock(BaseModel):
    level: int
    text: str
    source_chunk_index: int | None = None


class ParagraphBlock(BaseModel):
    text: str
    source_chunk_index: int | None = None


class TableBlock(BaseModel):
    caption: str
    placeholder: str
    source_chunk_index: int | None = None


class FigureBlock(BaseModel):
    caption: str
    placeholder: str
    source_chunk_index: int | None = None


ContentBlock = HeadingBlock | ParagraphBlock | TableBlock | FigureBlock


class Chapter(BaseModel):
    bab_number: int
    title: str
    blocks: list[ContentBlock]


class ProposalDocument(BaseModel):
    preliminary_sections: list[str]
    chapters: list[Chapter]
    has_daftar_pustaka: bool
    has_lampiran: bool
```

- [ ] **Step 4: Run test to verify it passes**

```bash
python -m pytest tests/docx/test_content_model.py -v
```
Expected: 8 passed

- [ ] **Step 5: Commit**

```bash
git add model_ai/docx/content_model.py tests/docx/test_content_model.py
git commit -m "feat: add content_model with HeadingBlock, ParagraphBlock, Chapter, ProposalDocument"
```

---

## Task 7: `renderer.py` — Per-Block Rendering

**Files:**
- Create: `model_ai/docx/renderer.py`
- Create: `tests/docx/test_renderer.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/docx/test_renderer.py
import pytest

pytest.importorskip("docx")

from docx import Document
from docx.shared import Pt

from model_ai.docx.content_model import (
    FigureBlock,
    HeadingBlock,
    ParagraphBlock,
    TableBlock,
)
from model_ai.docx.renderer import (
    render_figure_placeholder,
    render_heading,
    render_paragraph,
    render_table_placeholder,
)
from model_ai.docx.schema import DocxFormatSpec
from model_ai.extractor.models import SectionItem


def _sample_spec() -> DocxFormatSpec:
    return DocxFormatSpec(
        font_family="Times New Roman",
        font_size_body_pt=12,
        font_size_heading_pt=12,
        heading_bold=True,
        heading_all_caps=True,
        margin_top_cm=3.0,
        margin_bottom_cm=3.0,
        margin_left_cm=4.0,
        margin_right_cm=3.0,
        paper_size="A4",
        orientation="PORTRAIT",
        columns=1,
        line_spacing=1.15,
        line_spacing_rule="MULTIPLE",
        paragraph_alignment="JUSTIFY",
        first_line_indent_cm=None,
        page_number_prelim_location="footer",
        page_number_prelim_alignment="RIGHT",
        page_number_prelim_format="lowerRoman",
        page_number_content_location="header",
        page_number_content_alignment="RIGHT",
        page_number_content_format="decimal",
        chapter_format="BAB {n}",
        sub_chapter_format="{bab}.{sub}",
        figure_format="Gambar {n}.",
        table_format="Tabel {bab}.{n}",
        table_caption_position="ABOVE",
        figure_caption_position="BELOW",
        caption_format_figure="Gambar {n}. {title} ({source})",
        caption_format_table="Tabel {bab}.{n} {title}",
        source_required_if_not_own=True,
        proposal_sections=[SectionItem(type="bab", number=1, title="PENDAHULUAN")],
        proposal_max_halaman_inti=None,
        laporan_kemajuan_sections=[],
        laporan_akhir_sections=[],
    )


def test_render_heading_adds_heading_paragraph():
    doc = Document()
    block = HeadingBlock(level=1, text="BAB 1 PENDAHULUAN")
    render_heading(doc, block, _sample_spec())
    headings = [p for p in doc.paragraphs if p.style.name.startswith("Heading")]
    assert len(headings) == 1
    assert headings[0].text == "BAB 1 PENDAHULUAN"


def test_render_heading_level2_uses_heading2_style():
    doc = Document()
    block = HeadingBlock(level=2, text="1.1 Latar Belakang")
    render_heading(doc, block, _sample_spec())
    headings = [p for p in doc.paragraphs if "Heading 2" in p.style.name]
    assert len(headings) == 1


def test_render_paragraph_adds_text():
    doc = Document()
    block = ParagraphBlock(text="Ini adalah isi paragraf.")
    render_paragraph(doc, block, _sample_spec())
    texts = [p.text for p in doc.paragraphs if p.text]
    assert "Ini adalah isi paragraf." in texts


def test_render_table_placeholder_adds_caption_above():
    doc = Document()
    block = TableBlock(
        caption="Tabel 1.1 Jadwal",
        placeholder="[PLACEHOLDER_TABEL]",
    )
    render_table_placeholder(doc, block, _sample_spec())
    texts = [p.text for p in doc.paragraphs if p.text]
    caption_idx = next(i for i, t in enumerate(texts) if "Tabel" in t)
    placeholder_idx = next(i for i, t in enumerate(texts) if "[PLACEHOLDER_TABEL]" in t)
    assert caption_idx < placeholder_idx  # ABOVE means caption before placeholder


def test_render_figure_placeholder_adds_placeholder_above_caption():
    doc = Document()
    block = FigureBlock(
        caption="Gambar 1. Diagram",
        placeholder="[PLACEHOLDER_GAMBAR]",
    )
    render_figure_placeholder(doc, block, _sample_spec())
    texts = [p.text for p in doc.paragraphs if p.text]
    placeholder_idx = next(i for i, t in enumerate(texts) if "[PLACEHOLDER_GAMBAR]" in t)
    caption_idx = next(i for i, t in enumerate(texts) if "Gambar" in t)
    assert placeholder_idx < caption_idx  # BELOW means placeholder before caption
```

- [ ] **Step 2: Run test to verify it fails**

```bash
python -m pytest tests/docx/test_renderer.py -v
```
Expected: `ModuleNotFoundError: No module named 'model_ai.docx.renderer'`

- [ ] **Step 3: Create `model_ai/docx/renderer.py`**

```python
from docx import Document

from model_ai.docx.content_model import (
    FigureBlock,
    HeadingBlock,
    ParagraphBlock,
    TableBlock,
)
from model_ai.docx.ooxml_helper import append_field
from model_ai.docx.schema import DocxFormatSpec


def render_heading(document: Document, block: HeadingBlock, spec: DocxFormatSpec) -> None:
    level = max(1, min(block.level, 9))
    document.add_heading(block.text, level=level)


def render_paragraph(
    document: Document, block: ParagraphBlock, spec: DocxFormatSpec
) -> None:
    document.add_paragraph(block.text)


def render_table_placeholder(
    document: Document, block: TableBlock, spec: DocxFormatSpec
) -> None:
    position = spec.table_caption_position.upper()
    if position == "ABOVE":
        _add_caption(document, block.caption)
        document.add_paragraph(block.placeholder)
    else:
        document.add_paragraph(block.placeholder)
        _add_caption(document, block.caption)


def render_figure_placeholder(
    document: Document, block: FigureBlock, spec: DocxFormatSpec
) -> None:
    position = spec.figure_caption_position.upper()
    if position == "BELOW":
        document.add_paragraph(block.placeholder)
        _add_caption(document, block.caption)
    else:
        _add_caption(document, block.caption)
        document.add_paragraph(block.placeholder)


def _add_caption(document: Document, caption_text: str) -> None:
    paragraph = document.add_paragraph(caption_text)
```

- [ ] **Step 4: Run test to verify it passes**

```bash
python -m pytest tests/docx/test_renderer.py -v
```
Expected: 5 passed

- [ ] **Step 5: Run all tests**

```bash
python -m pytest tests/ -q
```
Expected: all pass

- [ ] **Step 6: Commit**

```bash
git add model_ai/docx/renderer.py tests/docx/test_renderer.py
git commit -m "feat: add per-block renderer for HeadingBlock, ParagraphBlock, TableBlock, FigureBlock"
```

---

## Task 8: `loader.py` + `builder.py` — Replace Generator Pipeline

**Files:**
- Create: `model_ai/docx/loader.py`
- Create: `model_ai/docx/builder.py`
- Create: `tests/docx/test_builder.py`
- Modify: `manage.py`
- Delete: `model_ai/docx/generator.py`, `model_ai/docx/docx_renderer.py`, `model_ai/docx/metadata_loader.py`, `model_ai/docx/style_translator_llm.py`, `tests/docx/test_docx_generator.py`, `tests/docx/test_style_translator_llm.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/docx/test_builder.py
import json
from pathlib import Path
from uuid import uuid4

import pytest

pytest.importorskip("docx")

from docx import Document

from model_ai.docx.builder import build_proposal
from model_ai.docx.loader import load_metadata
from model_ai.docx.resolver import resolve_spec
from model_ai.docx.validator import validate_spec


def _sample_output_json() -> dict:
    return {
        "document_type": "Panduan PKM-KC",
        "source_document": "file.pdf",
        "typography": {
            "font_family": "Times New Roman",
            "font_size_body_pt": 12,
            "heading_bold": True,
            "heading_all_caps": True,
            "sources": [],
        },
        "page_layout": {
            "margin_top_cm": 3,
            "margin_bottom_cm": 3,
            "margin_left_cm": 4,
            "margin_right_cm": 3,
            "paper_size": "A4",
            "orientation": "PORTRAIT",
            "columns": 1,
            "sources": [],
        },
        "spacing": {
            "line_spacing": 1.15,
            "line_spacing_rule": "MULTIPLE",
            "paragraph_alignment": "JUSTIFY",
            "sources": [],
        },
        "document_structure_proposal": {
            "sections": [
                {"type": "daftar_isi", "required": True},
                {"type": "bab", "number": 1, "title": "PENDAHULUAN"},
                {"type": "daftar_pustaka", "required": True},
                {"type": "lampiran", "required": True},
            ],
            "sources": [],
        },
        "document_structure_laporan_kemajuan": {"sections": [], "sources": []},
        "document_structure_laporan_akhir": {"sections": [], "sources": []},
        "numbering": {
            "preliminary": {
                "format": "lowerRoman",
                "location": "FOOTER",
                "alignment": "RIGHT",
            },
            "content": {
                "format": "decimal",
                "location": "HEADER",
                "alignment": "RIGHT",
            },
            "sources": [],
        },
        "figures_and_tables": {
            "table_caption_position": "ABOVE",
            "figure_caption_position": "BELOW",
            "caption_format_figure": "Gambar {n}. {title} ({source})",
            "caption_format_table": "Tabel {bab}.{n} {title}",
            "source_required_if_not_own": True,
            "sources": [],
        },
        "page_count_limits": {"sources": []},
    }


def _sample_chunks_json() -> list[dict]:
    return [
        {
            "chunk_index": 21,
            "chunk_parent": "BAB 1. PENDAHULUAN",
            "content": "Pendahuluan menjelaskan latar belakang penelitian yang sangat penting.",
            "page": {"start": 8, "end": 8},
        },
    ]


def _write_temp_files(data_dir: Path, run_id: str) -> tuple[Path, Path]:
    metadata_path = data_dir / f"test_output_{run_id}.json"
    chunks_path = data_dir / f"test_chunks_{run_id}.json"
    metadata_path.write_text(
        json.dumps(_sample_output_json(), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    chunks_path.write_text(
        json.dumps(_sample_chunks_json(), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return metadata_path, chunks_path


def test_load_metadata_returns_document_metadata(tmp_path):
    path = tmp_path / "meta.json"
    path.write_text(
        json.dumps(_sample_output_json(), ensure_ascii=False), encoding="utf-8"
    )
    from model_ai.extractor.models import DocumentMetadata
    result = load_metadata(path)
    assert isinstance(result, DocumentMetadata)
    assert result.typography.font_family == "Times New Roman"


def test_load_metadata_raises_if_file_missing():
    with pytest.raises(FileNotFoundError):
        load_metadata(Path("/nonexistent/path/meta.json"))


def test_build_proposal_creates_docx_file():
    data_dir = Path(__file__).resolve().parents[2] / "data"
    run_id = uuid4().hex
    metadata_path, chunks_path = _write_temp_files(data_dir, run_id)
    output_path = data_dir / f"test_proposal_{run_id}.docx"

    try:
        from model_ai.docx.chunk_loader import load_chunk_sources
        metadata = load_metadata(metadata_path)
        chunks = load_chunk_sources(chunks_path)
        spec = resolve_spec(metadata)
        validate_spec(spec)
        result = build_proposal(spec, chunks, output_path)

        assert result.exists()
        assert result.stat().st_size > 0
    finally:
        for path in (metadata_path, chunks_path, output_path):
            if path.exists():
                path.unlink()


def test_build_proposal_includes_bab_heading():
    data_dir = Path(__file__).resolve().parents[2] / "data"
    run_id = uuid4().hex
    metadata_path, chunks_path = _write_temp_files(data_dir, run_id)
    output_path = data_dir / f"test_proposal_{run_id}.docx"

    try:
        from model_ai.docx.chunk_loader import load_chunk_sources
        metadata = load_metadata(metadata_path)
        chunks = load_chunk_sources(chunks_path)
        spec = resolve_spec(metadata)
        result = build_proposal(spec, chunks, output_path)

        doc = Document(str(result))
        heading_texts = [p.text for p in doc.paragraphs if p.style.name.startswith("Heading")]
        assert any("PENDAHULUAN" in t for t in heading_texts)
    finally:
        for path in (metadata_path, chunks_path, output_path):
            if path.exists():
                path.unlink()


def test_build_proposal_includes_daftar_isi_section():
    data_dir = Path(__file__).resolve().parents[2] / "data"
    run_id = uuid4().hex
    metadata_path, chunks_path = _write_temp_files(data_dir, run_id)
    output_path = data_dir / f"test_proposal_{run_id}.docx"

    try:
        from model_ai.docx.chunk_loader import load_chunk_sources
        metadata = load_metadata(metadata_path)
        chunks = load_chunk_sources(chunks_path)
        spec = resolve_spec(metadata)
        result = build_proposal(spec, chunks, output_path)

        doc = Document(str(result))
        heading_texts = [p.text for p in doc.paragraphs if p.style.name.startswith("Heading")]
        assert any("DAFTAR ISI" in t for t in heading_texts)
    finally:
        for path in (metadata_path, chunks_path, output_path):
            if path.exists():
                path.unlink()
```

- [ ] **Step 2: Run test to verify it fails**

```bash
python -m pytest tests/docx/test_builder.py -v
```
Expected: `ModuleNotFoundError: No module named 'model_ai.docx.builder'`

- [ ] **Step 3: Create `model_ai/docx/loader.py`**

```python
import json
from pathlib import Path

from model_ai.extractor.models import DocumentMetadata


def load_metadata(path: Path) -> DocumentMetadata:
    if not path.exists():
        raise FileNotFoundError(f"File metadata tidak ditemukan: {path}")
    with open(path, encoding="utf-8") as f:
        payload = json.load(f)
    return DocumentMetadata.model_validate(payload)
```

- [ ] **Step 4: Create `model_ai/docx/builder.py`**

```python
from __future__ import annotations

import re
from pathlib import Path

from docx import Document
from docx.enum.section import WD_SECTION_START

from model_ai.docx.chunk_loader import ChunkSource, match_sources_for_section
from model_ai.docx.content_model import (
    Chapter,
    HeadingBlock,
    ParagraphBlock,
    ProposalDocument,
)
from model_ai.docx.docx_adapter import (
    apply_base_styles,
    apply_page_layout,
    apply_page_numbering,
)
from model_ai.docx.renderer import render_heading, render_paragraph
from model_ai.docx.schema import DocxFormatSpec

_PRELIM_DISPLAY: dict[str, str] = {
    "daftar_isi": "DAFTAR ISI",
    "daftar_gambar": "DAFTAR GAMBAR",
    "daftar_tabel": "DAFTAR TABEL",
    "daftar_lampiran": "DAFTAR LAMPIRAN",
}


def build_proposal(
    spec: DocxFormatSpec,
    chunks: list[ChunkSource],
    output_path: Path,
) -> Path:
    document = Document()
    first_section = document.sections[0]
    apply_page_layout(first_section, spec)
    apply_base_styles(document, spec)

    has_preliminary = any(
        s.type in _PRELIM_DISPLAY for s in spec.proposal_sections
    )

    if has_preliminary:
        apply_page_numbering(
            first_section,
            location=spec.page_number_prelim_location,
            alignment=spec.page_number_prelim_alignment,
            fmt=spec.page_number_prelim_format,
            start=1,
        )

    proposal_doc = _build_proposal_document(spec, chunks)

    # Render preliminary sections
    for i, section_name in enumerate(proposal_doc.preliminary_sections):
        document.add_heading(section_name, level=1)
        document.add_paragraph(f"[PLACEHOLDER_{section_name.replace(' ', '_')}]")
        if i < len(proposal_doc.preliminary_sections) - 1:
            document.add_page_break()

    # Add section break before body content
    if has_preliminary:
        content_section = document.add_section(WD_SECTION_START.NEW_PAGE)
        apply_page_layout(content_section, spec)
        apply_page_numbering(
            content_section,
            location=spec.page_number_content_location,
            alignment=spec.page_number_content_alignment,
            fmt=spec.page_number_content_format,
            start=1,
        )

    # Render chapters
    for chapter in proposal_doc.chapters:
        bab_label = spec.chapter_format.replace("{n}", str(chapter.bab_number))
        heading_text = f"{bab_label} {chapter.title}".strip()
        document.add_heading(heading_text, level=1)
        for block in chapter.blocks:
            if isinstance(block, HeadingBlock):
                render_heading(document, block, spec)
            elif isinstance(block, ParagraphBlock):
                render_paragraph(document, block, spec)

    # Render DAFTAR PUSTAKA
    if proposal_doc.has_daftar_pustaka:
        document.add_heading("DAFTAR PUSTAKA", level=1)
        document.add_paragraph("[PLACEHOLDER_DAFTAR_PUSTAKA]")
        sources = match_sources_for_section(
            chunks=chunks,
            section_label="DAFTAR PUSTAKA",
            section_title="DAFTAR PUSTAKA",
        )
        for src in sources:
            document.add_paragraph(
                f"Sumber: Hal. {src.page_start}-{src.page_end} | Header: {src.chunk_parent}"
            )

    # Render LAMPIRAN
    if proposal_doc.has_lampiran:
        document.add_heading("LAMPIRAN", level=1)
        document.add_paragraph("[PLACEHOLDER_LAMPIRAN]")

    output_path.parent.mkdir(parents=True, exist_ok=True)
    document.save(str(output_path))
    return output_path


def _build_proposal_document(
    spec: DocxFormatSpec,
    chunks: list[ChunkSource],
) -> ProposalDocument:
    preliminary_sections: list[str] = []
    chapters: list[Chapter] = []
    has_daftar_pustaka = False
    has_lampiran = False

    for section in spec.proposal_sections:
        if section.type in _PRELIM_DISPLAY:
            preliminary_sections.append(_PRELIM_DISPLAY[section.type])
        elif section.type == "bab" and section.number is not None:
            title = section.title or ""
            bab_label = spec.chapter_format.replace("{n}", str(section.number))
            relevant_chunks = match_sources_for_section(
                chunks=chunks,
                section_label=bab_label,
                section_title=title,
                limit=3,
            )
            blocks: list[ParagraphBlock] = []
            for chunk in relevant_chunks:
                snippet = _truncate_to_words(chunk.content, max_words=20)
                if snippet:
                    blocks.append(
                        ParagraphBlock(
                            text=snippet,
                            source_chunk_index=chunk.page_start,
                        )
                    )
            chapters.append(
                Chapter(bab_number=section.number, title=title, blocks=blocks)
            )
        elif section.type == "daftar_pustaka":
            has_daftar_pustaka = True
        elif section.type == "lampiran":
            has_lampiran = True

    return ProposalDocument(
        preliminary_sections=preliminary_sections,
        chapters=chapters,
        has_daftar_pustaka=has_daftar_pustaka,
        has_lampiran=has_lampiran,
    )


def _truncate_to_words(text: str, max_words: int = 20) -> str:
    words = text.split()
    if len(words) <= max_words:
        return text
    return " ".join(words[:max_words]) + "..."
```

- [ ] **Step 5: Run test to verify it passes**

```bash
python -m pytest tests/docx/test_builder.py -v
```
Expected: 5 passed

- [ ] **Step 6: Update `manage.py`** — route `docx` command to `builder.py`

Replace the `run_docx` function in `manage.py`:

```python
def run_docx(
    doc_type: str,
    input_path: str,
    chunks_path: str,
    output_path: str,
) -> None:
    if doc_type != "proposal":
        raise SystemExit(
            f"Tipe dokumen '{doc_type}' belum didukung. Gunakan '--type proposal'."
        )

    from model_ai.docx.builder import build_proposal
    from model_ai.docx.chunk_loader import load_chunk_sources
    from model_ai.docx.loader import load_metadata
    from model_ai.docx.resolver import resolve_spec
    from model_ai.docx.validator import validate_spec

    metadata = load_metadata(Path(input_path))
    chunks = load_chunk_sources(Path(chunks_path))
    spec = resolve_spec(metadata)
    validate_spec(spec)
    generated_path = build_proposal(spec, chunks, Path(output_path))
    print(f"[docx] Berhasil membuat dokumen: {generated_path}")
```

Remove `use_llm_normalization` parameter from `run_docx` and from the argparse definition in `main()`. Also remove `--no-llm-normalization` argument.

- [ ] **Step 7: Verify all tests still pass**

```bash
python -m pytest tests/ -q
```
Expected: all pass

- [ ] **Step 8: Delete old files**

```bash
git rm model_ai/docx/generator.py \
        model_ai/docx/docx_renderer.py \
        model_ai/docx/metadata_loader.py \
        model_ai/docx/style_translator_llm.py \
        tests/docx/test_docx_generator.py \
        tests/docx/test_style_translator_llm.py
```

- [ ] **Step 9: Run all tests one final time**

```bash
python -m pytest tests/ -q
```
Expected: all pass, no references to deleted modules

- [ ] **Step 10: Commit**

```bash
git add model_ai/docx/loader.py model_ai/docx/builder.py tests/docx/test_builder.py manage.py
git commit -m "feat: add builder.py and loader.py, remove legacy generator and docx_renderer"
```

---

## Task 9: `audit.py` — Post-Generation Verification

**Files:**
- Create: `model_ai/docx/audit.py`
- Create: `tests/docx/test_audit.py`
- Modify: `manage.py` (add `--audit` flag)

- [ ] **Step 1: Write the failing test**

```python
# tests/docx/test_audit.py
import json
from dataclasses import dataclass
from pathlib import Path
from uuid import uuid4

import pytest

pytest.importorskip("docx")

from model_ai.docx.audit import AuditResult, AuditViolation, audit_docx
from model_ai.docx.builder import build_proposal
from model_ai.docx.chunk_loader import load_chunk_sources
from model_ai.docx.loader import load_metadata
from model_ai.docx.resolver import resolve_spec
from model_ai.docx.schema import DocxFormatSpec
from model_ai.extractor.models import SectionItem


def _sample_spec() -> DocxFormatSpec:
    return DocxFormatSpec(
        font_family="Times New Roman",
        font_size_body_pt=12,
        font_size_heading_pt=12,
        heading_bold=True,
        heading_all_caps=True,
        margin_top_cm=3.0,
        margin_bottom_cm=3.0,
        margin_left_cm=4.0,
        margin_right_cm=3.0,
        paper_size="A4",
        orientation="PORTRAIT",
        columns=1,
        line_spacing=1.15,
        line_spacing_rule="MULTIPLE",
        paragraph_alignment="JUSTIFY",
        first_line_indent_cm=None,
        page_number_prelim_location="footer",
        page_number_prelim_alignment="RIGHT",
        page_number_prelim_format="lowerRoman",
        page_number_content_location="header",
        page_number_content_alignment="RIGHT",
        page_number_content_format="decimal",
        chapter_format="BAB {n}",
        sub_chapter_format="{bab}.{sub}",
        figure_format="Gambar {n}.",
        table_format="Tabel {bab}.{n}",
        table_caption_position="ABOVE",
        figure_caption_position="BELOW",
        caption_format_figure="Gambar {n}. {title} ({source})",
        caption_format_table="Tabel {bab}.{n} {title}",
        source_required_if_not_own=True,
        proposal_sections=[
            SectionItem(type="daftar_isi", required=True),
            SectionItem(type="bab", number=1, title="PENDAHULUAN"),
            SectionItem(type="daftar_pustaka", required=True),
        ],
        proposal_max_halaman_inti=None,
        laporan_kemajuan_sections=[],
        laporan_akhir_sections=[],
    )


def _build_test_docx(tmp_path: Path) -> Path:
    output_path = tmp_path / "proposal_test.docx"
    build_proposal(_sample_spec(), [], output_path)
    return output_path


def test_audit_result_is_dataclass():
    result = AuditResult(passed=True, violations=[])
    assert result.passed is True
    assert result.violations == []


def test_audit_violation_has_expected_fields():
    v = AuditViolation(
        field="font_family",
        expected="Times New Roman",
        actual="Arial",
        level="formatting",
    )
    assert v.field == "font_family"
    assert v.level == "formatting"


def test_audit_passes_for_correctly_built_docx(tmp_path):
    docx_path = _build_test_docx(tmp_path)
    result = audit_docx(docx_path, _sample_spec())
    assert result.passed is True
    assert result.violations == []


def test_audit_returns_auditresult_not_exception(tmp_path):
    docx_path = _build_test_docx(tmp_path)
    result = audit_docx(docx_path, _sample_spec())
    assert isinstance(result, AuditResult)


def test_audit_detects_missing_heading(tmp_path):
    from docx import Document
    docx_path = tmp_path / "empty.docx"
    Document().save(str(docx_path))
    spec = _sample_spec()
    result = audit_docx(docx_path, spec)
    assert not result.passed
    structural = [v for v in result.violations if v.level == "structural"]
    assert len(structural) > 0
```

- [ ] **Step 2: Run test to verify it fails**

```bash
python -m pytest tests/docx/test_audit.py -v
```
Expected: `ModuleNotFoundError: No module named 'model_ai.docx.audit'`

- [ ] **Step 3: Create `model_ai/docx/audit.py`**

```python
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal

from docx import Document
from docx.oxml.ns import qn
from docx.shared import Cm, Pt

from model_ai.docx.schema import DocxFormatSpec

_PRELIM_DISPLAY = {
    "daftar_isi": "DAFTAR ISI",
    "daftar_gambar": "DAFTAR GAMBAR",
    "daftar_tabel": "DAFTAR TABEL",
    "daftar_lampiran": "DAFTAR LAMPIRAN",
}
_MARGIN_TOLERANCE_EMU = int(Cm(0.1))  # ±0.1 cm in EMU


@dataclass
class AuditViolation:
    field: str
    expected: str
    actual: str
    level: Literal["structural", "formatting"]


@dataclass
class AuditResult:
    passed: bool
    violations: list[AuditViolation] = field(default_factory=list)


def audit_docx(docx_path: Path, spec: DocxFormatSpec) -> AuditResult:
    """Read a saved DOCX and compare its contents against DocxFormatSpec.
    Returns AuditResult — never raises.
    """
    violations: list[AuditViolation] = []
    doc = Document(str(docx_path))

    _check_structure(doc, spec, violations)
    _check_formatting(doc, spec, violations)

    return AuditResult(passed=len(violations) == 0, violations=violations)


def _check_structure(
    doc: Document, spec: DocxFormatSpec, violations: list[AuditViolation]
) -> None:
    heading_texts = {
        p.text.strip()
        for p in doc.paragraphs
        if p.style.name.startswith("Heading")
    }

    # Check all expected headings are present
    for section in spec.proposal_sections:
        if section.type in _PRELIM_DISPLAY:
            expected = _PRELIM_DISPLAY[section.type]
            if expected not in heading_texts:
                violations.append(
                    AuditViolation(
                        field=f"section:{section.type}",
                        expected=f"heading '{expected}' present",
                        actual="not found",
                        level="structural",
                    )
                )
        elif section.type == "bab" and section.number is not None and section.title:
            bab_label = spec.chapter_format.replace("{n}", str(section.number))
            expected_heading = f"{bab_label} {section.title}".strip()
            if expected_heading not in heading_texts:
                violations.append(
                    AuditViolation(
                        field=f"section:bab_{section.number}",
                        expected=f"heading '{expected_heading}' present",
                        actual="not found",
                        level="structural",
                    )
                )


def _check_formatting(
    doc: Document, spec: DocxFormatSpec, violations: list[AuditViolation]
) -> None:
    _check_normal_style(doc, spec, violations)
    _check_heading1_style(doc, spec, violations)
    _check_margins(doc, spec, violations)


def _check_normal_style(
    doc: Document, spec: DocxFormatSpec, violations: list[AuditViolation]
) -> None:
    normal = doc.styles["Normal"]
    actual_font = normal.font.name
    if actual_font and actual_font != spec.font_family:
        violations.append(
            AuditViolation(
                field="font_family",
                expected=spec.font_family,
                actual=str(actual_font),
                level="formatting",
            )
        )
    actual_size = normal.font.size
    expected_size = Pt(spec.font_size_body_pt)
    if actual_size and abs(actual_size - expected_size) > 100:
        violations.append(
            AuditViolation(
                field="font_size_body_pt",
                expected=str(spec.font_size_body_pt),
                actual=str(actual_size / 12700),
                level="formatting",
            )
        )


def _check_heading1_style(
    doc: Document, spec: DocxFormatSpec, violations: list[AuditViolation]
) -> None:
    h1 = doc.styles["Heading 1"]
    if h1.font.bold is not None and h1.font.bold != spec.heading_bold:
        violations.append(
            AuditViolation(
                field="heading_bold",
                expected=str(spec.heading_bold),
                actual=str(h1.font.bold),
                level="formatting",
            )
        )


def _check_margins(
    doc: Document, spec: DocxFormatSpec, violations: list[AuditViolation]
) -> None:
    section = doc.sections[0]
    margin_checks = [
        ("margin_top_cm", section.top_margin, Cm(spec.margin_top_cm)),
        ("margin_bottom_cm", section.bottom_margin, Cm(spec.margin_bottom_cm)),
        ("margin_left_cm", section.left_margin, Cm(spec.margin_left_cm)),
        ("margin_right_cm", section.right_margin, Cm(spec.margin_right_cm)),
    ]
    for field_name, actual, expected in margin_checks:
        if actual is not None and abs(actual - expected) > _MARGIN_TOLERANCE_EMU:
            violations.append(
                AuditViolation(
                    field=field_name,
                    expected=f"{expected / 914400:.2f} cm",
                    actual=f"{actual / 914400:.2f} cm",
                    level="formatting",
                )
            )
```

- [ ] **Step 4: Run test to verify it passes**

```bash
python -m pytest tests/docx/test_audit.py -v
```
Expected: 6 passed

- [ ] **Step 5: Add `--audit` flag to `manage.py`**

In the `run_docx` function, add an optional `audit: bool` parameter and call `audit_docx` after building:

```python
def run_docx(
    doc_type: str,
    input_path: str,
    chunks_path: str,
    output_path: str,
    audit: bool = False,
) -> None:
    if doc_type != "proposal":
        raise SystemExit(
            f"Tipe dokumen '{doc_type}' belum didukung. Gunakan '--type proposal'."
        )

    from model_ai.docx.builder import build_proposal
    from model_ai.docx.chunk_loader import load_chunk_sources
    from model_ai.docx.loader import load_metadata
    from model_ai.docx.resolver import resolve_spec
    from model_ai.docx.validator import validate_spec

    metadata = load_metadata(Path(input_path))
    chunks = load_chunk_sources(Path(chunks_path))
    spec = resolve_spec(metadata)
    validate_spec(spec)
    generated_path = build_proposal(spec, chunks, Path(output_path))
    print(f"[docx] Berhasil membuat dokumen: {generated_path}")

    if audit:
        from model_ai.docx.audit import audit_docx
        result = audit_docx(generated_path, spec)
        if result.passed:
            print("[audit] PASS — dokumen sesuai spec.")
        else:
            print(f"[audit] FAIL — {len(result.violations)} violation(s):")
            for v in result.violations:
                print(f"  [{v.level}] {v.field}: expected={v.expected}, actual={v.actual}")
```

In `main()`, add `--audit` flag to the `docx` subparser:
```python
docx_parser.add_argument(
    "--audit",
    action="store_true",
    help="Jalankan audit setelah dokumen dibuat dan tampilkan hasilnya.",
)
```

Update the `args.command == "docx"` block:
```python
if args.command == "docx":
    run_docx(
        doc_type=args.doc_type,
        input_path=args.input,
        chunks_path=args.chunks,
        output_path=args.output,
        audit=args.audit,
    )
    return
```

- [ ] **Step 6: Run all tests**

```bash
python -m pytest tests/ -q
```
Expected: all pass

- [ ] **Step 7: Commit**

```bash
git add model_ai/docx/audit.py tests/docx/test_audit.py manage.py
git commit -m "feat: add audit.py for post-generation DOCX verification and --audit flag"
```

---

## Self-Review Checklist

**Spec coverage:**
- [x] `schema.py` (DocxFormatSpec) → Task 1
- [x] `resolver.py` (normalisasi + _DEFAULTS) → Task 2
- [x] `validator.py` (collect-all-violations) → Task 3
- [x] `ooxml_helper.py` (OOXML functions) → Task 4
- [x] `docx_adapter.py` (page layout + styles) → Task 5
- [x] `content_model.py` (HeadingBlock, Chapter, ProposalDocument) → Task 6
- [x] `renderer.py` (per-block rendering) → Task 7
- [x] `loader.py` → Task 8
- [x] `builder.py` (orchestrator + chunk-to-placeholder logic) → Task 8
- [x] `audit.py` (structural + formatting check) → Task 9
- [x] `manage.py` routing updated → Task 8 + 9
- [x] Old files deleted → Task 8
- [x] Gradual refactor — pipeline stays working → verified by running pytest at each task

**Type consistency:**
- `DocxFormatSpec` defined in Task 1, used in Tasks 2, 3, 5, 7, 8, 9 — consistent
- `ProposalDocument` defined in Task 6, used in Task 8 — consistent
- `ChunkSource` from `chunk_loader.py` (unchanged) used in Tasks 8, 9 — consistent
- `apply_page_layout`, `apply_base_styles`, `apply_page_numbering` defined in Task 5, used in Task 8 — consistent
- `render_heading`, `render_paragraph` defined in Task 7, used in Task 8 — consistent
- `build_proposal(spec, chunks, output_path)` defined in Task 8, tested in Task 9 — consistent
