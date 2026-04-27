from typing import Literal

from pydantic import BaseModel

from model_ai.extractor.models import DocumentMetadata

PageNumberPosition = Literal[
    "header_left",
    "header_center",
    "header_right",
    "footer_left",
    "footer_center",
    "footer_right",
]
ParagraphAlignmentOption = Literal["LEFT", "CENTER", "RIGHT", "JUSTIFY"]


class DocxStyleConfig(BaseModel):
    heading_bold: bool = False
    heading_all_caps: bool = False
    paragraph_alignment: ParagraphAlignmentOption = "JUSTIFY"
    page_number_prelim_pos: PageNumberPosition = "footer_right"
    page_number_content_pos: PageNumberPosition = "header_right"


def translate_docx_style_config(metadata: DocumentMetadata) -> DocxStyleConfig:
    typ = metadata.typography
    spacing = metadata.spacing
    num = metadata.numbering

    return DocxStyleConfig(
        heading_bold=bool(typ.heading_bold),
        heading_all_caps=bool(typ.heading_all_caps),
        paragraph_alignment=_coerce_alignment(spacing.paragraph_alignment),
        page_number_prelim_pos=_build_position(
            num.preliminary.location if num.preliminary else None,
            num.preliminary.alignment if num.preliminary else None,
            default="footer_right",
        ),
        page_number_content_pos=_build_position(
            num.content.location if num.content else None,
            num.content.alignment if num.content else None,
            default="header_right",
        ),
    )


def _coerce_alignment(raw: str | None) -> ParagraphAlignmentOption:
    val = (raw or "JUSTIFY").strip().upper()
    if val in ("LEFT", "CENTER", "RIGHT", "JUSTIFY"):
        return val  # type: ignore[return-value]
    return "JUSTIFY"


def _build_position(
    location: str | None,
    alignment: str | None,
    default: PageNumberPosition,
) -> PageNumberPosition:
    loc = (location or "").strip().lower()
    aln = (alignment or "RIGHT").strip().lower()
    candidate = f"{loc}_{aln}"
    valid: set[str] = {
        "header_left", "header_center", "header_right",
        "footer_left", "footer_center", "footer_right",
    }
    return candidate if candidate in valid else default  # type: ignore[return-value]
