"""Ringkasan naratif hasil validasi dokumen via LLM (Groq primary, Gemini fallback).

Dipakai oleh endpoint POST /api/validation/summarize untuk memberi reviewer
catatan siap-pakai bergaya penilai dosen.
"""
from __future__ import annotations

import time
from typing import Any

from langchain_groq import ChatGroq
from langchain_google_genai import ChatGoogleGenerativeAI

from model_ai.config import get_config

CONFIG = get_config()

MAX_OCCURRENCES_PER_ISSUE = 3
TEXT_PREVIEW_LEN = 80
MAX_RATE_LIMIT_WAIT = 60

# ── Tabel translasi: nilai teknis → bahasa Indonesia yang mudah dipahami ─────

# Alignment (WD_ALIGN_PARAGRAPH: int 0-3 dan nama enum)
_ALIGN_LABEL: dict[str, str] = {
    "0":       "rata kiri",
    "1":       "rata tengah",
    "2":       "rata kanan",
    "3":       "rata kanan-kiri (justify)",
    "left":    "rata kiri",
    "center":  "rata tengah",
    "right":   "rata kanan",
    "justify": "rata kanan-kiri (justify)",
    "none":    "tidak diatur",
    # Dengan tambahan label dari validocx_runner
    "rata kiri (left)":              "rata kiri",
    "rata tengah (center)":          "rata tengah",
    "rata kanan (right)":            "rata kanan",
    "rata kanan-kiri (justify)":     "rata kanan-kiri (justify)",
}

# Line spacing (float string → deskripsi)
_SPACING_LABEL: dict[str, str] = {
    "1.0": "1 spasi (tunggal)",
    "1":   "1 spasi (tunggal)",
    "1.15": "1,15 spasi",
    "1.5": "1,5 spasi",
    "2.0": "2 spasi (ganda)",
    "2":   "2 spasi (ganda)",
}

# Boolean
_BOOL_LABEL: dict[str, str] = {
    "true":  "ya",
    "false": "tidak",
}

# Field name → deskripsi bahasa Indonesia
_FIELD_LABEL: dict[str, str] = {
    # Font
    "font_body":               "font teks isi",
    "font_heading":            "font heading/judul",
    "font_size_body":          "ukuran font teks isi",
    "font_size_heading":       "ukuran font heading",
    "font_family":             "jenis font",
    "font_size":               "ukuran font",
    # Spasi
    "line_spacing":            "spasi baris",
    "line_spacing_body":       "spasi baris teks isi",
    "line_spacing_heading1":   "spasi baris Heading 1",
    "line_spacing_heading2":   "spasi baris Heading 2",
    "line_spacing_heading3":   "spasi baris Heading 3",
    "space_before":            "spasi sebelum paragraf",
    "space_after":             "spasi setelah paragraf",
    # Perataan
    "alignment":               "perataan teks",
    "alignment_body":          "perataan teks isi",
    "alignment_heading":       "perataan heading",
    "alignment_caption":       "perataan caption",
    # Margin
    "margin_top":              "margin atas",
    "margin_bottom":           "margin bawah",
    "margin_left":             "margin kiri",
    "margin_right":            "margin kanan",
    # Halaman
    "halaman_inti":            "jumlah halaman inti",
    "page_size":               "ukuran halaman",
    "page_orientation":        "orientasi halaman",
    "page_numbering":          "penomoran halaman",
    # Struktur
    "heading_level":           "level heading",
    "toc":                     "daftar isi",
    "cover":                   "halaman sampul",
    "abstract":                "abstrak/ringkasan",
    "daftar_pustaka":          "daftar pustaka",
    # Lain-lain
    "bold":                    "tebal (bold)",
    "italic":                  "miring (italic)",
    "underline":               "garis bawah",
    "color":                   "warna teks",
    "highlight":               "sorotan teks",
    "indent":                  "indentasi",
}

# Category → deskripsi bahasa Indonesia
_CATEGORY_LABEL: dict[str, str] = {
    "typography":   "tipografi (font)",
    "spacing":      "spasi",
    "page_layout":  "tata letak halaman",
    "page_count":   "jumlah halaman",
    "structure":    "struktur dokumen",
    "content":      "konten",
    "margin":       "margin",
    "heading":      "heading/judul bab",
    "caption":      "caption (keterangan gambar/tabel)",
    "numbering":    "penomoran",
}


def _humanize_value(raw: Any, hint: str = "") -> Any:
    """Terjemahkan nilai teknis ke deskripsi bahasa Indonesia yang mudah dipahami.

    hint: nama field/atribut untuk membantu konteks translasi
          (mis. "alignment", "line_spacing").
    """
    if raw is None:
        return None

    s = str(raw).strip()
    sl = s.lower()
    hint_l = hint.lower()

    # Boolean
    if sl in _BOOL_LABEL:
        return _BOOL_LABEL[sl]

    # Alignment — berdasarkan hint atau nilai itu sendiri
    if "align" in hint_l or sl in _ALIGN_LABEL or sl.upper() in ("LEFT", "CENTER", "RIGHT", "JUSTIFY"):
        label = _ALIGN_LABEL.get(sl) or _ALIGN_LABEL.get(sl.lower()) or _ALIGN_LABEL.get(sl.upper())
        if label:
            return label

    # Line spacing — berdasarkan hint
    if "spacing" in hint_l or "spasi" in hint_l:
        try:
            rounded = f"{float(s):.2f}".rstrip("0").rstrip(".")
            label = _SPACING_LABEL.get(rounded) or _SPACING_LABEL.get(s)
            if label:
                return label
            # Kembalikan dengan satuan agar tidak membingungkan
            return f"{rounded} spasi"
        except ValueError:
            pass

    # Angka murni tanpa konteks — kembalikan apa adanya
    # (mis. ukuran font "12" tetap "12" bukan diterjemahkan)
    return raw


def _humanize_field(field: str | None) -> str:
    """Terjemahkan nama field teknis ke deskripsi bahasa Indonesia."""
    if not field:
        return "-"
    # Coba match langsung
    label = _FIELD_LABEL.get(field.strip().lower())
    if label:
        return label
    # Coba match parsial (mis. "body_alignment" → "alignment_body")
    fl = field.strip().lower()
    for key, val in _FIELD_LABEL.items():
        if key in fl or fl in key:
            return val
    # Fallback: bersihkan underscore
    return field.replace("_", " ")


def _humanize_category(category: str | None) -> str:
    """Terjemahkan nama kategori teknis ke deskripsi bahasa Indonesia."""
    if not category:
        return "-"
    return _CATEGORY_LABEL.get(category.strip().lower(), category.replace("_", " "))


def _compact_occurrence(occ: dict[str, Any], field_hint: str = "") -> dict[str, Any]:
    text = (occ.get("text") or "").strip()
    if len(text) > TEXT_PREVIEW_LEN:
        text = text[:TEXT_PREVIEW_LEN].rstrip() + "..."
    return {
        k: v for k, v in {
            "halaman":      occ.get("page"),
            "bab":          occ.get("bab"),
            "style":        occ.get("style"),
            "teks_contoh":  text or None,
            "ditemukan":    _humanize_value(occ.get("actual"),   hint=field_hint) if occ.get("actual") else None,
            "seharusnya":   _humanize_value(occ.get("expected"), hint=field_hint) if occ.get("expected") else None,
        }.items() if v is not None and v != ""
    }


def _compact_issue(issue: dict[str, Any]) -> dict[str, Any]:
    field = issue.get("field") or ""
    occurrences = issue.get("occurrences") or []
    return {
        k: v for k, v in {
            "tingkat":      issue.get("severity"),
            "kategori":     _humanize_category(issue.get("category")),
            "elemen":       _humanize_field(field),
            "pesan":        issue.get("message"),
            "lokasi":       issue.get("location"),
            "seharusnya":   _humanize_value(issue.get("expected"), hint=field),
            "ditemukan":    _humanize_value(issue.get("actual"),   hint=field),
            "kemunculan":   [
                _compact_occurrence(o, field_hint=field)
                for o in occurrences[:MAX_OCCURRENCES_PER_ISSUE]
            ] or None,
        }.items() if v is not None and v != ""
    }


def _build_llm():
    CONFIG.disable_blackhole_proxies()
    api_key, model_name = CONFIG.get_llm_api_key()
    if model_name.startswith("gemini"):
        return ChatGoogleGenerativeAI(
            model=model_name,
            google_api_key=api_key,
            temperature=CONFIG.temperature,
        )
    return ChatGroq(
        model=model_name,
        api_key=api_key,
        temperature=CONFIG.temperature,
    )


def _render_issue_block(idx: int, issue: dict[str, Any]) -> str:
    """Render satu issue sebagai blok teks terstruktur yang mudah dibaca LLM."""
    lines: list[str] = []
    lines.append(
        f"[{idx}] Elemen: {issue.get('elemen') or '-'}"
        f"  |  Kategori: {issue.get('kategori') or '-'}"
        f"  |  Tingkat: {issue.get('tingkat') or '-'}"
    )
    lines.append(f"    Pesan     : {issue.get('pesan') or '-'}")

    seharusnya = issue.get("seharusnya")
    ditemukan  = issue.get("ditemukan")
    if seharusnya or ditemukan:
        lines.append(
            f"    Seharusnya: {seharusnya or '(tidak diketahui)'}  "
            f"|  Ditemukan: {ditemukan or '(tidak diketahui)'}"
        )

    lokasi = issue.get("lokasi")
    if lokasi:
        lines.append(f"    Lokasi    : {lokasi}")

    kemunculan = issue.get("kemunculan") or []
    if kemunculan:
        lines.append("    Kemunculan:")
        for occ in kemunculan:
            parts: list[str] = []
            if occ.get("halaman"):
                parts.append(f"halaman {occ['halaman']}")
            if occ.get("bab"):
                parts.append(f"bab '{occ['bab']}'")
            if occ.get("style"):
                parts.append(f"style '{occ['style']}'")
            if occ.get("ditemukan") or occ.get("seharusnya"):
                detail = f"ditemukan: {occ.get('ditemukan', '?')}"
                if occ.get("seharusnya"):
                    detail += f", seharusnya: {occ['seharusnya']}"
                parts.append(f"[{detail}]")
            if occ.get("teks_contoh"):
                parts.append(f'contoh teks: "{occ["teks_contoh"]}"')
            lines.append("      - " + (", ".join(parts) if parts else "(tanpa detail)"))

    return "\n".join(lines)


SYSTEM_PROMPT = """\
Anda adalah dosen penilai proposal PKM yang memeriksa kesesuaian format dokumen.

== PROSES BERPIKIR ==
Sebelum menulis output, lakukan analisis ini di dalam tag <pikiran>...</pikiran>.
Isi analisis tersebut TIDAK akan ditampilkan ke reviewer — hanya untuk memandu \
jawaban Anda.

Di dalam <pikiran>, untuk setiap kesalahan lakukan:
  1. Identifikasi nama elemen yang salah dalam bahasa Indonesia sehari-hari.
  2. Catat nilai yang ditemukan di dokumen (aktual).
  3. Catat nilai yang seharusnya (expected).
  4. Catat lokasi (bab/halaman) jika tersedia.
  5. Pastikan tidak ada kode teknis, angka enum, atau singkatan asing yang tersisa.

== FORMAT OUTPUT AKHIR (setelah </pikiran>) ==
Tulis HANYA poin-poin berikut, tidak ada kalimat pengantar atau penutup:
  • [Nama elemen]: ditemukan [nilai aktual], seharusnya [nilai yang benar]\
[; pada [lokasi] jika tersedia]

Aturan tambahan:
- Satu baris per kesalahan, tidak ada sub-poin
- Bahasa Indonesia formal, ringkas, tidak ada frasa berlebihan
- Jangan tambahkan penjelasan, saran, atau konteks yang tidak ada di data
- Maksimal ~150 kata total pada output akhir\
"""


def _strip_scratchpad(text: str) -> str:
    """Buang blok <pikiran>...</pikiran> dari output LLM.

    Model diminta berpikir di dalam tag ini (CoT scratchpad); reviewer
    hanya perlu melihat poin-poin akhir di luar tag tersebut.
    Toleran terhadap variasi kapitalisasi dan spasi ekstra.
    """
    import re
    # Hapus blok <pikiran> beserta isinya (case-insensitive, multiline)
    cleaned = re.sub(r"<pikiran>.*?</pikiran>", "", text, flags=re.DOTALL | re.IGNORECASE)
    # Bersihkan baris kosong berlebih yang tersisa
    cleaned = re.sub(r"\n{3,}", "\n\n", cleaned)
    return cleaned.strip()


def _render_user_prompt(issues: list[dict[str, Any]], schema_name: str | None) -> str:
    compact = [_compact_issue(i) for i in issues]
    header  = f"Skema dokumen: {schema_name}\n" if schema_name else ""
    blocks  = "\n\n".join(_render_issue_block(i + 1, iss) for i, iss in enumerate(compact))
    return (
        f"{header}"
        f"Jumlah kesalahan: {len(compact)}\n\n"
        f"Daftar kesalahan:\n{blocks}\n\n"
        "Tulis analisis <pikiran> terlebih dahulu, lalu tulis poin-poin output akhir."
    )


def summarize_issues(
    issues: list[dict[str, Any]] | None,
    schema_name: str | None = None,
) -> str:
    """Panggil LLM untuk membuat catatan ringkas dari list issue.

    Return string kosong bila issues kosong/None. Lempar exception bila
    semua key LLM habis — caller (endpoint) yang menerjemahkannya ke HTTP error.
    """
    if not issues:
        return ""

    prompt = _render_user_prompt(issues, schema_name)
    max_retries = len(CONFIG.groq_api_keys) + len(CONFIG.google_api_keys) + 2

    groq_keys_tried = 0
    last_err: Exception | None = None
    for attempt in range(max_retries):
        try:
            llm = _build_llm()
            response = llm.invoke([
                ("system", SYSTEM_PROMPT),
                ("human", prompt),
            ])
            content = getattr(response, "content", response)
            return _strip_scratchpad(str(content))
        except Exception as e:
            last_err = e
            err_str = str(e)
            is_rate = (
                "429" in err_str
                or "rate_limit" in err_str.lower()
                or "quota" in err_str.lower()
                or "ResourceExhausted" in type(e).__name__
            )
            if not is_rate:
                raise

            if not CONFIG._groq_exhausted:
                groq_keys_tried += 1
                if groq_keys_tried < len(CONFIG.groq_api_keys):
                    CONFIG.rotate_groq_key()
                    print(f"[summarize] Rate limit Groq, rotasi key ({groq_keys_tried}/{len(CONFIG.groq_api_keys)})...")
                else:
                    CONFIG._groq_exhausted = True
                    print("[summarize] Semua Groq key exhausted, switch ke Gemini...")
            else:
                if len(CONFIG.google_api_keys) > 1:
                    CONFIG.rotate_google_key()
                wait_secs = min(30, MAX_RATE_LIMIT_WAIT)
                print(f"[summarize] Rate limit Gemini, tunggu {wait_secs}s...")
                time.sleep(wait_secs)

    raise RuntimeError(
        f"Gagal generate ringkasan setelah {max_retries} percobaan: {last_err}"
    )
