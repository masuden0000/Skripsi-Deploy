"""
Bandingkan properti DOCX dengan rules dari DocumentMetadata.

Digunakan oleh: validator.py

Tujuan: Mendeteksi deviasi format antara dokumen dengan rules yang diharapkan.
        Setiap properti dicatat hasilnya (passed / failed / warning / skipped).
"""
from typing import Any

from model_ai.extractor.models import DocumentMetadata
from model_ai.validation.models import DocxProperties, ValidationCheckResult, ValidationIssue


# ---------------------------------------------------------------------------
# Toleransi perbandingan float
# ---------------------------------------------------------------------------
MARGIN_TOLERANCE_CM = 0.1
LINE_SPACING_TOLERANCE = 0.01


# ---------------------------------------------------------------------------
# Helper: bandingkan dua nilai dengan toleransi opsional
# ---------------------------------------------------------------------------
def _compare_values(
    expected: Any,
    actual: Any,
    tolerance: float | None = None,
) -> bool:
    if expected is None and actual is None:
        return True
    if expected is None or actual is None:
        return False
    if isinstance(expected, str) and isinstance(actual, str):
        return expected.lower().strip() == actual.lower().strip()
    if isinstance(expected, bool) or isinstance(actual, bool):
        return bool(expected) == bool(actual)
    if isinstance(expected, (int, float)) and isinstance(actual, (int, float)):
        if tolerance is not None:
            return abs(float(expected) - float(actual)) <= tolerance
        return expected == actual
    return expected == actual


# ---------------------------------------------------------------------------
# Helper: catat satu pengecekan dan tambahkan issue jika gagal
# ---------------------------------------------------------------------------
def _record_check(
    checks: list[ValidationCheckResult],
    issues: list[ValidationIssue],
    category: str,
    field: str,
    expected: Any,
    actual: Any,
    severity: str = "error",
    message: str = "",
    location: str | None = None,
    tolerance: float | None = None,
) -> None:
    """Catat hasil satu pengecekan. Jika gagal, tambahkan juga ke issues."""
    # Tentukan skip_reason
    if expected is None and actual is None:
        checks.append(ValidationCheckResult(
            category=category, field=field, status="skipped",
            expected=expected, actual=actual,
            skip_reason="Kedua nilai tidak tersedia",
        ))
        return

    if expected is None:
        checks.append(ValidationCheckResult(
            category=category, field=field, status="skipped",
            expected=expected, actual=actual,
            skip_reason="Tidak ada nilai di metadata (ground truth)",
        ))
        return

    if actual is None:
        checks.append(ValidationCheckResult(
            category=category, field=field, status="skipped",
            expected=expected, actual=actual,
            skip_reason="Tidak terdeteksi di dokumen",
        ))
        return

    match = _compare_values(expected, actual, tolerance)
    msg = message or f"{field} tidak sesuai: diharapkan {expected!r}, ditemukan {actual!r}"

    if match:
        checks.append(ValidationCheckResult(
            category=category, field=field, status="passed",
            expected=expected, actual=actual,
            message="Sesuai", location=location,
        ))
    else:
        status = "failed" if severity == "error" else "warning"
        checks.append(ValidationCheckResult(
            category=category, field=field, status=status,
            expected=expected, actual=actual,
            message=msg, location=location,
        ))
        if severity not in ("error", "warning", "info"):
            severity = "error"
        issues.append(ValidationIssue(
            category=category, field=field,
            expected=expected, actual=actual,
            severity=severity, message=msg, location=location,
        ))


def _record_passed(
    checks: list[ValidationCheckResult],
    category: str,
    field: str,
    message: str,
    location: str | None = None,
) -> None:
    """Catat pengecekan yang lolos tanpa nilai expected/actual (misal: 0 anomali)."""
    checks.append(ValidationCheckResult(
        category=category, field=field, status="passed",
        message=message, location=location,
    ))


def _record_skipped(
    checks: list[ValidationCheckResult],
    category: str,
    field: str,
    expected: Any = None,
    actual: Any = None,
    skip_reason: str = "",
) -> None:
    checks.append(ValidationCheckResult(
        category=category, field=field, status="skipped",
        expected=expected, actual=actual, skip_reason=skip_reason,
    ))


# ---------------------------------------------------------------------------
# 1. TIPOGRAFI
# ---------------------------------------------------------------------------
def _validate_typography(
    props: DocxProperties,
    metadata: DocumentMetadata,
    issues: list[ValidationIssue],
    checks: list[ValidationCheckResult],
) -> None:
    if metadata.typography is None:
        return
    t = metadata.typography

    _record_check(checks, issues, "typography", "font_family",
                  t.font_family, props.font_family,
                  message=f"Font keluarga: diharapkan '{t.font_family}', ditemukan '{props.font_family}'",
                  location="Seluruh dokumen (gaya Normal)")

    _record_check(checks, issues, "typography", "font_size_body_pt",
                  t.font_size_body_pt, props.font_size_body_pt,
                  message=f"Ukuran font body: diharapkan {t.font_size_body_pt}pt, ditemukan {props.font_size_body_pt}pt",
                  location="Seluruh dokumen (gaya Normal)")

    _record_check(checks, issues, "typography", "font_size_heading_pt",
                  t.font_size_heading_pt, props.font_size_heading_pt,
                  message=f"Ukuran font heading: diharapkan {t.font_size_heading_pt}pt, ditemukan {props.font_size_heading_pt}pt",
                  location="Seluruh dokumen (gaya Heading)")

    _record_check(checks, issues, "typography", "heading_bold",
                  t.heading_bold, props.heading_bold,
                  severity="warning",
                  message=f"Heading bold: diharapkan {'Ya' if t.heading_bold else 'Tidak'}, ditemukan {'Ya' if props.heading_bold else 'Tidak'}",
                  location="Seluruh dokumen (gaya Heading)")

    # Per-heading ALL CAPS (H1) dan title case (H2)
    if props.heading_caps_anomalies:
        for anomaly in props.heading_caps_anomalies:
            field = "heading1_all_caps" if anomaly.level == 1 else "heading2_title_case"
            sev = "error" if anomaly.level == 1 else "warning"
            msg = (
                f"Heading BAB/DAFTAR harus ALL CAPS: '{anomaly.text}'"
                if anomaly.level == 1
                else f"Sub-judul harus title case (Bahasa Indonesia): '{anomaly.text}'"
            )
            status = "failed" if sev == "error" else "warning"
            checks.append(ValidationCheckResult(
                category="typography", field=field, status=status,
                expected=anomaly.expected_form, actual=anomaly.text,
                message=msg, location=anomaly.location,
            ))
            issues.append(ValidationIssue(
                category="typography", field=field,
                expected=anomaly.expected_form, actual=anomaly.text,
                severity=sev, message=msg, location=anomaly.location,
            ))
    else:
        _record_passed(checks, "typography", "heading1_all_caps",
                       "Semua Heading 1 sudah ALL CAPS")
        _record_passed(checks, "typography", "heading2_title_case",
                       "Semua Heading 2 sudah title case")


# ---------------------------------------------------------------------------
# 2. TATA LETAK HALAMAN
# ---------------------------------------------------------------------------
def _validate_page_layout(
    props: DocxProperties,
    metadata: DocumentMetadata,
    issues: list[ValidationIssue],
    checks: list[ValidationCheckResult],
) -> None:
    if metadata.page_layout is None:
        return
    l = metadata.page_layout
    loc = "Seluruh dokumen (pengaturan halaman section 1)"

    for field, exp, act, label in [
        ("margin_top_cm",    l.margin_top_cm,    props.margin_top_cm,    "Margin atas"),
        ("margin_bottom_cm", l.margin_bottom_cm, props.margin_bottom_cm, "Margin bawah"),
        ("margin_left_cm",   l.margin_left_cm,   props.margin_left_cm,   "Margin kiri"),
        ("margin_right_cm",  l.margin_right_cm,  props.margin_right_cm,  "Margin kanan"),
    ]:
        _record_check(checks, issues, "page_layout", field, exp, act,
                      tolerance=MARGIN_TOLERANCE_CM,
                      message=f"{label}: diharapkan {exp}cm, ditemukan {act}cm",
                      location=loc)

    _record_check(checks, issues, "page_layout", "paper_size",
                  l.paper_size, props.paper_size,
                  message=f"Ukuran kertas: diharapkan {l.paper_size}, ditemukan {props.paper_size}",
                  location=loc)

    _record_check(checks, issues, "page_layout", "orientation",
                  l.orientation, props.orientation,
                  message=f"Orientasi: diharapkan {l.orientation}, ditemukan {props.orientation}",
                  location=loc)

    _record_check(checks, issues, "page_layout", "columns",
                  l.columns, props.columns,
                  message=f"Jumlah kolom: diharapkan {l.columns}, ditemukan {props.columns}",
                  location=loc)


# ---------------------------------------------------------------------------
# 3. SPASI & INDENTASI
# ---------------------------------------------------------------------------
def _validate_spacing(
    props: DocxProperties,
    metadata: DocumentMetadata,
    issues: list[ValidationIssue],
    checks: list[ValidationCheckResult],
) -> None:
    if metadata.spacing is None:
        return
    s = metadata.spacing
    loc_global = "Seluruh dokumen (gaya Normal)"

    _record_check(checks, issues, "spacing", "line_spacing",
                  s.line_spacing, props.line_spacing,
                  tolerance=LINE_SPACING_TOLERANCE,
                  message=f"Line spacing: diharapkan {s.line_spacing}, ditemukan {props.line_spacing}",
                  location=loc_global)

    _record_check(checks, issues, "spacing", "paragraph_alignment",
                  s.paragraph_alignment, props.paragraph_alignment,
                  message=f"Alignment paragraf: diharapkan {s.paragraph_alignment}, ditemukan {props.paragraph_alignment}",
                  location=loc_global)

    _record_check(checks, issues, "spacing", "first_line_indent_cm",
                  s.first_line_indent_cm, props.first_line_indent_cm,
                  tolerance=MARGIN_TOLERANCE_CM,
                  message=f"First line indent: diharapkan {s.first_line_indent_cm}cm, ditemukan {props.first_line_indent_cm}cm",
                  location=loc_global)

    _record_check(checks, issues, "spacing", "references_hanging_indent",
                  s.references_hanging_indent, props.references_hanging_indent,
                  severity="warning",
                  message="Hanging indent daftar pustaka tidak sesuai",
                  location="Daftar Pustaka")

    # Per-paragraf spacing anomalies
    metadata_spacing = s.line_spacing
    reported = 0
    for anomaly in props.spacing_anomalies:
        if metadata_spacing is not None and abs(anomaly.actual - metadata_spacing) <= 0.05:
            continue
        preview = f' Teks: "{anomaly.text_preview}..."' if anomaly.text_preview else ""
        msg = (
            f"Line spacing tidak konsisten di '{anomaly.location}': "
            f"diharapkan {metadata_spacing or anomaly.expected}, "
            f"ditemukan {anomaly.actual}.{preview}"
        )
        checks.append(ValidationCheckResult(
            category="spacing", field="line_spacing_per_paragraph",
            status="warning",
            expected=metadata_spacing or anomaly.expected,
            actual=anomaly.actual,
            message=msg, location=anomaly.location,
        ))
        issues.append(ValidationIssue(
            category="spacing", field="line_spacing",
            expected=metadata_spacing or anomaly.expected,
            actual=anomaly.actual,
            severity="warning", message=msg, location=anomaly.location,
        ))
        reported += 1

    if reported == 0 and props.spacing_anomalies:
        _record_passed(checks, "spacing", "line_spacing_per_paragraph",
                       "Semua paragraf memiliki line spacing konsisten")
    elif reported == 0:
        _record_passed(checks, "spacing", "line_spacing_per_paragraph",
                       "Tidak ada anomali spacing per-paragraf")


# ---------------------------------------------------------------------------
# 4. STRUKTUR KELENGKAPAN DOKUMEN
# ---------------------------------------------------------------------------
def _validate_document_structure(
    props: DocxProperties,
    metadata: DocumentMetadata,
    issues: list[ValidationIssue],
    checks: list[ValidationCheckResult],
) -> None:
    if metadata.document_structure_proposal is None:
        return
    d = metadata.document_structure_proposal

    # Halaman sampul
    if d.halaman_sampul is True:
        _record_check(checks, issues, "document_structure", "halaman_sampul",
                      True, props.has_halaman_sampul, severity="warning",
                      message="Halaman sampul tidak ditemukan dalam dokumen",
                      location="Awal dokumen (halaman pertama)")
    else:
        _record_skipped(checks, "document_structure", "halaman_sampul",
                        skip_reason="Metadata tidak mengharuskan halaman sampul")

    # Halaman pengesahan
    if d.halaman_pengesahan is True:
        _record_check(checks, issues, "document_structure", "halaman_pengesahan",
                      True, props.has_halaman_pengesahan, severity="warning",
                      message="Halaman pengesahan tidak ditemukan dalam dokumen",
                      location="Awal dokumen (setelah halaman sampul)")
    else:
        _record_skipped(checks, "document_structure", "halaman_pengesahan",
                        skip_reason="Metadata tidak mengharuskan halaman pengesahan")

    # Ringkasan
    if d.ringkasan is True:
        _record_check(checks, issues, "document_structure", "ringkasan",
                      True, props.has_ringkasan, severity="warning",
                      message="Ringkasan/abstrak tidak ditemukan dalam dokumen",
                      location="Bagian awal dokumen")
    else:
        _record_skipped(checks, "document_structure", "ringkasan",
                        skip_reason="Metadata tidak mengharuskan ringkasan")

    # Section count
    if props.section_count < 1:
        checks.append(ValidationCheckResult(
            category="document_structure", field="section_count",
            status="failed", expected=">= 1", actual=props.section_count,
            message=f"Dokumen tidak memiliki section yang valid (ditemukan {props.section_count})",
            location="Seluruh dokumen",
        ))
        issues.append(ValidationIssue(
            category="document_structure", field="section_count",
            expected=">= 1", actual=props.section_count, severity="error",
            message=f"Dokumen tidak memiliki section yang valid (ditemukan {props.section_count})",
            location="Seluruh dokumen",
        ))
    else:
        _record_passed(checks, "document_structure", "section_count",
                       f"Dokumen memiliki {props.section_count} Word section")

    # Daftar sections
    _DAFTAR_MAP = {
        "daftar_isi":     ("has_daftar_isi",     "Daftar Isi"),
        "daftar_pustaka": ("has_daftar_pustaka",  "Daftar Pustaka"),
        "daftar_tabel":   ("has_daftar_tabel",    "Daftar Tabel"),
        "daftar_gambar":  ("has_daftar_gambar",   "Daftar Gambar"),
    }
    required_types = {s.type for s in d.sections if s.required}
    for section_type, (prop_field, label) in _DAFTAR_MAP.items():
        detected = getattr(props, prop_field, False)
        if section_type in required_types:
            _record_check(checks, issues, "document_structure", prop_field,
                          True, detected, severity="warning",
                          message=f"'{label}' tidak ditemukan dalam dokumen",
                          location="Seharusnya ada sebelum BAB 1")
        else:
            _record_skipped(checks, "document_structure", prop_field,
                            actual=detected,
                            skip_reason=f"'{label}' tidak diwajibkan oleh metadata")


# ---------------------------------------------------------------------------
# 5. PENOMORAN
# ---------------------------------------------------------------------------
def _validate_numbering(
    props: DocxProperties,
    metadata: DocumentMetadata,
    issues: list[ValidationIssue],
    checks: list[ValidationCheckResult],
) -> None:
    if metadata.numbering is None:
        return
    n = metadata.numbering

    _record_check(checks, issues, "numbering", "chapter_format",
                  n.chapter_format, props.chapter_format,
                  message=f"Format BAB: diharapkan '{n.chapter_format}', ditemukan '{props.chapter_format}'",
                  location="Heading BAB (Heading 1)")

    _record_check(checks, issues, "numbering", "sub_chapter_format",
                  n.sub_chapter_format, props.sub_chapter_format,
                  message=f"Format sub-BAB: diharapkan '{n.sub_chapter_format}', ditemukan '{props.sub_chapter_format}'",
                  location="Heading sub-BAB (Heading 2)")

    # Nomor halaman awal (preliminary)
    pre = n.preliminary
    if pre is not None:
        _record_check(checks, issues, "numbering", "preliminary_page_format",
                      pre.format, props.preliminary_page_format, severity="warning",
                      message=f"Format nomor halaman awal: diharapkan '{pre.format}', ditemukan '{props.preliminary_page_format}'",
                      location="Header/Footer halaman awal")
        _record_check(checks, issues, "numbering", "preliminary_page_location",
                      pre.location, props.preliminary_page_location, severity="warning",
                      message=f"Lokasi nomor halaman awal: diharapkan '{pre.location}', ditemukan '{props.preliminary_page_location}'",
                      location="Header/Footer halaman awal")
        _record_check(checks, issues, "numbering", "preliminary_page_alignment",
                      pre.alignment, props.preliminary_page_alignment, severity="warning",
                      message=f"Alignment nomor halaman awal: diharapkan '{pre.alignment}', ditemukan '{props.preliminary_page_alignment}'",
                      location="Header/Footer halaman awal")
    else:
        for f in ("preliminary_page_format", "preliminary_page_location", "preliminary_page_alignment"):
            _record_skipped(checks, "numbering", f,
                            skip_reason="Metadata tidak mendefinisikan nomor halaman awal")

    # Nomor halaman isi (content)
    con = n.content
    if con is not None:
        _record_check(checks, issues, "numbering", "content_page_format",
                      con.format, props.content_page_format, severity="warning",
                      message=f"Format nomor halaman isi: diharapkan '{con.format}', ditemukan '{props.content_page_format}'",
                      location="Header/Footer halaman isi")
        _record_check(checks, issues, "numbering", "content_page_location",
                      con.location, props.content_page_location, severity="warning",
                      message=f"Lokasi nomor halaman isi: diharapkan '{con.location}', ditemukan '{props.content_page_location}'",
                      location="Header/Footer halaman isi")
        _record_check(checks, issues, "numbering", "content_page_alignment",
                      con.alignment, props.content_page_alignment, severity="warning",
                      message=f"Alignment nomor halaman isi: diharapkan '{con.alignment}', ditemukan '{props.content_page_alignment}'",
                      location="Header/Footer halaman isi")
    else:
        for f in ("content_page_format", "content_page_location", "content_page_alignment"):
            _record_skipped(checks, "numbering", f,
                            skip_reason="Metadata tidak mendefinisikan nomor halaman isi")

    _record_check(checks, issues, "numbering", "figure_format",
                  n.figure_format, props.figure_format, severity="warning",
                  message=f"Format keterangan gambar: diharapkan '{n.figure_format}', ditemukan '{props.figure_format}'",
                  location="Keterangan gambar (Caption style)")

    _record_check(checks, issues, "numbering", "table_format",
                  n.table_format, props.table_format, severity="warning",
                  message=f"Format keterangan tabel: diharapkan '{n.table_format}', ditemukan '{props.table_format}'",
                  location="Keterangan tabel (Caption style)")


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------
def compare_properties(
    props: DocxProperties,
    metadata: DocumentMetadata,
) -> tuple[list[ValidationIssue], list[ValidationCheckResult]]:
    """Bandingkan properti DOCX terhadap rules DocumentMetadata.

    Returns:
        Tuple (issues, checks):
        - issues: hanya properti yang gagal (untuk backward compat)
        - checks: seluruh hasil pengecekan (passed/failed/warning/skipped)
    """
    issues: list[ValidationIssue] = []
    checks: list[ValidationCheckResult] = []

    _validate_typography(props, metadata, issues, checks)
    _validate_page_layout(props, metadata, issues, checks)
    _validate_spacing(props, metadata, issues, checks)
    _validate_document_structure(props, metadata, issues, checks)
    _validate_numbering(props, metadata, issues, checks)

    return issues, checks
