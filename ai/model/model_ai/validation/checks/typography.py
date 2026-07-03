"""Typography checks: heading case and body content formatting. Keyword: automated document validation"""
from __future__ import annotations

from pathlib import Path

from docx import Document as DocxDocument
from docx.enum.text import WD_ALIGN_PARAGRAPH

from model_ai.extractor.models import DocumentMetadata
from model_ai.validation.models import ValidationCheckResult, ValidationIssue
from model_ai.validation.validocx_adapter import (
    _heading_level_from_style,
)

from ._shared import (
    _CAPTION_ALIGN_MAP,
    _FIG_DETECT_RE,
    _TBL_DETECT_RE,
    _LAMPIRAN_BROAD_RE,
    _TOC_TOF_STYLE_NAMES,
    _build_occurrences,
    _is_heading_para,
)


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
    doc: DocxDocument | None = None,
) -> tuple[list[ValidationIssue], list[ValidationCheckResult]]:
    """Validasi style huruf (case) pada Heading 1–5."""
    issues: list[ValidationIssue] = []
    checks: list[ValidationCheckResult] = []

    t = metadata.typography
    if t is None:
        return issues, checks

    h1_case = t.heading_1_case

    case_per_level: dict[int, str | None] = {
        1: h1_case,
        2: t.heading_2_case,
        3: t.heading_3_case,
        4: t.heading_4_case,
        5: t.heading_5_case,
    }

    if all(v is None for v in case_per_level.values()):
        return issues, checks

    try:
        doc = doc or DocxDocument(str(docx_path))

        pass_per_level:     dict[int, list[dict]] = {lvl: [] for lvl in case_per_level}
        mismatch_per_level: dict[int, list[dict]] = {lvl: [] for lvl in case_per_level}

        for idx, para in enumerate(doc.paragraphs):
            text = para.text.strip()
            if not text:
                continue
            level = _heading_level_from_style(para.style)
            if level is None or level not in case_per_level:
                continue
            case_style = case_per_level[level]
            if not case_style:
                continue
            para_info: dict = {
                "para_idx"  : idx,
                "style"     : para.style.name,
                "text"      : text[:100],
                "full_text" : text,
                "bab"       : None,
                "page"      : None,
            }
            if not _text_matches_case_para(para, case_style):
                mismatch_per_level[level].append(para_info)
            else:
                pass_per_level[level].append(para_info)

        for level, case_style in case_per_level.items():
            if case_style is None:
                continue
            field_name = f"heading_{level}_case"
            mismatches = mismatch_per_level[level]
            passes     = pass_per_level[level]

            if not mismatches and not passes:
                continue

            if mismatches:
                first_actual = mismatches[0]["text"]
                msg = (
                    f"Heading {level} harus {case_style}. "
                    f"{len(mismatches)} heading tidak sesuai. "
                    f'Contoh: "{first_actual}"'
                )
                occs = _build_occurrences(
                    mismatches, actual_str=first_actual, expected_str=case_style
                ) or None
                issues.append(ValidationIssue(
                    category="typography", field=field_name,
                    severity="error", message=msg,
                    expected=case_style, actual=first_actual,
                    occurrences=occs,
                ))
                checks.append(ValidationCheckResult(
                    category="typography", field=field_name,
                    status="failed", message=msg,
                    expected=case_style, actual=first_actual,
                    occurrences=occs,
                ))
            else:
                occs = _build_occurrences(passes, expected_str=case_style) or None
                checks.append(ValidationCheckResult(
                    category="typography", field=field_name,
                    status="passed",
                    message=f"Heading {level} case {case_style}: semua sesuai",
                    expected=case_style,
                    actual=case_style,
                    occurrences=occs,
                ))

    except Exception as exc:
        checks.append(ValidationCheckResult(
            category="typography", field="heading_case",
            status="skipped",
            message=f"Pengecekan case heading dilewati: {exc}",
            skip_reason=str(exc),
        ))

    return issues, checks


def _check_body_content(
    docx_path: Path,
    metadata: DocumentMetadata,
    doc: DocxDocument | None = None,
) -> tuple[list[ValidationIssue], list[ValidationCheckResult]]:
    """Validasi konten non-heading via content-based check.

    Iterasi SEMUA paragraf (termasuk w:sdt seperti TOC), skip heading dan semua
    jenis caption, cek alignment/font_family/font_size/line_spacing dari metadata.
    Hasil diagregasi per nilai parameter — bukan per nama style.

    Skip rules:
      - Paragraf kosong (text.strip() == "")
      - Heading: style name/inheritance mengandung 'heading' atau 'judul'
      - Caption gambar   : teks diawali 'Gambar \\d'  → dicek _check_caption_format
      - Caption tabel    : teks diawali 'Tabel \\d'   → dicek _check_caption_format
      - Caption lampiran : teks diawali 'Lampiran '   → dicek _check_figures_tables
    """
    issues: list[ValidationIssue] = []
    checks: list[ValidationCheckResult] = []

    t = metadata.typography
    _body_align_str = (metadata.spacing.paragraph_alignment if metadata.spacing else None) or "JUSTIFY"
    expected_align  = _CAPTION_ALIGN_MAP.get(_body_align_str.upper(), WD_ALIGN_PARAGRAPH.JUSTIFY)
    try:
        from model_ai.validation.validocx.wrapper import DocumentWrapper

        doc     = doc or DocxDocument(str(docx_path))
        wrapper = DocumentWrapper(doc)

        align_pass: list[dict] = []
        align_fail: list[dict] = []

        for idx, para in enumerate(wrapper.iter_paragraphs()):
            text = para.text.strip()
            if not text:
                continue
            if _is_heading_para(para):
                continue
            if para.style.name not in _TOC_TOF_STYLE_NAMES and (
                _FIG_DETECT_RE.match(text)
                or _TBL_DETECT_RE.match(text)
                or _LAMPIRAN_BROAD_RE.match(text)
            ):
                continue

            para_info: dict = {
                "para_idx" : idx,
                "style"    : para.style.name,
                "text"     : text[:100],
                "full_text": text,
                "bab"      : None,
                "page"     : None,
            }

            align = para.paragraph_format.alignment
            if align is None:
                try:
                    align = para.style.paragraph_format.alignment
                except Exception:
                    align = None
            if align is None or align == expected_align:
                align_pass.append(para_info)
            else:
                align_fail.append({**para_info, "actual": str(int(align))})

        if align_pass or align_fail:
            actual_vals = list(dict.fromkeys(d.get("actual", "?") for d in align_fail))
            actual_str  = ", ".join(str(v) for v in actual_vals[:3])
            if align_fail:
                msg = (
                    f"Alignment: {len(align_fail)} elemen tidak sesuai "
                    f"(ekspektasi: JUSTIFY). Ditemukan: {actual_str}"
                )
                occs = _build_occurrences(align_fail, actual_str=actual_str, expected_str="JUSTIFY") or None
                issues.append(ValidationIssue(
                    category="typography", field="body_alignment",
                    severity="error", message=msg,
                    expected="JUSTIFY", actual=actual_str,
                    occurrences=occs,
                ))
                checks.append(ValidationCheckResult(
                    category="typography", field="body_alignment",
                    status="failed", message=msg,
                    expected="JUSTIFY", actual=actual_str,
                    occurrences=occs,
                ))
            if align_pass:
                occs = _build_occurrences(align_pass, expected_str="JUSTIFY") or None
                checks.append(ValidationCheckResult(
                    category="typography", field="body_alignment",
                    status="passed",
                    message=f"Alignment: {len(align_pass)} elemen lolos",
                    expected="JUSTIFY", actual="JUSTIFY",
                    occurrences=occs,
                ))
    except Exception as exc:
        checks.append(ValidationCheckResult(
            category="typography", field="body_content",
            status="skipped",
            message=f"Pengecekan konten body dilewati: {exc}",
            skip_reason=str(exc),
        ))

    return issues, checks
