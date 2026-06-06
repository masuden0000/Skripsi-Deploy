"""Schema Pydantic untuk hasil validasi dokumen. Posisi pipeline: dipakai oleh validocx_runner dan validator."""
from datetime import datetime, timezone
from typing import Literal

from pydantic import BaseModel, Field


VALIDATION_CATEGORIES = (
    "typography",
    "page_layout",
    "spacing",
    "document_structure",
    "numbering",
    "figures_tables",
    "page_count",
)


class ValidationCheckResult(BaseModel):
    """Hasil satu pengecekan properti: passed, failed, warning, atau skipped."""

    category: Literal[
        "typography",
        "page_layout",
        "spacing",
        "document_structure",
        "numbering",
        "figures_tables",
        "page_count",
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


class ValidationIssue(BaseModel):
    """Represents a single validation issue found in the document."""

    category: Literal[
        "typography",
        "page_layout",
        "spacing",
        "document_structure",
        "numbering",
        "figures_tables",
        "page_count",
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
    occurrences: list[dict] | None = Field(
        default=None,
        description=(
            "List lokasi spesifik setiap kejadian masalah ini. "
            "Setiap item berisi: page (int), bab (str|None), para_idx (int), "
            "style (str), text (str), actual (str|None), expected (str|None)."
        ),
    )

    def __str__(self) -> str:
        return f"[{self.severity.upper()}] {self.category}.{self.field}: {self.message}"


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
