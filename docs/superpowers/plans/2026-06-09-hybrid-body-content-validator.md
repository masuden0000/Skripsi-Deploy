# Hybrid Body Content Validator Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implementasi empat perubahan terkoordinasi: (1) `_check_body_content()` — content-based validator non-heading yang mengagregasi per nilai parameter; (2) filter `parameter_summary` ke heading only; (3) `caption_format_lampiran` — validasi format judul lampiran; (4) alignment caption dinamis dari metadata (`caption_alignment_figure`, `caption_alignment_table`, `caption_alignment_lampiran`) menggantikan nilai CENTER yang di-hardcode.

**Architecture:**
- **Hybrid validation**: Heading H1–H5 tetap style-based via `validocx_validate()`; semua paragraf non-heading divalidasi content-based via `DocumentWrapper.iter_paragraphs()` (mendukung `w:sdt`).
- **Alignment caption dinamis**: `_check_caption_format()` membaca alignment per tipe caption dari `metadata.figures_and_tables`; fallback ke CENTER jika null.
- **Lampiran scan terpisah**: `_build_content_elements()` sengaja berhenti sebelum LAMPIRAN, sehingga `caption_format_lampiran` dan `caption_alignment_lampiran` di-scan via loop terpisah di `_check_figures_tables()`.

**Tech Stack:** Python 3.11, python-docx, pytest — tidak ada dependensi baru.

---

## Status Komponen Saat Ini

| Komponen | File | Status |
|---|---|---|
| Field `caption_alignment_*` di frontend | `ExtractionValuesForm.tsx` | ✅ Sudah ada (3 Select fields) |
| CHECK constraint database | `20260609000000_figures_and_tables_caption_alignment.sql` | ✅ Sudah di-push |
| Field `caption_alignment_*` di Pydantic model | `ai/model/model_ai/extractor/models.py` | ❌ Belum ditambah |
| `_check_caption_format()` alignment | `validocx_runner.py` | ❌ Hardcode CENTER |
| `_check_body_content()` | `validocx_runner.py` | ❌ Belum ada |
| `caption_format_lampiran` check | `validocx_runner.py` | ❌ Belum ada |
| `caption_alignment_lampiran` check | `validocx_runner.py` | ❌ Belum ada |

---

## Konteks Penting (Baca Dulu)

**Distribusi style di `tests/file_target.docx` (202 paragraf termasuk w:sdt):**

| Kelompok | Jumlah | Status |
|---|---|---|
| Heading H1/H2 | 30 | ✅ Style-based |
| Normal | 100 | Dicek via validocx |
| List Paragraph | 20 | Tidak terdaftar → fallback Normal |
| `toc 1`/`toc 2` (lowercase) | 29 | Bug case-sensitivity, bypass via content-based |
| `table of figures`, `Lampiran` | 16 | Terdaftar |
| Caption (`Gambar`, `Tabel`) | 12 | Dicek `_check_caption_format` |

**Fungsi kunci yang sudah ada (tidak diubah kecuali sesuai rencana):**
- `_template_to_regex(template)` — konversi `"Lampiran {n}. {title}"` ke regex
- `_para_contains_image(para)` — cek `w:drawing`/`w:pict`
- `_build_content_elements(doc)` — flat list `("para"/"table", obj)`, berhenti sebelum LAMPIRAN/DAFTAR PUSTAKA
- `_FIG_DETECT_RE` = `r'^Gambar\s+\d+'`, `_TBL_DETECT_RE` = `r'^Tabel\s+\d+'` — baris 86–87
- `WD_ALIGN_PARAGRAPH` — sudah diimport di baris 12

**Alignment string → enum mapping** (dipakai di Task 4):
```python
_CAPTION_ALIGN_MAP: dict[str, WD_ALIGN_PARAGRAPH] = {
    "CENTER":  WD_ALIGN_PARAGRAPH.CENTER,
    "LEFT":    WD_ALIGN_PARAGRAPH.LEFT,
    "RIGHT":   WD_ALIGN_PARAGRAPH.RIGHT,
    "JUSTIFY": WD_ALIGN_PARAGRAPH.JUSTIFY,
}
```

---

## File Structure

| File | Aksi | Keterangan |
|---|---|---|
| `ai/model/model_ai/extractor/models.py` | Modify | Tambah 3 field `caption_alignment_*` ke `FiguresTablesExtracted` |
| `ai/model/model_ai/validation/validocx_runner.py` | Modify | Tambah `_LAMP_DETECT_RE`, `_CAPTION_ALIGN_MAP`, `_HEADING_STYLE_KEYWORDS`, `_HEADING_PARAM_KEYWORDS`, `_is_heading_para()`, `_check_body_content()`, update `_check_caption_format()`, update `_check_figures_tables()`, filter `_build_issues_checks()`, wire ke `run_validocx()` |
| `ai/model/tests/test_body_content_check.py` | Create | Unit test untuk semua fungsi baru + perubahan |

---

## Task 1: Tulis Failing Tests

**Files:**
- Create: `ai/model/tests/test_body_content_check.py`

- [ ] **Step 1: Buat file test**

```python
# ai/model/tests/test_body_content_check.py
"""Test untuk _is_heading_para, _check_body_content, caption_format_lampiran,
dan caption_alignment dinamis di _check_caption_format / _check_figures_tables."""
from pathlib import Path
from unittest.mock import MagicMock

from model_ai.validation.validocx_runner import (
    _is_heading_para,
    _check_body_content,
    _check_caption_format,
    _check_figures_tables,
)

_DOCX = Path(__file__).parent / "file_target.docx"


# ── Helpers ───────────────────────────────────────────────────────────────────

def _mock_para(style_name: str, base_style_name: str | None = None):
    para = MagicMock()
    style = MagicMock()
    style.name = style_name
    if base_style_name:
        base = MagicMock()
        base.name = base_style_name
        base.base_style = None
        style.base_style = base
    else:
        style.base_style = None
    para.style = style
    return para


def _make_body_metadata(font="Times New Roman", size=12, spacing=1.15):
    """Metadata mock untuk _check_body_content()."""
    meta = MagicMock()
    meta.typography.font_family = font
    meta.typography.font_size_body_pt = size
    meta.spacing.line_spacing = spacing
    meta.spacing.line_spacing_rule = None
    return meta


def _make_caption_metadata(
    font="Times New Roman",
    size=12,
    fig_align: str | None = "CENTER",
    tbl_align: str | None = "CENTER",
    lamp_align: str | None = "CENTER",
    fig_fmt: str | None = None,
    tbl_fmt: str | None = None,
    lamp_fmt: str | None = None,
    fig_pos: str | None = None,
    tbl_pos: str | None = None,
):
    """Metadata mock untuk _check_caption_format() dan _check_figures_tables()."""
    meta = MagicMock()
    meta.typography.font_family = font
    meta.typography.font_size_body_pt = size
    meta.figures_and_tables.caption_alignment_figure   = fig_align
    meta.figures_and_tables.caption_alignment_table    = tbl_align
    meta.figures_and_tables.caption_alignment_lampiran = lamp_align
    meta.figures_and_tables.caption_format_figure      = fig_fmt
    meta.figures_and_tables.caption_format_table       = tbl_fmt
    meta.figures_and_tables.caption_format_lampiran    = lamp_fmt
    meta.figures_and_tables.figure_caption_position    = fig_pos
    meta.figures_and_tables.table_caption_position     = tbl_pos
    return meta


# ── _is_heading_para() ────────────────────────────────────────────────────────

def test_is_heading_para_heading1():
    assert _is_heading_para(_mock_para("Heading 1")) is True

def test_is_heading_para_heading2():
    assert _is_heading_para(_mock_para("Heading 2")) is True

def test_is_heading_para_judul1():
    assert _is_heading_para(_mock_para("Judul1")) is True

def test_is_heading_para_judul_spasi():
    assert _is_heading_para(_mock_para("Judul 3")) is True

def test_is_heading_para_normal_is_not_heading():
    assert _is_heading_para(_mock_para("Normal")) is False

def test_is_heading_para_list_paragraph_is_not_heading():
    assert _is_heading_para(_mock_para("List Paragraph")) is False

def test_is_heading_para_toc_is_not_heading():
    assert _is_heading_para(_mock_para("toc 1")) is False

def test_is_heading_para_via_inheritance():
    """Style custom mewarisi Heading 1 harus terdeteksi sebagai heading."""
    para = _mock_para("CustomBab", base_style_name="Heading 1")
    assert _is_heading_para(para) is True


# ── _check_body_content() ─────────────────────────────────────────────────────

def test_check_body_content_returns_checks():
    _, checks = _check_body_content(_DOCX, _make_body_metadata())
    assert len(checks) > 0

def test_check_body_content_has_alignment_field():
    _, checks = _check_body_content(_DOCX, _make_body_metadata())
    fields = [c.field for c in checks]
    assert "body_alignment" in fields, f"body_alignment tidak ada. Fields: {fields}"

def test_check_body_content_has_font_family_field():
    _, checks = _check_body_content(_DOCX, _make_body_metadata())
    fields = [c.field for c in checks]
    assert "body_font_family" in fields, f"body_font_family tidak ada. Fields: {fields}"

def test_check_body_content_excludes_headings():
    """Heading 1/2 tidak boleh masuk ke body check."""
    _, checks = _check_body_content(_DOCX, _make_body_metadata())
    for chk in [c for c in checks if c.field == "body_alignment"]:
        for occ in (chk.occurrences or []):
            assert "Heading" not in (occ.get("style") or ""), (
                f"Heading ditemukan di body check: style='{occ.get('style')}'"
            )

def test_check_body_content_includes_list_paragraph():
    _, checks = _check_body_content(_DOCX, _make_body_metadata())
    all_occs = [o for c in checks for o in (c.occurrences or [])]
    assert any((o.get("style") or "") == "List Paragraph" for o in all_occs), (
        "List Paragraph tidak ditemukan di body content check"
    )

def test_check_body_content_excludes_lampiran_captions():
    """'Lampiran X...' tidak boleh masuk ke body check — divalidasi di _check_figures_tables."""
    _, checks = _check_body_content(_DOCX, _make_body_metadata())
    all_occs = [o for c in checks for o in (c.occurrences or [])]
    lamp_in_body = [o for o in all_occs if (o.get("text") or "").startswith("Lampiran ")]
    assert len(lamp_in_body) == 0, f"Lampiran captions ditemukan di body check: {lamp_in_body[:3]}"

def test_check_body_content_results_in_doc_order():
    _, checks = _check_body_content(_DOCX, _make_body_metadata())
    all_idxs = [
        o.get("para_idx") for c in checks for o in (c.occurrences or [])
        if o.get("para_idx") is not None
    ]
    assert all_idxs == sorted(all_idxs), f"para_idx tidak berurutan: {all_idxs[:10]}..."


# ── caption_alignment dinamis di _check_caption_format() ─────────────────────

def test_caption_format_emits_figure_alignment_field():
    """Harus ada check field 'caption_alignment_figure'."""
    meta = _make_caption_metadata(fig_align="CENTER", tbl_align="CENTER")
    _, checks = _check_caption_format(_DOCX, meta)
    fields = [c.field for c in checks]
    assert "caption_alignment_figure" in fields, f"Fields: {fields}"

def test_caption_format_emits_table_alignment_field():
    """Harus ada check field 'caption_alignment_table'."""
    meta = _make_caption_metadata(fig_align="CENTER", tbl_align="CENTER")
    _, checks = _check_caption_format(_DOCX, meta)
    fields = [c.field for c in checks]
    assert "caption_alignment_table" in fields, f"Fields: {fields}"

def test_caption_format_figure_alignment_uses_metadata():
    """Jika metadata fig_align=CENTER dan semua caption gambar CENTER → passed."""
    meta = _make_caption_metadata(fig_align="CENTER")
    _, checks = _check_caption_format(_DOCX, meta)
    fig_align_checks = [c for c in checks if c.field == "caption_alignment_figure"]
    assert any(c.status == "passed" for c in fig_align_checks), (
        f"Tidak ada passed untuk caption_alignment_figure: {[(c.status, c.message) for c in fig_align_checks]}"
    )

def test_caption_format_figure_alignment_fails_on_wrong_value():
    """Jika metadata fig_align=LEFT tapi caption gambar CENTER → warning/failed."""
    meta = _make_caption_metadata(fig_align="LEFT")
    _, checks = _check_caption_format(_DOCX, meta)
    fig_align_checks = [c for c in checks if c.field == "caption_alignment_figure"]
    # Caption gambar di file_target.docx harusnya CENTER, jadi jika expected LEFT → ada masalah
    if fig_align_checks:
        statuses = [c.status for c in fig_align_checks]
        assert any(s in ("warning", "failed") for s in statuses), (
            f"Diharapkan warning/failed jika expected=LEFT, dapat: {statuses}"
        )

def test_caption_format_uses_metadata_not_hardcoded():
    """_check_caption_format harus membaca dari ft.caption_alignment_figure, bukan hardcode."""
    meta_center = _make_caption_metadata(fig_align="CENTER")
    meta_left   = _make_caption_metadata(fig_align="LEFT")
    _, checks_center = _check_caption_format(_DOCX, meta_center)
    _, checks_left   = _check_caption_format(_DOCX, meta_left)
    # Expected value harus berbeda antara dua call
    expected_center = next(
        (c.expected for c in checks_center if c.field == "caption_alignment_figure"), None
    )
    expected_left = next(
        (c.expected for c in checks_left if c.field == "caption_alignment_figure"), None
    )
    assert expected_center != expected_left, (
        "expected value identik padahal metadata berbeda — alignment masih hardcode"
    )


# ── caption_format_lampiran + caption_alignment_lampiran ─────────────────────

def test_figures_tables_lampiran_format_field_emitted():
    """Jika caption_format_lampiran diset, harus ada field 'lampiran_caption_format'."""
    meta = _make_caption_metadata(lamp_fmt="Lampiran {n}. {title}")
    _, checks = _check_figures_tables(_DOCX, meta)
    fields = [c.field for c in checks]
    assert "lampiran_caption_format" in fields, f"Fields: {fields}"

def test_figures_tables_lampiran_format_skipped_when_none():
    """Jika caption_format_lampiran=None, tidak ada check 'lampiran_caption_format'."""
    meta = _make_caption_metadata(lamp_fmt=None, lamp_align=None)
    _, checks = _check_figures_tables(_DOCX, meta)
    fields = [c.field for c in checks]
    assert "lampiran_caption_format" not in fields, f"Muncul padahal None: {fields}"

def test_figures_tables_lampiran_alignment_field_emitted():
    """Jika caption_alignment_lampiran diset, harus ada field 'lampiran_caption_alignment'."""
    meta = _make_caption_metadata(lamp_align="CENTER", lamp_fmt=None)
    _, checks = _check_figures_tables(_DOCX, meta)
    fields = [c.field for c in checks]
    assert "lampiran_caption_alignment" in fields, f"Fields: {fields}"

def test_figures_tables_lampiran_alignment_skipped_when_none():
    """Jika caption_alignment_lampiran=None, tidak ada check 'lampiran_caption_alignment'."""
    meta = _make_caption_metadata(lamp_align=None, lamp_fmt=None)
    _, checks = _check_figures_tables(_DOCX, meta)
    fields = [c.field for c in checks]
    assert "lampiran_caption_alignment" not in fields, f"Muncul padahal None: {fields}"
```

- [ ] **Step 2: Pastikan test GAGAL**

```bash
cd ai/model && python -m pytest tests/test_body_content_check.py -v
```

Expected: `ImportError: cannot import name '_is_heading_para'` atau `'_check_body_content'`.

- [ ] **Step 3: Commit test**

```bash
git add ai/model/tests/test_body_content_check.py
git commit -m "test: tambah failing test untuk body_content, caption_alignment dinamis, lampiran format+alignment"
```

---

## Task 2: Tambah Field Model + Konstanta + `_is_heading_para()` + `_check_body_content()`

**Files:**
- Modify: `ai/model/model_ai/extractor/models.py`
- Modify: `ai/model/model_ai/validation/validocx_runner.py`

### Bagian A — Tambah field ke `FiguresTablesExtracted` di `models.py`

- [ ] **Step 1: Perbarui kelas `FiguresTablesExtracted` (baris 214–220)**

**Cari blok lama:**

```python
class FiguresTablesExtracted(BaseModel):
    table_caption_position: str | None = None
    figure_caption_position: str | None = None
    caption_format_figure: str | None = None
    caption_format_table: str | None = None
    caption_format_lampiran: str | None = None
    budget_format_rules: "BudgetFormatRules | None" = None
```

**Ganti dengan:**

```python
class FiguresTablesExtracted(BaseModel):
    table_caption_position: str | None = None
    figure_caption_position: str | None = None
    caption_format_figure: str | None = None
    caption_format_table: str | None = None
    caption_format_lampiran: str | None = None
    # Alignment caption per tipe — CENTER | LEFT | RIGHT | JUSTIFY.
    # Null berarti gunakan CENTER sebagai default (backward-compatible).
    caption_alignment_figure:   str | None = None
    caption_alignment_table:    str | None = None
    caption_alignment_lampiran: str | None = None
    budget_format_rules: "BudgetFormatRules | None" = None
```

### Bagian B — Tambah konstanta ke `validocx_runner.py`

- [ ] **Step 2: Ganti blok `_FIG_DETECT_RE` / `_TBL_DETECT_RE` (baris 84–88)**

**Cari blok lama:**

```python
# Pola deteksi caption gambar/tabel
_FIG_DETECT_RE = re.compile(r'^Gambar\s+\d+', re.IGNORECASE)
_TBL_DETECT_RE = re.compile(r'^Tabel\s+\d+', re.IGNORECASE)
```

**Ganti dengan:**

```python
# Pola deteksi caption gambar / tabel / lampiran
_FIG_DETECT_RE  = re.compile(r'^Gambar\s+\d+', re.IGNORECASE)
_TBL_DETECT_RE  = re.compile(r'^Tabel\s+\d+',  re.IGNORECASE)
_LAMP_DETECT_RE = re.compile(r'^Lampiran\s+',   re.IGNORECASE)

# Mapping string alignment dari metadata → enum WD_ALIGN_PARAGRAPH
_CAPTION_ALIGN_MAP: dict[str, "WD_ALIGN_PARAGRAPH"] = {
    "CENTER":  WD_ALIGN_PARAGRAPH.CENTER,
    "LEFT":    WD_ALIGN_PARAGRAPH.LEFT,
    "RIGHT":   WD_ALIGN_PARAGRAPH.RIGHT,
    "JUSTIFY": WD_ALIGN_PARAGRAPH.JUSTIFY,
}

# Keyword untuk mendeteksi heading dari style name / inheritance chain.
_HEADING_STYLE_KEYWORDS: frozenset[str] = frozenset({"heading", "judul"})
_HEADING_PARAM_KEYWORDS: frozenset[str] = frozenset({"heading", "judul"})
```

### Bagian C — Tambah `_is_heading_para()` setelah `_humanize_attr_value()`

- [ ] **Step 3: Tambah fungsi setelah penutup `_humanize_attr_value()` (sekitar baris 121)**

```python
def _is_heading_para(para) -> bool:
    """Deteksi apakah paragraf adalah heading berdasarkan style name + inheritance chain.

    Menelusuri style dan semua base_style-nya hingga kedalaman 10.
    Return True jika nama style mengandung 'heading' atau 'judul' (case-insensitive).
    """
    style = para.style
    depth = 0
    while style is not None and depth < 10:
        name = (style.name or "").lower()
        if any(k in name for k in _HEADING_STYLE_KEYWORDS):
            return True
        style = getattr(style, "base_style", None)
        depth += 1
    return False
```

### Bagian D — Tambah `_check_body_content()` setelah `_check_lampiran_format()`

- [ ] **Step 4: Tambah fungsi setelah `return issues, checks` penutup `_check_lampiran_format()` (~baris 1070)**

```python
def _check_body_content(
    docx_path: Path,
    metadata: DocumentMetadata,
) -> tuple[list[ValidationIssue], list[ValidationCheckResult]]:
    """Validasi konten non-heading via content-based check.

    Iterasi SEMUA paragraf (termasuk w:sdt seperti TOC), skip heading dan semua
    jenis caption, cek alignment/font_family/font_size/line_spacing dari metadata.
    Hasil diagregasi per nilai parameter — bukan per nama style.

    Skip rules:
      - Paragraf kosong (text.strip() == "")
      - Heading: style name/inheritance mengandung 'heading' atau 'judul'
      - Caption gambar   : teks diawali 'Gambar \\d'  → dicek _check_caption_format
      - Caption tabel    : teks diawali 'Tabel \\d'   → dicek _check_caption_format
      - Caption lampiran : teks diawali 'Lampiran '   → dicek _check_figures_tables
    """
    issues: list[ValidationIssue] = []
    checks: list[ValidationCheckResult] = []

    t = metadata.typography
    s = metadata.spacing
    expected_align   = WD_ALIGN_PARAGRAPH.JUSTIFY
    expected_font    = t.font_family if t else None
    expected_size    = int(t.font_size_body_pt) if t and t.font_size_body_pt else None
    expected_spacing = float(s.line_spacing) if s and s.line_spacing else None

    try:
        from model_ai.validation.validocx.wrapper import DocumentWrapper

        doc     = DocxDocument(str(docx_path))
        wrapper = DocumentWrapper(doc)

        align_pass:   list[dict] = []
        align_fail:   list[dict] = []
        font_pass:    list[dict] = []
        font_fail:    list[dict] = []
        size_pass:    list[dict] = []
        size_fail:    list[dict] = []
        spacing_pass: list[dict] = []
        spacing_fail: list[dict] = []

        for idx, para in enumerate(wrapper.iter_paragraphs()):
            text = para.text.strip()
            if not text:
                continue
            if _is_heading_para(para):
                continue
            # Caption gambar/tabel/lampiran divalidasi di fungsi tersendiri
            if (
                _FIG_DETECT_RE.match(text)
                or _TBL_DETECT_RE.match(text)
                or _LAMP_DETECT_RE.match(text)
            ):
                continue

            para_info: dict = {
                "para_idx" : idx,
                "style"    : para.style.name,
                "text"     : text[:100],
                "full_text": text,
                "bab"      : None,
                "page"     : None,
            }

            # ── Alignment ─────────────────────────────────────────────────────
            align = para.paragraph_format.alignment
            if align is None:
                try:
                    align = para.style.paragraph_format.alignment
                except Exception:
                    align = None
            if align is None or align == expected_align:
                align_pass.append(para_info)
            else:
                align_fail.append({**para_info, "actual": str(int(align))})

            # ── Font family & font size (run pertama yang punya teks) ─────────
            for run in para.runs:
                if not run.text.strip():
                    continue
                fn = run.font.name
                if fn is not None:
                    if expected_font and fn != expected_font:
                        font_fail.append({**para_info, "actual": fn})
                    else:
                        font_pass.append(para_info)
                fs = run.font.size
                if fs is not None:
                    fs_pt = round(fs.pt)
                    if expected_size and fs_pt != expected_size:
                        size_fail.append({**para_info, "actual": f"{fs_pt}pt"})
                    else:
                        size_pass.append(para_info)
                break  # cukup satu run

            # ── Line spacing ──────────────────────────────────────────────────
            if expected_spacing:
                ls = para.paragraph_format.line_spacing
                if ls is not None:
                    try:
                        ls_val = round(float(ls), 2)
                        if abs(ls_val - expected_spacing) > 0.05:
                            spacing_fail.append({**para_info, "actual": str(ls_val)})
                        else:
                            spacing_pass.append(para_info)
                    except (TypeError, ValueError):
                        spacing_pass.append(para_info)

        # ── Emit satu check per parameter ────────────────────────────────────
        def _emit(
            field: str,
            label: str,
            expected_val: str,
            pass_list: list[dict],
            fail_list: list[dict],
        ) -> None:
            if not pass_list and not fail_list:
                return
            if fail_list:
                actual_vals = list(dict.fromkeys(d.get("actual", "?") for d in fail_list))
                actual_str  = ", ".join(str(v) for v in actual_vals[:3])
                msg = (
                    f"{label}: {len(fail_list)} elemen tidak sesuai "
                    f"(ekspektasi: {expected_val}). Ditemukan: {actual_str}"
                )
                occs = _build_occurrences(fail_list, actual_str=actual_str,
                                          expected_str=expected_val) or None
                issues.append(ValidationIssue(
                    category="typography", field=field,
                    severity="error", message=msg,
                    expected=expected_val, actual=actual_str,
                    occurrences=occs,
                ))
                checks.append(ValidationCheckResult(
                    category="typography", field=field,
                    status="failed", message=msg,
                    expected=expected_val, actual=actual_str,
                    occurrences=occs,
                ))
            if pass_list:
                occs = _build_occurrences(pass_list, expected_str=expected_val) or None
                checks.append(ValidationCheckResult(
                    category="typography", field=field,
                    status="passed",
                    message=f"{label}: {len(pass_list)} elemen lolos",
                    expected=expected_val,
                    actual=expected_val,
                    occurrences=occs,
                ))

        _emit("body_alignment",    "Alignment (JUSTIFY)",            "JUSTIFY",
              align_pass,   align_fail)
        if expected_font:
            _emit("body_font_family",  f"Font family ({expected_font})",   expected_font,
                  font_pass,    font_fail)
        if expected_size:
            _emit("body_font_size",    f"Ukuran font ({expected_size}pt)", f"{expected_size}pt",
                  size_pass,    size_fail)
        if expected_spacing:
            _emit("body_line_spacing", f"Spasi baris ({expected_spacing})", str(expected_spacing),
                  spacing_pass, spacing_fail)

    except Exception as exc:
        checks.append(ValidationCheckResult(
            category="typography", field="body_content",
            status="skipped",
            message=f"Pengecekan konten body dilewati: {exc}",
            skip_reason=str(exc),
        ))

    return issues, checks
```

- [ ] **Step 5: Jalankan test subset — pastikan helper LULUS**

```bash
cd ai/model && python -m pytest tests/test_body_content_check.py -k "is_heading or body_content" -v
```

Expected: semua test `_is_heading_para` dan `_check_body_content` PASS.

- [ ] **Step 6: Commit**

```bash
git add ai/model/model_ai/extractor/models.py ai/model/model_ai/validation/validocx_runner.py
git commit -m "feat(validation): tambah caption_alignment fields ke model, _LAMP_DETECT_RE, _is_heading_para(), _check_body_content()"
```

---

## Task 3: Filter `parameter_summary` + Wire ke `run_validocx()`

**Files:**
- Modify: `ai/model/model_ai/validation/validocx_runner.py`

### Bagian A — Filter `_build_issues_checks()` parameter_summary

- [ ] **Step 1: Ganti blok parameter_summary (sekitar baris 460–481)**

**Cari blok lama** (persis):

```python
    # ── Parameter summary sebagai check passed ───────────────────────────────
    for ps in report.get("parameter_summary", []):
        if ps["status"] in ("lolos semua", "lolos semua (ada inherited)"):
            raw_details = ps.get("paragraph_details_pass", [])
            occs = _build_occurrences(raw_details) or None

            # Cari expected value dari requirements: "param (Style Name)" → parse → lookup
            expected_val: str | None = None
            if requirements:
                m = re.match(r'^(\S+)\s+\((.+)\)$', ps["parameter"])
                if m:
                    expected_val = _lookup_expected(requirements, m.group(1), m.group(2))

            checks.append(ValidationCheckResult(
                category="typography",
                field=f"validocx_param.{ps['parameter'].replace(' ', '_')}",
                status="passed",
                message=f"{ps['parameter']}: {ps['pass']} elemen lolos",
                expected=expected_val,
                actual=expected_val,  # sama dengan expected karena semua lolos
                occurrences=occs,
            ))
```

**Ganti dengan:**

```python
    # ── Parameter summary sebagai check passed (heading only) ────────────────
    # Non-heading summary digantikan oleh _check_body_content() yang mengagregasi
    # per nilai parameter. Di sini hanya tampilkan hasil heading (Heading 1–5, Judul*).
    for ps in report.get("parameter_summary", []):
        if ps["status"] not in ("lolos semua", "lolos semua (ada inherited)"):
            continue
        param_match = re.match(r'^(\S+)\s+\((.+)\)$', ps["parameter"])
        style_in_param = (param_match.group(2) if param_match else "").lower()
        if not any(k in style_in_param for k in _HEADING_PARAM_KEYWORDS):
            continue

        raw_details = ps.get("paragraph_details_pass", [])
        occs = _build_occurrences(raw_details) or None

        expected_val: str | None = None
        if requirements and param_match:
            expected_val = _lookup_expected(
                requirements, param_match.group(1), param_match.group(2)
            )

        checks.append(ValidationCheckResult(
            category="typography",
            field=f"validocx_param.{ps['parameter'].replace(' ', '_')}",
            status="passed",
            message=f"{ps['parameter']}: {ps['pass']} elemen lolos",
            expected=expected_val,
            actual=expected_val,
            occurrences=occs,
        ))
```

### Bagian B — Wire ke `run_validocx()`

- [ ] **Step 2: Ganti blok akhir `run_validocx()` (sekitar baris 2035–2050)**

**Cari blok lama:**

```python
    case_issues, case_checks         = _check_heading_case(path, metadata)
    struct_issues, struct_checks     = _check_document_structure(path, metadata)
    fig_issues, fig_checks           = _check_figures_tables(path, metadata)
    caption_issues, caption_checks   = _check_caption_format(path, metadata)
    lampiran_issues, lampiran_checks = _check_lampiran_format(path, metadata)
    num_issues, num_checks           = _check_numbering(path, metadata)
    pgcount_issues, pgcount_checks   = _check_page_count(path, metadata)

    all_issues = issues + case_issues + struct_issues + fig_issues + caption_issues + lampiran_issues + num_issues + pgcount_issues
    all_checks = checks + case_checks + struct_checks + fig_checks + caption_checks + lampiran_checks + num_checks + pgcount_checks
    return all_issues, all_checks
```

**Ganti dengan:**

```python
    case_issues, case_checks         = _check_heading_case(path, metadata)
    struct_issues, struct_checks     = _check_document_structure(path, metadata)
    fig_issues, fig_checks           = _check_figures_tables(path, metadata)
    caption_issues, caption_checks   = _check_caption_format(path, metadata)
    lampiran_issues, lampiran_checks = _check_lampiran_format(path, metadata)
    num_issues, num_checks           = _check_numbering(path, metadata)
    pgcount_issues, pgcount_checks   = _check_page_count(path, metadata)
    body_issues, body_checks         = _check_body_content(path, metadata)

    all_issues = (issues + case_issues + struct_issues + fig_issues
                  + caption_issues + lampiran_issues + num_issues
                  + pgcount_issues + body_issues)
    all_checks = (checks + case_checks + struct_checks + fig_checks
                  + caption_checks + lampiran_checks + num_checks
                  + pgcount_checks + body_checks)
    return all_issues, all_checks
```

- [ ] **Step 3: Jalankan test — pastikan tidak ada regresi**

```bash
cd ai/model && python -m pytest tests/ -v
```

Expected: test body_content PASS; test caption_alignment masih FAIL (Task 4 belum).

- [ ] **Step 4: Commit**

```bash
git add ai/model/model_ai/validation/validocx_runner.py
git commit -m "feat(validation): wire _check_body_content() ke run_validocx(), filter parameter_summary ke heading only"
```

---

## Task 4: Caption Alignment Dinamis + `caption_format_lampiran` + `caption_alignment_lampiran`

**Files:**
- Modify: `ai/model/model_ai/validation/validocx_runner.py`

Dua fungsi yang diperbarui:
1. `_check_caption_format()` — alignment gambar/tabel dibaca dari metadata, bukan hardcode CENTER
2. `_check_figures_tables()` — tambah scan lampiran: format + alignment

---

### Bagian A — Update `_check_caption_format()` untuk alignment dinamis

Fungsi saat ini (baris 1072–1214) memiliki satu `wrong_alignment` list yang mengecek semua caption terhadap CENTER. Perlu diganti agar gambar dan tabel dicek terpisah terhadap nilai dari metadata.

- [ ] **Step 1: Ganti seluruh isi fungsi `_check_caption_format()`**

**Cari fungsi lama** mulai dari:
```python
def _check_caption_format(
    docx_path: Path,
    metadata: DocumentMetadata,
) -> tuple[list[ValidationIssue], list[ValidationCheckResult]]:
    """Validasi atribut caption gambar/tabel via text-pattern, bukan style name.
```

**Ganti seluruh isi** hingga `return issues, checks` pertamanya dengan:

```python
def _check_caption_format(
    docx_path: Path,
    metadata: DocumentMetadata,
) -> tuple[list[ValidationIssue], list[ValidationCheckResult]]:
    """Validasi atribut caption gambar/tabel via text-pattern, bukan style name.

    Caption dideteksi dari teks yang diawali 'Gambar <angka>' atau 'Tabel <angka>'.
    Alignment dibaca dari metadata.figures_and_tables per tipe caption (CENTER fallback).
    Font family dan font size harus sama dengan body — dicek per tipe caption.
    Style name diabaikan agar tidak false positive pada nama dinamis.
    """
    issues: list[ValidationIssue] = []
    checks: list[ValidationCheckResult] = []

    t  = metadata.typography
    ft = metadata.figures_and_tables

    expected_font = t.font_family if t else None
    expected_size = int(t.font_size_body_pt) if t and t.font_size_body_pt else None

    # Baca alignment per tipe dari metadata; default CENTER jika null
    fig_align_str = ((ft.caption_alignment_figure or "CENTER").upper() if ft else "CENTER")
    tbl_align_str = ((ft.caption_alignment_table  or "CENTER").upper() if ft else "CENTER")
    fig_align_val = _CAPTION_ALIGN_MAP.get(fig_align_str, WD_ALIGN_PARAGRAPH.CENTER)
    tbl_align_val = _CAPTION_ALIGN_MAP.get(tbl_align_str, WD_ALIGN_PARAGRAPH.CENTER)

    try:
        doc = DocxDocument(str(docx_path))

        wrong_fig_alignment: list[str] = []
        wrong_tbl_alignment: list[str] = []
        wrong_font:          list[str] = []
        wrong_size:          list[str] = []
        fig_total = 0
        tbl_total = 0

        for para in doc.paragraphs:
            text = para.text.strip()
            if not text:
                continue

            is_fig = bool(_FIG_DETECT_RE.match(text))
            is_tbl = bool(_TBL_DETECT_RE.match(text))
            if not is_fig and not is_tbl:
                continue

            if is_fig:
                fig_total += 1
            else:
                tbl_total += 1

            # ── Alignment ────────────────────────────────────────────────────
            align = para.paragraph_format.alignment
            if align is None:
                try:
                    align = para.style.paragraph_format.alignment
                except Exception:
                    align = None

            if align is not None:
                if is_fig and align != fig_align_val:
                    wrong_fig_alignment.append(text[:70])
                elif is_tbl and align != tbl_align_val:
                    wrong_tbl_alignment.append(text[:70])

            # ── Font family & size ────────────────────────────────────────────
            for run in para.runs:
                if expected_font and run.font.name and run.font.name != expected_font:
                    wrong_font.append(text[:70])
                    break
                if expected_size and run.font.size:
                    run_pt = round(run.font.size.pt)
                    if run_pt != expected_size:
                        wrong_size.append(text[:70])
                        break

        # ── Emit alignment gambar ─────────────────────────────────────────────
        if fig_total > 0:
            if wrong_fig_alignment:
                msg = (
                    f"{len(wrong_fig_alignment)} caption gambar tidak {fig_align_str}. "
                    f'Contoh: "{wrong_fig_alignment[0]}"'
                )
                issues.append(ValidationIssue(
                    category="figures_tables", field="caption_alignment_figure",
                    severity="error", message=msg,
                    expected=fig_align_str, actual=f"bukan {fig_align_str}",
                ))
                checks.append(ValidationCheckResult(
                    category="figures_tables", field="caption_alignment_figure",
                    status="failed", message=msg,
                    expected=fig_align_str, actual=f"bukan {fig_align_str}",
                ))
            else:
                checks.append(ValidationCheckResult(
                    category="figures_tables", field="caption_alignment_figure",
                    status="passed",
                    message=f"Semua {fig_total} caption gambar alignment {fig_align_str}",
                    expected=fig_align_str,
                ))

        # ── Emit alignment tabel ──────────────────────────────────────────────
        if tbl_total > 0:
            if wrong_tbl_alignment:
                msg = (
                    f"{len(wrong_tbl_alignment)} caption tabel tidak {tbl_align_str}. "
                    f'Contoh: "{wrong_tbl_alignment[0]}"'
                )
                issues.append(ValidationIssue(
                    category="figures_tables", field="caption_alignment_table",
                    severity="error", message=msg,
                    expected=tbl_align_str, actual=f"bukan {tbl_align_str}",
                ))
                checks.append(ValidationCheckResult(
                    category="figures_tables", field="caption_alignment_table",
                    status="failed", message=msg,
                    expected=tbl_align_str, actual=f"bukan {tbl_align_str}",
                ))
            else:
                checks.append(ValidationCheckResult(
                    category="figures_tables", field="caption_alignment_table",
                    status="passed",
                    message=f"Semua {tbl_total} caption tabel alignment {tbl_align_str}",
                    expected=tbl_align_str,
                ))

        # ── Emit font (gabungan gambar + tabel) ───────────────────────────────
        total_captions = fig_total + tbl_total
        if wrong_font:
            msg = (
                f"{len(wrong_font)} caption font tidak sesuai (ekspektasi: {expected_font}). "
                f'Contoh: "{wrong_font[0]}"'
            )
            issues.append(ValidationIssue(
                category="figures_tables", field="caption_font",
                severity="warning", message=msg,
                expected=expected_font, actual=wrong_font[0],
            ))
            checks.append(ValidationCheckResult(
                category="figures_tables", field="caption_font",
                status="warning", message=msg,
                expected=expected_font, actual=wrong_font[0],
            ))
        elif expected_font and total_captions > 0:
            checks.append(ValidationCheckResult(
                category="figures_tables", field="caption_font",
                status="passed",
                message=f"Font caption sesuai: {expected_font}",
                expected=expected_font,
            ))

        if wrong_size:
            msg = (
                f"{len(wrong_size)} caption ukuran font tidak sesuai "
                f"(ekspektasi: {expected_size}pt). "
                f'Contoh: "{wrong_size[0]}"'
            )
            issues.append(ValidationIssue(
                category="figures_tables", field="caption_font_size",
                severity="warning", message=msg,
                expected=str(expected_size), actual=wrong_size[0],
            ))
            checks.append(ValidationCheckResult(
                category="figures_tables", field="caption_font_size",
                status="warning", message=msg,
                expected=str(expected_size), actual=wrong_size[0],
            ))
        elif expected_size and total_captions > 0:
            checks.append(ValidationCheckResult(
                category="figures_tables", field="caption_font_size",
                status="passed",
                message=f"Ukuran font caption sesuai: {expected_size}pt",
                expected=str(expected_size),
            ))

        if total_captions == 0:
            checks.append(ValidationCheckResult(
                category="figures_tables", field="caption_alignment_figure",
                status="skipped",
                message="Tidak ada caption gambar/tabel ditemukan",
                skip_reason="Tidak ada caption",
            ))

    except Exception as exc:
        checks.append(ValidationCheckResult(
            category="figures_tables", field="caption_alignment_figure",
            status="skipped",
            message=f"Pengecekan atribut caption dilewati: {exc}",
            skip_reason=str(exc),
        ))

    return issues, checks
```

---

### Bagian B — Update `_check_figures_tables()` untuk lampiran scan

- [ ] **Step 2: Perbarui blok baca metadata (baris 1235–1248)**

**Cari blok lama:**

```python
    tbl_pos_exp = (ft.table_caption_position or "").upper()
    fig_pos_exp = (ft.figure_caption_position or "").upper()
    fig_fmt_tpl = ft.caption_format_figure
    tbl_fmt_tpl = ft.caption_format_table

    if not tbl_pos_exp and not fig_pos_exp and not fig_fmt_tpl and not tbl_fmt_tpl:
```

**Ganti dengan:**

```python
    tbl_pos_exp  = (ft.table_caption_position or "").upper()
    fig_pos_exp  = (ft.figure_caption_position or "").upper()
    fig_fmt_tpl  = ft.caption_format_figure
    tbl_fmt_tpl  = ft.caption_format_table
    lamp_fmt_tpl = ft.caption_format_lampiran
    lamp_align_str = (ft.caption_alignment_lampiran or "").upper() or None

    if not tbl_pos_exp and not fig_pos_exp and not fig_fmt_tpl and not tbl_fmt_tpl \
            and not lamp_fmt_tpl and not lamp_align_str:
```

- [ ] **Step 3: Tambah `lamp_fmt_re` di blok inisialisasi regex (baris 1252–1253)**

**Cari blok lama:**

```python
        fig_fmt_re = _template_to_regex(fig_fmt_tpl) if fig_fmt_tpl else None
        tbl_fmt_re = _template_to_regex(tbl_fmt_tpl) if tbl_fmt_tpl else None
```

**Ganti dengan:**

```python
        fig_fmt_re  = _template_to_regex(fig_fmt_tpl)  if fig_fmt_tpl  else None
        tbl_fmt_re  = _template_to_regex(tbl_fmt_tpl)  if tbl_fmt_tpl  else None
        lamp_fmt_re = _template_to_regex(lamp_fmt_tpl) if lamp_fmt_tpl else None
        lamp_align_val = (
            _CAPTION_ALIGN_MAP.get(lamp_align_str, WD_ALIGN_PARAGRAPH.CENTER)
            if lamp_align_str else None
        )
```

- [ ] **Step 4: Tambah scan lampiran SETELAH blok `# Report tabel` (sebelum `except Exception`)**

Cari baris terakhir blok tabel:
```python
                else:
                    checks.append(ValidationCheckResult(
                        category="figures_tables", field="table_caption_format",
                        status="passed",
                        message=f"Format caption tabel '{tbl_fmt_tpl}': {tbl_count} caption sesuai",
                        expected=tbl_fmt_tpl,
                    ))
```

Tambahkan blok berikut SETELAH `))` penutupnya dan SEBELUM `    except Exception as exc:`:

```python
        # ── Lampiran scan (seluruh dokumen) ──────────────────────────────────
        # _build_content_elements() berhenti sebelum LAMPIRAN → scan terpisah.
        if lamp_fmt_re or lamp_align_val is not None:
            lamp_count          = 0
            lamp_fmt_errors:    list[str] = []
            lamp_align_errors:  list[str] = []

            for para in doc.paragraphs:
                text = para.text.strip()
                if not text or not _LAMP_DETECT_RE.match(text):
                    continue
                lamp_count += 1

                if lamp_fmt_re and not lamp_fmt_re.match(text):
                    lamp_fmt_errors.append(text[:70])

                if lamp_align_val is not None:
                    align = para.paragraph_format.alignment
                    if align is None:
                        try:
                            align = para.style.paragraph_format.alignment
                        except Exception:
                            align = None
                    if align is not None and align != lamp_align_val:
                        lamp_align_errors.append(text[:70])

            # Emit format lampiran
            if lamp_fmt_re:
                if lamp_count == 0:
                    checks.append(ValidationCheckResult(
                        category="figures_tables", field="lampiran_caption_format",
                        status="skipped",
                        message="Tidak ditemukan caption lampiran di dokumen",
                        skip_reason="Tidak ada paragraf diawali 'Lampiran '",
                    ))
                elif lamp_fmt_errors:
                    msg = (
                        f"Format caption lampiran tidak sesuai pola '{lamp_fmt_tpl}'. "
                        f"{len(lamp_fmt_errors)}x salah. "
                        f'Contoh: "{lamp_fmt_errors[0]}"'
                    )
                    issues.append(ValidationIssue(
                        category="figures_tables", field="lampiran_caption_format",
                        severity="warning", message=msg,
                        expected=lamp_fmt_tpl, actual=lamp_fmt_errors[0],
                    ))
                    checks.append(ValidationCheckResult(
                        category="figures_tables", field="lampiran_caption_format",
                        status="warning", message=msg,
                        expected=lamp_fmt_tpl, actual=lamp_fmt_errors[0],
                    ))
                else:
                    checks.append(ValidationCheckResult(
                        category="figures_tables", field="lampiran_caption_format",
                        status="passed",
                        message=f"Format caption lampiran '{lamp_fmt_tpl}': {lamp_count} caption sesuai",
                        expected=lamp_fmt_tpl,
                    ))

            # Emit alignment lampiran
            if lamp_align_val is not None:
                if lamp_count == 0:
                    checks.append(ValidationCheckResult(
                        category="figures_tables", field="lampiran_caption_alignment",
                        status="skipped",
                        message="Tidak ditemukan caption lampiran di dokumen",
                        skip_reason="Tidak ada paragraf diawali 'Lampiran '",
                    ))
                elif lamp_align_errors:
                    msg = (
                        f"{len(lamp_align_errors)} caption lampiran tidak {lamp_align_str}. "
                        f'Contoh: "{lamp_align_errors[0]}"'
                    )
                    issues.append(ValidationIssue(
                        category="figures_tables", field="lampiran_caption_alignment",
                        severity="error", message=msg,
                        expected=lamp_align_str, actual=f"bukan {lamp_align_str}",
                    ))
                    checks.append(ValidationCheckResult(
                        category="figures_tables", field="lampiran_caption_alignment",
                        status="failed", message=msg,
                        expected=lamp_align_str, actual=f"bukan {lamp_align_str}",
                    ))
                else:
                    checks.append(ValidationCheckResult(
                        category="figures_tables", field="lampiran_caption_alignment",
                        status="passed",
                        message=f"Semua {lamp_count} caption lampiran alignment {lamp_align_str}",
                        expected=lamp_align_str,
                    ))
```

- [ ] **Step 5: Jalankan semua test**

```bash
cd ai/model && python -m pytest tests/test_body_content_check.py -v
```

Expected: **semua test PASS**.

- [ ] **Step 6: Jalankan full test suite**

```bash
cd ai/model && python -m pytest tests/ -v
```

Expected: semua PASS, tidak ada regresi (3 pre-existing failures boleh tetap).

- [ ] **Step 7: Commit**

```bash
git add ai/model/model_ai/validation/validocx_runner.py
git commit -m "feat(validation): caption_alignment dinamis per tipe, tambah lampiran format+alignment scan di _check_figures_tables"
```

---

## Verifikasi Manual (Opsional)

```bash
cd ai/model && python - <<'EOF'
from pathlib import Path
from unittest.mock import MagicMock
from model_ai.validation.validocx_runner import (
    _check_body_content, _check_caption_format, _check_figures_tables
)

DOCX = Path("tests/file_target.docx")

# Body content
meta_b = MagicMock()
meta_b.typography.font_family = "Times New Roman"
meta_b.typography.font_size_body_pt = 12
meta_b.spacing.line_spacing = 1.15
meta_b.spacing.line_spacing_rule = None
_, checks = _check_body_content(DOCX, meta_b)
print("=== body_content ===")
for c in checks:
    print(f"  [{c.status}] {c.field}: {c.message[:70]}")

# Caption alignment
meta_c = MagicMock()
meta_c.typography.font_family = "Times New Roman"
meta_c.typography.font_size_body_pt = 12
meta_c.figures_and_tables.caption_alignment_figure   = "CENTER"
meta_c.figures_and_tables.caption_alignment_table    = "CENTER"
meta_c.figures_and_tables.caption_alignment_lampiran = "CENTER"
meta_c.figures_and_tables.caption_format_lampiran    = "Lampiran {n}. {title}"
meta_c.figures_and_tables.caption_format_figure      = None
meta_c.figures_and_tables.caption_format_table       = None
meta_c.figures_and_tables.figure_caption_position    = None
meta_c.figures_and_tables.table_caption_position     = None
_, checks2 = _check_caption_format(DOCX, meta_c)
print("\n=== caption_format (alignment dinamis) ===")
for c in checks2:
    print(f"  [{c.status}] {c.field}: {c.message[:70]}")

_, checks3 = _check_figures_tables(DOCX, meta_c)
print("\n=== figures_tables (lampiran) ===")
for c in checks3:
    if "lampiran" in c.field:
        print(f"  [{c.status}] {c.field}: {c.message[:70]}")
EOF
```

Expected output (contoh):
```
=== body_content ===
  [passed] body_alignment: Alignment (JUSTIFY): 155 elemen lolos
  [passed] body_font_family: Font family (Times New Roman): 89 elemen lolos
  ...

=== caption_format (alignment dinamis) ===
  [passed] caption_alignment_figure: Semua 7 caption gambar alignment CENTER
  [passed] caption_alignment_table: Semua 5 caption tabel alignment CENTER
  [passed] caption_font: Font caption sesuai: Times New Roman
  ...

=== figures_tables (lampiran) ===
  [passed] lampiran_caption_format: Format caption lampiran '...': 5 caption sesuai
  [passed] lampiran_caption_alignment: Semua 5 caption lampiran alignment CENTER
```
