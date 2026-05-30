"""Definisi schema Pydantic untuk hasil ekstraksi dokumen dan validasi turunannya. Posisi pipeline: dipakai oleh doc_extractor, metadata_loader, dan rule_validator."""
import re

from pydantic import BaseModel, model_validator


class Source(BaseModel):
    chunk_index: int
    page_start: int
    page_end: int
    header: str
    snippet: str


class TypographyExtracted(BaseModel):
    font_family: str | None = None
    font_size_body_pt: int | None = None
    font_size_heading_pt: int | None = None
    heading_bold: bool | None = True
    heading_all_caps: bool | None = True

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
        if normalized.get("font_size_heading_pt") is None and normalized.get("font_size_body_pt") is not None:
            normalized["font_size_heading_pt"] = normalized["font_size_body_pt"]
        if normalized.get("heading_bold") is None:
            normalized["heading_bold"] = True
        if normalized.get("heading_all_caps") is None:
            normalized["heading_all_caps"] = True
        return normalized


class TypographyInfo(TypographyExtracted):
    sources: list[Source] = []


class PageLayoutExtracted(BaseModel):
    margin_top_cm: float | None = None
    margin_bottom_cm: float | None = None
    margin_left_cm: float | None = None
    margin_right_cm: float | None = None
    paper_size: str | None = None
    orientation: str | None = None


class PageLayoutInfo(PageLayoutExtracted):
    sources: list[Source] = []


class SpacingExtracted(BaseModel):
    line_spacing: float | None = None
    line_spacing_rule: str | None = None
    paragraph_alignment: str | None = None
    first_line_indent_cm: float | None = None

    _RULE_ALIASES: dict[str, str] = {
        "EXACT":          "EXACTLY",
        "AT LEAST":       "AT_LEAST",
        "ONE POINT FIVE": "ONE_POINT_FIVE",
        "1.5":            "ONE_POINT_FIVE",
        "1.5 BARIS":      "ONE_POINT_FIVE",
        "1,5 BARIS":      "ONE_POINT_FIVE",
        "TUNGGAL":        "SINGLE",
        "GANDA":          "DOUBLE",
        "BEBERAPA":       "MULTIPLE",
        "SEDIKITNYA":     "AT_LEAST",
        "TEPAT":          "EXACTLY",
    }
    _VALID_RULES: frozenset[str] = frozenset(
        {"SINGLE", "ONE_POINT_FIVE", "DOUBLE", "MULTIPLE", "AT_LEAST", "EXACTLY"}
    )

    @model_validator(mode="after")
    def _normalize_rule(self) -> "SpacingExtracted":
        if self.line_spacing_rule is None:
            return self
        raw = self.line_spacing_rule.strip().upper()
        normalized = self._RULE_ALIASES.get(raw, raw)
        self.line_spacing_rule = normalized if normalized in self._VALID_RULES else None

        if self.line_spacing_rule in {"SINGLE", "ONE_POINT_FIVE", "DOUBLE"}:
            self.line_spacing = None
        return self


class SpacingInfo(SpacingExtracted):
    sources: list[Source] = []


_VALID_SECTION_TYPES = frozenset({
    "daftar_isi", "daftar_gambar", "daftar_tabel", "daftar_lampiran",
    "daftar_pustaka", "bab", "sub_bab", "lampiran", "item_lampiran",
})
_MAJOR_SECTION_TYPES = frozenset({
    "daftar_isi",
    "daftar_gambar",
    "daftar_tabel",
    "daftar_lampiran",
    "daftar_pustaka",
    "bab",
    "sub_bab",
    "lampiran",
})
_NON_BAB_SECTION_TITLES = {
    "daftar_isi": "DAFTAR ISI",
    "daftar_gambar": "DAFTAR GAMBAR",
    "daftar_tabel": "DAFTAR TABEL",
    "daftar_lampiran": "DAFTAR LAMPIRAN",
    "daftar_pustaka": "DAFTAR PUSTAKA",
    "lampiran": "LAMPIRAN",
}


def _normalize_section_type(raw: str) -> str:
    """Normalize LLM-generated section type to canonical snake_case.

    Handles Title Case ("Daftar Isi"), UPPERCASE ("DAFTAR ISI"),
    and mixed spacing/underscore variants before matching.
    """
    candidate = raw.strip().lower().replace(" ", "_")
    if candidate in _VALID_SECTION_TYPES:
        return candidate
    return raw


class SectionItem(BaseModel):
    type: str
    required: bool | None = None
    number: int | None = None
    sub_number: str | None = None
    title: str | None = None
    lampiran_number: str | None = None
    is_major_section: bool = False

    @model_validator(mode="before")
    @classmethod
    def normalize_section_type(cls, data: object) -> object:
        if not isinstance(data, dict):
            return data

        normalized = dict(data)
        raw_type = normalized.get("type")
        if not isinstance(raw_type, str):
            normalized.setdefault("is_major_section", False)
            return normalized

        canonical_type = _normalize_section_type(raw_type)
        normalized["type"] = canonical_type

        normalized["is_major_section"] = canonical_type in _MAJOR_SECTION_TYPES

        if canonical_type in _NON_BAB_SECTION_TITLES:
            normalized["title"] = _NON_BAB_SECTION_TITLES[canonical_type]

        return normalized


class DocumentStructureExtracted(BaseModel):
    sections: list[SectionItem] = []
    format_nama_file: str | None = None


class DocumentStructureInfo(DocumentStructureExtracted):
    sources: list[Source] = []
    user_placeholders: dict[str, str] = {}
    generated_placeholders: dict[str, str] = {}


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


class NumberingInfo(NumberingExtracted):
    sources: list[Source] = []


class FiguresTablesExtracted(BaseModel):
    table_caption_position: str | None = None
    figure_caption_position: str | None = None
    caption_format_figure: str | None = None
    caption_format_table: str | None = None
    budget_format_rules: "BudgetFormatRules | None" = None


class BudgetItem(BaseModel):
    """Single budget item with percentage rules."""
    jenis_pengeluaran: str
    persentase_maksimum: float | None = None
    contoh: str | None = None


class BudgetFormatRules(BaseModel):
    """Rules for budget table extraction from document chunks via LLM."""
    budget_items: list[BudgetItem] = []
    sumber_dana_options: list[str] = []
    additional_rules: list[str] | None = None


class FiguresTablesInfo(FiguresTablesExtracted):
    sources: list[Source] = []


_VALID_HALAMAN_INTI_SECTIONS = frozenset({
    "bab", "daftar_isi", "daftar_pustaka", "lampiran",
})


class PageCountExtracted(BaseModel):
    proposal_halaman_inti_maks: int | None = None
    halaman_inti_mulai: str = "bab"
    halaman_inti_selesai: str = "daftar_pustaka"

    @model_validator(mode="before")
    @classmethod
    def normalize_fields(cls, data: object) -> object:
        if not isinstance(data, dict):
            return data
        normalized = dict(data)

        normalized.pop("catatan", None)
        normalized.pop("definisi_halaman_inti", None)

        for field, default in (("halaman_inti_mulai", "bab"), ("halaman_inti_selesai", "daftar_pustaka")):
            val = normalized.get(field)
            if val not in _VALID_HALAMAN_INTI_SECTIONS:
                normalized[field] = default

        return normalized


class PageCountInfo(PageCountExtracted):
    sources: list[Source] = []


class DocumentMetadata(BaseModel):
    source_document: str | None = None
    typography: TypographyInfo | None = None
    page_layout: PageLayoutInfo | None = None
    spacing: SpacingInfo | None = None
    document_structure_proposal: DocumentStructureInfo | None = None
    numbering: NumberingInfo | None = None
    figures_and_tables: FiguresTablesInfo | None = None
    page_count_limits: PageCountInfo | None = None
