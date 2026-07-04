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
    "ABSTRAK": "abstrak",
    "ABSTRACT": "abstract",
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
    "0": "LEFT",
    "1": "CENTER",
    "2": "RIGHT",
    "3": "JUSTIFY",
    "LEFT":    "LEFT",
    "CENTER":  "CENTER",
    "RIGHT":   "RIGHT",
    "JUSTIFY": "JUSTIFY",
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


def _build_bab_re(chapter_format: str | None) -> re.Pattern:
    """Bangun regex deteksi heading BAB berdasarkan chapter_format dari metadata.

    chapter_format="{n}."   → r'^(\\d+)\\.'   cocok "1.", "2.", ...
    chapter_format="BAB {n}" → r'^BAB\\ (\\d+)' cocok "BAB 1", "BAB 2", ...
    chapter_format=None     → fallback ke _BAB_RE default

    PENTING: {n} HARUS diganti dengan capture group (\\d+) agar m.group(1) valid.
    """
    if not chapter_format or "{n}" not in chapter_format:
        return _BAB_RE
    escaped = re.escape(chapter_format)
    pattern = escaped.replace(r'\{n\}', r'(\d+)')
    # Jika format diakhiri titik (mis. "{n}."), tambah negative lookahead
    # agar "1.1" (sub-bab) tidak ikut cocok sebagai BAB.
    if chapter_format.endswith('.'):
        pattern += r'(?!\d)'
    return re.compile(f'^{pattern}', re.IGNORECASE)


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
        # Per-detail actual (misal: font per paragraf) lebih spesifik dari actual_str
        # (gabungan semua nilai). Gunakan detail.get("actual") jika tersedia.
        item_actual   = detail.get("actual") if detail.get("actual") is not None else actual_str
        # run_text: teks spesifik run yang gagal (font mismatch). full_text: teks penuh paragraf.
        _display_text = detail.get("run_text") or detail.get("full_text") or detail.get("text") or ""
        result.append({
            "page"      : detail.get("page"),
            "bab"       : detail.get("bab"),
            "para_idx"  : detail.get("para_idx"),
            "style"     : detail.get("style"),
            "text"      : _display_text[:100],
            "full_text" : _display_text,
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

    # section_missing dan section_attribute tidak ditulis ke issues/checks —
    # keduanya adalah isu document-level tanpa konteks paragraf yang actionable.

    # value_mismatch — agregasi per (category, field) agar label tidak duplikat
    _vm_grp: dict = {}
    for item in report["errors"].get("value_mismatch", []):
        _vk  = item.get("key", "")
        _vc  = item.get("count", 1)
        _vp  = item.get("paragraph_details", []) or item.get("paragraphs", [])
        _vcat, _vfld = _vm_category(_vk)

        _vm_act_m  = _re.search(r"actual=(\S+)", _vk)
        _vm_exp_m  = _re.search(r"expected=(\S+)", _vk)
        _vm_attr_m = _re.search(r"\.(\w+)\s*:", _vk)
        _vm_attr   = _vm_attr_m.group(1) if _vm_attr_m else ""
        _vm_act_s  = _humanize_attr_value(_vm_attr, _vm_act_m.group(1) if _vm_act_m else None)
        _vm_exp_s  = _humanize_attr_value(_vm_attr, _vm_exp_m.group(1) if _vm_exp_m else None)

        _valid = _coerce_paras(_vp)
        _ann   = [{**p, "actual": _vm_act_s} if isinstance(p, dict) and not p.get("actual") else p
                  for p in _valid]

        _gk = (_vcat, _vfld)
        if _gk not in _vm_grp:
            _vm_grp[_gk] = {"count": 0, "paras": [], "attr_names": [], "expected_strs": set()}
        _g = _vm_grp[_gk]
        _g["count"]    += _vc
        _g["paras"].extend(_ann)
        if _vm_attr:  _g["attr_names"].append(_vm_attr)
        if _vm_exp_s: _g["expected_strs"].add(_vm_exp_s)

    _SKIP_VM_FIELDS = {"section_attribute", "section_missing"}
    for (_vcat2, _vfld2), _gd in _vm_grp.items():
        if _vfld2 in _SKIP_VM_FIELDS:
            continue
        _vm_seen: set = set()
        _vm_dd:   list = []
        for _p in _gd["paras"]:
            if not isinstance(_p, dict): continue
            _pk = (_p.get("para_idx"), (_p.get("text") or "")[:40])
            if _pk not in _vm_seen:
                _vm_seen.add(_pk)
                _vm_dd.append(_p)
        _vl  = _para_location(_vm_dd) if _vm_dd and isinstance(_vm_dd[0], dict) else None
        _ve  = ", ".join(sorted(_gd["expected_strs"])) or None
        _va  = ", ".join(sorted({p["actual"] for p in _vm_dd
                                  if isinstance(p, dict) and p.get("actual")})) or None
        _ad  = ", ".join(sorted(set(_gd["attr_names"]))) or "atribut"
        _vm2 = f"Atribut tidak sesuai ({_ad}): {_gd['count']} elemen"
        _vo  = _build_occurrences(_vm_dd, None, _ve) or None

        issues.append(ValidationIssue(
            category=_vcat2, field=_vfld2,
            severity="error", message=_vm2, location=_vl,
            occurrences=_vo,
        ))
        checks.append(ValidationCheckResult(
            category=_vcat2, field=_vfld2,
            status="failed", message=_vm2, location=_vl,
            expected=_ve, actual=_va,
            occurrences=_vo,
        ))

    _font_mismatch_items = report["errors"].get("font_mismatch", [])
    if _font_mismatch_items:
        import math as _math
        from collections import defaultdict as _defaultdict

        _BOOL_FONT_ATTRS = {"bold"}

        def _split_font_attrs(attr_str: str):
            sizes, families, bools = [], [], []
            for p in (x.strip() for x in attr_str.split(",") if x.strip()):
                try:
                    sizes.append(float(p))
                except ValueError:
                    (bools if p.lower() in _BOOL_FONT_ATTRS else families).append(p)
            return sizes, families, bools

        def _size_ok(es: float, acts: list) -> bool:
            return any(_math.isclose(es, a, rel_tol=0.02) for a in acts) if acts else False

        _attr_grp = _defaultdict(lambda: {"actual": [], "expected": [], "paras": [], "count": 0})

        for _fmi in _font_mismatch_items:
            _key    = _fmi.get("key", "")
            _count  = _fmi.get("count", 1)
            _paras  = _fmi.get("paragraph_details", []) or _fmi.get("paragraphs", [])
            _valid  = _coerce_paras(_paras)
            _ma = _re.search(r"actual=\[([^\]]+)\]", _key)
            _me = _re.search(r"expected=\[([^\]]+)\]", _key)
            if not _ma or not _me:
                continue

            act_sz, act_fm, act_bl = _split_font_attrs(_ma.group(1))
            exp_sz, exp_fm, exp_bl = _split_font_attrs(_me.group(1))

            # Font family
            if any(ef not in act_fm for ef in exp_fm):
                g = _attr_grp["body_font_family"]
                g["count"] += _count
                _act_fm_str = ", ".join(act_fm) if act_fm else None
                for _p in _valid:
                    # Annotasi grup actual ke setiap dict agar per-occurrence akurat
                    g["paras"].append({**_p, "group_actual": _act_fm_str})
                for v in act_fm:
                    if v not in g["actual"]: g["actual"].append(v)
                for v in exp_fm:
                    if v not in g["expected"]: g["expected"].append(v)

            # Font size
            if any(not _size_ok(es, act_sz) for es in exp_sz):
                g = _attr_grp["body_font_size"]
                g["count"] += _count
                _act_sz_str = ", ".join(f"{v:g}pt" for v in act_sz) if act_sz else None
                for _p in _valid:
                    g["paras"].append({**_p, "group_actual": _act_sz_str})
                for v in act_sz:
                    s = f"{v:g}pt"
                    if s not in g["actual"]: g["actual"].append(s)
                for v in exp_sz:
                    s = f"{v:g}pt"
                    if s not in g["expected"]: g["expected"].append(s)

            # Bool attrs: bold, italic, underline, all_caps
            for eb in exp_bl:
                if eb not in act_bl:
                    g = _attr_grp[f"body_{eb}"]
                    g["count"] += _count
                    _act_bl_str = ", ".join(act_bl) if act_bl else f"tidak {eb}"
                    for _p in _valid:
                        g["paras"].append({**_p, "group_actual": _act_bl_str})
                    for v in act_bl:
                        if v not in g["actual"]: g["actual"].append(v)
                    if eb not in g["expected"]: g["expected"].append(eb)

        _FONT_LABELS = {
            "body_font_family": "Jenis huruf (font family)",
            "body_font_size":   "Ukuran huruf (font size)",
            "body_bold":        "Tebal (bold)",
        }

        for _field, _data in _attr_grp.items():
            _actual_str   = ", ".join(_data["actual"])   or None
            _expected_str = ", ".join(_data["expected"]) or None
            _label = _FONT_LABELS.get(_field, _field)
            # Dedup per (para_idx, run_text_prefix) agar satu paragraf dengan
            # beberapa run bermasalah (font berbeda) tetap menghasilkan occurrence terpisah.
            _seen: set = set()
            _deduped: list = []
            for p in _data["paras"]:
                if not isinstance(p, dict):
                    continue
                _rt_prefix = (p.get("run_text") or "")[:40]
                _pid_key   = (p.get("para_idx"), _rt_prefix)
                if _pid_key not in _seen:
                    _seen.add(_pid_key)
                    _deduped.append(p)

            # Gunakan group_actual (font dari group fm_key masing-masing) sebagai
            # actual per-occurrence, lebih akurat dari penggabungan semua font salah.
            for _pd in _deduped:
                if not isinstance(_pd, dict) or _pd.get("actual") is not None:
                    continue
                _ga = _pd.get("group_actual")
                if _ga:
                    _pd["actual"] = _ga

            _occurrences = _build_occurrences(_deduped, _actual_str, _expected_str) or None
            _location    = _para_location(_deduped) if _deduped and isinstance(_deduped[0], dict) else None
            _msg = (
                f"{_label} tidak sesuai: {_data['count']} elemen. "
                f"Ditemukan: {_actual_str or '?'}, Seharusnya: {_expected_str or '?'}"
            )
            issues.append(ValidationIssue(
                category="typography", field=_field,
                severity="error", message=_msg, location=_location,
                occurrences=_occurrences,
            ))
            checks.append(ValidationCheckResult(
                category="typography", field=_field,
                status="failed", message=_msg, location=_location,
                expected=_expected_str, actual=_actual_str,
                occurrences=_occurrences,
            ))

    normal_fmt_label = _normal_formatting_label(requirements) if requirements else None

    # undefined_styles — agregasi semua style tidak dikenal ke satu entry
    _undef_total = 0
    _undef_styles: list = []
    _undef_paras: list = []
    for item in report["warnings"].get("undefined_styles", []):
        _us = item.get("style", "?")
        _uc = item.get("count", 1)
        _undef_total += _uc
        _undef_styles.append(_us)
        _up = _coerce_paras(item.get("paragraph_details", []) or [])
        _undef_paras.extend([{**p, "actual": _us} if isinstance(p, dict) and not p.get("actual") else p
                              for p in _up])
    if _undef_total > 0:
        _undef_seen: set = set()
        _undef_dd:   list = []
        for _p in _undef_paras:
            if not isinstance(_p, dict): continue
            _pk = (_p.get("para_idx"), (_p.get("text") or "")[:40])
            if _pk not in _undef_seen:
                _undef_seen.add(_pk)
                _undef_dd.append(_p)
        _us_names = ", ".join(sorted(set(_undef_styles)))
        _us_msg   = f"Style tidak terdefinisi di requirements ({_us_names}): {_undef_total} elemen"
        _us_occ   = _build_occurrences(_undef_dd, actual_str=None, expected_str=normal_fmt_label) or None
        issues.append(ValidationIssue(
            category="typography", field="undefined_style",
            severity="error", message=_us_msg,
            occurrences=_us_occ,
        ))
        checks.append(ValidationCheckResult(
            category="typography", field="undefined_style",
            status="failed", message=_us_msg,
            expected=normal_fmt_label, actual=_us_names,
            occurrences=_us_occ,
        ))

    # attr_inherited tidak ditulis ke issues/checks — paragraf yang atributnya
    # diwarisi dari Word default tidak actionable tanpa konteks yang lebih spesifik.


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
