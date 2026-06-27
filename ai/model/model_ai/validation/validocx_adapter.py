"""Adapter: konversi DocumentMetadata Project 1 AI → requirements dict yang dikenali validocx.

Posisi pipeline: jembatan antara metadata Pydantic dan engine validocx (validate()).
Keyword: automated document validation
"""
from __future__ import annotations

import copy
import threading
from pathlib import Path
from typing import Any

from model_ai.extractor.models import DocumentMetadata


_ALIGNMENT_MAP: dict[str, int] = {
    "LEFT": 0,
    "CENTER": 1,
    "RIGHT": 2,
    "JUSTIFY": 3,
}

_ORIENTATION_MAP: dict[str, int] = {
    "PORTRAIT": 0,
    "portrait": 0,
    "LANDSCAPE": 1,
    "landscape": 1,
}

_GRUP_A_LINE_SPACING: dict[str, float] = {
    "SINGLE":         1.0,
    "ONE_POINT_FIVE": 1.5,
    "DOUBLE":         2.0,
}

_PT_TO_CM = 2.54 / 72

_GRUP_C_LINE_SPACING = frozenset({"AT_LEAST", "EXACTLY"})

_PAPER_SIZE_DIMS: dict[str, tuple[float, float]] = {
    "A4":     (21.0, 29.7),
    "F4":     (21.0, 33.0),
    "A5":     (14.85, 21.0),
    "A3":     (29.7, 42.0),
    "LETTER": (21.59, 27.94),
}


def _resolve_alignment(name: str | None, default: str = "JUSTIFY") -> int:
    if not name:
        return _ALIGNMENT_MAP[default]
    return _ALIGNMENT_MAP.get(name.upper().strip(), _ALIGNMENT_MAP[default])


def _resolve_line_spacing(metadata: DocumentMetadata) -> float:
    s = metadata.spacing
    if s is None:
        return 1.15
    rule = (s.line_spacing_rule or "").upper()
    if rule in _GRUP_A_LINE_SPACING:
        return _GRUP_A_LINE_SPACING[rule]
    if rule in _GRUP_C_LINE_SPACING and s.line_spacing is not None:
        return s.line_spacing * _PT_TO_CM
    return s.line_spacing if s.line_spacing is not None else 1.15


def _build_heading_font_attrs(metadata: DocumentMetadata, level: int) -> list[Any]:
    """Font attributes untuk Heading 1–5 (size + font family + bold sesuai metadata)."""
    t = metadata.typography
    attrs: list[Any] = []
    if t is None:
        return attrs
    size = t.font_size_heading_pt
    if size is not None:
        attrs.append(int(size))
    if t.font_family:
        attrs.append(t.font_family)
    bold = getattr(t, f"heading_{level}_bold", True)
    if bold is None:
        bold = True
    if bold:
        attrs.append("bold")
    return attrs


def _build_normal_font_attrs(metadata: DocumentMetadata) -> list[Any]:
    """Font attributes untuk style Normal dan H3–H5 (TNR 12pt tanpa bold)."""
    t = metadata.typography
    attrs: list[Any] = []
    if t is None:
        return attrs
    if t.font_size_body_pt is not None:
        attrs.append(int(t.font_size_body_pt))
    if t.font_family:
        attrs.append(t.font_family)
    return attrs


def _resolve_heading_alignment(spacing, level: int) -> Any:
    """Resolusi alignment untuk heading level tertentu.

    Prioritas: heading_{level}_alignment → heading_alignment (H1) / paragraph_alignment (H2–H5).
    """
    if spacing is None:
        return _resolve_alignment(None, default="CENTER" if level == 1 else "JUSTIFY")
    per_level = getattr(spacing, f"heading_{level}_alignment", None)
    if per_level:
        return _resolve_alignment(per_level, default="CENTER" if level == 1 else "JUSTIFY")
    if level == 1:
        return _resolve_alignment(getattr(spacing, "heading_alignment", None), default="CENTER")
    return _resolve_alignment(getattr(spacing, "paragraph_alignment", None), default="JUSTIFY")


def metadata_to_requirements(metadata: DocumentMetadata) -> dict:
    """Bangun dict requirements (styles + sections) sesuai schema validocx.

    Semua heading H1–H5 dicek font (termasuk bold), alignment, dan line_spacing.
    ─ H1      : alignment CENTER by default (bisa dioverride per metadata).
    ─ H2–H5   : alignment JUSTIFY by default (bisa dioverride per metadata).
    ─ Normal  : alignment JUSTIFY, font size body, line_spacing 1.15.
    """
    s = metadata.spacing
    l = metadata.page_layout

    body_alignment = _resolve_alignment(
        s.paragraph_alignment if s else None, default="JUSTIFY"
    )
    line_spacing = _resolve_line_spacing(metadata)

    normal_font_attrs = _build_normal_font_attrs(metadata)
    normal_style: dict = {
        "exclude": {"text_regex": r"(^\s*(\d{1,3})?\s*$|^(Gambar|Tabel)\s+\d+)"},
        "font": {
            "unit": "pt",
            "attributes": normal_font_attrs,
        },
        "paragraph": {
            "unit": "cm",
            "attributes": {
                "alignment": body_alignment,
                "line_spacing": line_spacing,
            },
        },
    }

    def _make_heading_style(level: int) -> dict:
        alignment = _resolve_heading_alignment(s, level)
        return {
            "font": {
                "unit": "pt",
                "attributes": _build_heading_font_attrs(metadata, level),
            },
            "paragraph": {
                "unit": "cm",
                "attributes": {
                    "alignment": alignment,
                    "line_spacing": line_spacing,
                },
            },
        }

    styles: dict[str, dict] = {
        "Normal": normal_style,
    }

    for level in (1, 2, 3, 4, 5):
        style_def = _make_heading_style(level)
        styles[f"Heading {level}"] = style_def
        styles[f"Judul{level}"]    = style_def
        styles[f"Judul {level}"]   = style_def

    toc_tof_style = copy.deepcopy({k: v for k, v in normal_style.items() if k != "exclude"})
    for name in (
        "table of figures",
        "TOC 1", "TOC 2", "TOC 3", "TOC 4", "TOC 5",
    ):
        styles[name] = toc_tof_style


    section_attrs: dict[str, Any] = {}
    if l is not None:
        if l.margin_left_cm is not None:
            section_attrs["left_margin"] = float(l.margin_left_cm)
        if l.margin_right_cm is not None:
            section_attrs["right_margin"] = float(l.margin_right_cm)
        if l.margin_top_cm is not None:
            section_attrs["top_margin"] = float(l.margin_top_cm)
        if l.margin_bottom_cm is not None:
            section_attrs["bottom_margin"] = float(l.margin_bottom_cm)
        if l.paper_size and l.paper_size.upper() in _PAPER_SIZE_DIMS:
            w, h = _PAPER_SIZE_DIMS[l.paper_size.upper()]
            section_attrs["page_width"] = w
            section_attrs["page_height"] = h
        if l.orientation:
            section_attrs["orientation"] = _ORIENTATION_MAP.get(l.orientation, 0)

    sections = [{"unit": "cm", "attributes": section_attrs}] if section_attrs else []

    requirements: dict = {"styles": styles}
    if sections:
        requirements["sections"] = sections
    else:
        requirements["sections"] = [{"unit": "cm", "attributes": {}}]

    return requirements


_HEADING_NAME_TO_LEVEL: dict[str, int] = {
    "Heading 1": 1, "Heading 2": 2, "Heading 3": 3, "Heading 4": 4, "Heading 5": 5,
    "Judul 1": 1, "Judul 2": 2, "Judul 3": 3, "Judul 4": 4, "Judul 5": 5,
    "Judul1": 1,  "Judul2": 2,  "Judul3": 3,  "Judul4": 4,  "Judul5": 5,
}

_style_level_local: threading.local = threading.local()


def clear_style_level_cache() -> None:
    """Reset cache level heading — dipanggil sekali di awal setiap run validasi."""
    _style_level_local.cache = {}


def _outline_level_from_style_xml(style) -> int | None:
    """Baca <w:outlineLvl w:val="N"/> langsung dari definisi style di styles.xml.

    Word menyimpan outline level (0-indexed) untuk style yang dipakai sebagai heading.
    val=0 → Heading 1, val=1 → Heading 2, dst. Style biasa (body) tidak punya elemen ini.
    """
    try:
        from docx.oxml.ns import qn
        el = getattr(style, "_element", None)
        if el is None:
            return None
        pPr = el.find(qn("w:pPr"))
        if pPr is None:
            return None
        outline = pPr.find(qn("w:outlineLvl"))
        if outline is None:
            return None
        val = outline.get(qn("w:val"))
        if val is None:
            return None
        lvl = int(val)
        if 0 <= lvl <= 8:
            return lvl + 1
    except (ValueError, AttributeError):
        return None
    return None


def _heading_level_from_style(style, max_depth: int = 10) -> int | None:
    """Deteksi level heading (1–5) dari sebuah style.

    Strategi berlapis:
      Layer A — Nama eksplisit ("Heading N", "JudulN")
      Layer B — Inheritance chain (basedOn → ancestor adalah heading)
      Layer C — Outline level dari styles.xml (<w:outlineLvl>)

    Return 1–5 jika ditemukan, None jika style biasa.
    """
    style_name = style.name
    cache: dict = getattr(_style_level_local, "cache", None)
    if cache is None:
        cache = {}
        _style_level_local.cache = cache
    if style_name in cache:
        return cache[style_name]

    seen: set[str] = set()
    current = style
    depth = 0
    result: int | None = None
    while current is not None and depth < max_depth:
        name = current.name
        if name in seen:
            break
        seen.add(name)

        if name in _HEADING_NAME_TO_LEVEL:
            result = _HEADING_NAME_TO_LEVEL[name]
            break

        outline_level = _outline_level_from_style_xml(current)
        if outline_level is not None:
            result = min(outline_level, 5)
            break

        current = getattr(current, "base_style", None)
        depth += 1

    cache[style_name] = result
    return result


def enrich_requirements_with_docx_styles(requirements: dict, docx_path: str | Path, doc=None) -> dict:
    """Tambahkan custom styles ke requirements berdasarkan deteksi heading H1–H5.

    Dokumen sering memakai style buatan sendiri (misal "Sub Judul Bab") yang:
      - mewarisi Heading N (inheritance), atau
      - punya outline level (<w:outlineLvl>) di definisinya, atau
      - bernama Judul1/Judul 2/dll.

    Fungsi ini scan semua style di DOCX, mendeteksi levelnya, lalu mendaftarkannya
    ke requirements memakai template yang sama dengan Heading N standar:
      H1 → template heading (alignment dari admin, default CENTER)
      H2 → template body (JUSTIFY, TNR 12, line spacing 1.15)
      H3–H5 → template body (sama seperti H2)
    """
    from docx import Document

    base_styles: dict = requirements.get("styles", {})

    level_to_req: dict[int, dict] = {}
    for level in (1, 2, 3, 4, 5):
        req = base_styles.get(f"Heading {level}")
        if req is not None:
            level_to_req[level] = req

    if not level_to_req:
        return requirements

    if doc is None:
        try:
            doc = Document(str(docx_path))
        except Exception:
            return requirements

    extra: dict[str, dict] = {}
    for style in doc.styles:
        name = style.name
        if name in base_styles or name in extra:
            continue
        level = _heading_level_from_style(style)
        if level is None:
            continue
        req = level_to_req.get(level)
        if req is not None:
            extra[name] = req

    if not extra:
        return requirements

    return {**requirements, "styles": {**base_styles, **extra}}
