"""
Fungsi: Definisi schema Pydantic untuk hasil ekstraksi dokumen dan validasi turunannya.

Digunakan oleh: model_ai/docx/metadata_loader.py; model_ai/docx/style_mapping_pipeline.py; model_ai/extractor/doc_extractor.py; tests/docx/test_style_translator_llm.py; tests/extractor/test_doc_extractor.py

Tujuan: Menstandarkan format output ekstraksi agar aman dipakai lintas modul.
"""
import re

from pydantic import BaseModel, model_validator


# ---------------------------------------------------------------------------
# Digunakan oleh: model_ai/extractor/doc_extractor.py
# Mendefinisikan class `Source` untuk kebutuhan modul `models`.
# ---------------------------------------------------------------------------
class Source(BaseModel):
    chunk_index: int
    page_start: int
    page_end: int
    header: str
    snippet: str


# --- Typography ---

# ---------------------------------------------------------------------------
# Digunakan oleh: model_ai/extractor/doc_extractor.py
# Mendefinisikan class `TypographyExtracted` untuk kebutuhan modul `models`.
# ---------------------------------------------------------------------------
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
        # Fallback: if heading size is null but body size is known, reuse body size
        if normalized.get("font_size_heading_pt") is None and normalized.get("font_size_body_pt") is not None:
            normalized["font_size_heading_pt"] = normalized["font_size_body_pt"]
        # Default heading style: assume bold when the extractor does not provide a value.
        if normalized.get("heading_bold") is None:
            normalized["heading_bold"] = True
        # Default heading style: assume all caps when extractor omits this field.
        if normalized.get("heading_all_caps") is None:
            normalized["heading_all_caps"] = True
        return normalized


# ---------------------------------------------------------------------------
# Digunakan oleh: model_ai/extractor/doc_extractor.py
# Mendefinisikan class `TypographyInfo` untuk kebutuhan modul `models`.
# ---------------------------------------------------------------------------
class TypographyInfo(TypographyExtracted):
    sources: list[Source] = []


# --- Page Layout ---

# ---------------------------------------------------------------------------
# Digunakan oleh: model_ai/extractor/doc_extractor.py
# Mendefinisikan class `PageLayoutExtracted` untuk kebutuhan modul `models`.
# ---------------------------------------------------------------------------
class PageLayoutExtracted(BaseModel):
    margin_top_cm: float | None = None
    margin_bottom_cm: float | None = None
    margin_left_cm: float | None = None
    margin_right_cm: float | None = None
    paper_size: str | None = None
    orientation: str | None = None


# ---------------------------------------------------------------------------
# Digunakan oleh: model_ai/extractor/doc_extractor.py
# Mendefinisikan class `PageLayoutInfo` untuk kebutuhan modul `models`.
# ---------------------------------------------------------------------------
class PageLayoutInfo(PageLayoutExtracted):
    sources: list[Source] = []


# --- Spacing ---

# ---------------------------------------------------------------------------
# Digunakan oleh: model_ai/extractor/doc_extractor.py
# Mendefinisikan class `SpacingExtracted` untuk kebutuhan modul `models`.
# ---------------------------------------------------------------------------
class SpacingExtracted(BaseModel):
    line_spacing: float | None = None
    line_spacing_rule: str | None = None
    paragraph_alignment: str | None = None
    first_line_indent_cm: float | None = None


# ---------------------------------------------------------------------------
# Digunakan oleh: model_ai/extractor/doc_extractor.py
# Mendefinisikan class `SpacingInfo` untuk kebutuhan modul `models`.
# ---------------------------------------------------------------------------
class SpacingInfo(SpacingExtracted):
    sources: list[Source] = []


# --- Document Structure ---

# ---------------------------------------------------------------------------
# Digunakan oleh: Dipakai oleh fungsi-fungsi di modul ini dan modul terkait saat import runtime.
# Blok konstanta `_VALID_SECTION_TYPES` untuk menyimpan konfigurasi/registry yang dipakai berulang.
# ---------------------------------------------------------------------------
_VALID_SECTION_TYPES = frozenset({
    "daftar_isi", "daftar_gambar", "daftar_tabel", "daftar_lampiran",
    "daftar_pustaka", "bab", "sub_bab", "lampiran", "item_lampiran",
})
# ---------------------------------------------------------------------------
# Digunakan oleh: Dipakai oleh fungsi-fungsi di modul ini dan modul terkait saat import runtime.
# Blok konstanta `_MAJOR_SECTION_TYPES` untuk menyimpan konfigurasi/registry yang dipakai berulang.
# ---------------------------------------------------------------------------
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
# ---------------------------------------------------------------------------
# Digunakan oleh: Dipakai oleh fungsi-fungsi di modul ini dan modul terkait saat import runtime.
# Blok konstanta `_NON_BAB_SECTION_TITLES` untuk menyimpan konfigurasi/registry yang dipakai berulang.
# ---------------------------------------------------------------------------
_NON_BAB_SECTION_TITLES = {
    "daftar_isi": "DAFTAR ISI",
    "daftar_gambar": "DAFTAR GAMBAR",
    "daftar_tabel": "DAFTAR TABEL",
    "daftar_lampiran": "DAFTAR LAMPIRAN",
    "daftar_pustaka": "DAFTAR PUSTAKA",
    "lampiran": "LAMPIRAN",
}


# ---------------------------------------------------------------------------
# Digunakan oleh: Dipakai internal di file ini atau dipanggil dari entrypoint runtime.
# Menjalankan fungsi `_normalize_section_type` sebagai bagian alur `models`.
# ---------------------------------------------------------------------------
def _normalize_section_type(raw: str) -> str:
    """Normalize LLM-generated section type to canonical snake_case.

    Handles Title Case ("Daftar Isi"), UPPERCASE ("DAFTAR ISI"),
    and mixed spacing/underscore variants before matching.
    """
    candidate = raw.strip().lower().replace(" ", "_")
    if candidate in _VALID_SECTION_TYPES:
        return candidate
    return raw  # pass through unknown values unchanged


# ---------------------------------------------------------------------------
# Digunakan oleh: model_ai/docx/docx_renderer.py
# Mendefinisikan class `SectionItem` untuk kebutuhan modul `models`.
# ---------------------------------------------------------------------------
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

        # Salin payload agar normalisasi tidak mengubah object input asli.
        normalized = dict(data)
        raw_type = normalized.get("type")
        if not isinstance(raw_type, str):
            normalized.setdefault("is_major_section", False)
            return normalized

        # Pakai canonical type agar konsisten lintas variasi hasil LLM.
        canonical_type = _normalize_section_type(raw_type)
        normalized["type"] = canonical_type

        # Tandai apakah section ini setara level utama seperti BAB.
        normalized["is_major_section"] = canonical_type in _MAJOR_SECTION_TYPES

        # Isi title non-BAB secara deterministik agar tidak null/lowercase.
        if canonical_type in _NON_BAB_SECTION_TITLES:
            normalized["title"] = _NON_BAB_SECTION_TITLES[canonical_type]

        return normalized


# ---------------------------------------------------------------------------
# Digunakan oleh: model_ai/extractor/doc_extractor.py
# Mendefinisikan class `DocumentStructureExtracted` untuk kebutuhan modul `models`.
# ---------------------------------------------------------------------------
class DocumentStructureExtracted(BaseModel):
    sections: list[SectionItem] = []
    max_halaman_inti: int | None = None
    format_nama_file: str | None = None


# ---------------------------------------------------------------------------
# Digunakan oleh: model_ai/extractor/doc_extractor.py
# Mendefinisikan class `DocumentStructureInfo` untuk kebutuhan modul `models`.
# ---------------------------------------------------------------------------
class DocumentStructureInfo(DocumentStructureExtracted):
    sources: list[Source] = []
    user_placeholders: dict[str, str] = {}       # key = instruction_key, value = teks override dari user
    generated_placeholders: dict[str, str] = {}  # key = instruction_key, value = hasil generate LLM saat pipeline docx


# --- Numbering ---

# ---------------------------------------------------------------------------
# Digunakan oleh: Dipakai internal di file ini atau dipanggil dari entrypoint runtime.
# Mendefinisikan class `PageNumberConfig` untuk kebutuhan modul `models`.
# ---------------------------------------------------------------------------
class PageNumberConfig(BaseModel):
    format: str | None = None
    location: str | None = None
    alignment: str | None = None
    start_at_section: str | None = None


# ---------------------------------------------------------------------------
# Digunakan oleh: model_ai/extractor/doc_extractor.py
# Mendefinisikan class `NumberingExtracted` untuk kebutuhan modul `models`.
# ---------------------------------------------------------------------------
class NumberingExtracted(BaseModel):
    preliminary: PageNumberConfig | None = None
    content: PageNumberConfig | None = None
    chapter_format: str | None = None
    sub_chapter_format: str | None = None


# ---------------------------------------------------------------------------
# Digunakan oleh: model_ai/extractor/doc_extractor.py
# Mendefinisikan class `NumberingInfo` untuk kebutuhan modul `models`.
# ---------------------------------------------------------------------------
class NumberingInfo(NumberingExtracted):
    sources: list[Source] = []


# --- Figures & Tables ---

# ---------------------------------------------------------------------------
# Digunakan oleh: model_ai/extractor/doc_extractor.py
# Mendefinisikan class `FiguresTablesExtracted` untuk kebutuhan modul `models`.
# ---------------------------------------------------------------------------
class FiguresTablesExtracted(BaseModel):
    table_caption_position: str | None = None
    figure_caption_position: str | None = None
    caption_format_figure: str | None = None
    caption_format_table: str | None = None
    budget_format_rules: "BudgetFormatRules | None" = None


# ---------------------------------------------------------------------------
# Budget Format Rules for extracting percentage-based budget constraints
# ---------------------------------------------------------------------------
class BudgetItem(BaseModel):
    """Single budget item with percentage rules."""
    jenis_pengeluaran: str
    persentase_maksimum: float | None = None
    contoh: str | None = None


class BudgetFormatRules(BaseModel):
    """Rules for budget table extraction from document chunks via LLM."""
    budget_items: list[BudgetItem] = []
    sumber_dana_options: list[str] = []
    additional_rules: str | None = None


# ---------------------------------------------------------------------------
# Digunakan oleh: model_ai/extractor/doc_extractor.py
# Mendefinisikan class `FiguresTablesInfo` untuk kebutuhan modul `models`.
# ---------------------------------------------------------------------------
class FiguresTablesInfo(FiguresTablesExtracted):
    sources: list[Source] = []


# --- Page Count Limits ---

# ---------------------------------------------------------------------------
# Digunakan oleh: model_ai/extractor/doc_extractor.py
# Mendefinisikan class `PageCountExtracted` untuk kebutuhan modul `models`.
# ---------------------------------------------------------------------------
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

        # Buang field legacy yang tidak lagi dipakai
        normalized.pop("catatan", None)
        normalized.pop("definisi_halaman_inti", None)

        # Pastikan nilai mulai/selesai valid; fallback ke default jika tidak
        for field, default in (("halaman_inti_mulai", "bab"), ("halaman_inti_selesai", "daftar_pustaka")):
            val = normalized.get(field)
            if val not in _VALID_HALAMAN_INTI_SECTIONS:
                normalized[field] = default

        return normalized


# ---------------------------------------------------------------------------
# Digunakan oleh: model_ai/extractor/doc_extractor.py
# Mendefinisikan class `PageCountInfo` untuk kebutuhan modul `models`.
# ---------------------------------------------------------------------------
class PageCountInfo(PageCountExtracted):
    sources: list[Source] = []


# --- Root Model ---

# ---------------------------------------------------------------------------
# Digunakan oleh: model_ai/docx/docx_renderer.py; model_ai/docx/metadata_loader.py; model_ai/docx/style_mapping_pipeline.py; model_ai/extractor/doc_extractor.py
# Mendefinisikan class `DocumentMetadata` untuk kebutuhan modul `models`.
# ---------------------------------------------------------------------------
class DocumentMetadata(BaseModel):
    document_type: str | None = None
    source_document: str | None = None
    typography: TypographyInfo
    page_layout: PageLayoutInfo
    spacing: SpacingInfo
    document_structure_proposal: DocumentStructureInfo
    numbering: NumberingInfo
    figures_and_tables: FiguresTablesInfo
    page_count_limits: PageCountInfo
