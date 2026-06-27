"""Definisi schema Pydantic untuk hasil ekstraksi dokumen dan validasi turunannya. Posisi pipeline: dipakai oleh doc_extractor, metadata_loader, dan validocx_adapter."""
import re
from typing import ClassVar, Literal

from pydantic import BaseModel, model_validator


class Source(BaseModel):
    chunk_index: int
    page_start: int | None = None
    page_end: int | None = None
    header: str
    snippet: str


_VALID_CASE_STYLES = frozenset({"UPPERCASE", "LOWERCASE", "SENTENCE_CASE", "TOGGLE_CASE"})
_VALID_TITLE_STYLES: frozenset[str] = frozenset({"BOLD_UPPERCASE", "BOLD", "UPPERCASE", "NORMAL"})


class TypographyExtracted(BaseModel):
    font_family: str | None = None
    font_size_body_pt: int | None = None
    font_size_heading_pt: int | None = None
    heading_1_case: Literal["UPPERCASE", "LOWERCASE", "SENTENCE_CASE", "TOGGLE_CASE"] | None = None
    heading_2_case: Literal["UPPERCASE", "LOWERCASE", "SENTENCE_CASE", "TOGGLE_CASE"] | None = "SENTENCE_CASE"
    heading_3_case: Literal["UPPERCASE", "LOWERCASE", "SENTENCE_CASE", "TOGGLE_CASE"] | None = "SENTENCE_CASE"
    heading_4_case: Literal["UPPERCASE", "LOWERCASE", "SENTENCE_CASE", "TOGGLE_CASE"] | None = "SENTENCE_CASE"
    heading_5_case: Literal["UPPERCASE", "LOWERCASE", "SENTENCE_CASE", "TOGGLE_CASE"] | None = "SENTENCE_CASE"
    heading_1_bold: bool = True
    heading_2_bold: bool = True
    heading_3_bold: bool = True
    heading_4_bold: bool = True
    heading_5_bold: bool = True
    font_size_title_pt: int | None = None
    font_size_author_pt: int | None = None
    font_size_abstract_pt: int | None = None
    title_style: Literal["BOLD_UPPERCASE", "BOLD", "UPPERCASE", "NORMAL"] | None = None

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
        for field in ("heading_1_case", "heading_2_case", "heading_3_case", "heading_4_case", "heading_5_case"):
            val = normalized.get(field)
            if isinstance(val, str):
                normalized[field] = val.strip().upper()
            if normalized.get(field) not in _VALID_CASE_STYLES:
                normalized[field] = None
        for field in ("heading_1_bold", "heading_2_bold", "heading_3_bold", "heading_4_bold", "heading_5_bold"):
            val = normalized.get(field)
            if isinstance(val, str):
                normalized[field] = val.strip().lower() not in ("false", "0", "tidak", "no")
            elif val is None:
                normalized[field] = True
        raw_style = normalized.get("title_style")
        if isinstance(raw_style, str):
            normalized["title_style"] = raw_style.strip().upper()
        if normalized.get("title_style") not in _VALID_TITLE_STYLES:
            normalized["title_style"] = None
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
    heading_alignment: str = "CENTER"
    heading_1_alignment: str | None = None
    heading_2_alignment: str | None = None
    heading_3_alignment: str | None = None
    heading_4_alignment: str | None = None
    heading_5_alignment: str | None = None
    line_spacing_title_abstract: float | None = None

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

    _VALID_HEADING_ALIGNMENTS: frozenset[str] = frozenset({"CENTER", "LEFT", "RIGHT", "JUSTIFY"})

    @model_validator(mode="after")
    def _normalize_rule(self) -> "SpacingExtracted":
        if self.line_spacing_rule is not None:
            raw = self.line_spacing_rule.strip().upper()
            normalized = self._RULE_ALIASES.get(raw, raw)
            self.line_spacing_rule = normalized if normalized in self._VALID_RULES else None
            if self.line_spacing_rule in {"SINGLE", "ONE_POINT_FIVE", "DOUBLE"}:
                self.line_spacing = None

        val = (self.heading_alignment or "CENTER").strip().upper()
        self.heading_alignment = val if val in self._VALID_HEADING_ALIGNMENTS else "CENTER"

        for field, default in (
            ("heading_1_alignment", None),
            ("heading_2_alignment", None),
            ("heading_3_alignment", None),
            ("heading_4_alignment", None),
            ("heading_5_alignment", None),
        ):
            raw_val = getattr(self, field)
            if raw_val is None:
                continue
            normalized_val = raw_val.strip().upper()
            setattr(self, field, normalized_val if normalized_val in self._VALID_HEADING_ALIGNMENTS else None)
        return self


class SpacingInfo(SpacingExtracted):
    sources: list[Source] = []


_VALID_SECTION_TYPES = frozenset({
    "daftar_isi", "daftar_gambar", "daftar_tabel", "daftar_lampiran",
    "daftar_pustaka", "bab", "sub_bab", "lampiran", "item_lampiran",
    "judul_abstrak", "lampiran_utama",
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
    "judul_abstrak",
    "lampiran_utama",
})

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

        return normalized


class DocumentStructureExtracted(BaseModel):
    sections: list[SectionItem] = []
    format_nama_file: str | None = None
    lampiran_heading_separator: str | None = "."


class _DocumentStructureDetailBase(DocumentStructureExtracted):
    sources: list[Source] = []
    user_placeholders: dict[str, str] = {}
    generated_placeholders: dict[str, str] = {}


class DocumentStructureInfo(_DocumentStructureDetailBase):
    """Struktur dokumen untuk Type A (proposal PKM-KC, PKM-K, dll.)."""


class DocumentStructureArtikelInfo(_DocumentStructureDetailBase):
    """Struktur dokumen untuk Type B (artikel ilmiah PKM-AI)."""


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
    caption_format_lampiran: str | None = None
    caption_alignment_figure:   str | None = None
    caption_alignment_table:    str | None = None
    caption_alignment_lampiran: str | None = None
    budget_format_rules: "BudgetFormatRules | None" = None
    caption_font_size: int | None = None
    caption_line_spacing: float | None = None

    _VALID_CAPTION_ALIGNMENTS: ClassVar[frozenset[str]] = frozenset({"CENTER", "LEFT", "RIGHT", "JUSTIFY"})

    @model_validator(mode="after")
    def _normalize_caption_alignments(self) -> "FiguresTablesExtracted":
        """Normalise alignment strings dari LLM: strip, upper-case, validasi ke enum.
        Nilai yang tidak dikenal di-set None (→ default CENTER saat digunakan).
        """
        for field in ("caption_alignment_figure", "caption_alignment_table", "caption_alignment_lampiran"):
            raw = getattr(self, field)
            if raw is None:
                continue
            normalized = raw.strip().upper()
            setattr(self, field, normalized if normalized in self._VALID_CAPTION_ALIGNMENTS else None)
        return self


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
    "judul_abstrak", "lampiran_utama",
})


class PageCountExtracted(BaseModel):
    proposal_halaman_inti_maks: int | None = None
    halaman_inti_mulai: str = "bab"
    halaman_inti_selesai: str = "daftar_pustaka"
    artikel_halaman_inti_min: int | None = None
    artikel_halaman_inti_maks: int | None = None

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
    document_structure_artikel: DocumentStructureArtikelInfo | None = None
    numbering: NumberingInfo | None = None
    figures_and_tables: FiguresTablesInfo | None = None
    page_count_limits: PageCountInfo | None = None
