"""Structure checks: document structure order and lampiran format. Keyword: automated document validation"""
from __future__ import annotations

import re
from pathlib import Path

from docx import Document as DocxDocument
from docx.enum.text import WD_ALIGN_PARAGRAPH

from model_ai.extractor.models import DocumentMetadata
from model_ai.validation.models import ValidationCheckResult, ValidationIssue
from model_ai.validation.validocx_adapter import (
    _resolve_line_spacing,
    _heading_level_from_style,
)

from ._shared import (
    _BAB_RE,
    _SUB_BAB_RE,
    _LAMPIRAN_ITEM_RE,
    _LAMPIRAN_BROAD_RE,
    _TOC_TOF_STYLE_NAMES,
    _HEADING_TITLE_MAP,
    _HEADING_TITLE_MAP_INV,
    _build_lampiran_re,
    _build_occurrences,
)


def _classify_heading(
    text: str,
    lampiran_re: re.Pattern | None = None,
) -> tuple[str | None, dict]:
    """Klasifikasi teks heading menjadi tipe section + info tambahan.

    lampiran_re: regex dinamis dari metadata (separator per skema).
                 Bila None, fallback ke _LAMPIRAN_ITEM_RE (titik).
    """
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

    m = (lampiran_re or _LAMPIRAN_ITEM_RE).match(text_stripped)
    if m:
        return "item_lampiran", {"lampiran_number": f"Lampiran {m.group(1)}"}

    return None, {}


def _check_document_structure(
    docx_path: Path,
    metadata: DocumentMetadata,
    doc: DocxDocument | None = None,
) -> tuple[list[ValidationIssue], list[ValidationCheckResult]]:
    """Validasi urutan dan kehadiran section dokumen berdasarkan document_structure_proposal."""
    issues: list[ValidationIssue] = []
    checks: list[ValidationCheckResult] = []

    ds = metadata.document_structure_artikel or metadata.document_structure_proposal
    if ds is None or not ds.sections:
        checks.append(ValidationCheckResult(
            category="document_structure", field="section_order",
            status="skipped",
            message="Tidak ada data document_structure di metadata",
            skip_reason="Tidak ada nilai di metadata",
        ))
        return issues, checks

    try:
        doc = doc or DocxDocument(str(docx_path))

        # Build lampiran regex dari metadata agar sesuai separator per skema.
        _ds_sep = ds.lampiran_heading_separator if ds else None
        _lampiran_re = _build_lampiran_re(_ds_sep if _ds_sep is not None else ".")

        # Ekstrak heading dari docx dan klasifikasikan.
        # Gunakan _heading_level_from_style agar style kustom (Judul 1, Judul 2, dll.)
        # yang mewarisi Heading atau punya outline level ikut terdeteksi.
        actual_classified: list[dict] = []
        for para in doc.paragraphs:
            text = para.text.strip()
            if not text:
                continue
            level = _heading_level_from_style(para.style)
            if level is None:
                continue
            section_type, extra = _classify_heading(text, lampiran_re=_lampiran_re)
            if section_type:
                actual_classified.append({"type": section_type, "text": text, **extra})

        # Ambil hanya major sections dari metadata sebagai expected order
        expected_major = [s for s in ds.sections if s.is_major_section]
        # required_types: hanya untuk non-BAB (BAB dicek per nomor agar BAB 1 ≠ BAB 2)
        required_non_bab_types = {
            s.type for s in expected_major if s.required is True and s.type != "bab"
        }
        required_bab_nums = {
            s.number for s in expected_major
            if s.type == "bab" and s.required is True and s.number is not None
        }
        actual_types_set = {s["type"] for s in actual_classified}
        actual_bab_nums  = {
            s["number"] for s in actual_classified
            if s["type"] == "bab" and "number" in s
        }

        # 1. Cek section wajib hadir
        def _req_label(section_type: str, title: str | None) -> str:
            """Label terbaca manusia untuk sebuah tipe section."""
            if section_type == "bab":
                return "BAB"
            if section_type == "sub_bab":
                return "Sub BAB"
            if title:
                return title
            return _HEADING_TITLE_MAP_INV.get(section_type, section_type.replace("_", " ").upper())

        # Kelompokkan section metadata: wajib vs opsional (deduplikasi by type)
        seen_meta: set[str] = set()
        required_labels: list[str] = []
        optional_labels: list[str] = []
        for s in expected_major:
            if s.type in seen_meta:
                continue
            seen_meta.add(s.type)
            lbl = _req_label(s.type, s.title)
            if s.required is True:
                required_labels.append(lbl)
            else:
                optional_labels.append(lbl)

        # Section aktual yang ditemukan (hanya major, BAB di-expand individual)
        major_types_set = {s.type for s in expected_major}
        seen_actual: set[str] = set()
        actual_section_texts: list[str] = []
        for s in actual_classified:
            if s["type"] not in major_types_set:
                continue
            if s["type"] == "bab":
                actual_section_texts.append(s["text"])  # tiap BAB ditampilkan
            elif s["type"] not in seen_actual:
                actual_section_texts.append(s["text"])
                seen_actual.add(s["type"])

        # Format display
        req_part = ', '.join(required_labels) if required_labels else "–"
        opt_part = ', '.join(optional_labels) if optional_labels else "–"
        expected_display_req = f"Wajib: {req_part} | Opsional: {opt_part}"
        actual_display_req   = ', '.join(actual_section_texts) if actual_section_texts else "Tidak ada"

        # Occurrences: semua major section yang ditemukan (tampil di passed & failed)
        actual_major_found = [s for s in actual_classified if s["type"] in major_types_set]
        occ_req = _build_occurrences(
            [{"text": s["text"][:100], "full_text": s["text"],
              "style": "", "page": None, "bab": None, "para_idx": None}
             for s in actual_major_found],
            actual_str=None, expected_str=None,
        ) or None

        # Hitung yang hilang — non-BAB by type, BAB by nomor individual
        missing_non_bab = required_non_bab_types - actual_types_set
        missing_bab_nums = required_bab_nums - actual_bab_nums
        total_required   = len(required_non_bab_types) + len(required_bab_nums)

        if missing_non_bab or missing_bab_nums:
            missing_labels: list[str] = []
            # Non-BAB hilang
            seen_ml: set[str] = set()
            for s in expected_major:
                if s.type != "bab" and s.type in missing_non_bab and s.type not in seen_ml:
                    seen_ml.add(s.type)
                    missing_labels.append(_req_label(s.type, s.title))
            # BAB hilang — tampilkan nama individual
            for s in sorted(
                [x for x in expected_major if x.type == "bab" and x.number in missing_bab_nums],
                key=lambda x: x.number or 0,
            ):
                lbl = f"BAB {s.number} {s.title.upper()}" if s.title else f"BAB {s.number}"
                missing_labels.append(lbl)

            total_missing = len(missing_non_bab) + len(missing_bab_nums)
            msg = f"{total_missing} section wajib tidak ditemukan: {', '.join(missing_labels)}"
            issues.append(ValidationIssue(
                category="document_structure", field="required_section",
                severity="error", message=msg,
                expected=expected_display_req, actual=actual_display_req,
            ))
            checks.append(ValidationCheckResult(
                category="document_structure", field="required_section",
                status="failed", message=msg,
                expected=expected_display_req, actual=actual_display_req,
                occurrences=occ_req,
            ))
        else:
            checks.append(ValidationCheckResult(
                category="document_structure", field="required_section",
                status="passed",
                message=f"Semua {total_required} section wajib ditemukan",
                expected=expected_display_req,
                actual=actual_display_req,
                occurrences=occ_req,
            ))

        # 2. Cek BAB berurutan — gunakan nama BAB dari metadata, bukan angka
        bab_actuals = [s for s in actual_classified if s["type"] == "bab"]
        bab_numbers = [s["number"] for s in bab_actuals if "number" in s]
        expected_bab_sections = sorted(
            [s for s in expected_major if s.type == "bab" and s.number is not None],
            key=lambda s: s.number,  # type: ignore[arg-type]
        )
        expected_bab_numbers = [s.number for s in expected_bab_sections]

        def _bab_label(number: int, title: str | None) -> str:
            """Format label BAB: 'BAB N JUDUL' atau fallback 'BAB N'."""
            if title:
                return f"BAB {number} {title.upper()}"
            return f"BAB {number}"

        # Label expected (dari metadata) dan actual (dari teks heading dokumen)
        expected_bab_labels = [_bab_label(s.number, s.title) for s in expected_bab_sections]  # type: ignore[arg-type]
        actual_bab_labels   = [s["text"] for s in bab_actuals]
        bab_num_to_text: dict[int, str] = {
            s["number"]: s["text"] for s in bab_actuals if "number" in s
        }

        if expected_bab_numbers and bab_numbers:
            if bab_numbers != sorted(bab_numbers):
                # Urutan salah — tampilkan nama, bukan angka
                actual_ordered_labels   = [bab_num_to_text.get(n, f"BAB {n}") for n in bab_numbers]
                expected_sorted_labels  = [_bab_label(s.number, s.title) for s in expected_bab_sections]  # type: ignore[arg-type]
                msg = f"BAB tidak berurutan. Ditemukan: {' → '.join(actual_ordered_labels)}"
                occ_bab_err = _build_occurrences(
                    [{"text": s["text"][:100], "full_text": s["text"],
                      "style": "", "page": None, "bab": None, "para_idx": None}
                     for s in bab_actuals],
                    actual_str=None, expected_str=None,
                ) or None
                issues.append(ValidationIssue(
                    category="document_structure", field="bab_order",
                    severity="error", message=msg,
                    expected=' → '.join(expected_sorted_labels),
                    actual=' → '.join(actual_ordered_labels),
                ))
                checks.append(ValidationCheckResult(
                    category="document_structure", field="bab_order",
                    status="failed", message=msg,
                    expected=' → '.join(expected_sorted_labels),
                    actual=' → '.join(actual_ordered_labels),
                    occurrences=occ_bab_err,
                ))
            else:
                missing_bab_nums = set(expected_bab_numbers) - set(bab_numbers)
                if missing_bab_nums:
                    missing_labels = [
                        _bab_label(s.number, s.title)  # type: ignore[arg-type]
                        for s in expected_bab_sections if s.number in missing_bab_nums
                    ]
                    msg = f"BAB berikut tidak ditemukan: {', '.join(missing_labels)}"
                    occ_bab_missing = _build_occurrences(
                        [{"text": s["text"][:100], "full_text": s["text"],
                          "style": "", "page": None, "bab": None, "para_idx": None}
                         for s in bab_actuals],
                        actual_str=None, expected_str=None,
                    ) or None
                    issues.append(ValidationIssue(
                        category="document_structure", field="bab_order",
                        severity="error", message=msg,
                        expected=' → '.join(expected_bab_labels),
                        actual=' → '.join(actual_bab_labels),
                    ))
                    checks.append(ValidationCheckResult(
                        category="document_structure", field="bab_order",
                        status="failed", message=msg,
                        expected=' → '.join(expected_bab_labels),
                        actual=' → '.join(actual_bab_labels),
                        occurrences=occ_bab_missing,
                    ))
                else:
                    occ_bab = _build_occurrences(
                        [{"text": s["text"][:100], "full_text": s["text"],
                          "style": "", "page": None, "bab": None, "para_idx": None}
                         for s in bab_actuals],
                        actual_str=None, expected_str=None,
                    ) or None
                    checks.append(ValidationCheckResult(
                        category="document_structure", field="bab_order",
                        status="passed",
                        message=f"BAB berurutan dengan benar: {' → '.join(actual_bab_labels)}",
                        expected=' → '.join(expected_bab_labels),
                        actual=' → '.join(actual_bab_labels),
                        occurrences=occ_bab,
                    ))

        # 3. Cek urutan major section secara keseluruhan
        # Mapping type → label sederhana (untuk non-bab)
        def _section_label(section_type: str, title: str | None = None) -> str:
            if section_type == "sub_bab":
                return "Sub BAB"
            if title:
                return title
            return _HEADING_TITLE_MAP_INV.get(section_type) or section_type.replace("_", " ").upper()

        type_to_label: dict[str, str] = {}
        for s in expected_major:
            if s.type not in type_to_label:
                type_to_label[s.type] = _section_label(s.type, s.title)

        # Expand type list ke label: "bab" dipecah ke label tiap BAB individual
        def _expand_labels(type_list: list[str], bab_labels: list[str]) -> str:
            parts: list[str] = []
            for t in type_list:
                if t == "bab":
                    # Expand ke nama tiap BAB; fallback ke "BAB" jika list kosong
                    parts.extend(bab_labels if bab_labels else ["BAB"])
                else:
                    parts.append(type_to_label.get(t, t.replace("_", " ").upper()))
            return ' → '.join(parts)

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

        # Label display: BAB di-expand ke nama masing-masing
        # expected_bab_labels dan actual_bab_labels sudah tersedia dari step 2
        exp_display = _expand_labels(expected_filtered, expected_bab_labels)
        act_display = _expand_labels(actual_filtered, actual_bab_labels)

        if expected_filtered and actual_filtered and actual_filtered != expected_filtered:
            msg = (
                f"Urutan section tidak sesuai. "
                f"Seharusnya: {exp_display}, "
                f"Ditemukan: {act_display}"
            )
            occ_sec_err = _build_occurrences(
                [{"text": s["text"][:100], "full_text": s["text"],
                  "style": "", "page": None, "bab": None, "para_idx": None}
                 for s in actual_classified if s["type"] in set(expected_order)],
                actual_str=None, expected_str=None,
            ) or None
            issues.append(ValidationIssue(
                category="document_structure", field="section_order",
                severity="error", message=msg,
                expected=exp_display,
                actual=act_display,
            ))
            checks.append(ValidationCheckResult(
                category="document_structure", field="section_order",
                status="failed", message=msg,
                expected=exp_display,
                actual=act_display,
                occurrences=occ_sec_err,
            ))
        elif expected_filtered:
            major_found = [s for s in actual_classified if s["type"] in set(expected_order)]
            occ_sec = _build_occurrences(
                [{"text": s["text"][:100], "full_text": s["text"],
                  "style": "", "page": None, "bab": None, "para_idx": None}
                 for s in major_found],
                actual_str=None, expected_str=None,
            ) or None
            checks.append(ValidationCheckResult(
                category="document_structure", field="section_order",
                status="passed",
                message=f"Urutan section sesuai: {act_display}",
                expected=exp_display,
                actual=act_display,
                occurrences=occ_sec,
            ))

    except Exception as exc:
        checks.append(ValidationCheckResult(
            category="document_structure", field="section_order",
            status="skipped",
            message=f"Pengecekan struktur dokumen dilewati: {exc}",
            skip_reason=str(exc),
        ))

    return issues, checks


def _check_lampiran_format(
    docx_path: Path,
    metadata: DocumentMetadata,
    doc: DocxDocument | None = None,
) -> tuple[list[ValidationIssue], list[ValidationCheckResult]]:
    """Validasi judul lampiran via text-pattern untuk SEMUA judul lampiran.

    Mendeteksi paragraf yang teksnya diawali 'Lampiran <angka>' (_LAMPIRAN_BROAD_RE),
    baik yang menggunakan style bernama 'Lampiran' maupun style lain (Normal, Body, dll).
    Aturan atribut: font family, font size, line spacing, alignment JUSTIFY — sama dengan body.
    """
    issues: list[ValidationIssue] = []
    checks: list[ValidationCheckResult] = []

    t  = metadata.typography
    ds = metadata.document_structure_artikel or metadata.document_structure_proposal
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
        doc = doc or DocxDocument(str(docx_path))

        pass_items:      list[dict] = []
        sep_pass_items:  list[dict] = []
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
            _sep_ok = bool(lampiran_re.match(text))
            if not _sep_ok:
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
            if _sep_ok:
                sep_pass_items.append(para_info)

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
            occ_sep_err = _build_occurrences(
                [{"text": t[:100], "full_text": t, "style": "",
                  "page": None, "bab": None, "para_idx": None}
                 for t in wrong_separator],
                actual_str=None, expected_str=effective_sep,
            ) or None
            issues.append(ValidationIssue(
                category="document_structure", field="lampiran_separator",
                severity="error", message=msg,
                expected=effective_sep, actual=wrong_separator[0],
            ))
            checks.append(ValidationCheckResult(
                category="document_structure", field="lampiran_separator",
                status="failed", message=msg,
                expected=effective_sep, actual=wrong_separator[0],
                occurrences=occ_sep_err,
            ))
        else:
            occ_sep = _build_occurrences(
                sep_pass_items, actual_str=effective_sep, expected_str=effective_sep,
            ) or None
            checks.append(ValidationCheckResult(
                category="document_structure", field="lampiran_separator",
                status="passed",
                message=f"Format penulisan judul lampiran sesuai ({sep_display} setelah nomor)",
                expected=effective_sep,
                occurrences=occ_sep,
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

        # ── Emit: atribut gagal → issue per atribut ──────────────────────────
        # alignment → error (konsisten dengan caption_alignment_* dan body_alignment)
        # font/size/spacing → warning
        for field, items, label, expected_val, is_error in [
            ("lampiran_alignment", wrong_alignment, "alignment",    "JUSTIFY",              True),
            ("lampiran_font",      wrong_font,      "font family",  expected_font or "",    False),
            ("lampiran_font_size", wrong_size,      "font size",    f"{expected_size}pt",   False),
            ("lampiran_spacing",   wrong_spacing,   "line spacing", str(expected_spacing),  False),
        ]:
            if not items:
                continue
            first_actual = items[0].get("actual", "")
            msg = (
                f"{len(items)} judul lampiran {label} tidak sesuai "
                f"(ekspektasi: {expected_val}). Contoh: \"{items[0]['text']}\""
            )
            occs_fail = _build_occurrences(items, expected_str=str(expected_val)) or None
            issues.append(ValidationIssue(
                category="typography", field=field,
                severity="error" if is_error else "warning", message=msg,
                expected=str(expected_val), actual=first_actual,
                occurrences=occs_fail,
            ))
            checks.append(ValidationCheckResult(
                category="typography", field=field,
                status="failed" if is_error else "warning", message=msg,
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
