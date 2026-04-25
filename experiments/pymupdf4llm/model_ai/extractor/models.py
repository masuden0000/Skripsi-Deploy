from pydantic import BaseModel


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
    font_size_heading_pt: str | None = None
    heading_style: str | None = None
    heading_capitalization: str | None = None


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
    line_spacing_body: float | None = None
    paragraph_alignment: str | None = None
    paragraph_first_indent: str | None = None
    hanging_indent_references: str | None = None


class SpacingInfo(SpacingExtracted):
    sources: list[Source] = []


# --- Document Structure ---

class BabItem(BaseModel):
    bab_number: str
    title: str | None = None


class DocumentStructureExtracted(BaseModel):
    halaman_sampul: bool | None = None
    halaman_pengesahan: bool | None = None
    ringkasan: bool | None = None
    daftar_isi: bool | None = None
    daftar_gambar: str | None = None
    daftar_tabel: str | None = None
    daftar_lampiran: str | None = None
    bab_list: list[BabItem] = []
    daftar_pustaka: bool | None = None
    lampiran: bool | None = None
    max_halaman_inti: int | None = None
    format_nama_file: str | None = None


class DocumentStructureInfo(DocumentStructureExtracted):
    sources: list[Source] = []


# --- Numbering ---

class NumberingExtracted(BaseModel):
    preliminary_page_format: str | None = None
    preliminary_page_position: str | None = None
    preliminary_page_start_from: str | None = None
    content_page_format: str | None = None
    content_page_position: str | None = None
    content_page_start_from: str | None = None
    chapter_numbering_format: str | None = None
    sub_chapter_format: str | None = None
    figure_numbering_format: str | None = None
    table_numbering_format: str | None = None


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
    catatan: str | None = None


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
