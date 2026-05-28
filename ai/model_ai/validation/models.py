"""
Schema untuk validasi dokumen.

Digunakan oleh: validator.py, rule_validator.py, docx_property_extractor.py

Tujuan: Mendefinisikan struktur data untuk hasil validasi dan properti DOCX.
"""
from datetime import datetime, timezone
from typing import Literal

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Sub-model untuk anomaly reporting (per-heading dan per-paragraph)
# ---------------------------------------------------------------------------
class HeadingCapsAnomaly(BaseModel):
    """Satu pelanggaran aturan kapitalisasi pada sebuah heading."""

    text: str = Field(description="Teks heading asli")
    level: int = Field(description="Level heading: 1 (BAB/DAFTAR) atau 2 (sub-bab)")
    issue: Literal["not_all_caps", "not_title_case"] = Field(
        description="Jenis pelanggaran: not_all_caps untuk H1, not_title_case untuk H2"
    )
    expected_form: str | None = Field(default=None, description="Bentuk yang benar (uppercase / title case)")
    location: str = Field(default="", description="Konteks lokasi heading dalam dokumen")


class SpacingAnomaly(BaseModel):
    """Satu paragraf yang memiliki line spacing berbeda dari mayoritas dokumen."""

    location: str = Field(description="Lokasi hierarkis: 'BAB 4 > 4.1 Anggaran Biaya'")
    paragraph_index: int = Field(description="Indeks paragraf dalam doc.paragraphs")
    expected: float = Field(description="Nilai line spacing yang diharapkan (mayoritas dokumen)")
    actual: float = Field(description="Nilai line spacing yang ditemukan")
    text_preview: str = Field(default="", description="60 karakter pertama teks paragraf")


# ---------------------------------------------------------------------------
# Digunakan oleh: Dipakai oleh fungsi-fungsi di modul ini dan modul terkait saat import runtime.
# Blok konstanta `VALIDATION_CATEGORIES` untuk menyimpan konfigurasi/registry yang dipakai berulang.
# ---------------------------------------------------------------------------
VALIDATION_CATEGORIES = (
    "typography",
    "page_layout",
    "spacing",
    "document_structure",
    "numbering",
    "figures_tables",
)


# ---------------------------------------------------------------------------
# Digunakan oleh: rule_validator.py — mencatat hasil setiap pengecekan properti.
# ---------------------------------------------------------------------------
class ValidationCheckResult(BaseModel):
    """Hasil satu pengecekan properti: passed, failed, warning, atau skipped."""

    category: Literal[
        "typography",
        "page_layout",
        "spacing",
        "document_structure",
        "numbering",
        "figures_tables",
    ]
    field: str = Field(description="Nama properti yang dicek")
    status: Literal["passed", "failed", "warning", "skipped"] = Field(
        description="Hasil pengecekan"
    )
    expected: str | int | float | bool | None = Field(
        default=None, description="Nilai yang diharapkan (dari metadata/ground truth)"
    )
    actual: str | int | float | bool | None = Field(
        default=None, description="Nilai yang ditemukan di dokumen"
    )
    message: str = Field(default="", description="Keterangan hasil")
    location: str | None = Field(default=None, description="Lokasi dalam dokumen")
    skip_reason: str | None = Field(
        default=None,
        description="Alasan dilewati: 'Tidak ada nilai di metadata' atau 'Tidak terdeteksi di dokumen'",
    )


# ---------------------------------------------------------------------------
# Digunakan oleh: Dipakai internal di file ini atau dipanggil dari entrypoint runtime.
# Mendefinisikan class `ValidationIssue` untuk kebutuhan modul `validation`.
# ---------------------------------------------------------------------------
class ValidationIssue(BaseModel):
    """Represents a single validation issue found in the document."""

    category: Literal[
        "typography",
        "page_layout",
        "spacing",
        "document_structure",
        "numbering",
        "figures_tables",
    ] = Field(
        description="Category of the validation issue"
    )
    field: str = Field(
        description="Field name that has the issue (e.g., 'font_family', 'margin_top_cm')"
    )
    expected: str | int | float | bool | None = Field(
        default=None,
        description="Expected value from the rules (DocumentMetadata)"
    )
    actual: str | int | float | bool | None = Field(
        default=None,
        description="Actual value found in the document"
    )
    severity: Literal["error", "warning", "info"] = Field(
        default="error",
        description="Severity level of the issue"
    )
    message: str = Field(
        default="",
        description="Human-readable description of the issue"
    )
    location: str | None = Field(
        default=None,
        description="Lokasi issue dalam dokumen (e.g., 'Seluruh dokumen', 'BAB 1 PENDAHULUAN', 'Paragraf ke-5')"
    )

    def __str__(self) -> str:
        return f"[{self.severity.upper()}] {self.category}.{self.field}: {self.message}"


# ---------------------------------------------------------------------------
# Digunakan oleh: Dipakai internal di file ini atau dipanggil dari entrypoint runtime.
# Mendefinisikan class `ValidationResult` untuk kebutuhan modul `validation`.
# ---------------------------------------------------------------------------
class ValidationResult(BaseModel):
    """Represents the result of a document validation."""

    status: Literal["pass", "fail", "warning"] = Field(
        default="pass",
        description="Overall validation status"
    )
    issues: list[ValidationIssue] = Field(
        default_factory=list,
        description="List of validation issues found"
    )
    checks: list[ValidationCheckResult] = Field(
        default_factory=list,
        description="Hasil lengkap setiap pengecekan properti (passed/failed/warning/skipped)",
    )
    validated_at: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat(),
        description="ISO timestamp when validation was performed"
    )
    document_path: str | None = Field(
        default=None,
        description="Path to the validated document"
    )
    document_name: str | None = Field(
        default=None,
        description="Name of the validated document"
    )
    summary: str = Field(
        default="",
        description="Human-readable summary of the validation result"
    )

    @property
    def error_count(self) -> int:
        return sum(1 for issue in self.issues if issue.severity == "error")

    @property
    def warning_count(self) -> int:
        return sum(1 for issue in self.issues if issue.severity == "warning")

    @property
    def info_count(self) -> int:
        return sum(1 for issue in self.issues if issue.severity == "info")

    @property
    def passed_count(self) -> int:
        return sum(1 for c in self.checks if c.status == "passed")

    @property
    def skipped_count(self) -> int:
        return sum(1 for c in self.checks if c.status == "skipped")

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        # Kelompokkan checks per kategori untuk report terstruktur
        report: dict[str, list[dict]] = {}
        for c in self.checks:
            report.setdefault(c.category, []).append(c.model_dump(exclude_none=False))

        return {
            "status": self.status,
            "summary": self.summary,
            "validated_at": self.validated_at,
            "document_name": self.document_name,
            "document_path": self.document_path,
            "error_count": self.error_count,
            "warning_count": self.warning_count,
            "passed_count": self.passed_count,
            "skipped_count": self.skipped_count,
            "report": report,
            "issues": [issue.model_dump() for issue in self.issues],
        }


# ---------------------------------------------------------------------------
# Digunakan oleh: Dipakai internal di file ini atau dipanggil dari entrypoint runtime.
# Mendefinisikan class `DocxProperties` untuk kebutuhan modul `validation`.
# ---------------------------------------------------------------------------
class DocxProperties(BaseModel):
    """Represents extracted properties from a DOCX file.

    This mirrors the structure of DocumentMetadata for easy comparison.
    """

    # Typography
    font_family: str | None = Field(default=None, description="Primary font family")
    font_size_body_pt: int | None = Field(default=None, description="Body font size in points")
    font_size_heading_pt: int | None = Field(default=None, description="Heading font size in points")
    heading_bold: bool | None = Field(default=None, description="Whether headings are bold")
    heading_all_caps: bool | None = Field(default=None, description="Whether headings are ALL CAPS")

    # Page Layout
    margin_top_cm: float | None = Field(default=None, description="Top margin in cm")
    margin_bottom_cm: float | None = Field(default=None, description="Bottom margin in cm")
    margin_left_cm: float | None = Field(default=None, description="Left margin in cm")
    margin_right_cm: float | None = Field(default=None, description="Right margin in cm")
    paper_size: str | None = Field(default=None, description="Paper size (A4, F4, etc.)")
    orientation: str | None = Field(default=None, description="Portrait or Landscape")
    columns: int | None = Field(default=None, description="Number of text columns per page")

    # Spacing
    # Grup A (SINGLE/ONE_POINT_FIVE/DOUBLE): line_spacing = None (multiplier dari rule).
    # Grup B (MULTIPLE): line_spacing = desimal pengali.
    # Grup C (AT_LEAST/EXACTLY): line_spacing = nilai pt.
    line_spacing: float | None = Field(default=None, description="Nilai spasi: None untuk Grup A, desimal untuk MULTIPLE, pt untuk AT_LEAST/EXACTLY")
    line_spacing_rule: str | None = Field(default=None, description="Aturan spasi: SINGLE | ONE_POINT_FIVE | DOUBLE | MULTIPLE | AT_LEAST | EXACTLY")
    paragraph_alignment: str | None = Field(default=None, description="Default paragraph alignment")
    first_line_indent_cm: float | None = Field(default=None, description="First line indent in cm")

    # Document Structure
    heading_count: int = Field(default=0, description="Number of headings in document")
    section_count: int = Field(default=0, description="Number of sections in document")

    # Numbering
    chapter_format: str | None = Field(default=None, description="Chapter number format")
    sub_chapter_format: str | None = Field(default=None, description="Sub-chapter number format")
    preliminary_page_format: str | None = Field(default=None, description="Preliminary pages numbering format")
    preliminary_page_location: str | None = Field(default=None, description="Preliminary page number location")
    preliminary_page_alignment: str | None = Field(default=None, description="Preliminary page number alignment")
    content_page_format: str | None = Field(default=None, description="Content pages numbering format")
    content_page_location: str | None = Field(default=None, description="Content page number location")
    content_page_alignment: str | None = Field(default=None, description="Content page number alignment")

    # Figures & Tables
    table_caption_position: str | None = Field(default=None, description="Table caption position (above/below)")
    figure_caption_position: str | None = Field(default=None, description="Figure caption position (above/below)")
    table_count: int = Field(default=0, description="Number of tables in document")
    figure_count: int = Field(default=0, description="Number of figures in document")

    # Document structure — detected daftar sections
    has_daftar_isi: bool = Field(default=False, description="Whether document has Daftar Isi")
    has_daftar_pustaka: bool = Field(default=False, description="Whether document has Daftar Pustaka")
    has_daftar_tabel: bool = Field(default=False, description="Whether document has Daftar Tabel")
    has_daftar_gambar: bool = Field(default=False, description="Whether document has Daftar Gambar")

    # Per-item anomaly lists for detailed location-aware reporting
    heading_caps_anomalies: list[HeadingCapsAnomaly] = Field(
        default_factory=list,
        description="List of heading paragraphs that violate ALL CAPS (H1) or title case (H2) rules",
    )
    spacing_anomalies: list[SpacingAnomaly] = Field(
        default_factory=list,
        description="List of body paragraphs with line spacing different from document majority",
    )

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return self.model_dump()