# ai/model/tests/test_body_content_check.py
"""Test untuk _is_heading_para, _check_body_content, caption_alignment dinamis di
_check_caption_format / _check_figures_tables, dan FiguresTablesExtracted validator."""
import pytest
from pathlib import Path
from unittest.mock import MagicMock

from model_ai.extractor.models import FiguresTablesExtracted
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


def _make_body_metadata(font: str = "Times New Roman", size: int = 12, spacing: float = 1.15) -> MagicMock:
    meta = MagicMock()
    meta.typography.font_family = font
    meta.typography.font_size_body_pt = size
    meta.spacing.line_spacing = spacing
    meta.spacing.line_spacing_rule = None
    return meta


def _make_caption_metadata(
    font: str = "Times New Roman",
    size: int = 12,
    fig_align: str | None = "CENTER",
    tbl_align: str | None = "CENTER",
    lamp_align: str | None = "CENTER",
    fig_fmt: str | None = None,
    tbl_fmt: str | None = None,
    lamp_fmt: str | None = None,
    fig_pos: str | None = None,
    tbl_pos: str | None = None,
) -> MagicMock:
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
    para = _mock_para("CustomBab", base_style_name="Heading 1")
    assert _is_heading_para(para) is True


# ── _check_body_content() ─────────────────────────────────────────────────────

@pytest.fixture(scope="module")
def _body_checks_cache():
    _, checks = _check_body_content(_DOCX, _make_body_metadata())
    return checks


def test_check_body_content_returns_checks(_body_checks_cache):
    checks = _body_checks_cache
    fields = {c.field for c in checks}
    assert {"body_alignment", "body_font_family"}.issubset(fields), (
        f"Check wajib tidak ada. Fields aktual: {fields}"
    )

def test_check_body_content_has_alignment_field(_body_checks_cache):
    checks = _body_checks_cache
    fields = [c.field for c in checks]
    assert "body_alignment" in fields, f"body_alignment tidak ada. Fields: {fields}"

def test_check_body_content_has_font_family_field(_body_checks_cache):
    checks = _body_checks_cache
    fields = [c.field for c in checks]
    assert "body_font_family" in fields, f"body_font_family tidak ada. Fields: {fields}"

def test_check_body_content_excludes_headings(_body_checks_cache):
    checks = _body_checks_cache
    for chk in [c for c in checks if c.field == "body_alignment"]:
        for occ in (chk.occurrences or []):
            assert "Heading" not in (occ.get("style") or ""), (
                f"Heading ditemukan di body check: style='{occ.get('style')}'"
            )

def test_check_body_content_includes_list_paragraph(_body_checks_cache):
    checks = _body_checks_cache
    all_occs = [o for c in checks for o in (c.occurrences or [])]
    assert any((o.get("style") or "") == "List Paragraph" for o in all_occs), (
        "List Paragraph tidak ditemukan di body content check"
    )

def test_check_body_content_excludes_lampiran_captions(_body_checks_cache):
    checks = _body_checks_cache
    all_occs = [o for c in checks for o in (c.occurrences or [])]
    lamp_in_body = [o for o in all_occs if (o.get("text") or "").startswith("Lampiran ")]
    assert len(lamp_in_body) == 0, f"Lampiran captions ditemukan di body check: {lamp_in_body[:3]}"

def test_check_body_content_results_in_doc_order(_body_checks_cache):
    checks = _body_checks_cache
    all_idxs = [
        o.get("para_idx") for c in checks for o in (c.occurrences or [])
        if o.get("para_idx") is not None
    ]
    assert all_idxs == sorted(all_idxs), f"para_idx tidak berurutan: {all_idxs[:10]}..."


# ── caption_alignment dinamis di _check_caption_format() ─────────────────────

def test_caption_format_emits_figure_alignment_field():
    meta = _make_caption_metadata(fig_align="CENTER", tbl_align="CENTER")
    _, checks = _check_caption_format(_DOCX, meta)
    fields = [c.field for c in checks]
    assert "caption_alignment_figure" in fields, f"Fields: {fields}"

def test_caption_format_emits_table_alignment_field():
    meta = _make_caption_metadata(fig_align="CENTER", tbl_align="CENTER")
    _, checks = _check_caption_format(_DOCX, meta)
    fields = [c.field for c in checks]
    assert "caption_alignment_table" in fields, f"Fields: {fields}"

def test_caption_format_figure_alignment_uses_metadata():
    meta = _make_caption_metadata(fig_align="CENTER")
    _, checks = _check_caption_format(_DOCX, meta)
    fig_align_checks = [c for c in checks if c.field == "caption_alignment_figure"]
    assert any(c.status == "passed" for c in fig_align_checks), (
        f"Tidak ada passed untuk caption_alignment_figure: {[(c.status, c.message) for c in fig_align_checks]}"
    )

def test_caption_format_figure_alignment_fails_on_wrong_value():
    meta = _make_caption_metadata(fig_align="LEFT")
    _, checks = _check_caption_format(_DOCX, meta)
    fig_align_checks = [c for c in checks if c.field == "caption_alignment_figure"]
    assert fig_align_checks, "caption_alignment_figure tidak ditemukan di checks"
    statuses = [c.status for c in fig_align_checks]
    assert any(s in ("warning", "failed") for s in statuses), (
        f"Diharapkan warning/failed jika expected=LEFT, dapat: {statuses}"
    )

def test_caption_format_uses_metadata_not_hardcoded():
    meta_center = _make_caption_metadata(fig_align="CENTER")
    meta_left   = _make_caption_metadata(fig_align="LEFT")
    _, checks_center = _check_caption_format(_DOCX, meta_center)
    _, checks_left   = _check_caption_format(_DOCX, meta_left)
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
    meta = _make_caption_metadata(lamp_fmt="Lampiran {n}. {title}")
    _, checks = _check_figures_tables(_DOCX, meta)
    fields = [c.field for c in checks]
    assert "lampiran_caption_format" in fields, f"Fields: {fields}"

def test_figures_tables_lampiran_format_skipped_when_none():
    meta = _make_caption_metadata(lamp_fmt=None, lamp_align=None)
    _, checks = _check_figures_tables(_DOCX, meta)
    fields = [c.field for c in checks]
    assert "lampiran_caption_format" not in fields, f"Muncul padahal None: {fields}"

def test_figures_tables_lampiran_alignment_field_emitted():
    meta = _make_caption_metadata(lamp_align="CENTER", lamp_fmt=None)
    _, checks = _check_figures_tables(_DOCX, meta)
    fields = [c.field for c in checks]
    assert "lampiran_caption_alignment" in fields, f"Fields: {fields}"

def test_figures_tables_lampiran_alignment_skipped_when_none():
    meta = _make_caption_metadata(lamp_align=None, lamp_fmt=None)
    _, checks = _check_figures_tables(_DOCX, meta)
    fields = [c.field for c in checks]
    assert "lampiran_caption_alignment" not in fields, f"Muncul padahal None: {fields}"


# ── FiguresTablesExtracted @model_validator ───────────────────────────────────

def test_figures_tables_extracted_normalizes_valid_alignment():
    """Nilai valid lowercase harus dinormalisasi ke uppercase."""
    ft = FiguresTablesExtracted(
        caption_alignment_figure="center",
        caption_alignment_table="left",
        caption_alignment_lampiran="RIGHT",
    )
    assert ft.caption_alignment_figure == "CENTER"
    assert ft.caption_alignment_table == "LEFT"
    assert ft.caption_alignment_lampiran == "RIGHT"


def test_figures_tables_extracted_invalid_alignment_becomes_none():
    """Nilai tidak valid (typo, tidak dikenal) harus di-set None."""
    ft = FiguresTablesExtracted(
        caption_alignment_figure="CENTRE",   # typo British English
        caption_alignment_table="MIDDLE",    # tidak valid
        caption_alignment_lampiran="JUSTIFY",  # valid — harus tetap
    )
    assert ft.caption_alignment_figure is None, "CENTRE harus menjadi None"
    assert ft.caption_alignment_table is None, "MIDDLE harus menjadi None"
    assert ft.caption_alignment_lampiran == "JUSTIFY"


def test_figures_tables_extracted_none_alignment_stays_none():
    """None harus tetap None — tidak diubah ke default CENTER."""
    ft = FiguresTablesExtracted(
        caption_alignment_figure=None,
        caption_alignment_table=None,
        caption_alignment_lampiran=None,
    )
    assert ft.caption_alignment_figure is None
    assert ft.caption_alignment_table is None
    assert ft.caption_alignment_lampiran is None


def test_valid_caption_alignments_not_in_model_fields():
    """_VALID_CAPTION_ALIGNMENTS (ClassVar) tidak boleh muncul di model_fields."""
    assert "_VALID_CAPTION_ALIGNMENTS" not in FiguresTablesExtracted.model_fields
