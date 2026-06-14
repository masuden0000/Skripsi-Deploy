"""Runner validocx — satu-satunya engine validasi per-paragraf.

Posisi pipeline: payload (DocumentMetadata) → adapter → validocx.validate() →
parse_entries/build_report → ValidationIssue + ValidationCheckResult.

Modul ini sekarang hanya bertindak sebagai orchestrator.
Logika check domain telah dipindah ke subpackage checks/:
  checks/_shared.py        — constants + shared helpers
  checks/typography.py     — _check_heading_case, _check_body_content
  checks/structure.py      — _check_document_structure, _check_lampiran_format
  checks/figures_tables.py — _check_figures_tables, _check_caption_format
  checks/numbering.py      — _check_numbering
  checks/page_count.py     — _check_page_count
"""
from __future__ import annotations

from pathlib import Path

from docx import Document as DocxDocument

from model_ai.extractor.models import DocumentMetadata
from model_ai.validation.models import ValidationCheckResult, ValidationIssue
from model_ai.validation.validocx.validator import validate as validocx_validate
from model_ai.validation.validocx.debug_report import parse_entries, build_report
from model_ai.validation.validocx_adapter import (
    enrich_requirements_with_docx_styles,
    metadata_to_requirements,
    clear_style_level_cache,
)

from .checks._shared import _capture_log, _build_issues_checks
from .checks.typography import _check_heading_case, _check_body_content
from .checks.structure import _check_document_structure, _check_lampiran_format
from .checks.figures_tables import _check_figures_tables, _check_caption_format
from .checks.numbering import _check_numbering
from .checks.page_count import _check_page_count


def run_validocx(
    docx_path: str | Path,
    metadata: DocumentMetadata,
) -> tuple[list[ValidationIssue], list[ValidationCheckResult]]:
    """Jalankan engine validocx penuh dan kembalikan issues + checks.

    Alur:
      DocumentMetadata → requirements (via adapter) →
      validocx.validate() → log capture → parse_entries → build_report →
      ValidationIssue + ValidationCheckResult

    Returns:
        Tuple (issues, checks) siap masuk ke ValidationResult.
    """
    # Reset cache style level agar hasil dokumen sebelumnya tidak terbawa.
    clear_style_level_cache()

    path = Path(docx_path)
    # Load dokumen SEKALI di sini; semua helper menerima objek doc yang sama
    # agar tidak perlu buka/parse ZIP berulang kali.
    doc  = DocxDocument(str(path))

    requirements = metadata_to_requirements(metadata)
    requirements = enrich_requirements_with_docx_styles(requirements, path, doc)
    log_text = _capture_log(path, requirements, validocx_validate, doc=doc)

    entries = parse_entries(log_text)
    report  = build_report(entries, doc=doc)

    # Ekstrak daftar style yang dikenali dari requirements untuk ditampilkan
    # sebagai nilai "Seharusnya" pada warning undefined_style.
    # Contoh hasil: ["Normal", "Heading 1", "Heading 2", "Heading 3"]
    known_styles = list(requirements.get("styles", {}).keys())

    issues, checks = _build_issues_checks(report, known_styles=known_styles, requirements=requirements)
    case_issues, case_checks         = _check_heading_case(path, metadata, doc)
    struct_issues, struct_checks     = _check_document_structure(path, metadata, doc)
    fig_issues, fig_checks           = _check_figures_tables(path, metadata, doc)
    caption_issues, caption_checks   = _check_caption_format(path, metadata, doc)
    lampiran_issues, lampiran_checks = _check_lampiran_format(path, metadata, doc)
    num_issues, num_checks           = _check_numbering(path, metadata, doc)
    pgcount_issues, pgcount_checks   = _check_page_count(path, metadata, doc)
    body_issues, body_checks         = _check_body_content(path, metadata, doc)

    all_issues = (issues + case_issues + struct_issues + fig_issues
                  + caption_issues + lampiran_issues + num_issues
                  + pgcount_issues + body_issues)
    all_checks = (checks + case_checks + struct_checks + fig_checks
                  + caption_checks + lampiran_checks + num_checks
                  + pgcount_checks + body_checks)
    return all_issues, all_checks
