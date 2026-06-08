"""Adapter: konversi DocumentMetadata Project 1 AI → requirements dict yang dikenali validocx.

Posisi pipeline: jembatan antara metadata Pydantic dan engine validocx (validate()).
"""
from __future__ import annotations

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
    "SINGLE": 1.0,
    "ONE_POINT_FIVE": 1.15,
    "DOUBLE": 2.0,
}

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
    return s.line_spacing if s.line_spacing is not None else 1.15


def _build_heading_font_attrs(metadata: DocumentMetadata, level: int) -> list[Any]:
    """Font attributes untuk Heading 1–5 (size + font family, tanpa bold).

    Semua level heading menggunakan font_size_heading_pt.
    Bold tidak divalidasi karena konvensi dokumen bervariasi.
    """
    t = metadata.typography
    attrs: list[Any] = []
    if t is None:
        return attrs
    size = t.font_size_heading_pt
    if size is not None:
        attrs.append(int(size))
    if t.font_family:
        attrs.append(t.font_family)
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
    # Tidak ada bold — normal paragraf tidak pernah diwajibkan bold.
    return attrs


def metadata_to_requirements(metadata: DocumentMetadata) -> dict:
    """Bangun dict requirements (styles + sections) sesuai schema validocx.

    Semua heading H1–H5 dicek font, alignment, dan line_spacing. Bold tidak divalidasi.
    ─ H1      : alignment CENTER (dari admin), font size heading.
    ─ H2–H5   : alignment JUSTIFY (body), font size heading.
    ─ Normal  : alignment JUSTIFY, font size body, line_spacing 1.15.
    """
    s = metadata.spacing
    l = metadata.page_layout

    body_alignment = _resolve_alignment(
        s.paragraph_alignment if s else None, default="JUSTIFY"
    )
    heading_alignment = _resolve_alignment(
        s.heading_alignment if s else None, default="CENTER"
    )
    line_spacing = _resolve_line_spacing(metadata)

    # ── Template Normal ───────────────────────────────────────────────────────
    # Dipakai oleh: Normal, Heading 3–5, dan semua alias style paragraf.
    normal_font_attrs = _build_normal_font_attrs(metadata)
    normal_style: dict = {
        # Exclude paragraf yang tidak perlu divalidasi via fallback Normal:
        # (1) angka halaman saja
        # (2) caption gambar/tabel — divalidasi terpisah via _check_caption_format
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

    # ── Template Heading H1–H5 ────────────────────────────────────────────────
    # H1 : alignment CENTER (dari admin), size heading, line spacing dicek.
    # H2 : alignment JUSTIFY (body), size heading, line spacing dicek.
    # H3–H5: alignment JUSTIFY (body), size body, line spacing dicek.
    # Bold tidak divalidasi di semua level.
    def _make_heading_style(level: int) -> dict:
        alignment = heading_alignment if level == 1 else body_alignment
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

    # H1–H5 dan alias Judul N
    for level in (1, 2, 3, 4, 5):
        style_def = _make_heading_style(level)
        styles[f"Heading {level}"] = style_def
        styles[f"Judul{level}"]    = style_def
        styles[f"Judul {level}"]   = style_def

    # ── Style Lampiran ────────────────────────────────────────────────────────
    # Divalidasi sama seperti body (TNR, 12pt, 1.15, JUSTIFY).
    # Alignment bisa diwarisi dari Normal — wrapper.py akan resolve via Normal fallback
    # sehingga tidak memunculkan false-positive "inherited" warning.
    lampiran_style = {k: v for k, v in normal_style.items() if k != "exclude"}
    styles["Lampiran"] = lampiran_style

    # ── Style TOC & TOF ───────────────────────────────────────────────────────
    # "table of figures" → entri Daftar Gambar, Daftar Tabel, Daftar Lampiran
    # "TOC 1"–"TOC 5"    → entri Daftar Isi per level
    #
    # Aturan: identik dengan Normal (JUSTIFY, 12pt, TNR, 1.15) TANPA exclude.
    # Exclude Normal sengaja tidak dipakai agar entri "Gambar N." / "Tabel N."
    # di halaman Daftar Gambar/Tabel tidak ter-skip (exclude itu untuk caption
    # inline di BAB yang sudah dicek terpisah via _check_caption_format).
    toc_tof_style = {k: v for k, v in normal_style.items() if k != "exclude"}
    for _toc_tof_name in (
        "table of figures",
        "TOC 1", "TOC 2", "TOC 3", "TOC 4", "TOC 5",
    ):
        styles[_toc_tof_name] = toc_tof_style

    # Caption tidak lagi divalidasi via style name — terlalu dinamis (Gambar, Gambar (Lampiran), dll).
    # Validasi caption dilakukan di runner via text-pattern detection (_check_caption_format).

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
    seen: set[str] = set()
    current = style
    depth = 0
    while current is not None and depth < max_depth:
        name = current.name
        if name in seen:
            break
        seen.add(name)

        if name in _HEADING_NAME_TO_LEVEL:
            return _HEADING_NAME_TO_LEVEL[name]

        outline_level = _outline_level_from_style_xml(current)
        if outline_level is not None:
            return min(outline_level, 5)

        current = getattr(current, "base_style", None)
        depth += 1
    return None


def enrich_requirements_with_docx_styles(requirements: dict, docx_path: str | Path) -> dict:
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
