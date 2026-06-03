"""Adapter: konversi DocumentMetadata Project 1 AI → requirements dict yang dikenali validocx.

Posisi pipeline: jembatan antara metadata Pydantic dan engine validocx (validate()).
"""
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


def _build_font_attributes(metadata: DocumentMetadata, is_heading: bool, heading_level: int = 1) -> list[Any]:
    """Hasilkan list attribute font untuk validocx (size + family + flags optional).

    all_caps hanya berlaku untuk Heading 1 (BAB) — Heading 2+ menggunakan sentence/title case.
    """
    t = metadata.typography
    attrs: list[Any] = []
    if t is None:
        return attrs

    size = t.font_size_heading_pt if is_heading else t.font_size_body_pt
    if size is not None:
        attrs.append(int(size))
    if t.font_family:
        attrs.append(t.font_family)
    if is_heading and t.heading_bold:
        attrs.append("bold")
    # all_caps tidak dicek — uppercase via Capslock dan via font property all_caps
    # menghasilkan visual yang sama, tidak bisa dibedakan lewat font property check.
    return attrs


def metadata_to_requirements(metadata: DocumentMetadata) -> dict:
    """Bangun dict requirements (styles + sections) sesuai schema validocx."""
    s = metadata.spacing
    l = metadata.page_layout

    body_alignment = _resolve_alignment(
        s.paragraph_alignment if s else None, default="JUSTIFY"
    )
    heading_alignment = _resolve_alignment(
        s.heading_alignment if s else None, default="CENTER"
    )
    line_spacing = _resolve_line_spacing(metadata)

    styles: dict[str, dict] = {
        "Normal": {
            "exclude": {"text_regex": r"^\s*(\d{1,3})?\s*$"},
            "font": {
                "unit": "pt",
                "attributes": _build_font_attributes(metadata, is_heading=False),
            },
            "paragraph": {
                "unit": "cm",
                "attributes": {
                    "alignment": body_alignment,
                    "line_spacing": line_spacing,
                },
            },
        }
    }

    for level in (1, 2, 3):
        styles[f"Heading {level}"] = {
            "font": {
                "unit": "pt",
                "attributes": _build_font_attributes(metadata, is_heading=True, heading_level=level),
            },
            "paragraph": {
                "unit": "cm",
                "attributes": {
                    "alignment": heading_alignment if level == 1 else body_alignment,
                },
            },
        }

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
