import re

from pydantic import BaseModel, model_validator


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
    font_size_heading_pt: int | None = None
    heading_bold: bool | None = True
    heading_all_caps: bool | None = None

    @model_validator(mode="before")
    @classmethod
    def normalize_heading_font_size(cls, data: object) -> object:
        if not isinstance(data, dict):
            return data
        normalized = dict(data)
        raw_size = normalized.get("font_size_heading_pt")
        if isinstance(raw_size, str):
            match = re.search(r"\d+", raw_size)
            normalized["font_size_heading_pt"] = int(match.group()) if match else None
        # Fallback: if heading size is null but body size is known, reuse body size
        if normalized.get("font_size_heading_pt") is None and normalized.get("font_size_body_pt") is not None:
            normalized["font_size_heading_pt"] = normalized["font_size_body_pt"]
        # Default heading style: assume bold when the extractor does not provide a value.
        if normalized.get("heading_bold") is None:
            normalized["heading_bold"] = True
        return normalized


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
    line_spacing: float | None = None
    line_spacing_rule: str | None = None
    paragraph_alignment: str | None = None
    first_line_indent_cm: float | None = None
    references_hanging_indent: bool | None = None


class SpacingInfo(SpacingExtracted):
    sources: list[Source] = []


# --- Document Structure ---

_VALID_SECTION_TYPES = frozenset({
    "daftar_isi", "daftar_gambar", "daftar_tabel", "daftar_lampiran",
    "daftar_pustaka", "bab", "lampiran",
})


def _normalize_section_type(raw: str) -> str:
    """Normalize LLM-generated section type to canonical snake_case.

    Handles Title Case ("Daftar Isi"), UPPERCASE ("DAFTAR ISI"),
    and mixed spacing/underscore variants before matching.
    """
    candidate = raw.strip().lower().replace(" ", "_")
    if candidate in _VALID_SECTION_TYPES:
        return candidate
    return raw  # pass through unknown values unchanged


class SectionItem(BaseModel):
    type: str
    required: bool | None = None
    number: int | None = None
    title: str | None = None

    @model_validator(mode="before")
    @classmethod
    def normalize_section_type(cls, data: object) -> object:
        if not isinstance(data, dict):
            return data
        raw_type = data.get("type")
        if not isinstance(raw_type, str):
            return data
        normalized = _normalize_section_type(raw_type)
        if normalized == raw_type:
            return data
        result = dict(data)
        result["type"] = normalized
        return result


class DocumentStructureExtracted(BaseModel):
    halaman_sampul: bool | None = None
    halaman_pengesahan: bool | None = None
    ringkasan: bool | None = None
    sections: list[SectionItem] = []
    max_halaman_inti: int | None = None
    format_nama_file: str | None = None


class DocumentStructureInfo(DocumentStructureExtracted):
    sources: list[Source] = []


# --- Numbering ---

class PageNumberConfig(BaseModel):
    format: str | None = None
    location: str | None = None
    alignment: str | None = None
    start_at_section: str | None = None


class NumberingExtracted(BaseModel):
    preliminary: PageNumberConfig | None = None
    content: PageNumberConfig | None = None
    chapter_format: str | None = None
    sub_chapter_format: str | None = None
    figure_format: str | None = None
    table_format: str | None = None


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
    definisi_halaman_inti: str | None = None
    lampiran_excluded: bool | None = None
    judul_maks_kata: int | None = None

    @model_validator(mode="before")
    @classmethod
    def normalize_legacy_keys(cls, data: object) -> object:
        if not isinstance(data, dict):
            return data
        normalized = dict(data)
        legacy_note = normalized.pop("catatan", None)
        if legacy_note and "definisi_halaman_inti" not in normalized:
            normalized["definisi_halaman_inti"] = legacy_note
        return normalized


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
