"""Test bahwa style TOC dan table of figures terdaftar di requirements validasi."""
from unittest.mock import MagicMock

from model_ai.validation.validocx_adapter import metadata_to_requirements


def _make_metadata(alignment="JUSTIFY", font="Times New Roman", size=12, spacing=1.15):
    """Buat mock DocumentMetadata minimal."""
    meta = MagicMock()
    meta.spacing.paragraph_alignment = alignment
    meta.spacing.heading_alignment = "CENTER"
    meta.spacing.line_spacing = spacing
    meta.spacing.line_spacing_rule = None
    meta.typography.font_family = font
    meta.typography.font_size_body_pt = size
    meta.typography.font_size_heading_pt = size
    meta.page_layout = None
    return meta


_TOC_TOF_STYLES = [
    "table of figures",
    "TOC 1",
    "TOC 2",
    "TOC 3",
    "TOC 4",
    "TOC 5",
]

_ALIGNMENT_JUSTIFY = 3  # WD_ALIGN_PARAGRAPH.JUSTIFY


def test_toc_tof_styles_registered_in_requirements():
    """Setiap style TOC/TOF harus ada di requirements dict."""
    req = metadata_to_requirements(_make_metadata())
    styles = req["styles"]
    for name in _TOC_TOF_STYLES:
        assert name in styles, f"Style '{name}' tidak ditemukan di requirements"


def test_toc_tof_styles_have_no_exclude_pattern():
    """Style TOC/TOF tidak boleh punya exclude pattern (berbeda dari Normal)."""
    req = metadata_to_requirements(_make_metadata())
    styles = req["styles"]
    for name in _TOC_TOF_STYLES:
        assert "exclude" not in styles[name], (
            f"Style '{name}' punya exclude pattern — entri TOC/TOF akan ter-skip"
        )


def test_toc_tof_alignment_is_justify():
    """Alignment style TOC/TOF harus JUSTIFY (sama seperti Normal)."""
    req = metadata_to_requirements(_make_metadata())
    styles = req["styles"]
    for name in _TOC_TOF_STYLES:
        actual = styles[name]["paragraph"]["attributes"]["alignment"]
        assert actual == _ALIGNMENT_JUSTIFY, (
            f"Style '{name}' alignment={actual}, seharusnya {_ALIGNMENT_JUSTIFY} (JUSTIFY)"
        )


def test_normal_exclude_pattern_still_present():
    """Normal harus tetap punya exclude pattern (tidak boleh dihapus)."""
    req = metadata_to_requirements(_make_metadata())
    normal = req["styles"]["Normal"]
    assert "exclude" in normal, "Normal kehilangan exclude pattern"
    assert "Gambar" in normal["exclude"]["text_regex"], (
        "Exclude pattern Normal tidak lagi menyaring caption Gambar"
    )
