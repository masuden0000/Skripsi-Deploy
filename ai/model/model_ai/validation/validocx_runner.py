"""Runner validocx — satu-satunya engine validasi per-paragraf.

Posisi pipeline: payload (DocumentMetadata) → adapter → validocx.validate() →
parse_entries/build_report → ValidationIssue + ValidationCheckResult.
"""
import io
import logging
import re
from pathlib import Path

from docx import Document as DocxDocument
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml.ns import qn

from model_ai.extractor.models import DocumentMetadata
from model_ai.validation.models import ValidationCheckResult, ValidationIssue
from model_ai.validation.validocx.validator import validate as validocx_validate
from model_ai.validation.validocx.debug_report import parse_entries, build_report, count_body_pages
from model_ai.validation.validocx_adapter import (
    enrich_requirements_with_docx_styles,
    metadata_to_requirements,
)


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
# Default: wajib ada titik+spasi setelah nomor ("Lampiran 1. Judul").
# Diperbarui secara dinamis via _build_lampiran_re() saat metadata tersedia.
_LAMPIRAN_ITEM_RE = re.compile(r'^Lampiran\s+\d+\.\s', re.IGNORECASE)
# Broad: menangkap SEMUA paragraf berawalan "Lampiran <angka>" (dipakai _check_lampiran_format)
_LAMPIRAN_BROAD_RE = re.compile(r'^Lampiran\s+\d+', re.IGNORECASE)

# Inverse dari _HEADING_TITLE_MAP: tipe section → teks heading
_HEADING_TITLE_MAP_INV: dict[str, str] = {v: k for k, v in _HEADING_TITLE_MAP.items()}

# Regex per tipe section untuk deteksi halaman pertama di _check_page_count
_SECTION_HEADING_MAP: dict[str, re.Pattern] = {
    "bab":            _BAB_RE,
    "daftar_isi":     re.compile(r"^DAFTAR\s+ISI$",       re.IGNORECASE),
    "daftar_gambar":  re.compile(r"^DAFTAR\s+GAMBAR$",     re.IGNORECASE),
    "daftar_tabel":   re.compile(r"^DAFTAR\s+TABEL$",      re.IGNORECASE),
    "daftar_lampiran":re.compile(r"^DAFTAR\s+LAMPIRAN$",   re.IGNORECASE),
    "daftar_pustaka": re.compile(r"^DAFTAR\s+PUSTAKA$",    re.IGNORECASE),
    "lampiran":       re.compile(r"^LAMPIRAN$",             re.IGNORECASE),
}


def _build_lampiran_re(separator: str | None) -> re.Pattern:
    """Bangun regex deteksi judul lampiran berdasarkan separator dari metadata.

    separator="."  → r'^Lampiran\\s+\\d+\\.\\s'   ("Lampiran 1. Judul")
    separator=""   → r'^Lampiran\\s+\\d+\\s'        ("Lampiran 1 Judul")
    separator=None → pakai default (titik)
    """
    sep = separator if separator is not None else "."
    if sep:
        escaped = re.escape(sep)
        pattern = rf'^Lampiran\s+\d+{escaped}\s'
    else:
        pattern = r'^Lampiran\s+\d+\s'
    return re.compile(pattern, re.IGNORECASE)

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

# ── Human-readable labels untuk nilai atribut ─────────────────────────────────
# Alignment: python-docx WD_ALIGN_PARAGRAPH integer → label Indonesia
_ALIGNMENT_LABELS: dict[str, str] = {
    "0": "rata kiri (LEFT)",
    "1": "rata tengah (CENTER)",
    "2": "rata kanan (RIGHT)",
    "3": "rata kanan-kiri (JUSTIFY)",
    # Nama enum (kadang muncul di actual)
    "LEFT":    "rata kiri (LEFT)",
    "CENTER":  "rata tengah (CENTER)",
    "RIGHT":   "rata kanan (RIGHT)",
    "JUSTIFY": "rata kanan-kiri (JUSTIFY)",
}

# Line spacing: float string → label
_LINE_SPACING_LABELS: dict[str, str] = {
    "1.0":  "1.0 (spasi tunggal)",
    "1.15": "1.15",
    "1.5":  "1.5 (satu setengah)",
    "2.0":  "2.0 (spasi ganda)",
}


def _humanize_attr_value(attr_name: str, raw_value: str | None) -> str | None:
    """Konversi nilai atribut mentah ke label yang mudah dibaca manusia.

    Contoh:
        _humanize_attr_value("alignment", "1")    → "rata tengah (CENTER)"
        _humanize_attr_value("alignment", "JUSTIFY") → "rata kanan-kiri (JUSTIFY)"
        _humanize_attr_value("line_spacing", "1.15") → "1.15"
        _humanize_attr_value("font_size", "12")   → "12"
    """
    if raw_value is None:
        return None
    key = raw_value.strip().upper()
    attr_lower = (attr_name or "").lower()

    if "alignment" in attr_lower:
        # Coba match numeric (0-3) atau nama enum
        label = _ALIGNMENT_LABELS.get(raw_value.strip()) or _ALIGNMENT_LABELS.get(key)
        if label:
            return label

    if "line_spacing" in attr_lower or "spacing" in attr_lower:
        # Bulatkan ke 2 desimal untuk lookup
        try:
            rounded = f"{float(raw_value.strip()):.2f}".rstrip("0").rstrip(".")
            label = _LINE_SPACING_LABELS.get(rounded) or _LINE_SPACING_LABELS.get(raw_value.strip())
            if label:
                return label
        except ValueError:
            pass

    return raw_value


def _vm_category(key: str) -> tuple[str, str]:
    """Tentukan category/field untuk value_mismatch berdasarkan key report."""
    attr = key.split(".")[1].split(":")[0].strip() if "." in key else key
    if attr in _SECTION_ATTR_KEYS or key.lstrip().startswith("'Section"):
        return "page_layout", "section_attribute"
    spacing_attrs = {"alignment", "line_spacing", "space_before", "space_after"}
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
    return f"Elemen ke-{first['para_idx'] + 1} (style: {first.get('style', '?')})"


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
        # Lewati paragraf kosong (misal heading tanpa teks yang tidak sengaja diberi style)
        if not (detail.get("text") or "").strip():
            continue
        result.append({
            "page"      : detail.get("page"),
            "bab"       : detail.get("bab"),
            "para_idx"  : detail.get("para_idx"),
            "style"     : detail.get("style"),
            "text"      : (detail.get("text") or "")[:100],
            "full_text" : detail.get("full_text") or "",
            "actual"    : actual_str,
            "expected"  : expected_str,
        })
    return result


def _coerce_paras(paras) -> list[dict]:
    """Kembalikan paras sebagai list[dict] yang valid, atau [] jika bukan."""
    return paras if isinstance(paras, list) and paras and isinstance(paras[0], dict) else []


_ALIGN_LABEL: dict[int, str] = {0: "LEFT", 1: "CENTER", 2: "RIGHT", 3: "JUSTIFY"}


def _lookup_expected(requirements: dict, param: str, style: str) -> str | None:
    """Ambil nilai expected untuk satu parameter dari requirements dict.

    Dipakai saat membangun passed checks agar field 'expected' terisi
    dan bisa ditampilkan di frontend section Lulus.

    Jika style tidak terdaftar di requirements (mis. 'List Paragraph',
    'table of figures'), gunakan 'Normal' sebagai fallback — sesuai perilaku
    validator.py yang melakukan hal yang sama saat memvalidasi paragraf.
    """
    styles = requirements.get("styles", {})
    style_req = styles.get(style)
    if not isinstance(style_req, dict):
        # Fallback ke Normal — validator.py juga pakai Normal untuk style tak dikenal
        style_req = styles.get("Normal")
    if not isinstance(style_req, dict):
        return None

    if param == "alignment":
        attrs = style_req.get("paragraph", {}).get("attributes", {})
        val = attrs.get("alignment") if isinstance(attrs, dict) else None
        return _ALIGN_LABEL.get(val) if val is not None else None

    if param == "line_spacing":
        attrs = style_req.get("paragraph", {}).get("attributes", {})
        val = attrs.get("line_spacing") if isinstance(attrs, dict) else None
        return str(val) if val is not None else None

    if param == "font":
        font_attrs = style_req.get("font", {}).get("attributes") or []
        if font_attrs:
            return ", ".join(str(a) for a in font_attrs if a is not None)
        return None

    return None


def _normal_formatting_label(requirements: dict) -> str | None:
    """Bangun label human-readable dari nilai formatting style Normal.

    Dipakai sebagai 'expected' pada warning undefined_style agar reviewer tahu
    nilai yang seharusnya ada pada paragraf (mengacu aturan Normal sebagai fallback).

    Contoh output: "Font: 12pt Times New Roman | Spasi: 1.15 | Rata: JUSTIFY"
    """
    normal = requirements.get("styles", {}).get("Normal")
    if not isinstance(normal, dict):
        return None

    parts: list[str] = []

    # ── Font ──────────────────────────────────────────────────────────────────
    font_block = normal.get("font", {})
    font_size  = font_block.get("size")
    font_name  = font_block.get("name")
    if font_size or font_name:
        font_str = "Font:"
        if font_size:
            font_str += f" {font_size}pt"
        if font_name:
            font_str += f" {font_name}"
        parts.append(font_str)

    # ── Line spacing ──────────────────────────────────────────────────────────
    para_attrs = normal.get("paragraph", {}).get("attributes", {})
    if isinstance(para_attrs, dict):
        ls = para_attrs.get("line_spacing")
        if ls is not None:
            parts.append(f"Spasi: {ls}")

        # ── Alignment ─────────────────────────────────────────────────────────
        align = para_attrs.get("alignment")
        if align is not None:
            label = _ALIGN_LABEL.get(align, str(align))
            parts.append(f"Rata: {label}")

    return " | ".join(parts) if parts else None


def _build_issues_checks(
    report: dict,
    known_styles: list[str] | None = None,
    requirements: dict | None = None,
) -> tuple[list[ValidationIssue], list[ValidationCheckResult]]:
    """Konversi report dict dari build_report ke issues + checks.

    known_styles:  daftar style yang terdaftar di requirements (mis. ['Normal', 'Heading 1', ...]).
                   Jika diberikan, dipakai sebagai nilai 'expected' untuk warning undefined_style
                   supaya user tahu style mana yang seharusnya dipakai.
    requirements:  dict requirements lengkap (dari metadata_to_requirements). Jika diberikan,
                   dipakai untuk mengisi field 'expected' pada passed checks sehingga
                   frontend section Lulus bisa menampilkan nilai yang diharapkan.
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
        vm_actual_raw = vm_actual.group(1) if vm_actual else None
        vm_expected_raw = vm_expected.group(1) if vm_expected else None

        # Ekstrak nama atribut dari key (mis. "Heading 2.alignment: ..." → "alignment")
        attr_match = re.search(r"\.(\w+)\s*:", key)
        attr_name = attr_match.group(1) if attr_match else ""

        # Konversi ke label yang mudah dibaca (mis. "1" → "rata tengah (CENTER)")
        vm_actual_str   = _humanize_attr_value(attr_name, vm_actual_raw)
        vm_expected_str = _humanize_attr_value(attr_name, vm_expected_raw)

        valid_paras = _coerce_paras(paras)
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

        valid_paras = _coerce_paras(paras)
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
    # Nilai "Seharusnya" pada occurrence undefined_style menggunakan nilai formatting
    # dari style Normal (fallback yang juga dipakai validator.py), bukan daftar nama style.
    # Contoh: "Font: 12pt Times New Roman | Spasi: 1.15 | Rata: JUSTIFY"
    normal_fmt_label = _normal_formatting_label(requirements) if requirements else None

    for item in report["warnings"].get("undefined_styles", []):
        style = item.get("style", "?")
        count = item.get("count", 1)
        paras = item.get("paragraph_details", []) or []
        msg = f"Style tidak terdefinisi di requirements: '{style}' ({count}x elemen)"

        valid_paras = _coerce_paras(paras)
        occurrences = _build_occurrences(valid_paras, actual_str=style, expected_str=normal_fmt_label) or None

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

        valid_paras = _coerce_paras(paras)
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
        if ps["status"] in ("lolos semua", "lolos semua (ada inherited)"):
            raw_details = ps.get("paragraph_details_pass", [])
            occs = _build_occurrences(raw_details) or None

            # Cari expected value dari requirements: "param (Style Name)" → parse → lookup
            expected_val: str | None = None
            if requirements:
                m = re.match(r'^(\S+)\s+\((.+)\)$', ps["parameter"])
                if m:
                    expected_val = _lookup_expected(requirements, m.group(1), m.group(2))

            checks.append(ValidationCheckResult(
                category="typography",
                field=f"validocx_param.{ps['parameter'].replace(' ', '_')}",
                status="passed",
                message=f"{ps['parameter']}: {ps['pass']} elemen lolos",
                expected=expected_val,
                actual=expected_val,  # sama dengan expected karena semua lolos
                occurrences=occs,
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
    """Validasi style huruf (case) pada Heading 1–5."""
    issues: list[ValidationIssue] = []
    checks: list[ValidationCheckResult] = []

    t = metadata.typography
    if t is None:
        return issues, checks

    h1_case = t.heading_1_case

    # H2–H5 tidak ada fallback, hanya dari field eksplisit.
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
        doc = DocxDocument(str(docx_path))

        mismatches_per_level: dict[int, list[str]] = {lvl: [] for lvl in case_per_level}

        for para in doc.paragraphs:
            style_name = para.style.name
            text = para.text.strip()
            if not text:
                continue
            for level in range(1, 6):
                case_style = case_per_level[level]
                if case_style and style_name == f"Heading {level}":
                    if not _text_matches_case_para(para, case_style):
                        mismatches_per_level[level].append(text[:80])
                    break

        for level, case_style in case_per_level.items():
            if case_style is None:
                continue
            field_name = f"heading_{level}_case"
            mismatches = mismatches_per_level[level]
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
                severity="error", message=msg, expected=label,
            ))
            checks.append(ValidationCheckResult(
                category="document_structure", field="required_section",
                status="failed", message=msg, expected=label,
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
                        expected=str(expected_bab_numbers),
                        actual=str(bab_numbers),
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
                expected=' → '.join(expected_filtered),
                actual=' → '.join(actual_filtered),
            ))
            checks.append(ValidationCheckResult(
                category="document_structure", field="section_order",
                status="warning", message=msg,
                expected=' → '.join(expected_filtered),
                actual=' → '.join(actual_filtered),
            ))
        elif expected_filtered:
            checks.append(ValidationCheckResult(
                category="document_structure", field="section_order",
                status="passed",
                message=f"Urutan section sesuai: {' → '.join(actual_filtered)}",
                expected=' → '.join(expected_filtered),
                actual=' → '.join(actual_filtered),
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
    """Konversi template caption seperti 'Gambar {n}. {title}' ke regex.

    Titik (.) yang memisahkan nomor bab/urutan diizinkan diikuti spasi opsional,
    sehingga '4.1.' dan '4. 1.' sama-sama diterima.
    """
    escaped = re.escape(template)
    escaped = escaped.replace(r'\{n\}', r'\d+')
    escaped = escaped.replace(r'\{bab\}', r'\d+')
    escaped = escaped.replace(r'\{title\}', r'.+')
    # Izinkan spasi opsional setelah setiap titik literal agar format
    # "4.1." maupun "4. 1." sama-sama cocok dengan pola.
    escaped = escaped.replace(r'\.', r'\.\s*')
    return re.compile(r'^' + escaped, re.IGNORECASE)


def _para_contains_image(para) -> bool:
    """Cek apakah paragraf mengandung gambar inline."""
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


def _check_lampiran_format(
    docx_path: Path,
    metadata: DocumentMetadata,
) -> tuple[list[ValidationIssue], list[ValidationCheckResult]]:
    """Validasi judul lampiran via text-pattern, bukan style name.

    Judul lampiran dideteksi dari teks yang diawali 'Lampiran <angka>'.
    Aturan: sama dengan body (font family, font size, line spacing, alignment JUSTIFY).
    Berlaku sebagai contingency jika style tidak bernama eksplisit 'Lampiran'.
    """
    issues: list[ValidationIssue] = []
    checks: list[ValidationCheckResult] = []

    t = metadata.typography
    s = metadata.spacing
    ds = metadata.document_structure_proposal
    expected_font    = t.font_family if t else None
    expected_size    = int(t.font_size_body_pt) if t and t.font_size_body_pt else None
    expected_spacing = float(s.line_spacing) if s and s.line_spacing else None

    # Separator dari payload; None → default "."
    separator = ds.lampiran_heading_separator if ds else None
    effective_sep = separator if separator is not None else "."

    # Regex format yang DIHARAPKAN (dari metadata)
    lampiran_re = _build_lampiran_re(effective_sep)

    try:
        doc = DocxDocument(str(docx_path))

        wrong_alignment:  list[str] = []
        wrong_font:       list[str] = []
        wrong_size:       list[str] = []
        wrong_spacing:    list[str] = []
        wrong_separator:  list[str] = []
        total = 0

        for para in doc.paragraphs:
            text = para.text.strip()
            if not text or not _LAMPIRAN_BROAD_RE.match(text):
                continue

            # ── Cek format separator ──────────────────────────────────────────
            # Semua paragraf "Lampiran \d+..." dicek, termasuk style "Lampiran",
            # karena format heading adalah tanggung jawab penulis dokumen.
            if not lampiran_re.match(text):
                wrong_separator.append(text[:70])

            # Untuk cek atribut: skip style "Lampiran" eksplisit (dicek engine)
            if para.style.name == "Lampiran":
                continue

            total += 1

            # ── Alignment harus JUSTIFY ───────────────────────────────────────
            align = para.paragraph_format.alignment
            if align is None:
                try:
                    align = para.style.paragraph_format.alignment
                except Exception:
                    align = None
            if align is not None and align != WD_ALIGN_PARAGRAPH.JUSTIFY:
                wrong_alignment.append(text[:70])

            # ── Font & size ───────────────────────────────────────────────────
            for run in para.runs:
                if expected_font and run.font.name and run.font.name != expected_font:
                    wrong_font.append(text[:70])
                    break
                if expected_size and run.font.size:
                    if round(run.font.size.pt) != expected_size:
                        wrong_size.append(text[:70])
                        break

            # ── Line spacing ──────────────────────────────────────────────────
            if expected_spacing:
                ls = para.paragraph_format.line_spacing
                if ls is not None:
                    try:
                        ls_val = round(float(ls), 2)
                        if abs(ls_val - expected_spacing) > 0.05:
                            wrong_spacing.append(text[:70])
                    except (TypeError, ValueError):
                        pass

        if total == 0:
            checks.append(ValidationCheckResult(
                category="typography", field="lampiran_format",
                status="skipped",
                message="Tidak ada judul lampiran (non-Lampiran style) yang perlu diperiksa via text-pattern",
                skip_reason="Semua lampiran pakai style eksplisit atau tidak ada",
            ))
            return issues, checks

        # ── Emit: format separator ────────────────────────────────────────────
        sep_display = f'titik (".")' if effective_sep == "." else (
            f'"{effective_sep}"' if effective_sep else "tanpa titik"
        )
        if wrong_separator:
            msg = (
                f"{len(wrong_separator)} judul lampiran tidak menggunakan format yang diharapkan "
                f"({sep_display} setelah nomor). Contoh: \"{wrong_separator[0]}\""
            )
            issues.append(ValidationIssue(
                category="document_structure", field="lampiran_separator",
                severity="warning", message=msg,
                expected=effective_sep, actual=wrong_separator[0],
            ))
            checks.append(ValidationCheckResult(
                category="document_structure", field="lampiran_separator",
                status="warning", message=msg,
                expected=effective_sep, actual=wrong_separator[0],
            ))
        else:
            checks.append(ValidationCheckResult(
                category="document_structure", field="lampiran_separator",
                status="passed",
                message=f"Format penulisan judul lampiran sesuai ({sep_display} setelah nomor)",
                expected=effective_sep,
            ))

        # ── Emit: atribut (font, alignment, spacing) ─────────────────────────
        all_ok = not any([wrong_alignment, wrong_font, wrong_size, wrong_spacing])
        if all_ok and total > 0:
            checks.append(ValidationCheckResult(
                category="typography", field="lampiran_format",
                status="passed",
                message=f"Semua {total} judul lampiran (non-Lampiran style) sesuai format body",
            ))
        else:
            for field, items, label, expected_val in [
                ("lampiran_alignment",  wrong_alignment, "alignment",   "JUSTIFY"),
                ("lampiran_font",       wrong_font,      "font family", expected_font),
                ("lampiran_font_size",  wrong_size,      "font size",   f"{expected_size}pt"),
                ("lampiran_spacing",    wrong_spacing,   "line spacing",f"{expected_spacing}"),
            ]:
                if not items:
                    continue
                msg = (
                    f"{len(items)} judul lampiran {label} tidak sesuai "
                    f"(ekspektasi: {expected_val}). Contoh: \"{items[0]}\""
                )
                issues.append(ValidationIssue(
                    category="typography", field=field,
                    severity="warning", message=msg,
                    expected=str(expected_val), actual=items[0],
                ))
                checks.append(ValidationCheckResult(
                    category="typography", field=field,
                    status="warning", message=msg,
                    expected=str(expected_val), actual=items[0],
                ))

    except Exception as exc:
        checks.append(ValidationCheckResult(
            category="typography", field="lampiran_format",
            status="skipped",
            message=f"Pengecekan format lampiran dilewati: {exc}",
            skip_reason=str(exc),
        ))

    return issues, checks


def _check_caption_format(
    docx_path: Path,
    metadata: DocumentMetadata,
) -> tuple[list[ValidationIssue], list[ValidationCheckResult]]:
    """Validasi atribut caption gambar/tabel via text-pattern, bukan style name.

    Caption dideteksi dari teks yang diawali 'Gambar <angka>' atau 'Tabel <angka>'.
    Aturan: atribut sama dengan Normal (font family, font size) kecuali alignment = CENTER.
    Style name diabaikan agar tidak false positive pada nama dinamis seperti 'Gambar (Lampiran)'.
    """
    issues: list[ValidationIssue] = []
    checks: list[ValidationCheckResult] = []

    t = metadata.typography
    expected_font   = t.font_family if t else None
    expected_size   = int(t.font_size_body_pt) if t and t.font_size_body_pt else None

    try:

        doc = DocxDocument(str(docx_path))

        wrong_alignment: list[str] = []
        wrong_font:      list[str] = []
        wrong_size:      list[str] = []

        for para in doc.paragraphs:
            text = para.text.strip()
            if not text:
                continue
            if not (_FIG_DETECT_RE.match(text) or _TBL_DETECT_RE.match(text)):
                continue

            # ── Alignment harus CENTER ────────────────────────────────────────
            align = para.paragraph_format.alignment
            if align is None:
                # Ambil dari style jika tidak di-override di paragraf
                try:
                    align = para.style.paragraph_format.alignment
                except Exception:
                    align = None
            if align is not None and align != WD_ALIGN_PARAGRAPH.CENTER:
                wrong_alignment.append(text[:70])

            # ── Font family & size harus sama dengan body ─────────────────────
            for run in para.runs:
                if expected_font and run.font.name and run.font.name != expected_font:
                    wrong_font.append(text[:70])
                    break
                if expected_size and run.font.size:
                    run_pt = round(run.font.size.pt)
                    if run_pt != expected_size:
                        wrong_size.append(text[:70])
                        break

        total_captions = sum(
            1 for para in doc.paragraphs
            if (_FIG_DETECT_RE.match(para.text.strip()) or _TBL_DETECT_RE.match(para.text.strip()))
            and para.text.strip()
        )

        # ── Emit results ──────────────────────────────────────────────────────
        if wrong_alignment:
            msg = (
                f"{len(wrong_alignment)} caption tidak rata tengah. "
                f'Contoh: "{wrong_alignment[0]}"'
            )
            issues.append(ValidationIssue(
                category="figures_tables", field="caption_alignment",
                severity="error", message=msg,
                expected="CENTER", actual="bukan CENTER",
            ))
            checks.append(ValidationCheckResult(
                category="figures_tables", field="caption_alignment",
                status="failed", message=msg,
                expected="CENTER", actual="bukan CENTER",
            ))
        else:
            checks.append(ValidationCheckResult(
                category="figures_tables", field="caption_alignment",
                status="passed" if total_captions > 0 else "skipped",
                message=(
                    f"Semua {total_captions} caption rata tengah"
                    if total_captions > 0
                    else "Tidak ada caption ditemukan"
                ),
                expected="CENTER",
            ))

        if wrong_font:
            msg = (
                f"{len(wrong_font)} caption font tidak sesuai (ekspektasi: {expected_font}). "
                f'Contoh: "{wrong_font[0]}"'
            )
            issues.append(ValidationIssue(
                category="figures_tables", field="caption_font",
                severity="warning", message=msg,
                expected=expected_font, actual=wrong_font[0],
            ))
            checks.append(ValidationCheckResult(
                category="figures_tables", field="caption_font",
                status="warning", message=msg,
                expected=expected_font, actual=wrong_font[0],
            ))
        elif expected_font and total_captions > 0:
            checks.append(ValidationCheckResult(
                category="figures_tables", field="caption_font",
                status="passed",
                message=f"Font caption sesuai: {expected_font}",
                expected=expected_font,
            ))

        if wrong_size:
            msg = (
                f"{len(wrong_size)} caption ukuran font tidak sesuai (ekspektasi: {expected_size}pt). "
                f'Contoh: "{wrong_size[0]}"'
            )
            issues.append(ValidationIssue(
                category="figures_tables", field="caption_font_size",
                severity="warning", message=msg,
                expected=str(expected_size), actual=wrong_size[0],
            ))
            checks.append(ValidationCheckResult(
                category="figures_tables", field="caption_font_size",
                status="warning", message=msg,
                expected=str(expected_size), actual=wrong_size[0],
            ))
        elif expected_size and total_captions > 0:
            checks.append(ValidationCheckResult(
                category="figures_tables", field="caption_font_size",
                status="passed",
                message=f"Ukuran font caption sesuai: {expected_size}pt",
                expected=str(expected_size),
            ))

    except Exception as exc:
        checks.append(ValidationCheckResult(
            category="figures_tables", field="caption_alignment",
            status="skipped",
            message=f"Pengecekan atribut caption dilewati: {exc}",
            skip_reason=str(exc),
        ))

    return issues, checks


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

def _get_pgnum_fmt(sectPr) -> str:
    """Ambil format nomor halaman dari elemen sectPr (w:pgNumType w:fmt).

    Mengembalikan 'decimal' sebagai default apabila elemen w:pgNumType tidak
    ada atau atribut w:fmt tidak di-set — sesuai perilaku default Microsoft
    Word (OOXML spec: nilai default w:fmt adalah 'decimal').
    """
    pgNumType = sectPr.find(qn('w:pgNumType'))
    if pgNumType is not None:
        fmt = pgNumType.get(qn('w:fmt'))
        return fmt if fmt else "decimal"
    return "decimal"


def _hdrftr_has_page_field(hdrftr) -> bool:
    """Cek apakah header/footer mengandung field PAGE."""
    if hdrftr is None:
        return False
    for instrText in hdrftr._element.iter(qn('w:instrText')):
        if 'PAGE' in (instrText.text or '').upper():
            return True
    return False


def _scan_numbering_zones(doc) -> tuple[dict | None, dict | None]:
    """Identifikasi zone preliminary dan content berdasarkan posisi BAB 1.

    Mengembalikan tuple (prelim_info, content_info) di mana masing-masing
    adalah dict {'fmt', 'has_header_page', 'has_footer_page'} atau None.

    Strategi content-aware:
    1. Scan semua elemen body untuk mengumpulkan section boundaries (sectPr).
    2. Cari paragraf Heading 1 yang teksnya diawali "BAB" → ini adalah awal
       section content (BAB 1).
    3. Section yang MENGANDUNG BAB 1 = content zone.
    4. Section yang berakhir SEBELUM BAB 1 = preliminary zone.
    5. Jika BAB 1 tidak ditemukan, semua section dianggap content.
    """
    body = doc.element.body
    all_children = list(body)

    # ── Kumpulkan section boundaries ─────────────────────────────────────────
    # Setiap entry: (last_element_idx, sectPr_element)
    # Inline sectPr di pPr → mengakhiri section di paragraf tersebut.
    # Body-level sectPr → mengakhiri section terakhir.
    boundaries: list[tuple[int, object]] = []
    for idx, child in enumerate(all_children):
        if child.tag.endswith('}p') or child.tag == 'p':
            pPr = child.find(qn('w:pPr'))
            if pPr is not None:
                inline_spr = pPr.find(qn('w:sectPr'))
                if inline_spr is not None:
                    boundaries.append((idx, inline_spr))
    body_spr = body.find(qn('w:sectPr'))
    if body_spr is not None:
        boundaries.append((len(all_children) - 1, body_spr))

    if not boundaries:
        return None, None

    # ── Cari BAB 1 ────────────────────────────────────────────────────────────
    # Cari paragraf yang teksnya diawali "BAB" DAN memiliki style heading.
    # Style heading bisa bermacam-macam tergantung template Word yang dipakai:
    #   - Standar Word : "Heading 1", "Heading1", "heading1"
    #   - Template PKM : "Judul1", "Judul 1", "BAB"
    # Untuk robustness, kita cek style yang mengandung kata "heading" atau
    # "judul" atau "bab", ATAU teksnya dimulai "BAB" dan berada di level
    # atas (style tidak kosong — bukan paragraf isi biasa).
    _HEADING_STYLE_KEYWORDS = ("heading", "judul", "bab")

    bab1_idx: int | None = None
    for idx, child in enumerate(all_children):
        if not (child.tag.endswith('}p') or child.tag == 'p'):
            continue
        pPr = child.find(qn('w:pPr'))
        style_val = ''
        if pPr is not None:
            pStyle = pPr.find(qn('w:pStyle'))
            if pStyle is not None:
                style_val = (pStyle.get(qn('w:val')) or '').lower()
        full_text = ''.join(
            (t.text or '') for t in child.iter(qn('w:t'))
        ).strip()
        full_upper = full_text.upper()
        if not full_upper.startswith('BAB'):
            continue
        # Teks dimulai "BAB" — cek apakah ini heading (ada style) atau
        # hanya teks biasa yang kebetulan dimulai "BAB"
        is_heading_style = any(k in style_val for k in _HEADING_STYLE_KEYWORDS)
        is_styled = bool(style_val)  # memiliki style apapun (bukan Normal/kosong)
        if is_heading_style or is_styled:
            bab1_idx = idx
            break

    # ── Tentukan section mana yang berisi BAB 1 ───────────────────────────────
    def _section_info(sectPr, doc_obj) -> dict:
        """Buat dict info section dari sectPr-nya."""
        fmt = _get_pgnum_fmt(sectPr)
        has_own_hdr = bool(sectPr.findall(qn('w:headerReference')))
        has_own_ftr = bool(sectPr.findall(qn('w:footerReference')))

        # Cari section python-docx yang sectPr-nya sama
        has_header_page = False
        has_footer_page = False
        for sec in doc_obj.sections:
            if sec._sectPr is sectPr:
                if has_own_hdr:
                    try:
                        has_header_page = _hdrftr_has_page_field(sec.header)
                    except Exception:
                        pass
                if has_own_ftr:
                    try:
                        has_footer_page = _hdrftr_has_page_field(sec.footer)
                    except Exception:
                        pass
                break
        return {
            "fmt": fmt,
            "has_header_page": has_header_page,
            "has_footer_page": has_footer_page,
            "has_any_page": has_header_page or has_footer_page,
        }

    # Tentukan: section mana preliminary, mana content
    # Section boundaries diurutkan menaik berdasarkan indeks.
    prev_end = -1
    prelim_info: dict | None = None
    content_info: dict | None = None

    for i, (end_idx, sectPr) in enumerate(boundaries):
        sec_start = prev_end + 1
        sec_end = end_idx

        info = _section_info(sectPr, doc)

        if bab1_idx is None:
            # Tidak ada BAB 1 terdeteksi → semua dianggap content
            content_info = info
        else:
            if bab1_idx > sec_end:
                # BAB 1 belum dimulai di section ini → preliminary
                prelim_info = info
            elif sec_start <= bab1_idx <= sec_end:
                # BAB 1 ada di section ini → content
                content_info = info
            else:
                # Section setelah BAB 1 (masih content)
                if content_info is None:
                    content_info = info

        prev_end = sec_end

    return prelim_info, content_info


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
            message="Data nomor halaman awal (romawi) dan isi (angka arab) kosong di metadata",
            skip_reason="Tidak ada nilai di metadata",
        ))
        return issues, checks

    try:
        doc = DocxDocument(str(docx_path))

        # Gunakan pendekatan content-aware: cari BAB 1 lalu tentukan zone
        # preliminary dan content berdasarkan posisi di dokumen.
        prelim_zone, content_zone = _scan_numbering_zones(doc)

        # Fallback: jika scan gagal, bangun section_infos biasa
        if prelim_zone is None and content_zone is None:
            section_infos = []
            for section in doc.sections:
                sectPr = section._sectPr
                fmt = _get_pgnum_fmt(sectPr)
                has_own_hdr = bool(sectPr.findall(qn('w:headerReference')))
                has_own_ftr = bool(sectPr.findall(qn('w:footerReference')))
                has_header_page = False
                has_footer_page = False
                if has_own_hdr:
                    try:
                        has_header_page = _hdrftr_has_page_field(section.header)
                    except Exception:
                        pass
                if has_own_ftr:
                    try:
                        has_footer_page = _hdrftr_has_page_field(section.footer)
                    except Exception:
                        pass
                section_infos.append({
                    "fmt": fmt,
                    "has_header_page": has_header_page,
                    "has_footer_page": has_footer_page,
                    "has_any_page": has_header_page or has_footer_page,
                })
            # Tebak zone: section pertama = preliminary, terakhir = content
            prelim_zone = section_infos[0] if section_infos else None
            content_zone = section_infos[-1] if len(section_infos) > 1 else None

        all_formats: set[str] = set()
        if prelim_zone:
            all_formats.add(prelim_zone["fmt"])
        if content_zone:
            all_formats.add(content_zone["fmt"])

        # ── Preliminary (romawi) ──────────────────────────────────────────────
        if prelim:
            exp_fmt = prelim.format  # e.g. "lowerRoman"
            exp_loc = (prelim.location or "").upper()  # "HEADER" atau "FOOTER"
            exp_start = prelim.start_at_section  # e.g. "daftar_isi"

            zone = prelim_zone
            fmt_match = zone is not None and zone["fmt"] == exp_fmt

            if fmt_match:
                checks.append(ValidationCheckResult(
                    category="numbering", field="preliminary_format",
                    status="passed",
                    message=(
                        f"Format nomor halaman awal '{exp_fmt}' "
                        f"({_NUM_FORMAT_DISPLAY.get(exp_fmt, exp_fmt)}): sesuai"
                    ),
                    expected=exp_fmt,
                ))
                # Cek lokasi
                if exp_loc in ("HEADER", "FOOTER") and zone["has_any_page"]:
                    loc_ok = (
                        (exp_loc == "HEADER" and zone["has_header_page"])
                        or (exp_loc == "FOOTER" and zone["has_footer_page"])
                    )
                    if not loc_ok:
                        actual_loc = "HEADER" if zone["has_header_page"] else "FOOTER"
                        msg = (
                            f"Nomor halaman awal seharusnya di {exp_loc}, "
                            f"tetapi ditemukan di {actual_loc}."
                        )
                        issues.append(ValidationIssue(
                            category="numbering", field="preliminary_location",
                            severity="warning", message=msg, expected=exp_loc,
                            actual=actual_loc,
                        ))
                        checks.append(ValidationCheckResult(
                            category="numbering", field="preliminary_location",
                            status="warning", message=msg, expected=exp_loc,
                            actual=actual_loc,
                        ))
                    else:
                        checks.append(ValidationCheckResult(
                            category="numbering", field="preliminary_location",
                            status="passed",
                            message=f"Lokasi nomor halaman awal ({exp_loc}): sesuai",
                            expected=exp_loc,
                        ))
            else:
                actual_fmt = zone["fmt"] if zone else None
                found_fmts = sorted(all_formats)
                msg = (
                    f"Format nomor halaman awal '{exp_fmt}' "
                    f"({_NUM_FORMAT_DISPLAY.get(exp_fmt, exp_fmt)}) tidak ditemukan "
                    f"di bagian sebelum BAB 1. "
                    + (f"Format yang ada: {found_fmts}" if found_fmts else "Tidak ada nomor halaman terdeteksi.")
                )
                issues.append(ValidationIssue(
                    category="numbering", field="preliminary_format",
                    severity="error", message=msg,
                    expected=exp_fmt,
                    actual=actual_fmt,
                ))
                checks.append(ValidationCheckResult(
                    category="numbering", field="preliminary_format",
                    status="failed", message=msg,
                    expected=exp_fmt,
                    actual=actual_fmt,
                ))

            if exp_start:
                _check_start_section(exp_start, doc, issues, checks, zone="awal")

        # ── Content (angka arab) ──────────────────────────────────────────────
        if content:
            exp_fmt = content.format  # e.g. "decimal"
            exp_loc = (content.location or "").upper()
            exp_start = content.start_at_section  # e.g. "bab_1"

            zone = content_zone
            fmt_match = zone is not None and zone["fmt"] == exp_fmt

            if fmt_match:
                checks.append(ValidationCheckResult(
                    category="numbering", field="content_format",
                    status="passed",
                    message=(
                        f"Format nomor halaman isi '{exp_fmt}' "
                        f"({_NUM_FORMAT_DISPLAY.get(exp_fmt, exp_fmt)}): sesuai "
                        f"(ditemukan mulai BAB 1)"
                    ),
                    expected=exp_fmt,
                ))
                # Cek lokasi
                if exp_loc in ("HEADER", "FOOTER") and zone["has_any_page"]:
                    loc_ok = (
                        (exp_loc == "HEADER" and zone["has_header_page"])
                        or (exp_loc == "FOOTER" and zone["has_footer_page"])
                    )
                    if not loc_ok:
                        actual_loc = "HEADER" if zone["has_header_page"] else "FOOTER"
                        msg = (
                            f"Nomor halaman isi seharusnya di {exp_loc}, "
                            f"tetapi ditemukan di {actual_loc}."
                        )
                        issues.append(ValidationIssue(
                            category="numbering", field="content_location",
                            severity="warning", message=msg, expected=exp_loc,
                            actual=actual_loc,
                        ))
                        checks.append(ValidationCheckResult(
                            category="numbering", field="content_location",
                            status="warning", message=msg, expected=exp_loc,
                            actual=actual_loc,
                        ))
                    else:
                        checks.append(ValidationCheckResult(
                            category="numbering", field="content_location",
                            status="passed",
                            message=f"Lokasi nomor halaman isi ({exp_loc}): sesuai",
                            expected=exp_loc,
                        ))
            else:
                actual_fmt = zone["fmt"] if zone else None
                found_fmts = sorted(all_formats)
                msg = (
                    f"Format nomor halaman isi '{exp_fmt}' "
                    f"({_NUM_FORMAT_DISPLAY.get(exp_fmt, exp_fmt)}) tidak ditemukan "
                    f"di section yang mengandung BAB 1. "
                    + (f"Format yang ada: {found_fmts}" if found_fmts else "Tidak ada nomor halaman terdeteksi.")
                )
                issues.append(ValidationIssue(
                    category="numbering", field="content_format",
                    severity="error", message=msg,
                    expected=exp_fmt,
                    actual=actual_fmt,
                ))
                checks.append(ValidationCheckResult(
                    category="numbering", field="content_format",
                    status="failed", message=msg,
                    expected=exp_fmt,
                    actual=actual_fmt,
                ))

            if exp_start:
                _check_start_section(exp_start, doc, issues, checks, zone="isi")

    except Exception as exc:
        checks.append(ValidationCheckResult(
            category="numbering", field="page_number",
            status="skipped",
            message=f"Pengecekan nomor halaman dilewati: {exc}",
            skip_reason=str(exc),
        ))

    return issues, checks


def _check_page_count(
    docx_path: Path,
    metadata: DocumentMetadata,
) -> tuple[list[ValidationIssue], list[ValidationCheckResult]]:
    """Validasi jumlah halaman inti tidak melebihi batas maksimum.

    Halaman inti dihitung dari section halaman_inti_mulai (default: bab)
    sampai halaman_inti_selesai (default: daftar_pustaka), inklusif.
    """
    issues: list[ValidationIssue] = []
    checks: list[ValidationCheckResult] = []

    pc = metadata.page_count_limits
    if pc is None or pc.proposal_halaman_inti_maks is None:
        checks.append(ValidationCheckResult(
            category="page_count", field="halaman_inti",
            status="skipped",
            message="Batas maksimum halaman inti tidak dikonfigurasi di metadata",
            skip_reason="proposal_halaman_inti_maks tidak ada",
        ))
        return issues, checks

    maks = pc.proposal_halaman_inti_maks
    mulai_type  = pc.halaman_inti_mulai   # default: "bab"
    selesai_type = pc.halaman_inti_selesai  # default: "daftar_pustaka"

    try:
        doc = DocxDocument(str(docx_path))

        # ── Identifikasi section content (BAB) vs preliminary (romawi) ────
        # _scan_numbering_zones sudah membedakan section berdasarkan posisi BAB 1.
        # Kita gunakan informasi ini untuk:
        #   1. Tahu apakah document punya section preliminary (romawi) sebelum BAB
        #   2. Agar page counting dimulai dari awal section content, bukan awal doc
        _, content_info = _scan_numbering_zones(doc)

        # ── Kumpulkan semua elemen body + identifikasi batas section ─────
        body = doc.element.body
        qn_p = qn("w:p")
        qn_pPr = qn("w:pPr")
        qn_sectPr = qn("w:sectPr")
        qn_type = qn("w:type")
        qn_val = qn("w:val")

        # Cari sectPr content section (section yang mengandung BAB 1)
        # untuk menentukan paragraf awal content section
        content_sectPr = None
        if content_info is not None:
            # Cari sectPr yang cocok dengan content_info
            for child in body:
                pPr = child.find(qn_pPr) if child.tag == qn_p else None
                if pPr is not None:
                    sp = pPr.find(qn_sectPr)
                    if sp is not None:
                        fmt = _get_pgnum_fmt(sp)
                        if fmt == content_info.get("fmt", "decimal"):
                            content_sectPr = sp
                            break
            if content_sectPr is None:
                body_spr = body.find(qn_sectPr)
                if body_spr is not None:
                    content_sectPr = body_spr

        # ── Bangun peta halaman per paragraf (seluruh dokumen) ────────────
        # Nomor halaman di sini adalah nomor sekuensial dari awal dokumen.
        # Setelah peta dibangun, kita hitung SELISIH antara halaman mulai
        # dan halaman selesai agar preliminary section tidak mempengaruhi hasil.
        current_page = 1
        para_pages: list[tuple[int, str, str]] = []  # (page, style, text)

        for para in doc.paragraphs:
            para_xml = para._p

            # Deteksi section break (nextPage/oddPage/evenPage).
            # Section break ada di paragraf TERAKHIR section sebelumnya,
            # artinya paragraf BERIKUTNYA mulai di halaman baru.
            pPr = para_xml.find(qn("w:pPr"))
            sect_pr = pPr.find(qn("w:sectPr")) if pPr is not None else None
            has_section_break = False
            if sect_pr is not None:
                type_el = sect_pr.find(qn("w:type"))
                sect_type_val = type_el.get(qn("w:val")) if type_el is not None else None
                if sect_type_val in ("nextPage", "oddPage", "evenPage", None):
                    has_section_break = True

            has_rendered_break = bool(
                para_xml.findall(".//" + qn("w:lastRenderedPageBreak"))
            )
            has_explicit_break = any(
                br.get(qn("w:type")) == "page"
                for br in para_xml.findall(".//" + qn("w:br"))
            )
            has_break = has_rendered_break or has_explicit_break

            if has_section_break and para_pages:
                # Tambah paragraf ini dulu (masih halaman lama), baru pindah halaman
                para_pages.append((current_page, para.style.name, para.text.strip()))
                current_page += 1
                continue

            if has_break and para_pages:
                current_page += 1
            para_pages.append((current_page, para.style.name, para.text.strip()))

        def _find_first_page(section_type: str) -> int | None:
            pattern = _SECTION_HEADING_MAP.get(section_type)
            if pattern is None:
                return None
            for page, style, text in para_pages:
                if "Heading" in style and pattern.match(text.upper()):
                    return page
            return None

        page_mulai   = _find_first_page(mulai_type)
        page_selesai = _find_first_page(selesai_type)

        if page_mulai is None:
            checks.append(ValidationCheckResult(
                category="page_count", field="halaman_inti",
                status="skipped",
                message=f"Titik mulai halaman inti '{mulai_type}' tidak ditemukan di dokumen",
                skip_reason=f"Section {mulai_type} tidak ada",
            ))
            return issues, checks

        # Jika selesai tidak ditemukan, hitung sampai akhir dokumen
        if page_selesai is None:
            page_selesai = para_pages[-1][0] if para_pages else page_mulai

        # jumlah_halaman = selisih halaman sekuensial antara mulai dan selesai + 1.
        # Preliminary pages (romawi) otomatis ter-cancel karena kita hitung SELISIH,
        # bukan posisi absolut. Misal: BAB=5, DAFTAR PUSTAKA=13 → 13-5+1=9 halaman inti.
        jumlah_halaman = page_selesai - page_mulai + 1

        if jumlah_halaman > maks:
            msg = (
                f"Halaman inti melebihi batas maksimum: "
                f"{jumlah_halaman} halaman (maks {maks}). "
                f"Dihitung dari halaman {page_mulai} ({mulai_type}) "
                f"sampai {page_selesai} ({selesai_type})."
            )
            issues.append(ValidationIssue(
                category="page_count", field="halaman_inti",
                severity="error", message=msg,
                expected=str(maks), actual=str(jumlah_halaman),
            ))
            checks.append(ValidationCheckResult(
                category="page_count", field="halaman_inti",
                status="failed", message=msg,
                expected=str(maks), actual=str(jumlah_halaman),
            ))
        else:
            msg = (
                f"Jumlah halaman inti: {jumlah_halaman} halaman "
                f"(maks {maks}) — sesuai."
            )
            checks.append(ValidationCheckResult(
                category="page_count", field="halaman_inti",
                status="passed", message=msg,
                expected=str(maks), actual=str(jumlah_halaman),
            ))

    except Exception as exc:
        checks.append(ValidationCheckResult(
            category="page_count", field="halaman_inti",
            status="skipped",
            message=f"Pengecekan jumlah halaman dilewati: {exc}",
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
        expected_title = _HEADING_TITLE_MAP_INV.get(start_at, start_at.upper().replace("_", " "))
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
# Page Number Display Map
# ─────────────────────────────────────────────────────────────────────────────

def _int_to_roman_lower(n: int) -> str:
    """Konversi integer positif ke angka romawi huruf kecil."""
    val  = [1000, 900, 500, 400, 100, 90, 50, 40, 10, 9, 5, 4, 1]
    syms = ['m', 'cm', 'd', 'cd', 'c', 'xc', 'l', 'xl', 'x', 'ix', 'v', 'iv', 'i']
    result = ''
    for i in range(len(val)):
        while n >= val[i]:
            result += syms[i]
            n -= val[i]
    return result


def _read_pgNumType(sectPr) -> tuple[str, int]:
    """Baca format dan nomor awal dari elemen w:pgNumType dalam sectPr.

    Returns:
        (fmt, start_num)
        fmt       → "lowerRoman", "upperRoman", "decimal", dsb.
        start_num → nomor halaman awal section (default 1)
    """
    pgNumType = sectPr.find(qn("w:pgNumType"))
    fmt       = "decimal"
    start_num = 1
    if pgNumType is not None:
        fmt = pgNumType.get(qn("w:fmt"), "decimal") or "decimal"
        s   = pgNumType.get(qn("w:start"), "1")
        try:
            start_num = int(s)
        except (TypeError, ValueError):
            start_num = 1
    return fmt, start_num


def _build_page_display_map(docx_path: Path) -> dict[int, str]:
    """Bangun peta nomor halaman fisik → label display sesuai penomoran dokumen.

    Langkah:
    1. Hitung halaman fisik via count_body_pages (hanya pakai w:lastRenderedPageBreak,
       tabel dihitung per baris bukan per sel)
    2. Baca section properties (w:pgNumType) untuk menentukan format penomoran
       (Romawi/Arab) dan nomor awal per section
    3. Jika section properties tidak tersedia atau tidak jelas → fallback ke
       deteksi teks "BAB 1"
    """
    try:
        doc = DocxDocument(str(docx_path))

        # ── 1. Hitung halaman fisik ──────────────────────────────────────────
        para_page_map, total_pages = count_body_pages(doc.element.body)

        # ── 2. Baca section properties ───────────────────────────────────────
        # Setiap section dalam dokumen punya format penomoran (Romawi/Arab) dan
        # nomor awal. Section break tersimpan di w:pPr/w:sectPr pada paragraf
        # TERAKHIR tiap section. Section paling akhir ada di w:body/w:sectPr.
        #
        # Struktur 'sections': list yang sudah diurutkan berdasarkan kemunculan,
        # setiap item berisi:
        #   start_page : halaman fisik pertama section ini
        #   fmt        : format angka ("lowerRoman", "upperRoman", "decimal", ...)
        #   start_num  : nomor halaman awal section ini
        raw_sections: list[dict] = []   # [{fmt, start_num, next_start}, ...]

        for para in doc.paragraphs:
            pPr    = para._p.find(qn("w:pPr"))
            if pPr is None:
                continue
            sectPr = pPr.find(qn("w:sectPr"))
            if sectPr is None:
                continue

            fmt, start_num = _read_pgNumType(sectPr)
            sect_page      = para_page_map.get(id(para._p), 1)

            t   = sectPr.find(qn("w:type"))
            val = t.get(qn("w:val"), "nextPage") if t is not None else "nextPage"

            # Section berikutnya mulai satu halaman setelah section break ini
            # (kecuali continuous yang tidak pindah halaman)
            next_start = sect_page + 1 if val in ("nextPage", "evenPage", "oddPage") else sect_page

            raw_sections.append({"fmt": fmt, "start_num": start_num, "next_start": next_start})

        # Tambahkan section terakhir (w:body/w:sectPr)
        last_sectPr = doc.element.body.find(qn("w:sectPr"))
        if last_sectPr is not None:
            fmt, start_num = _read_pgNumType(last_sectPr)
            raw_sections.append({"fmt": fmt, "start_num": start_num, "next_start": total_pages + 1})

        # Hitung start_page untuk setiap section dalam satu pass
        sections: list[dict] = []
        current_start = 1
        for rs in raw_sections:
            sections.append({
                "start_page": current_start,
                "fmt"       : rs["fmt"],
                "start_num" : rs["start_num"],
            })
            current_start = rs["next_start"]

        # ── 3. Bangun peta halaman → label ───────────────────────────────────
        page_map: dict[int, str] = {}

        roman_fmts        = {"lowerRoman", "upperRoman"}
        has_clear_sections = (
            len(sections) >= 2
            and any(s["fmt"] in roman_fmts for s in sections[:-1])
            and sections[-1]["fmt"] not in roman_fmts
        )

        def _page_label(page: int, fmt: str, start_num: int, section_start: int) -> str:
            num = start_num + (page - section_start)
            if fmt == "lowerRoman":
                return _int_to_roman_lower(max(num, 1))
            if fmt == "upperRoman":
                return _int_to_roman_lower(max(num, 1)).upper()
            return str(max(num, 1))

        if has_clear_sections:
            # Gunakan section properties
            for p in range(1, total_pages + 1):
                active = sections[0]
                for s in sections:
                    if s["start_page"] <= p:
                        active = s
                page_map[p] = _page_label(p, active["fmt"], active["start_num"], active["start_page"])

        else:
            # Fallback: deteksi BAB 1 (Heading 1 yang teksnya diawali "BAB")
            bab1_page: int | None = None
            for para in doc.paragraphs:
                if "Heading" in para.style.name and _BAB_RE.match(para.text.strip().upper()):
                    bab1_page = para_page_map.get(id(para._p))
                    break

            if bab1_page is None or bab1_page <= 1:
                for p in range(1, total_pages + 1):
                    page_map[p] = str(p)
            else:
                for p in range(1, bab1_page):
                    page_map[p] = _int_to_roman_lower(p)
                for p in range(bab1_page, total_pages + 1):
                    page_map[p] = str(p - bab1_page + 1)

        return page_map
    except Exception:
        return {}


def _patch_report_pages(report: dict, page_map: dict[int, str]) -> None:
    """Konversi field 'page' di semua paragraph_details dari nomor fisik ke label display.

    Iterasi seluruh paragraph_details dan paragraph_details_pass di setiap
    bucket report, lalu ganti nilai integer fisik dengan label dari page_map.
    """
    if not page_map:
        return

    def _patch_items(items: list[dict]) -> None:
        for item in items:
            for detail in item.get("paragraph_details", []):
                phys = detail.get("page")
                if isinstance(phys, int):
                    detail["page"] = page_map.get(phys, str(phys))
            for detail in item.get("paragraph_details_pass", []):
                phys = detail.get("page")
                if isinstance(phys, int):
                    detail["page"] = page_map.get(phys, str(phys))

    _patch_items(report["errors"].get("value_mismatch", []))
    _patch_items(report["errors"].get("font_mismatch", []))
    _patch_items(report["warnings"].get("undefined_styles", []))
    _patch_items(report["warnings"].get("attr_inherited", []))
    _patch_items(report.get("parameter_summary", []))


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
    requirements = enrich_requirements_with_docx_styles(requirements, path)
    log_text = _capture_log(path, requirements)

    entries = parse_entries(log_text)
    report = build_report(entries, docx_path=str(path))

    # Konversi nomor halaman fisik → label display (romawi / angka arab)
    # sesuai penomoran dokumen aktual, sebelum laporan diproses lebih lanjut.
    page_map = _build_page_display_map(path)
    _patch_report_pages(report, page_map)

    # Ekstrak daftar style yang dikenali dari requirements untuk ditampilkan
    # sebagai nilai "Seharusnya" pada warning undefined_style.
    # Contoh hasil: ["Normal", "Heading 1", "Heading 2", "Heading 3"]
    known_styles = list(requirements.get("styles", {}).keys())

    issues, checks = _build_issues_checks(report, known_styles=known_styles, requirements=requirements)
    case_issues, case_checks         = _check_heading_case(path, metadata)
    struct_issues, struct_checks     = _check_document_structure(path, metadata)
    fig_issues, fig_checks           = _check_figures_tables(path, metadata)
    caption_issues, caption_checks   = _check_caption_format(path, metadata)
    lampiran_issues, lampiran_checks = _check_lampiran_format(path, metadata)
    num_issues, num_checks           = _check_numbering(path, metadata)
    pgcount_issues, pgcount_checks   = _check_page_count(path, metadata)

    all_issues = issues + case_issues + struct_issues + fig_issues + caption_issues + lampiran_issues + num_issues + pgcount_issues
    all_checks = checks + case_checks + struct_checks + fig_checks + caption_checks + lampiran_checks + num_checks + pgcount_checks
    return all_issues, all_checks
