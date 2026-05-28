"""
Validation package untuk automated document validation.

Digunakan oleh: ai-backend, manage.py, atau command-line

Tujuan: Validasi otomatis apakah DOCX hasil generate sesuai dengan formatting rules
yang diekstraksi dari document_metadata.payload.

Modul:
- models: ValidationIssue, ValidationResult, DocxProperties schemas
- docx_property_extractor: Extract formatting properties from DOCX files
- rule_validator: Compare properties against DocumentMetadata rules
- validator: Main entry point

Contoh penggunaan:
```python
from model_ai.validation import validate_document

result = validate_document(
    docx_path="output/proposal.docx",
    metadata_dict=document_metadata.payload
)
print(result.status)  # 'pass', 'fail', atau 'warning'
print(result.issues)   # List of ValidationIssue objects
```
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
    # Models
    "DocxProperties",
    "ValidationIssue",
    "ValidationResult",
    # Extractors
    "extract_docx_properties",
    "extract_docx_properties_dict",
    # Validators
    "compare_properties",
    # Main entry points
    "validate_document",
    "validate_document_simple",
    "validate_and_print",
    "print_validation_result",
]