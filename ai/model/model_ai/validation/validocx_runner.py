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
from model_ai.validation.validocx.debug_report import parse_entries, build_report
from model_ai.validation.validocx_adapter import (
    enrich_requirements_with_docx_styles,
    metadata_to_requirements,
    _resolve_line_spacing,
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
_LAMPIRAN_ITEM_RE = re.compile(r'^Lampiran\s+(\d+)\.\s', re.IGNORECASE)
# Broad: menangkap SEMUA paragraf berawalan "Lampiran <angka>" (dipakai _check_lampiran_format)
_LAMPIRAN_BROAD_RE = re.compile(r'^Lampiran\s+\d+', re.IGNORECASE)

# Style TOC/TOF — dipakai sebagai filter di _check_lampiran_format dan
# _check_body_content (agar entri daftar yang teksnya diawali "Gambar/Tabel/Lampiran"
# tidak salah dikira caption inline).
# Word menyimpan style name dengan case yang bervariasi (mis. "toc 1" lowercase),
# sehingga kedua varian (upper dan lower) didaftarkan.
_TOC_TOF_STYLE_NAMES: frozenset[str] = frozenset({
    "table of figures",
    "TOC 1", "TOC 2", "TOC 3", "TOC 4", "TOC 5",
    "toc 1", "toc 2", "toc 3", "toc 4", "toc 5",
})

# Inverse dari _HEADING_TITLE_MAP: tipe section → teks heading
_HEADING_TITLE_MAP_INV: dict[str, str] = {v: k for k, v in _HEADING_TITLE_MAP.items()}

# Normalisasi format penomoran halaman: alias → nilai kanonik ODF.
# Digunakan di _classify_sections_by_metadata dan _check_numbering.
_FORMAT_ALIAS: dict[str, str] = {
    "arabic":      "decimal",
    "number":      "decimal",
    "roman":       "lowerRoman",
    "lowerroman":  "lowerRoman",
    "upperroman":  "upperRoman",
    "lowerletter": "lowerLetter",
    "upperletter": "upperLetter",
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

# Pola deteksi caption gambar / tabel / lampiran
_FIG_DETECT_RE  = re.compile(r'^Gambar\s+\d+', re.IGNORECASE)
_TBL_DETECT_RE  = re.compile(r'^Tabel\s+\d+',  re.IGNORECASE)
_LAMP_DETECT_RE = re.compile(r'^Lampiran\s+',   re.IGNORECASE)

# Mapping string alignment dari metadata → enum WD_ALIGN_PARAGRAPH
_CAPTION_ALIGN_MAP: dict[str, "WD_ALIGN_PARAGRAPH"] = {
    "CENTER":  WD_ALIGN_PARAGRAPH.CENTER,
    "LEFT":    WD_ALIGN_PARAGRAPH.LEFT,
    "RIGHT":   WD_ALIGN_PARAGRAPH.RIGHT,
    "JUSTIFY": WD_ALIGN_PARAGRAPH.JUSTIFY,
}

# Keyword untuk mendeteksi heading dari style name / inheritance chain.
_HEADING_STYLE_KEYWORDS: frozenset[str] = frozenset({"heading", "judul"})
_HEADING_PARAM_KEYWORDS: frozenset[str] = frozenset({"heading", "judul"})

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


def _is_heading_para(para) -> bool:
    """Deteksi apakah paragraf adalah heading berdasarkan style name + inheritance chain.

    Menelusuri style dan semua base_style-nya hingga kedalaman 10.
    Return True jika nama style mengandung 'heading' atau 'judul' (case-insensitive).
    """
    style = para.style
    depth = 0
    while style is not None and depth < 10:
        name = (style.name or "").lower()
        if any(k in name for k in _HEADING_STYLE_KEYWORDS):
            return True
        style = getattr(style, "base_style", None)
        depth += 1
    return False


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
    para_details adalah list dict dari build_report() via debug_report._get_para_details().
    Field 'page' dan 'bab' dapat bernilai None jika tidak tersedia di sumber.
    """
    result = []
    for detail in para_details:
        if not isinstance(detail, dict):
            continue
        # Lewati paragraf kosong (misal heading tanpa teks yang tidak sengaja diberi style)
        if not (detail.get("text") or "").strip():
            continue
        # Jika actual_str tidak diberikan, coba ambil dari item itu sendiri
        # (berguna untuk kasus di mana tiap paragraf punya actual value berbeda).
        item_actual = actual_str if actual_str is not None else detail.get("actual")
        result.append({
            "page"      : detail.get("page"),
            "bab"       : detail.get("bab"),
            "para_idx"  : detail.get("para_idx"),
            "style"     : detail.get("style"),
            "text"      : (detail.get("text") or "")[:100],
            "full_text" : detail.get("full_text") or "",
            "actual"    : item_actual,
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

    # ── Parameter summary sebagai check (heading only) ───────────────────────
    # Non-heading summary digantikan oleh _check_body_content() yang mengagregasi
    # per nilai parameter. Di sini tampilkan hasil heading (Heading 1–5, Judul*):
    #   - lolos semua / lolos semua (ada inherited) → check passed saja
    #   - ada yang gagal → check failed (elemen gagal) + check passed (elemen lolos)
    #     Keduanya ditampilkan agar user tahu berapa yang lolos dan berapa yang error.
    for ps in report.get("parameter_summary", []):
        param_match = re.match(r'^(\S+)\s+\((.+)\)$', ps["parameter"])
        style_in_param = (param_match.group(2) if param_match else "").lower()
        if not any(k in style_in_param for k in _HEADING_PARAM_KEYWORDS):
            continue

        expected_val: str | None = None
        if requirements and param_match:
            expected_val = _lookup_expected(
                requirements, param_match.group(1), param_match.group(2)
            )

        field = f"validocx_param.{ps['parameter'].replace(' ', '_')}"

        # ── Elemen yang lolos → selalu emit passed check ──────────────────────
        # Gunakan len(raw_pass) bukan ps["pass"] karena ps["pass"] menghitung
        # baris log per run (bisa >1 per paragraf), sedangkan raw_pass berisi
        # satu entry per paragraf unik — konsisten dengan jumlah lokasi yang ditampilkan.
        if ps["pass"] > 0 or ps["status"] in ("lolos semua", "lolos semua (ada inherited)"):
            raw_pass = ps.get("paragraph_details_pass", [])
            n_pass = len(raw_pass)
            occs_pass = _build_occurrences(raw_pass) or None
            checks.append(ValidationCheckResult(
                category="typography",
                field=field,
                status="passed",
                message=f"{ps['parameter']}: {n_pass} elemen lolos",
                expected=expected_val,
                actual=expected_val,
                occurrences=occs_pass,
            ))

        # ── Elemen yang gagal → emit failed check + issue ─────────────────────
        if ps["status"] == "ada yang gagal":
            raw_fail = ps.get("paragraph_details_fail", [])
            n_fail  = len(raw_fail)
            n_total = len(ps.get("paragraph_details_pass", [])) + n_fail
            occs_fail = _build_occurrences(raw_fail, expected_str=expected_val) or None
            msg = (
                f"{ps['parameter']}: {n_fail} dari {n_total} elemen gagal"
                + (f" (expected: {expected_val})" if expected_val else "")
            )
            issues.append(ValidationIssue(
                category="typography",
                field=field,
                severity="error",
                message=msg,
                occurrences=occs_fail,
            ))
            checks.append(ValidationCheckResult(
                category="typography",
                field=field,
                status="failed",
                message=msg,
                expected=expected_val,
                occurrences=occs_fail,
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

        pass_per_level:     dict[int, list[dict]] = {lvl: [] for lvl in case_per_level}
        mismatch_per_level: dict[int, list[dict]] = {lvl: [] for lvl in case_per_level}

        for idx, para in enumerate(doc.paragraphs):
            style_name = para.style.name
            text = para.text.strip()
            if not text:
                continue
            for level in range(1, 6):
                case_style = case_per_level[level]
                if case_style and style_name == f"Heading {level}":
                    para_info: dict = {
                        "para_idx"  : idx,
                        "style"     : style_name,
                        "text"      : text[:100],
                        "full_text" : text,
                        "bab"       : None,
                        "page"      : None,
                    }
                    if not _text_matches_case_para(para, case_style):
                        mismatch_per_level[level].append(para_info)
                    else:
                        pass_per_level[level].append(para_info)
                    break

        for level, case_style in case_per_level.items():
            if case_style is None:
                continue
            field_name = f"heading_{level}_case"
            mismatches = mismatch_per_level[level]
            passes     = pass_per_level[level]

            # Jika tidak ada paragraf sama sekali untuk level ini,
            # heading tidak digunakan di dokumen → tidak perlu emit check.
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
                    severity="warning", message=msg,
                    expected=case_style, actual=first_actual,
                    occurrences=occs,
                ))
                checks.append(ValidationCheckResult(
                    category="typography", field=field_name,
                    status="warning", message=msg,
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
    """Validasi judul lampiran via text-pattern untuk SEMUA judul lampiran.

    Mendeteksi paragraf yang teksnya diawali 'Lampiran <angka>' (_LAMPIRAN_BROAD_RE),
    baik yang menggunakan style bernama 'Lampiran' maupun style lain (Normal, Body, dll).
    Aturan atribut: font family, font size, line spacing, alignment JUSTIFY — sama dengan body.
    """
    issues: list[ValidationIssue] = []
    checks: list[ValidationCheckResult] = []

    t  = metadata.typography
    ds = metadata.document_structure_proposal
    expected_font    = t.font_family if t else None
    expected_size    = int(t.font_size_body_pt) if t and t.font_size_body_pt else None
    expected_spacing = _resolve_line_spacing(metadata)

    # Separator dari payload; None → default "."
    separator   = ds.lampiran_heading_separator if ds else None
    effective_sep = separator if separator is not None else "."
    lampiran_re = _build_lampiran_re(effective_sep)

    # Rangkuman nilai yang diharapkan (dipakai di occurrences)
    expected_summary = ", ".join(filter(None, [
        expected_font or None,
        f"{expected_size}pt" if expected_size else None,
        f"spacing {expected_spacing}",
        "JUSTIFY",
    ]))

    try:
        doc = DocxDocument(str(docx_path))

        pass_items:      list[dict] = []
        wrong_alignment: list[dict] = []
        wrong_font:      list[dict] = []
        wrong_size:      list[dict] = []
        wrong_spacing:   list[dict] = []
        wrong_separator: list[str]  = []
        total = 0

        for para in doc.paragraphs:
            text = para.text.strip()
            if not text or not _LAMPIRAN_BROAD_RE.match(text):
                continue

            # Entri Daftar Lampiran (style TOC/TOF) sudah divalidasi engine → skip
            if para.style.name in _TOC_TOF_STYLE_NAMES:
                continue

            # ── Separator ────────────────────────────────────────────────────
            if not lampiran_re.match(text):
                wrong_separator.append(text[:70])

            total += 1
            para_info: dict = {
                "text"      : text[:100],
                "full_text" : text,
                "style"     : para.style.name,
                "page"      : None,
                "bab"       : None,
                "para_idx"  : None,
            }
            has_issue = False

            # ── Alignment harus JUSTIFY ──────────────────────────────────────
            align = para.paragraph_format.alignment
            if align is None:
                try:
                    align = para.style.paragraph_format.alignment
                except Exception:
                    align = None
            if align is not None and align != WD_ALIGN_PARAGRAPH.JUSTIFY:
                _align_names = {0: "LEFT", 1: "CENTER", 2: "RIGHT", 3: "JUSTIFY"}
                wrong_alignment.append({**para_info, "actual": _align_names.get(int(align), str(align))})
                has_issue = True

            # ── Font & size ──────────────────────────────────────────────────
            for run in para.runs:
                if expected_font and run.font.name and run.font.name != expected_font:
                    wrong_font.append({**para_info, "actual": run.font.name})
                    has_issue = True
                    break
                if expected_size and run.font.size:
                    actual_pt = round(run.font.size.pt)
                    if actual_pt != expected_size:
                        wrong_size.append({**para_info, "actual": f"{actual_pt}pt"})
                        has_issue = True
                        break

            # ── Line spacing ─────────────────────────────────────────────────
            ls = para.paragraph_format.line_spacing
            if ls is not None:
                try:
                    ls_val = round(float(ls), 2)
                    if abs(ls_val - expected_spacing) > 0.05:
                        wrong_spacing.append({**para_info, "actual": str(ls_val)})
                        has_issue = True
                except (TypeError, ValueError):
                    pass

            if not has_issue:
                pass_items.append(para_info)

        # ── Emit: format separator ───────────────────────────────────────────
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

        # Tidak ada judul lampiran sama sekali → skip atribut check
        if total == 0:
            checks.append(ValidationCheckResult(
                category="typography", field="lampiran_format",
                status="skipped",
                message="Tidak ada judul lampiran yang ditemukan di dokumen",
                skip_reason="Tidak ada paragraf dengan pola 'Lampiran <angka>'",
            ))
            return issues, checks

        # ── Emit: atribut lolos → passed check dengan occurrences ────────────
        all_ok = not any([wrong_alignment, wrong_font, wrong_size, wrong_spacing])
        if pass_items:
            n_pass = len(pass_items)
            occs_pass = _build_occurrences(
                pass_items,
                actual_str=expected_summary,
                expected_str=expected_summary,
            ) or None
            checks.append(ValidationCheckResult(
                category="typography", field="lampiran_format",
                status="passed",
                message=(
                    f"Semua {total} judul lampiran sesuai format body"
                    if all_ok else
                    f"{n_pass} dari {total} judul lampiran sesuai format body"
                ),
                expected=expected_summary,
                actual=expected_summary,
                occurrences=occs_pass,
            ))

        # ── Emit: atribut gagal → warning check + issue per atribut ──────────
        for field, items, label, expected_val in [
            ("lampiran_alignment", wrong_alignment, "alignment",    "JUSTIFY"),
            ("lampiran_font",      wrong_font,      "font family",  expected_font or ""),
            ("lampiran_font_size", wrong_size,      "font size",    f"{expected_size}pt"),
            ("lampiran_spacing",   wrong_spacing,   "line spacing", str(expected_spacing)),
        ]:
            if not items:
                continue
            first_actual = items[0].get("actual", "")
            msg = (
                f"{len(items)} judul lampiran {label} tidak sesuai "
                f"(ekspektasi: {expected_val}). Contoh: \"{items[0]['text']}\""
            )
            # actual_str=None → _build_occurrences akan pakai "actual" tiap item
            occs_fail = _build_occurrences(items, expected_str=str(expected_val)) or None
            issues.append(ValidationIssue(
                category="typography", field=field,
                severity="warning", message=msg,
                expected=str(expected_val), actual=first_actual,
                occurrences=occs_fail,
            ))
            checks.append(ValidationCheckResult(
                category="typography", field=field,
                status="warning", message=msg,
                expected=str(expected_val), actual=first_actual,
                occurrences=occs_fail,
            ))

    except Exception as exc:
        checks.append(ValidationCheckResult(
            category="typography", field="lampiran_format",
            status="skipped",
            message=f"Pengecekan format lampiran dilewati: {exc}",
            skip_reason=str(exc),
        ))

    return issues, checks


def _check_body_content(
    docx_path: Path,
    metadata: DocumentMetadata,
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
    s = metadata.spacing
    expected_align   = WD_ALIGN_PARAGRAPH.JUSTIFY
    expected_font    = t.font_family if t else None
    expected_size    = int(t.font_size_body_pt) if t and t.font_size_body_pt else None
    # Gunakan _resolve_line_spacing agar rule seperti ONE_POINT_FIVE/SINGLE/DOUBLE
    # juga menghasilkan nilai float yang benar (bukan None).
    expected_spacing = _resolve_line_spacing(metadata)

    try:
        from model_ai.validation.validocx.wrapper import DocumentWrapper

        doc     = DocxDocument(str(docx_path))
        wrapper = DocumentWrapper(doc)

        align_pass:   list[dict] = []
        align_fail:   list[dict] = []
        font_pass:    list[dict] = []
        font_fail:    list[dict] = []
        size_pass:    list[dict] = []
        size_fail:    list[dict] = []
        spacing_pass: list[dict] = []
        spacing_fail: list[dict] = []

        for idx, para in enumerate(wrapper.iter_paragraphs()):
            text = para.text.strip()
            if not text:
                continue
            if _is_heading_para(para):
                continue
            # Entri TOC/TOF divalidasi oleh engine validocx — skip di sini agar
            # teksnya (mis. "DAFTAR ISI i", "Gambar 1. Judul...3") tidak muncul
            # sebagai elemen body. Konsisten dengan _check_lampiran_format.
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

            # ── Alignment ─────────────────────────────────────────────────────
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

            # ── Font family & font size (run pertama yang punya teks) ─────────
            _run_checked = False
            for run in para.runs:
                if not run.text.strip():
                    continue
                _run_checked = True
                fn = run.font.name
                if fn is not None:
                    if expected_font and fn != expected_font:
                        font_fail.append({**para_info, "actual": fn})
                    else:
                        font_pass.append(para_info)
                else:
                    # Font None = inherited — anggap lolos (backward-compatible)
                    font_pass.append(para_info)
                fs = run.font.size
                if fs is not None:
                    fs_pt = round(fs.pt)
                    if expected_size and fs_pt != expected_size:
                        size_fail.append({**para_info, "actual": f"{fs_pt}pt"})
                    else:
                        size_pass.append(para_info)
                else:
                    # Size None = inherited — anggap lolos
                    size_pass.append(para_info)
                break  # cukup satu run
            if not _run_checked:
                # Tidak ada run dengan teks — anggap font/size lolos (inherited)
                font_pass.append(para_info)
                size_pass.append(para_info)

            # ── Line spacing ──────────────────────────────────────────────────
            if expected_spacing:
                ls = para.paragraph_format.line_spacing
                if ls is None:
                    # Inherited dari style/dokumen default — anggap lolos,
                    # konsisten dengan penanganan font/size yang juga None = lolos.
                    spacing_pass.append(para_info)
                else:
                    try:
                        ls_val = round(float(ls), 2)
                        if abs(ls_val - expected_spacing) > 0.05:
                            spacing_fail.append({**para_info, "actual": str(ls_val)})
                        else:
                            spacing_pass.append(para_info)
                    except (TypeError, ValueError):
                        spacing_pass.append(para_info)

        # ── Emit satu check per parameter ────────────────────────────────────
        # Occurrences hanya disertakan pada satu check — body_alignment — agar
        # para_idx lintas semua checks tetap monotone (sesuai urutan dokumen).
        # Check lain (font, size, spacing) hanya melaporkan jumlah tanpa occurrences.
        def _emit(
            field: str,
            label: str,
            expected_val: str,
            pass_list: list[dict],
            fail_list: list[dict],
            include_occurrences: bool = False,
        ) -> None:
            if not pass_list and not fail_list:
                return
            if fail_list:
                actual_vals = list(dict.fromkeys(d.get("actual", "?") for d in fail_list))
                actual_str  = ", ".join(str(v) for v in actual_vals[:3])
                msg = (
                    f"{label}: {len(fail_list)} elemen tidak sesuai "
                    f"(ekspektasi: {expected_val}). Ditemukan: {actual_str}"
                )
                occs = (
                    _build_occurrences(fail_list, actual_str=actual_str,
                                       expected_str=expected_val) or None
                ) if include_occurrences else None
                issues.append(ValidationIssue(
                    category="typography", field=field,
                    severity="error", message=msg,
                    expected=expected_val, actual=actual_str,
                    occurrences=occs,
                ))
                checks.append(ValidationCheckResult(
                    category="typography", field=field,
                    status="failed", message=msg,
                    expected=expected_val, actual=actual_str,
                    occurrences=occs,
                ))
            if pass_list:
                occs = (
                    _build_occurrences(pass_list, expected_str=expected_val) or None
                ) if include_occurrences else None
                checks.append(ValidationCheckResult(
                    category="typography", field=field,
                    status="passed",
                    message=f"{label}: {len(pass_list)} elemen lolos",
                    expected=expected_val,
                    actual=expected_val,
                    occurrences=occs,
                ))

        _emit("body_alignment",    "Alignment (JUSTIFY)",            "JUSTIFY",
              align_pass,   align_fail,   include_occurrences=True)
        if expected_font:
            _emit("body_font_family",  f"Font family ({expected_font})",   expected_font,
                  font_pass,    font_fail,    include_occurrences=True)
        if expected_size:
            _emit("body_font_size",    f"Ukuran font ({expected_size}pt)", f"{expected_size}pt",
                  size_pass,    size_fail,    include_occurrences=True)
        if expected_spacing:
            _emit("body_line_spacing", f"Spasi baris ({expected_spacing})", str(expected_spacing),
                  spacing_pass, spacing_fail, include_occurrences=True)

    except Exception as exc:
        checks.append(ValidationCheckResult(
            category="typography", field="body_content",
            status="skipped",
            message=f"Pengecekan konten body dilewati: {exc}",
            skip_reason=str(exc),
        ))

    return issues, checks


def _check_caption_format(
    docx_path: Path,
    metadata: DocumentMetadata,
) -> tuple[list[ValidationIssue], list[ValidationCheckResult]]:
    """Validasi atribut caption gambar/tabel via text-pattern, bukan style name.

    Caption dideteksi dari teks yang diawali 'Gambar <angka>' atau 'Tabel <angka>'.
    Alignment dibaca dari metadata.figures_and_tables per tipe caption (CENTER fallback).
    Font family dan font size harus sama dengan body — dicek per tipe caption.
    Style name diabaikan agar tidak false positive pada nama dinamis.
    """
    issues: list[ValidationIssue] = []
    checks: list[ValidationCheckResult] = []

    t  = metadata.typography
    ft = metadata.figures_and_tables

    expected_font = t.font_family if t else None
    expected_size = int(t.font_size_body_pt) if t and t.font_size_body_pt else None

    # Baca alignment per tipe dari metadata; default CENTER jika null
    fig_align_str = ((ft.caption_alignment_figure or "CENTER").upper() if ft else "CENTER")
    tbl_align_str = ((ft.caption_alignment_table  or "CENTER").upper() if ft else "CENTER")
    fig_align_val = _CAPTION_ALIGN_MAP.get(fig_align_str, WD_ALIGN_PARAGRAPH.CENTER)
    tbl_align_val = _CAPTION_ALIGN_MAP.get(tbl_align_str, WD_ALIGN_PARAGRAPH.CENTER)

    try:
        doc = DocxDocument(str(docx_path))

        wrong_fig_alignment: list[str] = []
        wrong_tbl_alignment: list[str] = []
        wrong_font:          list[str] = []
        wrong_size:          list[str] = []
        fig_total = 0
        tbl_total = 0

        for para in doc.paragraphs:
            text = para.text.strip()
            if not text:
                continue

            is_fig = bool(_FIG_DETECT_RE.match(text))
            is_tbl = bool(_TBL_DETECT_RE.match(text))
            if not is_fig and not is_tbl:
                continue

            if is_fig:
                fig_total += 1
            else:
                tbl_total += 1

            # ── Alignment ────────────────────────────────────────────────────
            align = para.paragraph_format.alignment
            if align is None:
                try:
                    align = para.style.paragraph_format.alignment
                except Exception:
                    align = None

            if align is not None:
                if is_fig and align != fig_align_val:
                    wrong_fig_alignment.append(text[:70])
                elif is_tbl and align != tbl_align_val:
                    wrong_tbl_alignment.append(text[:70])

            # ── Font family & size (run pertama non-empty saja) ──────────────
            for run in para.runs:
                if not run.text.strip():
                    continue
                if expected_font and run.font.name and run.font.name != expected_font:
                    wrong_font.append(text[:70])
                if expected_size and run.font.size:
                    run_pt = round(run.font.size.pt)
                    if run_pt != expected_size:
                        wrong_size.append(text[:70])
                break  # cukup satu run

        # ── Emit alignment gambar ─────────────────────────────────────────────
        if fig_total > 0:
            if wrong_fig_alignment:
                msg = (
                    f"{len(wrong_fig_alignment)} caption gambar tidak {fig_align_str}. "
                    f'Contoh: "{wrong_fig_alignment[0]}"'
                )
                issues.append(ValidationIssue(
                    category="figures_tables", field="caption_alignment_figure",
                    severity="error", message=msg,
                    expected=fig_align_str, actual=f"bukan {fig_align_str}",
                ))
                checks.append(ValidationCheckResult(
                    category="figures_tables", field="caption_alignment_figure",
                    status="failed", message=msg,
                    expected=fig_align_str, actual=f"bukan {fig_align_str}",
                ))
            else:
                checks.append(ValidationCheckResult(
                    category="figures_tables", field="caption_alignment_figure",
                    status="passed",
                    message=f"Semua {fig_total} caption gambar alignment {fig_align_str}",
                    expected=fig_align_str,
                ))

        # ── Emit alignment tabel ──────────────────────────────────────────────
        if tbl_total > 0:
            if wrong_tbl_alignment:
                msg = (
                    f"{len(wrong_tbl_alignment)} caption tabel tidak {tbl_align_str}. "
                    f'Contoh: "{wrong_tbl_alignment[0]}"'
                )
                issues.append(ValidationIssue(
                    category="figures_tables", field="caption_alignment_table",
                    severity="error", message=msg,
                    expected=tbl_align_str, actual=f"bukan {tbl_align_str}",
                ))
                checks.append(ValidationCheckResult(
                    category="figures_tables", field="caption_alignment_table",
                    status="failed", message=msg,
                    expected=tbl_align_str, actual=f"bukan {tbl_align_str}",
                ))
            else:
                checks.append(ValidationCheckResult(
                    category="figures_tables", field="caption_alignment_table",
                    status="passed",
                    message=f"Semua {tbl_total} caption tabel alignment {tbl_align_str}",
                    expected=tbl_align_str,
                ))

        # ── Emit font (gabungan gambar + tabel) ───────────────────────────────
        total_captions = fig_total + tbl_total
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
                f"{len(wrong_size)} caption ukuran font tidak sesuai "
                f"(ekspektasi: {expected_size}pt). "
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

        if total_captions == 0:
            for _fld in ("caption_alignment_figure", "caption_alignment_table"):
                checks.append(ValidationCheckResult(
                    category="figures_tables", field=_fld,
                    status="skipped",
                    message="Tidak ada caption gambar/tabel ditemukan",
                    skip_reason="Tidak ada caption",
                ))

    except Exception as exc:
        checks.append(ValidationCheckResult(
            category="figures_tables", field="caption_alignment_figure",
            status="skipped",
            message=f"Pengecekan atribut caption dilewati: {exc}",
            skip_reason=str(exc),
        ))

    return issues, checks


def _check_figures_tables(
    docx_path: Path,
    metadata: DocumentMetadata,
) -> tuple[list[ValidationIssue], list[ValidationCheckResult]]:
    """Validasi posisi caption dan format penomoran gambar/tabel + lampiran.

    Kepemilikan field (tidak overlap dengan _check_lampiran_format):
      - figure_caption_position / table_caption_position — posisi relatif gambar/tabel
      - figure_caption_format / table_caption_format — template penomoran (via _build_content_elements)
      - lampiran_caption_format — template penomoran header lampiran (via doc.paragraphs scan terpisah)
      - lampiran_caption_alignment — alignment header lampiran

    _check_lampiran_format() memiliki: lampiran_separator, lampiran_font, lampiran_spacing.
    Keduanya scan _LAMPIRAN_BROAD_RE tetapi mengecek field yang berbeda.
    """
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

    tbl_pos_exp  = (ft.table_caption_position or "").upper()
    fig_pos_exp  = (ft.figure_caption_position or "").upper()
    fig_fmt_tpl  = ft.caption_format_figure
    tbl_fmt_tpl  = ft.caption_format_table
    lamp_fmt_tpl = ft.caption_format_lampiran
    lamp_align_str = (ft.caption_alignment_lampiran or "").upper() or None

    if not tbl_pos_exp and not fig_pos_exp and not fig_fmt_tpl and not tbl_fmt_tpl \
            and not lamp_fmt_tpl and not lamp_align_str:
        checks.append(ValidationCheckResult(
            category="figures_tables", field="caption",
            status="skipped",
            message="Tidak ada aturan caption di metadata",
            skip_reason="Tidak ada nilai di metadata",
        ))
        return issues, checks

    try:
        doc = DocxDocument(str(docx_path))

        fig_fmt_re  = _template_to_regex(fig_fmt_tpl)  if fig_fmt_tpl  else None
        tbl_fmt_re  = _template_to_regex(tbl_fmt_tpl)  if tbl_fmt_tpl  else None
        lamp_fmt_re = _template_to_regex(lamp_fmt_tpl) if lamp_fmt_tpl else None
        lamp_align_val = (
            _CAPTION_ALIGN_MAP.get(lamp_align_str, WD_ALIGN_PARAGRAPH.CENTER)
            if lamp_align_str else None
        )

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

        # ── Lampiran scan (seluruh dokumen) ──────────────────────────────────
        # _build_content_elements() berhenti sebelum LAMPIRAN → scan terpisah.
        if lamp_fmt_re or lamp_align_val is not None:
            lamp_count          = 0
            lamp_fmt_errors:    list[str] = []
            lamp_align_errors:  list[str] = []

            for para in doc.paragraphs:
                text = para.text.strip()
                if not text or not _LAMPIRAN_BROAD_RE.match(text):
                    continue
                lamp_count += 1

                if lamp_fmt_re and not lamp_fmt_re.match(text):
                    lamp_fmt_errors.append(text[:70])

                if lamp_align_val is not None:
                    align = para.paragraph_format.alignment
                    if align is None:
                        try:
                            align = para.style.paragraph_format.alignment
                        except Exception:
                            align = None
                    if align is not None and align != lamp_align_val:
                        lamp_align_errors.append(text[:70])

            # Emit format lampiran
            if lamp_fmt_re:
                if lamp_count == 0:
                    checks.append(ValidationCheckResult(
                        category="figures_tables", field="lampiran_caption_format",
                        status="skipped",
                        message="Tidak ditemukan caption lampiran di dokumen",
                        skip_reason="Tidak ada paragraf diawali 'Lampiran '",
                    ))
                elif lamp_fmt_errors:
                    msg = (
                        f"Format caption lampiran tidak sesuai pola '{lamp_fmt_tpl}'. "
                        f"{len(lamp_fmt_errors)}x salah. "
                        f'Contoh: "{lamp_fmt_errors[0]}"'
                    )
                    issues.append(ValidationIssue(
                        category="figures_tables", field="lampiran_caption_format",
                        severity="warning", message=msg,
                        expected=lamp_fmt_tpl, actual=lamp_fmt_errors[0],
                    ))
                    checks.append(ValidationCheckResult(
                        category="figures_tables", field="lampiran_caption_format",
                        status="warning", message=msg,
                        expected=lamp_fmt_tpl, actual=lamp_fmt_errors[0],
                    ))
                else:
                    checks.append(ValidationCheckResult(
                        category="figures_tables", field="lampiran_caption_format",
                        status="passed",
                        message=f"Format caption lampiran '{lamp_fmt_tpl}': {lamp_count} caption sesuai",
                        expected=lamp_fmt_tpl,
                    ))

            # Emit alignment lampiran
            if lamp_align_val is not None:
                if lamp_count == 0:
                    checks.append(ValidationCheckResult(
                        category="figures_tables", field="lampiran_caption_alignment",
                        status="skipped",
                        message="Tidak ditemukan caption lampiran di dokumen",
                        skip_reason="Tidak ada paragraf diawali 'Lampiran '",
                    ))
                elif lamp_align_errors:
                    msg = (
                        f"{len(lamp_align_errors)} caption lampiran tidak {lamp_align_str}. "
                        f'Contoh: "{lamp_align_errors[0]}"'
                    )
                    issues.append(ValidationIssue(
                        category="figures_tables", field="lampiran_caption_alignment",
                        severity="error", message=msg,
                        expected=lamp_align_str, actual=f"bukan {lamp_align_str}",
                    ))
                    checks.append(ValidationCheckResult(
                        category="figures_tables", field="lampiran_caption_alignment",
                        status="failed", message=msg,
                        expected=lamp_align_str, actual=f"bukan {lamp_align_str}",
                    ))
                else:
                    checks.append(ValidationCheckResult(
                        category="figures_tables", field="lampiran_caption_alignment",
                        status="passed",
                        message=f"Semua {lamp_count} caption lampiran alignment {lamp_align_str}",
                        expected=lamp_align_str,
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


def _classify_sections_by_metadata(
    doc,
    metadata: "DocumentMetadata",
) -> dict[str, dict | None]:
    """Klasifikasi section dokumen ke zone preliminary/content berdasarkan metadata.

    Menggunakan format penomoran yang diexpect dari metadata (misal lowerRoman vs
    decimal) untuk mencocokkan section DOCX ke zone yang tepat — lebih andal
    daripada mengandalkan posisi heading BAB 1 sebagai satu-satunya penanda.

    Strategi:
    1. Kumpulkan semua sectPr + batas paragraf dari dokumen (inline + body level)
    2. Untuk setiap section, baca pgNumType (fmt + start_num) dan info header/footer
    3. Cocokkan ke zone preliminary/content berdasarkan format dari metadata
    4. Tiebreaker jika ada dua section dengan format sama: section yang mengandung
       heading BAB = content zone

    Fallback jika metadata.numbering kosong:
    - Section dengan fmt romawi (lowerRoman/upperRoman) → preliminary
    - Section dengan fmt decimal → content

    Returns:
        {
            "preliminary": info_dict | None,
            "content":     info_dict | None,
        }
        di mana info_dict memiliki keys:
            fmt, start_num, location, has_header_page, has_footer_page,
            has_any_page, start_para_idx, end_para_idx
    """
    num = metadata.numbering if metadata else None
    prelim_fmt_exp  = (num.preliminary.format if num and num.preliminary else None)
    content_fmt_exp = (num.content.format     if num and num.content     else None)

    body      = doc.element.body
    para_list = list(doc.paragraphs)
    if not para_list:
        return {"preliminary": None, "content": None}

    para_idx_by_id = {id(p._p): i for i, p in enumerate(para_list)}

    # ── Kumpulkan section boundaries ─────────────────────────────────────────
    raw_sections: list[dict] = []
    prev_end = 0

    for child in body:
        if not (child.tag.endswith('}p') or child.tag == 'p'):
            continue
        pPr = child.find(qn('w:pPr'))
        if pPr is None:
            continue
        sectPr = pPr.find(qn('w:sectPr'))
        if sectPr is None:
            continue
        para_idx = para_idx_by_id.get(id(child))
        if para_idx is None:
            continue
        raw_sections.append({
            "start_para_idx": prev_end,
            "end_para_idx":   para_idx,
            "sectPr":         sectPr,
        })
        prev_end = para_idx + 1

    # Section terakhir (body-level sectPr)
    body_sectPr = body.find(qn('w:sectPr'))
    if body_sectPr is not None:
        raw_sections.append({
            "start_para_idx": prev_end,
            "end_para_idx":   len(para_list) - 1,
            "sectPr":         body_sectPr,
        })

    if not raw_sections:
        return {"preliminary": None, "content": None}

    # ── Baca info tiap section ────────────────────────────────────────────────
    def _sec_info(sec: dict) -> dict:
        sp = sec["sectPr"]
        fmt, start_num = _read_pgNumType(sp)
        has_own_hdr = bool(sp.findall(qn('w:headerReference')))
        has_own_ftr = bool(sp.findall(qn('w:footerReference')))
        has_header_page = False
        has_footer_page = False
        for s in doc.sections:
            if s._sectPr is sp:
                if has_own_hdr:
                    try:
                        has_header_page = _hdrftr_has_page_field(s.header)
                    except Exception:
                        pass
                if has_own_ftr:
                    try:
                        has_footer_page = _hdrftr_has_page_field(s.footer)
                    except Exception:
                        pass
                break
        location: str | None = (
            "HEADER" if has_header_page else
            "FOOTER" if has_footer_page else None
        )
        return {
            "sectPr":          sp,
            "fmt":             fmt,
            "start_num":       start_num,
            "location":        location,
            "has_header_page": has_header_page,
            "has_footer_page": has_footer_page,
            "has_any_page":    has_header_page or has_footer_page,
            "start_para_idx":  sec["start_para_idx"],
            "end_para_idx":    sec["end_para_idx"],
        }

    section_infos = [_sec_info(s) for s in raw_sections]

    # ── Normalisasi format metadata (case-insensitive + alias umum) ───────────
    def _norm_fmt(fmt: str | None) -> str | None:
        if not fmt:
            return fmt
        return _FORMAT_ALIAS.get(fmt.lower(), fmt)

    prelim_fmt_exp  = _norm_fmt(prelim_fmt_exp)
    content_fmt_exp = _norm_fmt(content_fmt_exp)

    # ── Cari BAB 1 sebagai tiebreaker — hanya dari heading level 1 ───────────
    # Penting: hanya paragraf ber-style Heading 1 yang diterima, bukan entri
    # daftar isi yang juga berawalan "BAB" (teks "BAB 1 PENDAHULUAN......1").
    _HEADING_STYLE_KW = ("heading", "judul", "bab")
    bab1_para_idx: int | None = None
    for i, para in enumerate(para_list):
        style_val  = (para.style.name or "").lower()
        text_upper = (para.text or "").strip().upper()
        if not text_upper.startswith("BAB"):
            continue
        # Hanya diterima jika style mengandung kata "heading"/"judul"/"bab"
        # (bukan paragraf biasa seperti entri daftar isi)
        if any(k in style_val for k in _HEADING_STYLE_KW):
            bab1_para_idx = i
            break

    # ── Cocokkan ke zone ──────────────────────────────────────────────────────
    prelim_info:  dict | None = None
    content_info: dict | None = None

    prelim_candidates:  list[dict] = []
    content_candidates: list[dict] = []

    for info in section_infos:
        fmt = _norm_fmt(info["fmt"])
        if prelim_fmt_exp and fmt == prelim_fmt_exp:
            prelim_candidates.append(info)
        elif content_fmt_exp and fmt == content_fmt_exp:
            content_candidates.append(info)
        else:
            # Format tidak cocok dengan keduanya — tebak dari tipe umum
            if not prelim_fmt_exp and fmt in ("lowerRoman", "upperRoman"):
                prelim_candidates.append(info)
            elif not content_fmt_exp and fmt == "decimal":
                content_candidates.append(info)

    # Pilih preliminary: section pertama yang cocok
    prelim_info = prelim_candidates[0] if prelim_candidates else None

    # Pilih content: terapkan tiebreaker via BAB 1 sebelum memilih
    if content_candidates:
        if bab1_para_idx is not None:
            bab_match = next(
                (i for i in content_candidates
                 if i["start_para_idx"] <= bab1_para_idx <= i["end_para_idx"]),
                None,
            )
            content_info = bab_match or content_candidates[0]
        else:
            content_info = content_candidates[0]

    # Fallback 1: gunakan posisi heading BAB 1 jika format match gagal
    if content_info is None and bab1_para_idx is not None:
        for info in section_infos:
            if info["start_para_idx"] <= bab1_para_idx <= info["end_para_idx"]:
                content_info = info
                break

    # Fallback 2: doc.sections[-1] sebagai last resort untuk content zone.
    # Dalam dokumen PKM, section terakhir selalu merupakan section isi (arabic).
    # Ini menangani kasus di mana format pada sectPr tidak cocok dengan metadata.
    if content_info is None and len(doc.sections) >= 1:
        last_sp = doc.sections[-1]._sectPr
        # Cek apakah body sectPr ini sudah ada di section_infos (cegah duplikasi).
        existing = next(
            (info for info in section_infos if info["sectPr"] is last_sp),
            None,
        )
        if existing is not None:
            # Body sectPr sudah dalam section_infos — gunakan langsung
            content_info = {k: v for k, v in existing.items() if k != "sectPr"}
            content_info["fmt"] = _norm_fmt(existing["fmt"]) or existing["fmt"]
        else:
            fmt_last, start_last = _read_pgNumType(last_sp)
            # start_para_idx: tepat setelah section sebelumnya berakhir
            prev_end_idx = (section_infos[-1]["end_para_idx"] + 1
                            if section_infos else 0)
            content_info = {
                "fmt":             _norm_fmt(fmt_last) or fmt_last,
                "start_num":       start_last,
                "location":        None,
                "has_header_page": False,
                "has_footer_page": False,
                "has_any_page":    False,
                "start_para_idx":  prev_end_idx,
                "end_para_idx":    len(para_list) - 1,
            }
            # Coba cek header/footer pada section terakhir
            try:
                last_sec = doc.sections[-1]
                has_own_hdr = bool(last_sp.findall(qn('w:headerReference')))
                has_own_ftr = bool(last_sp.findall(qn('w:footerReference')))
                if has_own_hdr:
                    content_info["has_header_page"] = _hdrftr_has_page_field(last_sec.header)
                if has_own_ftr:
                    content_info["has_footer_page"] = _hdrftr_has_page_field(last_sec.footer)
                content_info["has_any_page"] = (
                    content_info["has_header_page"] or content_info["has_footer_page"]
                )
                content_info["location"] = (
                    "HEADER" if content_info["has_header_page"] else
                    "FOOTER" if content_info["has_footer_page"] else None
                )
            except Exception:
                pass

    if prelim_info is None and content_info is not None and len(section_infos) > 1:
        for info in section_infos:
            if info["end_para_idx"] < content_info["start_para_idx"]:
                prelim_info = info

    return {"preliminary": prelim_info, "content": content_info}


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

        # Klasifikasi section berdasarkan format yang diexpect dari metadata.
        # Lebih andal daripada pendekatan sebelumnya karena tidak bergantung
        # semata-mata pada posisi heading BAB 1 sebagai penanda zone.
        zones        = _classify_sections_by_metadata(doc, metadata)
        prelim_zone  = zones["preliminary"]
        content_zone = zones["content"]

        all_formats: set[str] = set()
        if prelim_zone:
            all_formats.add(prelim_zone["fmt"])
        if content_zone:
            all_formats.add(content_zone["fmt"])

        # ── Preliminary (romawi) ──────────────────────────────────────────────
        if prelim:
            exp_fmt = _FORMAT_ALIAS.get((prelim.format or "").lower(), prelim.format)
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
            exp_fmt = _FORMAT_ALIAS.get((content.format or "").lower(), content.format)
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

    checks.append(ValidationCheckResult(
        category="page_count", field="halaman_inti",
        status="skipped",
        message="Pengecekan jumlah halaman inti dilewati: mekanisme penghitungan halaman tidak tersedia",
        skip_reason="page counting mechanism removed",
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
            and (m := _BAB_RE.match(para.text.strip().upper())) is not None
            and int(m.group(1)) == target_num
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
    report  = build_report(entries, docx_path=path)

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
    body_issues, body_checks         = _check_body_content(path, metadata)

    all_issues = (issues + case_issues + struct_issues + fig_issues
                  + caption_issues + lampiran_issues + num_issues
                  + pgcount_issues + body_issues)
    all_checks = (checks + case_checks + struct_checks + fig_checks
                  + caption_checks + lampiran_checks + num_checks
                  + pgcount_checks + body_checks)
    return all_issues, all_checks
