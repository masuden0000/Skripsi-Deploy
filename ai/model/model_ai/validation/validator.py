"""Main entry point validasi dokumen DOCX. Pipeline: payload (DocumentMetadata) → validocx engine → ValidationResult. Keyword: automated document validation"""
from datetime import datetime, timezone
from pathlib import Path

from model_ai.extractor.models import DocumentMetadata
from model_ai.validation.models import ValidationCheckResult, ValidationIssue, ValidationResult
from model_ai.validation.validocx_runner import run_validocx


def validate_document(
    docx_path: str | Path,
    metadata: DocumentMetadata | None = None,
    metadata_dict: dict | None = None,
) -> ValidationResult:
    """Validasi dokumen DOCX menggunakan engine validocx.

    Args:
        docx_path: Path ke file DOCX yang akan divalidasi.
        metadata: DocumentMetadata berisi rules (dari payload).
                  Jika None, metadata_dict harus diberikan.
        metadata_dict: Alternatif metadata sebagai dict; dikonversi ke DocumentMetadata.

    Returns:
        ValidationResult berisi status, issues, dan checks.

    Raises:
        FileNotFoundError: Jika file DOCX tidak ditemukan.
        ValueError: Jika metadata maupun metadata_dict tidak diberikan.
    """
    path = Path(docx_path)
    if not path.exists():
        raise FileNotFoundError(f"DOCX file not found: {path}")

    if metadata is None:
        if metadata_dict is None:
            raise ValueError("Either metadata or metadata_dict must be provided")
        metadata = DocumentMetadata.model_validate(metadata_dict)

    try:
        issues, checks = run_validocx(path, metadata)
    except Exception as exc:
        issues = [ValidationIssue(
            category="system",
            field="engine_error",
            severity="error",
            message=f"Engine validasi gagal dijalankan: {exc}",
        )]
        checks = [ValidationCheckResult(
            category="system",
            field="engine_error",
            status="failed",
            message=f"validocx tidak berhasil dijalankan: {exc}",
        )]

    status = "pass"
    if any(i.severity == "error" for i in issues):
        status = "fail"
    elif any(i.severity == "warning" for i in issues):
        status = "warning"

    error_count   = sum(1 for i in issues if i.severity == "error")
    warning_count = sum(1 for i in issues if i.severity == "warning")
    info_count    = sum(1 for i in issues if i.severity == "info")

    if status == "pass":
        summary = "Dokumen sesuai dengan rules yang diharapkan."
    else:
        parts = []
        if error_count:
            parts.append(f"{error_count} error(s)")
        if warning_count:
            parts.append(f"{warning_count} warning(s)")
        if info_count:
            parts.append(f"{info_count} info(s)")
        summary = f"Ditemukan {', '.join(parts)} yang perlu diperbaiki."

    return ValidationResult(
        status=status,
        issues=issues,
        checks=checks,
        validated_at=datetime.now(timezone.utc).isoformat(),
        document_path=str(path),
        document_name=path.name,
        summary=summary,
    )


def validate_document_simple(
    docx_path: str | Path,
    rules: dict,
) -> ValidationResult:
    """Validasi dengan raw rules dict (dari DocumentMetadata.payload)."""
    return validate_document(docx_path=docx_path, metadata_dict=rules)


def print_validation_result(result: ValidationResult) -> None:
    """Cetak ValidationResult ke stdout dalam format human-readable."""
    print(f"\n{'='*60}")
    print("VALIDATION RESULT")
    print(f"{'='*60}")
    print(f"Status: {result.status.upper()}")
    print(f"Document: {result.document_name}")
    print(f"Validated at: {result.validated_at}")
    print(f"Summary: {result.summary}")
    print()

    if result.issues:
        print(f"Issues found ({len(result.issues)}):")
        print("-" * 60)
        for i, issue in enumerate(result.issues, 1):
            icon = {"error": "[ERROR]", "warning": "[WARN] ", "info": "[INFO] "}.get(
                issue.severity, "[?]   "
            )
            print(f"\n{i}. {icon} {issue.category}.{issue.field}")
            print(f"   Message : {issue.message}")
            if issue.location:
                print(f"   Location: {issue.location}")
            if issue.expected is not None:
                print(f"   Expected: {issue.expected}")
            if issue.actual is not None:
                print(f"   Actual  : {issue.actual}")
    else:
        print("No issues found. Document is valid!")

    print(f"\n{'='*60}\n")


def validate_and_print(
    docx_path: str | Path,
    metadata_dict: dict,
) -> ValidationResult:
    """Validasi dokumen dan langsung cetak hasilnya."""
    result = validate_document(docx_path=docx_path, metadata_dict=metadata_dict)
    print_validation_result(result)
    return result


if __name__ == "__main__":
    import sys
    import json

    if len(sys.argv) < 3:
        print("Usage: python -m model_ai.validation.validator <docx_path> <metadata_json_path>")
        sys.exit(1)

    with open(sys.argv[2], "r", encoding="utf-8") as f:
        metadata_dict = json.load(f)

    result = validate_and_print(sys.argv[1], metadata_dict)
    sys.exit(0 if result.status == "pass" else 1)
