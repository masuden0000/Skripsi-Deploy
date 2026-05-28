"""
Fungsi: Package validasi dokumen.
Digunakan oleh: ai-backend, manage.py, command-line
Tujuan: Validasi otomatis apakah DOCX hasil generate sesuai dengan formatting rules.
Keyword: automated document generation
"""
from model_ai.validation.models import (
    DocxProperties,
    ValidationIssue,
    ValidationResult,
)
from model_ai.validation.docx_property_extractor import (
    extract_docx_properties,
    extract_docx_properties_dict,
)
from model_ai.validation.rule_validator import compare_properties
from model_ai.validation.validator import (
    validate_document,
    validate_document_simple,
    validate_and_print,
    print_validation_result,
)

__all__ = [
    "DocxProperties",
    "ValidationIssue",
    "ValidationResult",
    "extract_docx_properties",
    "extract_docx_properties_dict",
    "compare_properties",
    "validate_document",
    "validate_document_simple",
    "validate_and_print",
    "print_validation_result",
]