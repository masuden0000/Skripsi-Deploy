"""Main entry point untuk validasi dokumen DOCX terhadap formatting rules. Posisi pipeline: DOCX + metadata → validator (menggunakan docx_property_extractor dan rule_validator)."""
from datetime import datetime, timezone
from pathlib import Path

from model_ai.extractor.models import DocumentMetadata
from model_ai.validation.docx_property_extractor import extract_docx_properties
from model_ai.validation.models import DocxProperties, ValidationResult
from model_ai.validation.rule_validator import compare_properties


def validate_document(
    docx_path: str | Path,
    metadata: DocumentMetadata | None = None,
    metadata_dict: dict | None = None,
) -> ValidationResult:
    """Validate a DOCX document against formatting rules.

    Args:
        docx_path: Path to the DOCX file to validate.
        metadata: DocumentMetadata object containing rules.
                  If None, metadata_dict must be provided.
        metadata_dict: Alternative to metadata, as dict.
                        Will be converted to DocumentMetadata.

    Returns:
        ValidationResult containing status and list of issues.

    Raises:
        FileNotFoundError: If the DOCX file does not exist.
        ValueError: If neither metadata nor metadata_dict is provided.
    """
    path = Path(docx_path)
    if not path.exists():
        raise FileNotFoundError(f"DOCX file not found: {path}")

    if metadata is None:
        if metadata_dict is None:
            raise ValueError("Either metadata or metadata_dict must be provided")
        metadata = DocumentMetadata.model_validate(metadata_dict)

    props = extract_docx_properties(path)

    issues, checks = compare_properties(props, metadata)

    status = "pass"
    if any(i.severity == "error" for i in issues):
        status = "fail"
    elif any(i.severity == "warning" for i in issues):
        status = "warning"

    error_count = sum(1 for i in issues if i.severity == "error")
    warning_count = sum(1 for i in issues if i.severity == "warning")
    info_count = sum(1 for i in issues if i.severity == "info")

    if status == "pass":
        summary = "Dokumen sesuai dengan rules yang diharapkan."
    else:
        summary_parts = []
        if error_count > 0:
            summary_parts.append(f"{error_count} error(s)")
        if warning_count > 0:
            summary_parts.append(f"{warning_count} warning(s)")
        if info_count > 0:
            summary_parts.append(f"{info_count} info(s)")
        summary = f"Ditemukan {', '.join(summary_parts)} yang perlu diperbaiki."

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
    """Simplified validation using raw rules dict.

    Args:
        docx_path: Path to the DOCX file to validate.
        rules: Dictionary containing rules (typically from DocumentMetadata.payload).

    Returns:
        ValidationResult containing status and list of issues.
    """
    return validate_document(docx_path=docx_path, metadata_dict=rules)


def print_validation_result(result: ValidationResult) -> None:
    """Print validation result in a human-readable format."""
    print(f"\n{'='*60}")
    print(f"VALIDATION RESULT")
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
            severity_icon = {
                "error": "[ERROR]",
                "warning": "[WARN] ",
                "info": "[INFO] ",
            }.get(issue.severity, "[?]   ")
            print(f"\n{i}. {severity_icon} {issue.category}.{issue.field}")
            print(f"   Message : {issue.message}")
            if issue.location:
                print(f"   Location: {issue.location}")
            print(f"   Expected: {issue.expected}")
            print(f"   Actual  : {issue.actual}")
    else:
        print("✅ No issues found. Document is valid!")

    print(f"\n{'='*60}\n")


def validate_and_print(
    docx_path: str | Path,
    metadata_dict: dict,
) -> ValidationResult:
    """Validate document and print results.

    Args:
        docx_path: Path to the DOCX file to validate.
        metadata_dict: Rules dictionary (from DocumentMetadata.payload).

    Returns:
        ValidationResult containing status and list of issues.
    """
    result = validate_document(docx_path=docx_path, metadata_dict=metadata_dict)
    print_validation_result(result)
    return result


if __name__ == "__main__":
    import sys
    import json

    if len(sys.argv) < 3:
        print("Usage: python -m model_ai.validation.validator <docx_path> <metadata_json_path>")
        print("  <docx_path>: Path to the DOCX file to validate")
        print("  <metadata_json_path>: Path to JSON file containing DocumentMetadata payload")
        sys.exit(1)

    docx_path = sys.argv[1]
    metadata_path = sys.argv[2]

    with open(metadata_path, "r", encoding="utf-8") as f:
        metadata_dict = json.load(f)

    result = validate_and_print(docx_path, metadata_dict)

    sys.exit(0 if result.status == "pass" else 1)