"""Runner validocx — satu-satunya engine validasi per-paragraf.

Posisi pipeline: payload (DocumentMetadata) → adapter → validocx.validate() →
parse_entries/build_report → ValidationIssue + ValidationCheckResult.
"""
import io
import logging
import re
from pathlib import Path

from model_ai.extractor.models import DocumentMetadata
from model_ai.validation.models import ValidationCheckResult, ValidationIssue
from model_ai.validation.validocx.validator import validate as validocx_validate
from model_ai.validation.validocx.debug_report import parse_entries, build_report
from model_ai.validation.validocx_adapter import metadata_to_requirements


_SECTION_ATTR_KEYS = frozenset({
    "left_margin", "right_margin", "top_margin", "bottom_margin",
    "page_width", "page_height", "orientation", "start_type",
})

_CATEGORY_MAP: dict[str, tuple[str, str]] = {
    "section_missing":  ("page_layout",  "section_missing"),
    "font_mismatch":    ("typography",   "font_per_paragraph"),
    "undefined_style":  ("typography",   "undefined_style"),
    "attr_inherited":   ("spacing",      "paragraph_inherited"),
}


def _vm_category(key: str) -> tuple[str, str]:
    """Tentukan category/field untuk value_mismatch berdasarkan key report."""
    attr = key.split(".")[1].split(":")[0].strip() if "." in key else key
    if attr in _SECTION_ATTR_KEYS or key.lstrip().startswith("'Section"):
        return "page_layout", "section_attribute"
    spacing_attrs = {"alignment", "line_spacing", "first_line_indent", "space_before", "space_after"}
    if any(a in attr.lower() for a in spacing_attrs):
        return "spacing", "paragraph_attribute"
    return "typography", "paragraph_attribute"


def _capture_log(docx_path: Path, requirements: dict) -> str:
    """Jalankan validocx dan capture seluruh log (termasuk multi-line) ke string."""
    buf = io.StringIO()
    handler = logging.StreamHandler(buf)
    # Format HARUS cocok dengan LOG_PATTERN di debug_report.parse_entries
    # yang mengharapkan timestamp dengan millisecond: "2026-01-01 12:00:00.123 LEVEL"
    handler.setFormatter(logging.Formatter(
        "%(asctime)s.%(msecs)03d %(levelname)s (%(module)s) %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    ))

    # Attach ke root logger global agar tidak ada log validocx yang lolos.
    # Pendekatan ini sama dengan validate.py di Extractor Document aslinya.
    root = logging.getLogger()
    orig_level = root.level
    root.addHandler(handler)
    root.setLevel(logging.DEBUG)

    try:
        validocx_validate(str(docx_path), requirements)
    finally:
        root.removeHandler(handler)
        root.setLevel(orig_level)

    return buf.getvalue()


def _para_location(paragraphs: list[dict]) -> str | None:
    if not paragraphs:
        return None
    first = paragraphs[0]
    return f"Paragraf ke-{first['para_idx'] + 1} (style: {first.get('style', '?')})"


def _build_issues_checks(
    report: dict,
) -> tuple[list[ValidationIssue], list[ValidationCheckResult]]:
    """Konversi report dict dari build_report ke issues + checks."""
    issues: list[ValidationIssue] = []
    checks: list[ValidationCheckResult] = []

    # ── Section missing ──────────────────────────────────────────────────────
    for item in report["errors"].get("section_missing", []):
        msg = item.get("message", "Section attribute missing")
        issues.append(ValidationIssue(
            category="page_layout", field="section_missing",
            severity="error", message=msg,
        ))
        checks.append(ValidationCheckResult(
            category="page_layout", field="section_missing",
            status="failed", message=msg,
        ))

    # ── Value mismatch ───────────────────────────────────────────────────────
    for item in report["errors"].get("value_mismatch", []):
        key = item.get("key", "")
        count = item.get("count", 1)
        examples = item.get("examples", [])
        paras = item.get("paragraph_details", []) or item.get("paragraphs", [])
        category, field = _vm_category(key)
        location = _para_location(paras) if isinstance(paras, list) and paras and isinstance(paras[0], dict) else None

        example_str = f' Contoh: "{examples[0]}"' if examples else ""
        msg = f"{key} ({count}x mismatch).{example_str}"

        issues.append(ValidationIssue(
            category=category, field=field,
            severity="error", message=msg, location=location,
        ))
        checks.append(ValidationCheckResult(
            category=category, field=field,
            status="failed", message=msg, location=location,
        ))

    # ── Font mismatch ────────────────────────────────────────────────────────
    for item in report["errors"].get("font_mismatch", []):
        key = item.get("key", "")
        count = item.get("count", 1)
        examples = item.get("examples", [])
        paras = item.get("paragraph_details", []) or item.get("paragraphs", [])
        location = _para_location(paras) if isinstance(paras, list) and paras and isinstance(paras[0], dict) else None

        example_str = f' Contoh: "{examples[0]}"' if examples else ""
        msg = f"Font mismatch: {key} ({count}x).{example_str}"

        issues.append(ValidationIssue(
            category="typography", field="font_per_paragraph",
            severity="error", message=msg, location=location,
        ))
        checks.append(ValidationCheckResult(
            category="typography", field="font_per_paragraph",
            status="failed", message=msg, location=location,
        ))

    # ── Undefined styles ─────────────────────────────────────────────────────
    for item in report["warnings"].get("undefined_styles", []):
        style = item.get("style", "?")
        count = item.get("count", 1)
        msg = f"Style tidak terdefinisi di requirements: '{style}' ({count}x paragraf)"
        issues.append(ValidationIssue(
            category="typography", field="undefined_style",
            severity="warning", message=msg,
        ))
        checks.append(ValidationCheckResult(
            category="typography", field="undefined_style",
            status="warning", message=msg,
        ))

    # ── Attr inherited ───────────────────────────────────────────────────────
    for item in report["warnings"].get("attr_inherited", []):
        attr = item.get("attribute", "?")
        count = item.get("count", 1)
        msg = f"Atribut '{attr}' tidak di-set eksplisit (diwarisi dari Word default), {count}x"
        issues.append(ValidationIssue(
            category="spacing", field="paragraph_inherited",
            severity="warning", message=msg,
        ))
        checks.append(ValidationCheckResult(
            category="spacing", field="paragraph_inherited",
            status="warning", message=msg,
        ))

    # ── Parameter summary sebagai check passed ───────────────────────────────
    for ps in report.get("parameter_summary", []):
        if ps["status"] == "lolos semua":
            checks.append(ValidationCheckResult(
                category="typography",
                field=f"validocx_param.{ps['parameter'].replace(' ', '_')}",
                status="passed",
                message=f"{ps['parameter']}: {ps['pass']} paragraf lolos",
            ))

    # ── Summary check ────────────────────────────────────────────────────────
    s = report["summary"]
    total_err = s["total_error"]
    total_warn = s["total_warning"]
    counts_str = (
        f"{total_err} error, {total_warn} warning"
        if total_err or total_warn
        else "Semua pengecekan validocx lolos"
    )
    checks.append(ValidationCheckResult(
        category="typography",
        field="validocx_summary",
        status="passed" if not total_err and not total_warn else (
            "failed" if total_err else "warning"
        ),
        message=f"validocx: {counts_str}",
    ))

    return issues, checks


def _text_matches_case_para(para, case_style: str) -> bool:
    """Cek apakah teks paragraf sesuai case_style yang diharapkan."""
    text = para.text.strip()
    alpha = [c for c in text if c.isalpha()]
    if not alpha:
        return True

    has_all_caps = any(run.font.all_caps for run in para.runs if run.text.strip())

    if case_style == "UPPERCASE":
        return all(c.isupper() for c in alpha) or has_all_caps
    if case_style == "LOWERCASE":
        return all(c.islower() for c in alpha) and not has_all_caps
    if case_style == "SENTENCE_CASE":
        first_alpha = next((c for c in text if c.isalpha()), None)
        return first_alpha is not None and first_alpha.isupper() and not has_all_caps
    if case_style == "TOGGLE_CASE":
        return True
    return True


def _check_heading_case(
    docx_path: Path,
    metadata: DocumentMetadata,
) -> tuple[list[ValidationIssue], list[ValidationCheckResult]]:
    """Validasi style huruf (case) pada Heading 1 dan Heading 2."""
    issues: list[ValidationIssue] = []
    checks: list[ValidationCheckResult] = []

    t = metadata.typography
    if t is None:
        return issues, checks

    h1_case = t.heading_1_case
    h2_case = t.heading_2_case

    if h1_case is None and h2_case is None:
        return issues, checks

    try:
        from docx import Document as DocxDocument
        doc = DocxDocument(str(docx_path))

        h1_mismatches: list[str] = []
        h2_mismatches: list[str] = []

        for para in doc.paragraphs:
            style_name = para.style.name
            text = para.text.strip()
            if not text:
                continue
            if style_name == "Heading 1" and h1_case:
                if not _text_matches_case_para(para, h1_case):
                    h1_mismatches.append(text[:80])
            elif style_name == "Heading 2" and h2_case:
                if not _text_matches_case_para(para, h2_case):
                    h2_mismatches.append(text[:80])

        for level, case_style, mismatches in [
            (1, h1_case, h1_mismatches),
            (2, h2_case, h2_mismatches),
        ]:
            if case_style is None:
                continue
            field_name = f"heading_{level}_case"
            if mismatches:
                msg = (
                    f"Heading {level} harus {case_style}. "
                    f"{len(mismatches)} heading tidak sesuai. "
                    f'Contoh: "{mismatches[0]}"'
                )
                issues.append(ValidationIssue(
                    category="typography", field=field_name,
                    severity="error", message=msg,
                    expected=case_style, actual=mismatches[0],
                ))
                checks.append(ValidationCheckResult(
                    category="typography", field=field_name,
                    status="failed", message=msg,
                    expected=case_style, actual=mismatches[0],
                ))
            else:
                checks.append(ValidationCheckResult(
                    category="typography", field=field_name,
                    status="passed",
                    message=f"Heading {level} case {case_style}: semua sesuai",
                    expected=case_style,
                ))

    except Exception as exc:
        checks.append(ValidationCheckResult(
            category="typography", field="heading_case",
            status="skipped",
            message=f"Pengecekan case heading dilewati: {exc}",
            skip_reason=str(exc),
        ))

    return issues, checks


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
    path = Path(docx_path)
    requirements = metadata_to_requirements(metadata)
    log_text = _capture_log(path, requirements)

    entries = parse_entries(log_text)
    report = build_report(entries, docx_path=str(path))

    issues, checks = _build_issues_checks(report)
    case_issues, case_checks = _check_heading_case(path, metadata)
    return issues + case_issues, checks + case_checks
