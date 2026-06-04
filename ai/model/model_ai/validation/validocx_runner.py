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

# Mapping teks heading ke tipe section
_HEADING_TITLE_MAP: dict[str, str] = {
    "DAFTAR ISI": "daftar_isi",
    "DAFTAR GAMBAR": "daftar_gambar",
    "DAFTAR TABEL": "daftar_tabel",
    "DAFTAR LAMPIRAN": "daftar_lampiran",
    "DAFTAR PUSTAKA": "daftar_pustaka",
    "LAMPIRAN": "lampiran",
}
_BAB_RE = re.compile(r'^BAB\s+(\d+)\b', re.IGNORECASE)
_SUB_BAB_RE = re.compile(r'^(\d+)\.(\d+)\b')
_LAMPIRAN_ITEM_RE = re.compile(r'^Lampiran\s+(\d+)\.?', re.IGNORECASE)

# Pola deteksi caption gambar/tabel
_FIG_DETECT_RE = re.compile(r'^Gambar\s+\d+', re.IGNORECASE)
_TBL_DETECT_RE = re.compile(r'^Tabel\s+\d+', re.IGNORECASE)

# Format nomor halaman
_NUM_FORMAT_DISPLAY: dict[str, str] = {
    "lowerRoman": "romawi kecil (i, ii, iii, ...)",
    "upperRoman": "romawi besar (I, II, III, ...)",
    "decimal":    "angka arab (1, 2, 3, ...)",
    "lowerLetter": "huruf kecil (a, b, c, ...)",
    "upperLetter": "huruf besar (A, B, C, ...)",
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


def _build_occurrences(
    para_details: list[dict],
    actual_str: str | None = None,
    expected_str: str | None = None,
) -> list[dict]:
    """Bangun list occurrence dari paragraph_details.

    Setiap occurrence berisi: page, bab, para_idx, style, text, actual, expected.
    para_details adalah list dict hasil _inject_para_details() yang sudah
    menyertakan field 'page' dan 'bab' dari debug_report._get_para_details().
    """
    result = []
    for detail in para_details:
        if not isinstance(detail, dict):
            continue
        result.append({
            "page"     : detail.get("page"),
            "bab"      : detail.get("bab"),
            "para_idx" : detail.get("para_idx"),
            "style"    : detail.get("style"),
            "text"     : (detail.get("text") or "")[:100],
            "actual"   : actual_str,
            "expected" : expected_str,
        })
    return result


def _build_issues_checks(
    report: dict,
    known_styles: list[str] | None = None,
) -> tuple[list[ValidationIssue], list[ValidationCheckResult]]:
    """Konversi report dict dari build_report ke issues + checks.

    known_styles: daftar style yang terdaftar di requirements (mis. ['Normal', 'Heading 1', ...]).
                  Jika diberikan, dipakai sebagai nilai 'expected' untuk warning undefined_style
                  supaya user tahu style mana yang seharusnya dipakai.
    """
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

        # Parse actual/expected dari format key: "Style.attr: actual=X expected=Y"
        vm_actual = re.search(r"actual=(\S+)", key)
        vm_expected = re.search(r"expected=(\S+)", key)
        vm_actual_str = vm_actual.group(1) if vm_actual else None
        vm_expected_str = vm_expected.group(1) if vm_expected else None

        valid_paras = paras if isinstance(paras, list) and paras and isinstance(paras[0], dict) else []
        occurrences = _build_occurrences(valid_paras, vm_actual_str, vm_expected_str) or None

        issues.append(ValidationIssue(
            category=category, field=field,
            severity="error", message=msg, location=location,
            occurrences=occurrences,
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

        # Pisahkan actual/expected dari key: "Style: actual=[X] expected=[Y]"
        fm_actual = re.search(r"actual=\[([^\]]+)\]", key)
        fm_expected = re.search(r"expected=\[([^\]]+)\]", key)
        fm_actual_str = fm_actual.group(1) if fm_actual else None
        fm_expected_str = fm_expected.group(1) if fm_expected else None

        valid_paras = paras if isinstance(paras, list) and paras and isinstance(paras[0], dict) else []
        occurrences = _build_occurrences(valid_paras, fm_actual_str, fm_expected_str) or None

        issues.append(ValidationIssue(
            category="typography", field="font_per_paragraph",
            severity="error", message=msg, location=location,
            occurrences=occurrences,
        ))
        checks.append(ValidationCheckResult(
            category="typography", field="font_per_paragraph",
            status="failed", message=msg, location=location,
        ))

    # ── Undefined styles ─────────────────────────────────────────────────────
    # Bentuk label "Seharusnya" secara dinamis dari daftar style yang dikenali requirements.
    # Jika known_styles tersedia (mis. ["Normal", "Heading 1", "Heading 2", "Heading 3"]),
    # tampilkan sebagai pilihan style yang valid. Jika tidak ada, biarkan None.
    known_styles_label = ", ".join(known_styles) if known_styles else None

    for item in report["warnings"].get("undefined_styles", []):
        style = item.get("style", "?")
        count = item.get("count", 1)
        paras = item.get("paragraph_details", []) or []
        msg = f"Style tidak terdefinisi di requirements: '{style}' ({count}x paragraf)"

        valid_paras = paras if isinstance(paras, list) and paras and isinstance(paras[0], dict) else []
        occurrences = _build_occurrences(valid_paras, actual_str=style, expected_str=known_styles_label) or None

        issues.append(ValidationIssue(
            category="typography", field="undefined_style",
            severity="warning", message=msg,
            occurrences=occurrences,
        ))
        checks.append(ValidationCheckResult(
            category="typography", field="undefined_style",
            status="warning", message=msg,
        ))

    # ── Attr inherited ───────────────────────────────────────────────────────
    for item in report["warnings"].get("attr_inherited", []):
        attr = item.get("attribute", "?")
        count = item.get("count", 1)
        paras = item.get("paragraph_details", []) or []
        msg = f"Atribut '{attr}' tidak di-set eksplisit (diwarisi dari Word default), {count}x"

        valid_paras = paras if isinstance(paras, list) and paras and isinstance(paras[0], dict) else []
        occurrences = _build_occurrences(valid_paras, actual_str="inherited", expected_str="explicit") or None

        issues.append(ValidationIssue(
            category="spacing", field="paragraph_inherited",
            severity="warning", message=msg,
            occurrences=occurrences,
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

    # Gunakan heading_1_case eksplisit jika ada; fallback dari heading_all_caps.
    h1_case = t.heading_1_case
    if h1_case is None and t.heading_all_caps is True:
        h1_case = "UPPERCASE"

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
                    severity="warning", message=msg,
                    expected=case_style, actual=mismatches[0],
                ))
                checks.append(ValidationCheckResult(
                    category="typography", field=field_name,
                    status="warning", message=msg,
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


# ─────────────────────────────────────────────────────────────────────────────
# Document Structure Check
# ─────────────────────────────────────────────────────────────────────────────

def _classify_heading(text: str) -> tuple[str | None, dict]:
    """Klasifikasi teks heading menjadi tipe section + info tambahan."""
    text_stripped = text.strip()
    text_upper = text_stripped.upper()

    if text_upper in _HEADING_TITLE_MAP:
        return _HEADING_TITLE_MAP[text_upper], {}

    m = _BAB_RE.match(text_upper)
    if m:
        return "bab", {"number": int(m.group(1))}

    m = _SUB_BAB_RE.match(text_stripped)
    if m:
        return "sub_bab", {"sub_number": f"{m.group(1)}.{m.group(2)}"}

    m = _LAMPIRAN_ITEM_RE.match(text_stripped)
    if m:
        return "item_lampiran", {"lampiran_number": f"Lampiran {m.group(1)}"}

    return None, {}


def _check_document_structure(
    docx_path: Path,
    metadata: DocumentMetadata,
) -> tuple[list[ValidationIssue], list[ValidationCheckResult]]:
    """Validasi urutan dan kehadiran section dokumen berdasarkan document_structure_proposal."""
    issues: list[ValidationIssue] = []
    checks: list[ValidationCheckResult] = []

    ds = metadata.document_structure_proposal
    if ds is None or not ds.sections:
        checks.append(ValidationCheckResult(
            category="document_structure", field="section_order",
            status="skipped",
            message="Tidak ada data document_structure_proposal di metadata",
            skip_reason="Tidak ada nilai di metadata",
        ))
        return issues, checks

    try:
        from docx import Document as DocxDocument
        doc = DocxDocument(str(docx_path))

        # Ekstrak heading dari docx dan klasifikasikan
        actual_classified: list[dict] = []
        for para in doc.paragraphs:
            style_name = para.style.name
            text = para.text.strip()
            if not text:
                continue
            if style_name not in ("Heading 1", "Heading 2", "Heading 3"):
                continue
            section_type, extra = _classify_heading(text)
            if section_type:
                actual_classified.append({"type": section_type, "text": text, **extra})

        # Ambil hanya major sections dari metadata sebagai expected order
        expected_major = [s for s in ds.sections if s.is_major_section]
        required_types = {s.type for s in expected_major if s.required is True}
        actual_types_set = {s["type"] for s in actual_classified}

        # 1. Cek section wajib hadir
        missing_required = required_types - actual_types_set
        for t in sorted(missing_required):
            expected_section = next((s for s in expected_major if s.type == t), None)
            label = expected_section.title if expected_section and expected_section.title else t
            msg = f"Section wajib '{label}' tidak ditemukan di dokumen"
            issues.append(ValidationIssue(
                category="document_structure", field="required_section",
                severity="error", message=msg, expected=t,
            ))
            checks.append(ValidationCheckResult(
                category="document_structure", field="required_section",
                status="failed", message=msg, expected=t,
            ))

        if not missing_required:
            checks.append(ValidationCheckResult(
                category="document_structure", field="required_section",
                status="passed",
                message=f"Semua section wajib ditemukan ({len(required_types)} section)",
            ))

        # 2. Cek BAB berurutan (1, 2, 3, ...)
        bab_actuals = [s for s in actual_classified if s["type"] == "bab"]
        bab_numbers = [s["number"] for s in bab_actuals if "number" in s]
        expected_bab_numbers = sorted({
            s.number for s in expected_major if s.type == "bab" and s.number is not None
        })
        if expected_bab_numbers and bab_numbers:
            if bab_numbers != sorted(bab_numbers):
                msg = f"BAB tidak berurutan. Ditemukan urutan: {bab_numbers}"
                issues.append(ValidationIssue(
                    category="document_structure", field="bab_order",
                    severity="error", message=msg,
                    expected=str(sorted(bab_numbers)), actual=str(bab_numbers),
                ))
                checks.append(ValidationCheckResult(
                    category="document_structure", field="bab_order",
                    status="failed", message=msg,
                    expected=str(sorted(bab_numbers)), actual=str(bab_numbers),
                ))
            else:
                missing_babs = set(expected_bab_numbers) - set(bab_numbers)
                if missing_babs:
                    msg = f"BAB {sorted(missing_babs)} tidak ditemukan di dokumen"
                    issues.append(ValidationIssue(
                        category="document_structure", field="bab_order",
                        severity="error", message=msg,
                        expected=str(expected_bab_numbers), actual=str(bab_numbers),
                    ))
                    checks.append(ValidationCheckResult(
                        category="document_structure", field="bab_order",
                        status="failed", message=msg,
                        expected=str(expected_bab_numbers), actual=str(bab_numbers),
                    ))
                else:
                    checks.append(ValidationCheckResult(
                        category="document_structure", field="bab_order",
                        status="passed",
                        message=f"BAB berurutan dengan benar: {bab_numbers}",
                    ))

        # 3. Cek urutan major section secara keseluruhan
        # Ambil tipe unik dari actual (pertahankan urutan kemunculan pertama)
        seen: set[str] = set()
        actual_order: list[str] = []
        for s in actual_classified:
            key = s["type"]
            if key not in seen:
                actual_order.append(key)
                seen.add(key)

        # Expected order: tipe dari major sections, deduplikasi (bab hanya sekali)
        seen = set()
        expected_order: list[str] = []
        for s in expected_major:
            key = s.type
            if key not in seen:
                expected_order.append(key)
                seen.add(key)

        # Filter expected ke yang muncul di actual
        expected_filtered = [t for t in expected_order if t in actual_types_set]
        # Filter actual ke yang ada di expected
        actual_filtered = [t for t in actual_order if t in set(expected_order)]

        if expected_filtered and actual_filtered and actual_filtered != expected_filtered:
            msg = (
                f"Urutan section tidak sesuai. "
                f"Seharusnya: {' → '.join(expected_filtered)}, "
                f"Ditemukan: {' → '.join(actual_filtered)}"
            )
            issues.append(ValidationIssue(
                category="document_structure", field="section_order",
                severity="warning", message=msg,
            ))
            checks.append(ValidationCheckResult(
                category="document_structure", field="section_order",
                status="warning", message=msg,
            ))
        elif expected_filtered:
            checks.append(ValidationCheckResult(
                category="document_structure", field="section_order",
                status="passed",
                message=f"Urutan section sesuai: {' → '.join(actual_filtered)}",
            ))

    except Exception as exc:
        checks.append(ValidationCheckResult(
            category="document_structure", field="section_order",
            status="skipped",
            message=f"Pengecekan struktur dokumen dilewati: {exc}",
            skip_reason=str(exc),
        ))

    return issues, checks


# ─────────────────────────────────────────────────────────────────────────────
# Figures & Tables Caption Check
# ─────────────────────────────────────────────────────────────────────────────

def _template_to_regex(template: str) -> re.Pattern:
    """Konversi template caption seperti 'Gambar {n}. {title}' ke regex."""
    escaped = re.escape(template)
    escaped = escaped.replace(r'\{n\}', r'\d+')
    escaped = escaped.replace(r'\{bab\}', r'\d+')
    escaped = escaped.replace(r'\{title\}', r'.+')
    return re.compile(r'^' + escaped, re.IGNORECASE)


def _para_contains_image(para) -> bool:
    """Cek apakah paragraf mengandung gambar inline."""
    from docx.oxml.ns import qn
    el = para._element
    return (
        el.find('.//' + qn('w:drawing')) is not None
        or el.find('.//' + qn('w:pict')) is not None
    )


def _build_content_elements(doc) -> tuple[list[tuple[str, object]], str]:
    """Bangun daftar elemen body yang dibatasi pada section dengan penomoran decimal.

    Urutan prioritas batas scan:
      1. Mulai dari awal section yang punya pgNumType decimal
      2. Fallback: mulai dari Heading 1 BAB pertama jika tidak ada section decimal
      3. Berhenti tepat sebelum heading DAFTAR PUSTAKA atau LAMPIRAN

    Returns:
        (elements, source) di mana source menjelaskan metode yang dipakai.
    """
    from docx.oxml.ns import qn
    body = doc.element.body
    para_by_el = {id(p._element): p for p in doc.paragraphs}
    tbl_by_el  = {id(t._element): t for t in doc.tables}

    # Satu pass: bangun daftar elemen + deteksi section break dalam setiap paragraf
    all_elements: list[tuple[str, object]] = []
    section_ends: list[tuple[int, str | None]] = []  # (element_idx, pgNumType fmt)

    for child in body:
        tag = child.tag.split('}')[-1] if '}' in child.tag else child.tag
        if tag == 'p' and id(child) in para_by_el:
            para = para_by_el[id(child)]
            idx = len(all_elements)
            all_elements.append(("para", para))
            pPr = child.find(qn('w:pPr'))
            if pPr is not None:
                sectPr = pPr.find(qn('w:sectPr'))
                if sectPr is not None:
                    section_ends.append((idx, _get_pgnum_fmt(sectPr)))
        elif tag == 'tbl' and id(child) in tbl_by_el:
            all_elements.append(("table", tbl_by_el[id(child)]))

    # Section terakhir ditandai oleh sectPr di level body
    body_sectPr = body.find(qn('w:sectPr'))
    if body_sectPr is not None:
        section_ends.append((len(all_elements) - 1, _get_pgnum_fmt(body_sectPr)))

    # Cari range section decimal (bisa lebih dari satu section berturut-turut)
    decimal_start: int | None = None
    decimal_end:   int | None = None
    prev_end = -1
    for end_idx, fmt in section_ends:
        if fmt == "decimal":
            if decimal_start is None:
                decimal_start = prev_end + 1
            decimal_end = end_idx
        prev_end = end_idx

    if decimal_start is not None and decimal_end is not None:
        candidate = all_elements[decimal_start : decimal_end + 1]
        source = "decimal_section"
    else:
        # Fallback: mulai dari BAB pertama
        bab1_idx = next(
            (i for i, (etype, elem) in enumerate(all_elements)
             if etype == "para"
             and elem.style.name == "Heading 1"
             and _BAB_RE.match((elem.text or "").strip().upper())),
            0,
        )
        candidate = all_elements[bab1_idx:]
        source = "bab1_fallback"

    # Potong sebelum DAFTAR PUSTAKA atau LAMPIRAN
    _EXCLUDED_HEADINGS = frozenset({"DAFTAR PUSTAKA", "LAMPIRAN"})
    cutoff = len(candidate)
    for i, (etype, elem) in enumerate(candidate):
        if etype == "para" and elem.style.name == "Heading 1":
            if (elem.text or "").strip().upper() in _EXCLUDED_HEADINGS:
                cutoff = i
                break

    return candidate[:cutoff], source


def _check_figures_tables(
    docx_path: Path,
    metadata: DocumentMetadata,
) -> tuple[list[ValidationIssue], list[ValidationCheckResult]]:
    """Validasi posisi caption dan format penomoran gambar/tabel."""
    issues: list[ValidationIssue] = []
    checks: list[ValidationCheckResult] = []

    ft = metadata.figures_and_tables
    if ft is None:
        checks.append(ValidationCheckResult(
            category="figures_tables", field="caption",
            status="skipped",
            message="Tidak ada data figures_and_tables di metadata",
            skip_reason="Tidak ada nilai di metadata",
        ))
        return issues, checks

    tbl_pos_exp = (ft.table_caption_position or "").upper()
    fig_pos_exp = (ft.figure_caption_position or "").upper()
    fig_fmt_tpl = ft.caption_format_figure
    tbl_fmt_tpl = ft.caption_format_table

    if not tbl_pos_exp and not fig_pos_exp and not fig_fmt_tpl and not tbl_fmt_tpl:
        checks.append(ValidationCheckResult(
            category="figures_tables", field="caption",
            status="skipped",
            message="Tidak ada aturan caption di metadata",
            skip_reason="Tidak ada nilai di metadata",
        ))
        return issues, checks

    try:
        from docx import Document as DocxDocument
        doc = DocxDocument(str(docx_path))

        fig_fmt_re = _template_to_regex(fig_fmt_tpl) if fig_fmt_tpl else None
        tbl_fmt_re = _template_to_regex(tbl_fmt_tpl) if tbl_fmt_tpl else None

        # Batasi scan hanya pada section dengan penomoran decimal,
        # kecualikan DAFTAR PUSTAKA dan LAMPIRAN.
        elements, scan_source = _build_content_elements(doc)

        fig_pos_errors: list[str] = []
        fig_fmt_errors: list[str] = []
        tbl_pos_errors: list[str] = []
        tbl_fmt_errors: list[str] = []
        fig_count = 0
        tbl_count = 0

        for i, (etype, elem) in enumerate(elements):
            if etype != "para":
                continue
            text = elem.text.strip() if hasattr(elem, 'text') and elem.text else ""
            if not text:
                continue

            if _FIG_DETECT_RE.match(text):
                fig_count += 1
                if fig_fmt_re and not fig_fmt_re.match(text):
                    fig_fmt_errors.append(text[:70])
                # Cek posisi: BELOW → gambar sebelum caption
                if fig_pos_exp == "BELOW":
                    found_img = any(
                        elements[j][0] == "para" and _para_contains_image(elements[j][1])
                        for j in range(max(0, i - 3), i)
                    )
                    if not found_img:
                        fig_pos_errors.append(f'"{text[:60]}"')
                elif fig_pos_exp == "ABOVE":
                    found_img = any(
                        elements[j][0] == "para" and _para_contains_image(elements[j][1])
                        for j in range(i + 1, min(len(elements), i + 4))
                    )
                    if not found_img:
                        fig_pos_errors.append(f'"{text[:60]}"')

            elif _TBL_DETECT_RE.match(text):
                tbl_count += 1
                if tbl_fmt_re and not tbl_fmt_re.match(text):
                    tbl_fmt_errors.append(text[:70])
                # Cek posisi: ABOVE → tabel setelah caption
                if tbl_pos_exp == "ABOVE":
                    next_is_tbl = i + 1 < len(elements) and elements[i + 1][0] == "table"
                    if not next_is_tbl:
                        tbl_pos_errors.append(f'"{text[:60]}"')
                elif tbl_pos_exp == "BELOW":
                    prev_is_tbl = i > 0 and elements[i - 1][0] == "table"
                    if not prev_is_tbl:
                        tbl_pos_errors.append(f'"{text[:60]}"')

        # Gambar — tidak ditemukan sama sekali dalam area yang di-scan
        if fig_count == 0 and tbl_count == 0:
            scan_label = (
                "section dengan nomor halaman angka arab"
                if scan_source == "decimal_section"
                else "mulai BAB 1 (fallback — section decimal tidak ditemukan)"
            )
            checks.append(ValidationCheckResult(
                category="figures_tables", field="caption",
                status="skipped",
                message=f"Tidak ditemukan caption gambar atau tabel di area scan: {scan_label}",
                skip_reason="Tidak ada caption terdeteksi",
            ))
            return issues, checks

        # Report gambar
        if fig_count > 0:
            if fig_pos_errors:
                msg = (
                    f"Caption gambar seharusnya {fig_pos_exp} gambar. "
                    f"{len(fig_pos_errors)}x salah posisi. "
                    f"Contoh: {fig_pos_errors[0]}"
                )
                issues.append(ValidationIssue(
                    category="figures_tables", field="figure_caption_position",
                    severity="warning", message=msg, expected=fig_pos_exp,
                ))
                checks.append(ValidationCheckResult(
                    category="figures_tables", field="figure_caption_position",
                    status="warning", message=msg, expected=fig_pos_exp,
                ))
            else:
                checks.append(ValidationCheckResult(
                    category="figures_tables", field="figure_caption_position",
                    status="passed",
                    message=f"Posisi caption gambar ({fig_pos_exp}): {fig_count} caption sesuai",
                    expected=fig_pos_exp,
                ))

            if fig_fmt_re:
                if fig_fmt_errors:
                    msg = (
                        f"Format caption gambar tidak sesuai pola '{fig_fmt_tpl}'. "
                        f"{len(fig_fmt_errors)}x salah format. "
                        f"Contoh: \"{fig_fmt_errors[0]}\""
                    )
                    issues.append(ValidationIssue(
                        category="figures_tables", field="figure_caption_format",
                        severity="warning", message=msg,
                        expected=fig_fmt_tpl, actual=fig_fmt_errors[0],
                    ))
                    checks.append(ValidationCheckResult(
                        category="figures_tables", field="figure_caption_format",
                        status="warning", message=msg,
                        expected=fig_fmt_tpl, actual=fig_fmt_errors[0],
                    ))
                else:
                    checks.append(ValidationCheckResult(
                        category="figures_tables", field="figure_caption_format",
                        status="passed",
                        message=f"Format caption gambar '{fig_fmt_tpl}': {fig_count} caption sesuai",
                        expected=fig_fmt_tpl,
                    ))

        # Report tabel
        if tbl_count > 0:
            if tbl_pos_errors:
                msg = (
                    f"Caption tabel seharusnya {tbl_pos_exp} tabel. "
                    f"{len(tbl_pos_errors)}x salah posisi. "
                    f"Contoh: {tbl_pos_errors[0]}"
                )
                issues.append(ValidationIssue(
                    category="figures_tables", field="table_caption_position",
                    severity="error", message=msg, expected=tbl_pos_exp,
                ))
                checks.append(ValidationCheckResult(
                    category="figures_tables", field="table_caption_position",
                    status="failed", message=msg, expected=tbl_pos_exp,
                ))
            else:
                checks.append(ValidationCheckResult(
                    category="figures_tables", field="table_caption_position",
                    status="passed",
                    message=f"Posisi caption tabel ({tbl_pos_exp}): {tbl_count} caption sesuai",
                    expected=tbl_pos_exp,
                ))

            if tbl_fmt_re:
                if tbl_fmt_errors:
                    msg = (
                        f"Format caption tabel tidak sesuai pola '{tbl_fmt_tpl}'. "
                        f"{len(tbl_fmt_errors)}x salah format. "
                        f"Contoh: \"{tbl_fmt_errors[0]}\""
                    )
                    issues.append(ValidationIssue(
                        category="figures_tables", field="table_caption_format",
                        severity="warning", message=msg,
                        expected=tbl_fmt_tpl, actual=tbl_fmt_errors[0],
                    ))
                    checks.append(ValidationCheckResult(
                        category="figures_tables", field="table_caption_format",
                        status="warning", message=msg,
                        expected=tbl_fmt_tpl, actual=tbl_fmt_errors[0],
                    ))
                else:
                    checks.append(ValidationCheckResult(
                        category="figures_tables", field="table_caption_format",
                        status="passed",
                        message=f"Format caption tabel '{tbl_fmt_tpl}': {tbl_count} caption sesuai",
                        expected=tbl_fmt_tpl,
                    ))

    except Exception as exc:
        checks.append(ValidationCheckResult(
            category="figures_tables", field="caption",
            status="skipped",
            message=f"Pengecekan caption dilewati: {exc}",
            skip_reason=str(exc),
        ))

    return issues, checks


# ─────────────────────────────────────────────────────────────────────────────
# Page Numbering Check
# ─────────────────────────────────────────────────────────────────────────────

def _get_pgnum_fmt(sectPr) -> str | None:
    """Ambil format nomor halaman dari elemen sectPr (w:pgNumType w:fmt)."""
    from docx.oxml.ns import qn
    pgNumType = sectPr.find(qn('w:pgNumType'))
    if pgNumType is not None:
        return pgNumType.get(qn('w:fmt'))
    return None


def _hdrftr_has_page_field(hdrftr) -> bool:
    """Cek apakah header/footer mengandung field PAGE."""
    from docx.oxml.ns import qn
    if hdrftr is None:
        return False
    for instrText in hdrftr._element.iter(qn('w:instrText')):
        if 'PAGE' in (instrText.text or '').upper():
            return True
    return False


def _check_numbering(
    docx_path: Path,
    metadata: DocumentMetadata,
) -> tuple[list[ValidationIssue], list[ValidationCheckResult]]:
    """Validasi format dan posisi nomor halaman (preliminary vs content)."""
    issues: list[ValidationIssue] = []
    checks: list[ValidationCheckResult] = []

    num = metadata.numbering
    if num is None:
        checks.append(ValidationCheckResult(
            category="numbering", field="page_number",
            status="skipped",
            message="Tidak ada data numbering di metadata",
            skip_reason="Tidak ada nilai di metadata",
        ))
        return issues, checks

    prelim = num.preliminary
    content = num.content

    if prelim is None and content is None:
        checks.append(ValidationCheckResult(
            category="numbering", field="page_number",
            status="skipped",
            message="Data preliminary dan content numbering kosong di metadata",
            skip_reason="Tidak ada nilai di metadata",
        ))
        return issues, checks

    try:
        from docx import Document as DocxDocument
        doc = DocxDocument(str(docx_path))

        # Kumpulkan info tiap section: format nomor halaman + letak (header/footer)
        section_infos: list[dict] = []
        for section in doc.sections:
            fmt = _get_pgnum_fmt(section._sectPr)

            has_header_page = False
            has_footer_page = False
            try:
                if not section.header_is_linked_to_previous:
                    has_header_page = _hdrftr_has_page_field(section.header)
            except Exception:
                pass
            try:
                if not section.footer_is_linked_to_previous:
                    has_footer_page = _hdrftr_has_page_field(section.footer)
            except Exception:
                pass

            section_infos.append({
                "fmt": fmt,
                "has_header_page": has_header_page,
                "has_footer_page": has_footer_page,
                "has_any_page": has_header_page or has_footer_page,
            })

        all_formats = {s["fmt"] for s in section_infos if s["fmt"]}

        # ── Preliminary (romawi) ──────────────────────────────────────────────
        if prelim:
            exp_fmt = prelim.format  # e.g. "lowerRoman"
            exp_loc = (prelim.location or "").upper()  # "HEADER" atau "FOOTER"
            exp_start = prelim.start_at_section  # e.g. "daftar_isi"

            prelim_sections = [s for s in section_infos if s["fmt"] == exp_fmt]
            wrong_fmt_sections = [
                s for s in section_infos
                if s["has_any_page"] and s["fmt"] not in (exp_fmt, content.format if content else None)
            ]

            if prelim_sections:
                checks.append(ValidationCheckResult(
                    category="numbering", field="preliminary_format",
                    status="passed",
                    message=(
                        f"Format nomor halaman preliminary '{exp_fmt}' "
                        f"({_NUM_FORMAT_DISPLAY.get(exp_fmt, exp_fmt)}): "
                        f"ditemukan di {len(prelim_sections)} section"
                    ),
                    expected=exp_fmt,
                ))
                # Cek lokasi
                if exp_loc in ("HEADER", "FOOTER"):
                    loc_ok = [
                        s for s in prelim_sections
                        if (exp_loc == "HEADER" and s["has_header_page"])
                        or (exp_loc == "FOOTER" and s["has_footer_page"])
                    ]
                    loc_wrong = [
                        s for s in prelim_sections
                        if s["has_any_page"] and s not in loc_ok
                    ]
                    if loc_wrong:
                        msg = (
                            f"Nomor halaman preliminary seharusnya di {exp_loc}. "
                            f"{len(loc_wrong)} section menggunakan lokasi berbeda."
                        )
                        issues.append(ValidationIssue(
                            category="numbering", field="preliminary_location",
                            severity="warning", message=msg, expected=exp_loc,
                        ))
                        checks.append(ValidationCheckResult(
                            category="numbering", field="preliminary_location",
                            status="warning", message=msg, expected=exp_loc,
                        ))
                    elif loc_ok:
                        checks.append(ValidationCheckResult(
                            category="numbering", field="preliminary_location",
                            status="passed",
                            message=f"Lokasi nomor halaman preliminary ({exp_loc}): sesuai",
                            expected=exp_loc,
                        ))
            else:
                # Format preliminary tidak ditemukan sama sekali
                found_fmts = sorted(all_formats)
                msg = (
                    f"Format nomor halaman preliminary '{exp_fmt}' "
                    f"({_NUM_FORMAT_DISPLAY.get(exp_fmt, exp_fmt)}) tidak ditemukan. "
                    + (f"Format yang ada: {found_fmts}" if found_fmts else "Tidak ada nomor halaman terdeteksi.")
                )
                issues.append(ValidationIssue(
                    category="numbering", field="preliminary_format",
                    severity="error", message=msg,
                    expected=exp_fmt,
                    actual=str(found_fmts[0]) if found_fmts else None,
                ))
                checks.append(ValidationCheckResult(
                    category="numbering", field="preliminary_format",
                    status="failed", message=msg,
                    expected=exp_fmt,
                    actual=str(found_fmts[0]) if found_fmts else None,
                ))

            # Cek titik mulai: verifikasi section start_at_section ada di dokumen
            if exp_start:
                _check_start_section(exp_start, doc, issues, checks, zone="preliminary")

        # ── Content (angka arab) ──────────────────────────────────────────────
        if content:
            exp_fmt = content.format  # e.g. "decimal"
            exp_loc = (content.location or "").upper()
            exp_start = content.start_at_section  # e.g. "bab_1"

            content_sections = [s for s in section_infos if s["fmt"] == exp_fmt]

            if content_sections:
                checks.append(ValidationCheckResult(
                    category="numbering", field="content_format",
                    status="passed",
                    message=(
                        f"Format nomor halaman isi '{exp_fmt}' "
                        f"({_NUM_FORMAT_DISPLAY.get(exp_fmt, exp_fmt)}): "
                        f"ditemukan di {len(content_sections)} section"
                    ),
                    expected=exp_fmt,
                ))
                # Cek lokasi
                if exp_loc in ("HEADER", "FOOTER"):
                    loc_ok = [
                        s for s in content_sections
                        if (exp_loc == "HEADER" and s["has_header_page"])
                        or (exp_loc == "FOOTER" and s["has_footer_page"])
                    ]
                    loc_wrong = [
                        s for s in content_sections
                        if s["has_any_page"] and s not in loc_ok
                    ]
                    if loc_wrong:
                        msg = (
                            f"Nomor halaman isi seharusnya di {exp_loc}. "
                            f"{len(loc_wrong)} section menggunakan lokasi berbeda."
                        )
                        issues.append(ValidationIssue(
                            category="numbering", field="content_location",
                            severity="warning", message=msg, expected=exp_loc,
                        ))
                        checks.append(ValidationCheckResult(
                            category="numbering", field="content_location",
                            status="warning", message=msg, expected=exp_loc,
                        ))
                    elif loc_ok:
                        checks.append(ValidationCheckResult(
                            category="numbering", field="content_location",
                            status="passed",
                            message=f"Lokasi nomor halaman isi ({exp_loc}): sesuai",
                            expected=exp_loc,
                        ))
            else:
                found_fmts = sorted(all_formats)
                msg = (
                    f"Format nomor halaman isi '{exp_fmt}' "
                    f"({_NUM_FORMAT_DISPLAY.get(exp_fmt, exp_fmt)}) tidak ditemukan. "
                    + (f"Format yang ada: {found_fmts}" if found_fmts else "Tidak ada nomor halaman terdeteksi.")
                )
                issues.append(ValidationIssue(
                    category="numbering", field="content_format",
                    severity="error", message=msg,
                    expected=exp_fmt,
                    actual=str(found_fmts[0]) if found_fmts else None,
                ))
                checks.append(ValidationCheckResult(
                    category="numbering", field="content_format",
                    status="failed", message=msg,
                    expected=exp_fmt,
                    actual=str(found_fmts[0]) if found_fmts else None,
                ))

            if exp_start:
                _check_start_section(exp_start, doc, issues, checks, zone="content")

    except Exception as exc:
        checks.append(ValidationCheckResult(
            category="numbering", field="page_number",
            status="skipped",
            message=f"Pengecekan nomor halaman dilewati: {exc}",
            skip_reason=str(exc),
        ))

    return issues, checks


def _check_start_section(
    start_at: str,
    doc,
    issues: list[ValidationIssue],
    checks: list[ValidationCheckResult],
    zone: str,
) -> None:
    """Verifikasi bahwa titik mulai penomoran (start_at_section) ada di dokumen."""
    # "bab_1" → BAB 1, "daftar_isi" → heading DAFTAR ISI, dst.
    bab_m = re.match(r'^bab_(\d+)$', start_at, re.IGNORECASE)
    if bab_m:
        target_num = int(bab_m.group(1))
        found = any(
            para.style.name == "Heading 1"
            and bool(_BAB_RE.match(para.text.strip().upper()))
            and int((_BAB_RE.match(para.text.strip().upper()) or re.match(r'(\d+)', '0')).group(1)) == target_num
            for para in doc.paragraphs
            if para.text.strip()
        )
        label = f"BAB {target_num}"
    else:
        # Cari heading yang cocok dengan tipe section
        title_map_inv = {v: k for k, v in _HEADING_TITLE_MAP.items()}
        expected_title = title_map_inv.get(start_at, start_at.upper().replace("_", " "))
        found = any(
            para.style.name == "Heading 1"
            and para.text.strip().upper() == expected_title
            for para in doc.paragraphs
        )
        label = expected_title

    field = f"{zone}_start"
    if found:
        checks.append(ValidationCheckResult(
            category="numbering", field=field,
            status="passed",
            message=f"Titik mulai nomor halaman {zone}: '{label}' ditemukan di dokumen",
            expected=start_at,
        ))
    else:
        issues.append(ValidationIssue(
            category="numbering", field=field,
            severity="warning",
            message=f"Titik mulai nomor halaman {zone} '{label}' tidak ditemukan di dokumen",
            expected=start_at,
        ))
        checks.append(ValidationCheckResult(
            category="numbering", field=field,
            status="warning",
            message=f"Titik mulai nomor halaman {zone} '{label}' tidak ditemukan di dokumen",
            expected=start_at,
        ))


# ─────────────────────────────────────────────────────────────────────────────
# Main entry point
# ─────────────────────────────────────────────────────────────────────────────

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

    # Ekstrak daftar style yang dikenali dari requirements untuk ditampilkan
    # sebagai nilai "Seharusnya" pada warning undefined_style.
    # Contoh hasil: ["Normal", "Heading 1", "Heading 2", "Heading 3"]
    known_styles = list(requirements.get("styles", {}).keys())

    issues, checks = _build_issues_checks(report, known_styles=known_styles)
    case_issues, case_checks = _check_heading_case(path, metadata)
    struct_issues, struct_checks = _check_document_structure(path, metadata)
    fig_issues, fig_checks = _check_figures_tables(path, metadata)
    num_issues, num_checks = _check_numbering(path, metadata)

    all_issues = issues + case_issues + struct_issues + fig_issues + num_issues
    all_checks = checks + case_checks + struct_checks + fig_checks + num_checks
    return all_issues, all_checks
