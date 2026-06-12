"""
validocx/debug_report.py
Parse log validasi dan hasilkan laporan debugging dalam format JSON.
"""

import json
import re
from collections import defaultdict

# ── Kategori ───────────────────────────────────────────────────────────────
CAT_CHECK           = "CHECK"
CAT_ATTR_INHERITED  = "ATTR INHERITED (not explicit)"   # WARNING — bukan error nyata
CAT_VALUE_MISMATCH  = "VALUE MISMATCH"
CAT_FONT_MISMATCH   = "FONT MISMATCH"
CAT_UNDEF_STYLE     = "UNDEFINED STYLE"
CAT_SECTION_MISSING = "SECTION MISSING"
CAT_INFO            = "INFO"

LOG_PATTERN = re.compile(
    r"\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}\.\d+ (INFO|WARNING|ERROR) \(\w+\) (.+)"
)


def categorize(msg):
    if msg.startswith("CHECK "):
        return CAT_CHECK
    if "is not set explicitly (inherited from Word default)" in msg:
        return CAT_ATTR_INHERITED
    if "does not match required value" in msg:
        return CAT_VALUE_MISMATCH
    if "Font attributes" in msg and "mismatch required" in msg:
        return CAT_FONT_MISMATCH
    if "Undefined style" in msg:
        return CAT_UNDEF_STYLE
    if "requirements for 'Section" in msg and "not specified" in msg:
        return CAT_SECTION_MISSING
    return CAT_INFO


def parse_entries(text):
    """Parse teks log (string) → list of (level, category, message)."""
    entries = []
    current_level = None
    current_msg   = None

    for raw in text.splitlines():
        line = raw.rstrip()
        m = LOG_PATTERN.match(line)
        if m:
            if current_msg is not None:
                entries.append((current_level, categorize(current_msg), current_msg))
            current_level = m.group(1)
            current_msg   = m.group(2)
        else:
            if current_msg is not None:
                current_msg += " " + line.strip()

    if current_msg is not None:
        entries.append((current_level, categorize(current_msg), current_msg))

    return entries


def parse_entries_from_file(path):
    """Parse dari file log langsung."""
    with open(path, encoding="utf-8", errors="replace") as f:
        return parse_entries(f.read())


def _get_para_details(docx_path):
    """Muat semua paragraf dari docx, kembalikan dict {idx: detail}.

    Setiap entri menyertakan:
      - bab  : teks Heading 1 terakhir sebelum paragraf ini (atau None)

    PENTING: menggunakan DocumentWrapper.iter_paragraphs() — sama persis dengan
    yang dipakai validator.py saat membangun para_idx di log CHECK. Ini memastikan
    indeks di sini selaras dengan indeks yang ditulis ke log, termasuk paragraf
    di dalam w:sdt (misalnya TOC yang dibuat otomatis oleh Word).
    """
    try:
        from docx import Document
        from model_ai.validation.validocx.wrapper import DocumentWrapper

        doc     = Document(docx_path)
        wrapper = DocumentWrapper(doc)

        result      = {}
        current_bab = None

        for idx, para in enumerate(wrapper.iter_paragraphs()):
            style_name = para.style.name
            text       = para.text.strip()

            if style_name == "Heading 1" and text:
                current_bab = text

            pf    = para.paragraph_format
            ls    = pf.line_spacing
            rule  = str(pf.line_spacing_rule) if pf.line_spacing_rule else "inherited"
            align = str(pf.alignment) if pf.alignment else "inherited"

            runs = []
            for r in para.runs:
                size  = round(r.font.size.pt, 1) if r.font.size else None
                name  = r.font.name or None
                attrs = [a for a in ("bold", "italic", "underline", "all_caps")
                         if getattr(r.font, a)]
                runs.append({
                    "text"      : r.text[:60],
                    "font_size" : size,
                    "font_name" : name,
                    "attributes": attrs,
                })

            result[idx] = {
                "style"       : style_name,
                "alignment"   : align,
                "line_spacing": float(ls) if ls is not None else None,
                "spacing_rule": rule,
                "text"        : text[:100],
                "full_text"   : text,
                "runs"        : runs,
                "bab"         : current_bab,
            }

        return result
    except Exception:
        return {}


def _extract_paragraph_text(msg):
    """Ambil teks paragraf dari pesan log (dalam tanda kutip terakhir)."""
    m = re.search(r":\s*\n?'([^']*)'$", msg)
    return m.group(1).strip() if m else ""


def _extract_para_idx(msg):
    """Ambil nomor paragraf dari tag [para#N] di awal pesan."""
    m = re.search(r"\[para#(\d+)\]", msg)
    return int(m.group(1)) if m else None


def _dedup(items, key_fn):
    """Deduplikasi list pesan, kembalikan list {count, paragraphs, examples}."""
    counts = defaultdict(lambda: {"count": 0, "paragraphs": [], "examples": []})
    for item in items:
        key = key_fn(item)
        counts[key]["count"] += 1

        # Simpan nomor paragraf
        idx = _extract_para_idx(item)
        if idx is not None and idx not in counts[key]["paragraphs"]:
            counts[key]["paragraphs"].append(idx)

        # Simpan contoh teks (max 3)
        text = _extract_paragraph_text(item)
        if text and text not in counts[key]["examples"] and len(counts[key]["examples"]) < 3:
            counts[key]["examples"].append(text)

    return sorted(
        [{"key": k, **v} for k, v in counts.items()],
        key=lambda x: -x["count"]
    )


def _build_parameter_summary(check_msgs):
    """
    Parse semua CHECK log dan bangun ringkasan per parameter.

    Format log CHECK:
      CHECK [para#N] font (Style) PASS
      CHECK [para#N] font (Style) FAIL missing=X,Y
      CHECK [para#N] alignment (Style) PASS
      CHECK [para#N] alignment (Style) FAIL actual=V expected=W
      CHECK [para#N] line_spacing (Style) INHERITED
    """
    # key = "parameter (Style)", value = {pass, fail, inherited, paragraphs_pass, paragraphs_fail}
    summary = defaultdict(lambda: {
        "pass": 0, "fail": 0, "inherited": 0,
        "paragraphs_pass": [], "paragraphs_fail": [],
    })

    for msg in check_msgs:
        # Ambil para_idx, parameter, style, dan hasil
        m = re.search(r"CHECK \[para#(\d+)\] (\S+) \(([^)]+)\) (PASS|FAIL|INHERITED)", msg)
        if not m:
            continue
        para_idx_str, param, style, result = m.group(1), m.group(2), m.group(3), m.group(4)
        key = f"{param} ({style})"
        summary[key][result.lower()] += 1
        para_idx = int(para_idx_str)
        if result == "PASS":
            if para_idx not in summary[key]["paragraphs_pass"]:
                summary[key]["paragraphs_pass"].append(para_idx)
        elif result == "FAIL":
            if para_idx not in summary[key]["paragraphs_fail"]:
                summary[key]["paragraphs_fail"].append(para_idx)

    result_list = []
    for key, counts in sorted(summary.items()):
        total  = counts["pass"] + counts["fail"] + counts["inherited"]
        status = ("lolos semua" if counts["fail"] == 0 and counts["inherited"] == 0
                  else "lolos semua (ada inherited)" if counts["fail"] == 0
                  else "ada yang gagal")
        result_list.append({
            "parameter"      : key,
            "status"         : status,
            "total"          : total,
            "pass"           : counts["pass"],
            "fail"           : counts["fail"],
            "inherited"      : counts["inherited"],
            "paragraphs_pass": counts["paragraphs_pass"],
            "paragraphs_fail": counts["paragraphs_fail"],
        })

    return result_list


def _inject_para_details(items, para_map):
    """Tambahkan field 'paragraph_details' ke setiap item berdasarkan paragraphs list."""
    for item in items:
        details = []
        for idx in item.get("paragraphs", []):
            if idx in para_map:
                details.append({"para_idx": idx, **para_map[idx]})
        item["paragraph_details"] = details
    return items


def build_report(entries, docx_path=None, para_map=None):
    """Bangun laporan dalam format dict (siap di-serialize ke JSON).

    docx_path: opsional — jika diberikan, detail isi paragraf akan
               disertakan langsung di dalam setiap entri error/warning.
               Diabaikan jika para_map sudah diberikan secara eksplisit.
    para_map:  opsional — dict {idx: detail} yang sudah dibangun dari luar.
               Jika diberikan, docx_path tidak dipakai untuk membangun para_map.
    """
    if para_map is None:
        para_map = _get_para_details(docx_path) if docx_path else {}

    buckets = defaultdict(list)
    for level, cat, msg in entries:
        if cat != CAT_INFO:
            buckets[cat].append(msg)

    total_errors   = sum(1 for l, _, __ in entries if l == "ERROR")
    total_warnings = sum(1 for l, _, __ in entries if l == "WARNING")

    # ── Section missing ────────────────────────────────────────────────────
    section_missing = [
        {"message": msg}
        for msg in buckets.get(CAT_SECTION_MISSING, [])
    ]

    # ── Value mismatch ─────────────────────────────────────────────────────
    def vm_key(msg):
        # format: "[para#N] ...paragraph 'ATTR' (STYLE) with value VAL does not match..."
        # [^']+ agar nama atribut boleh mengandung karakter non-word (future-proof).
        # (.+?) non-greedy agar style name boleh mengandung tanda kurung nested,
        # mis. "Custom (Style 2)" — anchored oleh ") with value" di sebelah kanannya.
        m = re.search(
            r"paragraph '([^']+)' \((.+?)\) with value (.+?) does not match required value (.+?):",
            msg,
        )
        if m:
            return f"{m.group(2)}.{m.group(1)}: actual={m.group(3).strip()} expected={m.group(4).strip()}"
        return msg

    value_mismatch = _dedup(buckets.get(CAT_VALUE_MISMATCH, []), vm_key)

    # ── Font mismatch ──────────────────────────────────────────────────────
    def fm_key(msg):
        # format: "[para#N] Font attributes (A,B) mismatch required (X,Y)..."
        # (.+?) non-greedy agar nilai font boleh mengandung tanda kurung.
        m = re.search(
            r"Font attributes \((.+?)\) mismatch required \((.+?)\).*style '([^']+)'",
            msg,
        )
        if m:
            return f"{m.group(3)}: actual=[{m.group(1)}] expected=[{m.group(2)}]"
        return msg

    font_mismatch = _dedup(buckets.get(CAT_FONT_MISMATCH, []), fm_key)

    # ── Undefined styles ───────────────────────────────────────────────────
    undef_data = defaultdict(lambda: {"count": 0, "paragraphs": []})
    for msg in buckets.get(CAT_UNDEF_STYLE, []):
        m = re.search(r"'([^']+)'", msg)
        if m:
            key = m.group(1)
            undef_data[key]["count"] += 1
            idx = _extract_para_idx(msg)
            if idx is not None and idx not in undef_data[key]["paragraphs"]:
                undef_data[key]["paragraphs"].append(idx)
    undefined_styles = [
        {"style": s, **v}
        for s, v in sorted(undef_data.items(), key=lambda x: -x[1]["count"])
    ]

    # ── Attr inherited ─────────────────────────────────────────────────────
    inh_data = defaultdict(lambda: {"count": 0, "paragraphs": []})
    for msg in buckets.get(CAT_ATTR_INHERITED, []):
        m = re.search(r"paragraph '([\w_]+)' \(([\w ]+)\)", msg)
        if m:
            key = f"{m.group(2)}.{m.group(1)}"
            inh_data[key]["count"] += 1
            idx = _extract_para_idx(msg)
            if idx is not None and idx not in inh_data[key]["paragraphs"]:
                inh_data[key]["paragraphs"].append(idx)
    attr_inherited = [
        {"attribute": k, **v}
        for k, v in sorted(inh_data.items(), key=lambda x: -x[1]["count"])
    ]

    # ── Parameter summary ──────────────────────────────────────────────────
    parameter_summary = _build_parameter_summary(buckets.get(CAT_CHECK, []))

    # Inject detail paragraf jika docx tersedia
    if para_map:
        value_mismatch  = _inject_para_details(value_mismatch,  para_map)
        font_mismatch   = _inject_para_details(font_mismatch,   para_map)
        undefined_styles= _inject_para_details(undefined_styles,para_map)
        attr_inherited  = _inject_para_details(attr_inherited,  para_map)
        for item in parameter_summary:
            details_pass = []
            for idx in item.get("paragraphs_pass", []):
                if idx in para_map:
                    details_pass.append({"para_idx": idx, **para_map[idx]})
            item["paragraph_details_pass"] = details_pass

            details_fail = []
            for idx in item.get("paragraphs_fail", []):
                if idx in para_map:
                    details_fail.append({"para_idx": idx, **para_map[idx]})
            item["paragraph_details_fail"] = details_fail

    report = {
        "summary": {
            "total_error"   : total_errors,
            "total_warning" : total_warnings,
            "counts": {
                "section_missing" : len(section_missing),
                "value_mismatch"  : len(buckets.get(CAT_VALUE_MISMATCH, [])),
                "font_mismatch"   : len(buckets.get(CAT_FONT_MISMATCH, [])),
                "undefined_style" : len(buckets.get(CAT_UNDEF_STYLE, [])),
                "attr_inherited"  : len(buckets.get(CAT_ATTR_INHERITED, [])),
            }
        },
        "errors": {
            "section_missing" : section_missing,
            "value_mismatch"  : value_mismatch,
            "font_mismatch"   : font_mismatch,
        },
        "warnings": {
            "undefined_styles": undefined_styles,
            "attr_inherited"  : attr_inherited,
        },
        "parameter_summary": parameter_summary,
    }

    return report


# ── Standalone usage ───────────────────────────────────────────────────────
if __name__ == "__main__":
    import argparse, io, sys
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

    p = argparse.ArgumentParser(description="Parse log validasi menjadi debug report JSON.")
    p.add_argument("log",    default="hasil_validasi.log", nargs="?")
    p.add_argument("output", default="debug_report.json",  nargs="?")
    args = p.parse_args()

    entries = parse_entries_from_file(args.log)
    report  = build_report(entries)
    output  = json.dumps(report, indent=2, ensure_ascii=False)

    with open(args.output, "w", encoding="utf-8") as f:
        f.write(output)

    print(output)
    print(f"\n[OK] Report → {args.output}")
