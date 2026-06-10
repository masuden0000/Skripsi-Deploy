# ai/model/tests/test_page_count_check.py
"""Test untuk _count_pages_structural, _find_section_para_idx, dan _check_page_count."""
import pytest
from pathlib import Path
from unittest.mock import MagicMock, patch
from lxml import etree

from model_ai.validation.validocx_runner import (
    _count_pages_structural,
    _find_section_para_idx,
    _check_page_count,
)

_DOCX = next(
    (p for p in (Path(__file__).parent).iterdir()
     if p.suffix == ".docx" and not p.name.startswith("~")),
    Path(__file__).parent / "file_target.docx",
)

# Namespace OOXML
_W = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"


# ── XML helper ────────────────────────────────────────────────────────────────

def _wns(tag: str) -> str:
    return f"{{{_W}}}{tag}"


def _make_p(
    *,
    has_lrpb: bool = False,
    has_page_br: bool = False,
    has_sect_pr: bool = False,
) -> etree._Element:
    """Buat elemen <w:p> minimal sesuai flag yang diberikan."""
    p = etree.Element(_wns("p"))

    if has_lrpb:
        r = etree.SubElement(p, _wns("r"))
        etree.SubElement(r, _wns("lastRenderedPageBreak"))

    if has_page_br:
        r = etree.SubElement(p, _wns("r"))
        br = etree.SubElement(r, _wns("br"))
        br.set(_wns("type"), "page")

    if has_sect_pr:
        pPr = etree.SubElement(p, _wns("pPr"))
        etree.SubElement(pPr, _wns("sectPr"))

    return p


def _make_mock_para(
    *,
    has_lrpb: bool = False,
    has_page_br: bool = False,
    has_sect_pr: bool = False,
    style_name: str = "Normal",
    text: str = "",
) -> MagicMock:
    para = MagicMock()
    para._p = _make_p(has_lrpb=has_lrpb, has_page_br=has_page_br, has_sect_pr=has_sect_pr)
    style = MagicMock()
    style.name = style_name
    style.base_style = None
    para.style = style
    para.text = text
    return para


def _make_doc(paras: list[MagicMock]) -> MagicMock:
    doc = MagicMock()
    doc.paragraphs = paras
    return doc


def _make_pc_metadata(
    maks: int | None = 10,
    mulai: str = "bab",
    selesai: str = "daftar_pustaka",
) -> MagicMock:
    meta = MagicMock()
    meta.page_count_limits.proposal_halaman_inti_maks = maks
    meta.page_count_limits.halaman_inti_mulai = mulai
    meta.page_count_limits.halaman_inti_selesai = selesai
    return meta


# ── _count_pages_structural ───────────────────────────────────────────────────

class TestCountPagesStructural:
    def test_empty_doc_returns_empty(self):
        doc = _make_doc([])
        assert _count_pages_structural(doc) == {}

    def test_single_para_no_break_is_page_1(self):
        doc = _make_doc([_make_mock_para()])
        result = _count_pages_structural(doc)
        assert result == {0: 1}

    def test_lrpb_increments_page(self):
        paras = [
            _make_mock_para(),                     # page 1
            _make_mock_para(has_lrpb=True),        # page 2
            _make_mock_para(),                     # page 2
        ]
        doc = _make_doc(paras)
        result = _count_pages_structural(doc)
        assert result[0] == 1
        assert result[1] == 2
        assert result[2] == 2

    def test_explicit_page_break_increments_page(self):
        paras = [
            _make_mock_para(),                      # page 1
            _make_mock_para(has_page_br=True),      # page 2
            _make_mock_para(),                      # page 2
        ]
        doc = _make_doc(paras)
        result = _count_pages_structural(doc)
        assert result[0] == 1
        assert result[1] == 2
        assert result[2] == 2

    def test_sect_pr_increments_next_para(self):
        paras = [
            _make_mock_para(has_sect_pr=True),   # page 1, but increments for next
            _make_mock_para(),                   # page 2
        ]
        doc = _make_doc(paras)
        result = _count_pages_structural(doc)
        assert result[0] == 1
        assert result[1] == 2

    def test_multiple_breaks_accumulate(self):
        paras = [
            _make_mock_para(),                    # page 1
            _make_mock_para(has_lrpb=True),       # page 2
            _make_mock_para(has_lrpb=True),       # page 3
            _make_mock_para(),                    # page 3
        ]
        doc = _make_doc(paras)
        result = _count_pages_structural(doc)
        assert result[0] == 1
        assert result[1] == 2
        assert result[2] == 3
        assert result[3] == 3

    def test_fallback_when_no_lrpb(self):
        # No lrpb → should fall back to explicit breaks
        paras = [
            _make_mock_para(),                      # page 1
            _make_mock_para(has_page_br=True),      # page 2 (via fallback)
            _make_mock_para(),                      # page 2
        ]
        doc = _make_doc(paras)
        result = _count_pages_structural(doc)
        assert result[0] == 1
        assert result[1] == 2
        assert result[2] == 2

    def test_first_para_never_increments(self):
        # Even with lrpb in first para, page should stay 1
        paras = [_make_mock_para(has_lrpb=True)]
        doc = _make_doc(paras)
        result = _count_pages_structural(doc)
        assert result[0] == 1


# ── _find_section_para_idx ────────────────────────────────────────────────────

class TestFindSectionParaIdx:
    def _heading_para(self, text: str) -> MagicMock:
        para = MagicMock()
        style = MagicMock()
        style.name = "Heading 1"
        style._element = None  # Pastikan _outline_level_from_style_xml tidak membaca MagicMock
        base = MagicMock()
        base.name = "Normal"
        base._element = None
        base.base_style = None
        style.base_style = base
        para.style = style
        para.text = text
        para._p = _make_p()
        return para

    def _normal_para(self, text: str) -> MagicMock:
        para = MagicMock()
        style = MagicMock()
        style.name = "Normal"
        style._element = None  # Mencegah MagicMock auto-create yang menyebabkan false positive
        style.base_style = None
        para.style = style
        para.text = text
        para._p = _make_p()
        return para

    def test_finds_bab_heading(self):
        paras = [
            self._normal_para(""),
            self._heading_para("BAB 1 PENDAHULUAN"),
            self._heading_para("BAB 2 TINJAUAN"),
        ]
        idx, text = _find_section_para_idx(paras, "bab")
        assert idx == 1
        assert "BAB 1" in text.upper()

    def test_bab_not_matched_in_normal_style(self):
        # TOC entry: text starts with BAB but not a heading style
        paras = [
            self._normal_para("BAB 1 PENDAHULUAN..........1"),
        ]
        idx, text = _find_section_para_idx(paras, "bab")
        assert idx is None

    def test_finds_daftar_pustaka(self):
        paras = [
            self._heading_para("BAB 1 PENDAHULUAN"),
            self._heading_para("DAFTAR PUSTAKA"),
        ]
        idx, text = _find_section_para_idx(paras, "daftar_pustaka")
        assert idx == 1

    def test_search_from_skips_earlier_paras(self):
        paras = [
            self._heading_para("DAFTAR PUSTAKA"),  # idx 0
            self._heading_para("BAB 1 PENDAHULUAN"),
            self._heading_para("DAFTAR PUSTAKA"),  # idx 2
        ]
        # Search from idx 1 → should find idx 2, not idx 0
        idx, text = _find_section_para_idx(paras, "daftar_pustaka", search_from=1)
        assert idx == 2

    def test_returns_none_when_not_found(self):
        paras = [self._normal_para("hello")]
        idx, text = _find_section_para_idx(paras, "bab")
        assert idx is None
        assert text == ""


# ── _check_page_count ─────────────────────────────────────────────────────────

class TestCheckPageCount:
    def test_skipped_when_pc_is_none(self):
        meta = MagicMock()
        meta.page_count_limits = None
        _, checks = _check_page_count(Path("dummy.docx"), meta)
        assert checks[0].status == "skipped"

    def test_skipped_when_maks_is_none(self):
        meta = _make_pc_metadata(maks=None)
        _, checks = _check_page_count(Path("dummy.docx"), meta)
        assert checks[0].status == "skipped"

    @pytest.mark.skipif(not _DOCX.exists(), reason="Dokumen uji tidak tersedia")
    def test_real_docx_not_skipped_with_mechanism(self):
        """Dengan dokumen nyata, hasil tidak lagi 'skipped' karena mekanisme sudah diimplementasikan."""
        meta = _make_pc_metadata(maks=10)
        _, checks = _check_page_count(_DOCX, meta)
        # Tidak boleh skipped karena alasan "mechanism removed"
        for c in checks:
            assert "mechanism removed" not in (c.skip_reason or "")

    @pytest.mark.skipif(not _DOCX.exists(), reason="Dokumen uji tidak tersedia")
    def test_real_docx_fields_populated_on_result(self):
        """Jika passed/failed, expected dan actual harus terisi."""
        meta = _make_pc_metadata(maks=10)
        _, checks = _check_page_count(_DOCX, meta)
        for c in checks:
            if c.status in ("passed", "failed"):
                assert c.expected is not None
                assert c.actual is not None
                assert "halaman" in (c.actual or "")
                assert "halaman" in (c.expected or "")

    @pytest.mark.skipif(not _DOCX.exists(), reason="Dokumen uji tidak tersedia")
    def test_real_docx_occurrences_lists_all_elements(self):
        """Occurrences harus berisi SEMUA heading antara START dan END (bukan hanya 2 marker)."""
        meta = _make_pc_metadata(maks=10)
        _, checks = _check_page_count(_DOCX, meta)
        for c in checks:
            if c.status in ("passed", "failed"):
                assert c.occurrences is not None
                # Harus ada lebih dari 2 entry (semua heading, bukan hanya START+END)
                assert len(c.occurrences) > 2
                # Entry pertama harus heading BAB pertama
                assert "BAB" in (c.occurrences[0].get("text", "")).upper()
                # Setiap entry harus punya page number
                for occ in c.occurrences:
                    assert occ.get("page") is not None
                    assert isinstance(occ["page"], int)
