"""Shared constants and helper functions used across all check modules. Keyword: automated document validation"""
from __future__ import annotations

import io
import logging
import re
import threading

from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml.ns import qn

from model_ai.validation.models import ValidationCheckResult, ValidationIssue



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
_LAMPIRAN_ITEM_RE = re.compile(r'^Lampiran\s+(\d+)\.\s', re.IGNORECASE)
_LAMPIRAN_BROAD_RE = re.compile(r'^Lampiran\s+\d+', re.IGNORECASE)
_UNREALISTIC_PAGE_FACTOR = 10
_VALIDOCX_LOG_NAMESPACE = "model_ai.validation.validocx"

_TOC_TOF_STYLE_NAMES: frozenset[str] = frozenset({
    "table of figures",
    "TOC 1", "TOC 2", "TOC 3", "TOC 4", "TOC 5",
    "toc 1", "toc 2", "toc 3", "toc 4", "toc 5",
})

_HEADING_TITLE_MAP_INV: dict[str, str] = {v: k for k, v in _HEADING_TITLE_MAP.items()}

_FORMAT_ALIAS: dict[str, str] = {
    "arabic":      "decimal",
    "number":      "decimal",
    "roman":       "lowerRoman",
    "lowerroman":  "lowerRoman",
    "upperroman":  "upperRoman",
    "lowerletter": "lowerLetter",
    "upperletter": "upperLetter",
}

_FIG_DETECT_RE  = re.compile(r'^Gambar\s+\d+', re.IGNORECASE)
_TBL_DETECT_RE  = re.compile(r'^Tabel\s+\d+',  re.IGNORECASE)
_LAMP_DETECT_RE = re.compile(r'^Lampiran\s+',   re.IGNORECASE)

_CAPTION_ALIGN_MAP: dict[str, "WD_ALIGN_PARAGRAPH"] = {
    "CENTER":  WD_ALIGN_PARAGRAPH.CENTER,
    "LEFT":    WD_ALIGN_PARAGRAPH.LEFT,
    "RIGHT":   WD_ALIGN_PARAGRAPH.RIGHT,
    "JUSTIFY": WD_ALIGN_PARAGRAPH.JUSTIFY,
}

_HEADING_STYLE_KEYWORDS: frozenset[str] = frozenset({"heading", "judul"})

_NUM_FORMAT_DISPLAY: dict[str, str] = {
    "lowerRoman": "romawi kecil (i, ii, iii, ...)",
    "upperRoman": "romawi besar (I, II, III, ...)",
    "decimal":    "angka arab (1, 2, 3, ...)",
    "lowerLetter": "huruf kecil (a, b, c, ...)",
    "upperLetter": "huruf besar (A, B, C, ...)",
}

_ALIGNMENT_LABELS: dict[str, str] = {
    "0": "rata kiri (LEFT)",
    "1": "rata tengah (CENTER)",
    "2": "rata kanan (RIGHT)",
    "3": "rata kanan-kiri (JUSTIFY)",
    "LEFT":    "rata kiri (LEFT)",
    "CENTER":  "rata tengah (CENTER)",
    "RIGHT":   "rata kanan (RIGHT)",
    "JUSTIFY": "rata kanan-kiri (JUSTIFY)",
}

_LINE_SPACING_LABELS: dict[str, str] = {
    "1.0":  "1.0 (spasi tunggal)",
    "1.15": "1.15",
    "1.5":  "1.5 (satu setengah)",
    "2.0":  "2.0 (spasi ganda)",
}

_ALIGN_LABEL: dict[int, str] = {0: "LEFT", 1: "CENTER", 2: "RIGHT", 3: "JUSTIFY"}



def _build_lampiran_re(separator: str | None) -> re.Pattern:
    """Bangun regex deteksi judul lampiran berdasarkan separator dari metadata.

    separator="."  → r'^Lampiran\\s+(\\d+)\\.\\s'  ("Lampiran 1. Judul")
    separator=""   → r'^Lampiran\\s+(\\d+)\\s'       ("Lampiran 1 Judul")
    separator=None → pakai default (titik)

    PENTING: \\d+ HARUS dibungkus capture group agar _classify_heading bisa
    memanggil m.group(1) tanpa IndexError.
    """
    sep = separator if separator is not None else "."
    if sep:
        escaped = re.escape(sep)
        pattern = rf'^Lampiran\s+(\d+){escaped}\s'
    else:
        pattern = r'^Lampiran\s+(\d+)\s'
    return re.compile(pattern, re.IGNORECASE)


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
        label = _ALIGNMENT_LABELS.get(raw_value.strip()) or _ALIGNMENT_LABELS.get(key)
        if label:
            return label

    if "line_spacing" in attr_lower or "spacing" in attr_lower:
        try:
            rounded = f"{float(raw_value.strip()):.2f}".rstrip("0").rstrip(".")
            label = _LINE_SPACING_LABELS.get(rounded) or _LINE_SPACING_LABELS.get(raw_value.strip())
            if label:
                return label
            return rounded
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
    """Tentukan category/field untuk value_mismatch berdasarkan key report.

    Format key: "StyleName.attr: actual=X expected=Y"
    Deteksi heading dari nama style sebelum titik pertama.
    """
    parts = key.split(".", 1)
    style_part = parts[0].strip().lower() if len(parts) > 1 else ""
    attr_part  = parts[1].split(":")[0].strip() if len(parts) > 1 else key

    if attr_part in _SECTION_ATTR_KEYS or key.lstrip().startswith("'Section"):
        return "page_layout", "section_attribute"

    spacing_attrs = {"alignment", "line_spacing", "space_before", "space_after"}
    is_spacing  = any(a in attr_part.lower() for a in spacing_attrs)
    is_heading  = any(k in style_part for k in _HEADING_STYLE_KEYWORDS)

    if is_heading:
        return ("spacing", "heading_attribute") if is_spacing else ("typography", "heading_attribute")
    return ("spacing", "body_attribute") if is_spacing else ("typography", "body_attribute")


class _ThreadFilter(logging.Filter):
    """Hanya terima log record dari thread yang membuat filter ini.

    Dipasang pada setiap handler di _capture_log sehingga dalam skenario
    multi-user, log validasi milik thread A tidak bocor ke buffer milik
    thread B dan sebaliknya.
    """

    def __init__(self) -> None:
        super().__init__()
        self._tid = threading.current_thread().ident

    def filter(self, record: logging.LogRecord) -> bool:
        return threading.current_thread().ident == self._tid


def _capture_log(docx_path, requirements: dict, validate_fn, doc=None) -> str:
    """Jalankan validocx dan capture seluruh log (termasuk multi-line) ke string.

    doc: objek Document yang sudah dibuka — jika diberikan, validocx tidak membuka
         ulang file dari disk sehingga menghemat satu siklus ZIP decompress + XML parse.
    """
    from pathlib import Path
    buf = io.StringIO()
    handler = logging.StreamHandler(buf)
    handler.setFormatter(logging.Formatter(
        "%(asctime)s.%(msecs)03d %(levelname)s (%(module)s) %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    ))
    handler.addFilter(_ThreadFilter())

    target = logging.getLogger(_VALIDOCX_LOG_NAMESPACE)
    orig_level = target.level
    target.addHandler(handler)
    target.setLevel(logging.INFO)

    try:
        validate_fn(str(docx_path), requirements, doc=doc)
    finally:
        target.removeHandler(handler)
        target.setLevel(orig_level)

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
        if not (detail.get("text") or "").strip():
            continue
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

    para_attrs = normal.get("paragraph", {}).get("attributes", {})
    if isinstance(para_attrs, dict):
        ls = para_attrs.get("line_spacing")
        if ls is not None:
            parts.append(f"Spasi: {ls}")

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
    import re as _re
    issues: list[ValidationIssue] = []
    checks: list[ValidationCheckResult] = []

    for item in report["errors"].get("section_missing", []):
        msg = item.get("message", "Section attribute missing")
        attr_m = _re.search(r"'([^']+)'", msg)
        expected_attr = attr_m.group(1) if attr_m else "attribute"
        occ_sec_missing = _build_occurrences(
            [{"text": msg[:100], "full_text": msg, "style": "",
              "page": None, "bab": None, "para_idx": None,
              "actual": "Tidak ada"}],
            actual_str="Tidak ada", expected_str=expected_attr,
        ) or None
        issues.append(ValidationIssue(
            category="page_layout", field="section_missing",
            severity="error", message=msg,
            expected=expected_attr, actual="Tidak ada",
        ))
        checks.append(ValidationCheckResult(
            category="page_layout", field="section_missing",
            status="failed", message=msg,
            expected=expected_attr, actual="Tidak ada",
            occurrences=occ_sec_missing,
        ))

    for item in report["errors"].get("value_mismatch", []):
        key = item.get("key", "")
        count = item.get("count", 1)
        examples = item.get("examples", [])
        paras = item.get("paragraph_details", []) or item.get("paragraphs", [])
        category, field = _vm_category(key)
        location = _para_location(paras) if isinstance(paras, list) and paras and isinstance(paras[0], dict) else None

        example_str = f' Contoh: "{examples[0]}"' if examples else ""
        msg = f"{key} ({count}x mismatch).{example_str}"

        vm_actual = _re.search(r"actual=(\S+)", key)
        vm_expected = _re.search(r"expected=(\S+)", key)
        vm_actual_raw = vm_actual.group(1) if vm_actual else None
        vm_expected_raw = vm_expected.group(1) if vm_expected else None

        attr_match = _re.search(r"\.(\w+)\s*:", key)
        attr_name = attr_match.group(1) if attr_match else ""

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
            expected=vm_expected_str, actual=vm_actual_str,
            occurrences=occurrences,
        ))

    for item in report["errors"].get("font_mismatch", []):
        key = item.get("key", "")
        count = item.get("count", 1)
        examples = item.get("examples", [])
        paras = item.get("paragraph_details", []) or item.get("paragraphs", [])
        location = _para_location(paras) if isinstance(paras, list) and paras and isinstance(paras[0], dict) else None

        example_str = f' Contoh: "{examples[0]}"' if examples else ""
        msg = f"Font mismatch: {key} ({count}x).{example_str}"

        fm_actual = _re.search(r"actual=\[([^\]]+)\]", key)
        fm_expected = _re.search(r"expected=\[([^\]]+)\]", key)
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
            expected=fm_expected_str, actual=fm_actual_str,
            occurrences=occurrences,
        ))

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
            severity="error", message=msg,
            occurrences=occurrences,
        ))
        checks.append(ValidationCheckResult(
            category="typography", field="undefined_style",
            status="failed", message=msg,
            expected=normal_fmt_label, actual=style,
            occurrences=occurrences,
        ))

    for item in report["warnings"].get("attr_inherited", []):
        attr = item.get("attribute", "?")
        count = item.get("count", 1)
        paras = item.get("paragraph_details", []) or []
        msg = f"Atribut '{attr}' tidak di-set eksplisit (diwarisi dari Word default), {count}x"

        valid_paras = _coerce_paras(paras)
        occurrences = _build_occurrences(valid_paras, actual_str="inherited", expected_str="explicit") or None

        issues.append(ValidationIssue(
            category="spacing", field="paragraph_inherited",
            severity="error", message=msg,
            occurrences=occurrences,
        ))
        checks.append(ValidationCheckResult(
            category="spacing", field="paragraph_inherited",
            status="failed", message=msg,
            expected="explicit", actual="inherited",
            occurrences=occurrences,
        ))


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
