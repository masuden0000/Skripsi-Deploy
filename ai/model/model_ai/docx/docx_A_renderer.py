"""Renderer Type A: menulis konten terstruktur ke dokumen .docx untuk semua skema PKM kecuali PKM-AI (proposal). Posisi pipeline: instructional_placeholder_builder → docx_A_renderer → DOCX output. Keyword: automated document generation."""
from io import BytesIO
from pathlib import Path

from docx import Document
from docx.enum.section import WD_ORIENT, WD_SECTION_START
from docx.enum.style import WD_STYLE_TYPE
from docx.enum.table import WD_ALIGN_VERTICAL
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_LINE_SPACING, WD_TAB_ALIGNMENT, WD_TAB_LEADER
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Cm, Mm, Pt, RGBColor

from model_ai.docx.chunk_loader import (
    ChunkSource,
    format_source_line,
    match_sources_for_section,
)
from model_ai.docx.instructional_placeholder_builder import make_instruction_key


PAPER_SIZES_CM: dict[str, tuple[float, float]] = {
    "A3":     (29.7, 42.0),
    "A4":     (21.0, 29.7),
    "A5":     (14.85, 21.0),
    "F4":     (21.0, 33.0),
    "FOLIO":  (21.0, 33.0),
    "LETTER": (21.59, 27.94),
    "LEGAL":  (21.59, 35.56),
}


def _get_paper_dimensions(paper_size: str | None) -> tuple[float, float]:
    """Get paper dimensions (width, height) in cm from paper_size code.

    Args:
        paper_size: Paper size code like "A4", "F4", "LETTER", etc.

    Returns:
        (width_cm, height_cm) tuple
    """
    if not paper_size:
        return (21.0, 29.7)
    return PAPER_SIZES_CM.get(paper_size.upper(), (21.0, 29.7))


BIBLIOGRAPHY_STYLES: dict[str, str] = {
    "HARVARD": (
        "Tuliskan daftar pustaka menggunakan format Harvard style:\n\n"
        "Lastname, F. (Tahun). Judul buku. Penerbit.\n"
        "Lastname, F., & Lastname2, G. (Tahun). Judul artikel. Nama Jurnal, Vol(No), hal. XX-XX. "
        "https://doi.org/xxxxx\n\n"
        "Contoh:\n"
        "Wicaksono, H. R. (2024). Sistem Kecerdasan Buatan untuk Evaluasi Dokumen. Universitas Indonesia.\n"
        "Doe, J., & Smith, A. (2023). Deep learning in NLP tasks. Journal of AI Research, 5(2), 45-78."
    ),
    "APA": (
        "Tuliskan daftar pustaka menggunakan format APA style:\n\n"
        "Lastname, F. F. (Tahun). Judul buku dalam huruf miring. Penerbit.\n"
        "Lastname, F. F., & Lastname2, G. G. (Tahun). Judul artikel. Nama Jurnal, Vol(No), XX-XX. "
        "https://doi.org/xxxxx\n\n"
        "Contoh:\n"
        "Wicaksono, H. R. (2024). Sistem Kecerdasan Buatan untuk Evaluasi Dokumen. Universitas Indonesia.\n"
        "Doe, J., & Smith, A. (2023). Deep learning in NLP tasks. Journal of AI Research, 5(2), 45-78."
    ),
    "MLA": (
        "Tuliskan daftar pustaka menggunakan format MLA style:\n\n"
        "Lastname, FirstName. Judul Buku dalam Huruf Miring. Penerbit, Tahun.\n"
        "Lastname, FirstName, and FirstName Lastname. \"Judul Artikel.\" Nama Jurnal, vol. #, no. #, Tahun, hal. XX-XX.\n\n"
        "Contoh:\n"
        "Wicaksono, Huda Rasyad. Sistem Kecerdasan Buatan untuk Evaluasi Dokumen. Universitas Indonesia, 2024.\n"
        "Doe, John, and Anne Smith. \"Deep Learning in NLP Tasks.\" Journal of AI Research, vol. 5, no. 2, 2023, pp. 45-78."
    ),
    "CHICAGO": (
        "Tuliskan daftar pustaka menggunakan format Chicago style:\n\n"
        "Lastname, FirstName. Tahun. Judul Buku dalam Huruf Miring. Kota: Penerbit.\n"
        "Lastname, FirstName, and FirstName Lastname. Tahun. \"Judul Artikel.\" Nama Jurnal Vol, no. # (bulan): XX-XX.\n\n"
        "Contoh:\n"
        "Wicaksono, Huda Rasyad. 2024. Sistem Kecerdasan Buatan untuk Evaluasi Dokumen. Jakarta: Universitas Indonesia.\n"
        "Doe, John, and Anne Smith. 2023. \"Deep Learning in NLP Tasks.\" Journal of AI Research 5, no. 2: 45-78."
    ),
    "VANCOUVER": (
        "Tuliskan daftar pustaka menggunakan format Vancouver style:\n\n"
        "Lastname Initials. Judul buku. Edisi. Kota: Penerbit; Tahun.\n"
        "Lastname Initials, Initials Lastname. Judul artikel. Nama Jurnal. Tahun;Vol(No):hal-XX.\n\n"
        "Contoh:\n"
        "Wicaksono HR. Sistem Kecerdasan Buatan untuk Evaluasi Dokumen. Jakarta: Universitas Indonesia; 2024.\n"
        "Doe J, Smith A. Deep learning in NLP tasks. Journal of AI Research. 2023;5(2):45-78."
    ),
}


def _get_bibliography_placeholder(style: str | None) -> str:
    """Get bibliography placeholder text based on style.

    Args:
        style: Bibliography style code like "HARVARD", "APA", etc.

    Returns:
        Placeholder text for the specified style
    """
    return BIBLIOGRAPHY_STYLES.get((style or "HARVARD").upper(), BIBLIOGRAPHY_STYLES["HARVARD"])


_SECTION_DELETE_NOTE = "(Catatan: bagian ini boleh dihapus)"


def _apply_heading_case(text: str, case_style: str | None) -> str:
    if not case_style:
        return text
    s = case_style.upper()
    if s == "UPPERCASE":
        return text.upper()
    if s == "LOWERCASE":
        return text.lower()
    if s == "SENTENCE_CASE":
        return text.capitalize()
    if s == "TOGGLE_CASE":
        return text.swapcase()
    return text


_BOOKMARK_IDS: dict[str, int] = {
    "daftar_isi": 4,    "daftar_gambar": 5,      "daftar_tabel": 6,
    "daftar_lampiran": 7, "daftar_pustaka": 20,  "lampiran": 21,
}


def _bookmark_name(section_type: str, number=None) -> str:
    if section_type == "bab" and number:
        return f"bab_{number}"
    if section_type == "sub_bab" and number:
        return f"sub_bab_{number}"
    return section_type


def _bookmark_id(section_type: str, number=None) -> int:
    if section_type == "bab" and number:
        return 10 + int(number)
    if section_type == "sub_bab" and number:
        parts = str(number).split(".")
        if len(parts) == 2:
            return 40 + int(parts[1])
    return _BOOKMARK_IDS.get(section_type, 99)


def _add_bookmark_to_paragraph(paragraph, bm_id: int, bm_name: str) -> None:
    bm_start = OxmlElement("w:bookmarkStart")
    bm_start.set(qn("w:id"), str(bm_id))
    bm_start.set(qn("w:name"), bm_name)
    bm_end = OxmlElement("w:bookmarkEnd")
    bm_end.set(qn("w:id"), str(bm_id))

    p = paragraph._p
    first_child = p[0] if len(p) > 0 else None
    if first_child is not None:
        first_child.addprevious(bm_start)
    else:
        p.append(bm_start)
    p.append(bm_end)


def render_proposal_docx(
    output_data: dict,
    chunks: list[ChunkSource],
    instructional_placeholders: dict[str, str],
    output_path: Path,
) -> Path:
    typography     = output_data["typography"]
    page_layout    = output_data["page_layout"]
    spacing        = output_data["spacing"]
    numbering      = output_data["numbering"]
    figures_tables = output_data["figures_and_tables"]
    doc_structure  = output_data["document_structure_proposal"]

    document = Document()
    first_section = document.sections[0]
    _configure_page_layout(first_section, page_layout)
    _apply_base_styles(document, typography, spacing, figures_tables)

    prelim_num  = numbering.get("preliminary") or {}
    content_num = numbering.get("content") or {}

    has_preliminary = _has_preliminary_pages(doc_structure)
    if has_preliminary:
        _render_preliminary_pages(document, doc_structure, page_layout, typography, instructional_placeholders, figures_tables)
        _apply_page_numbering(
            first_section,
            _build_page_num_position(prelim_num.get("location", "FOOTER"), prelim_num.get("alignment", "RIGHT")),
            fmt=prelim_num.get("format", "lowerRoman"),
            start=1,
        )
        content_section = document.add_section(WD_SECTION_START.NEW_PAGE)
        _configure_page_layout(content_section, page_layout)
        _apply_page_numbering(
            content_section,
            _build_page_num_position(content_num.get("location", "HEADER"), content_num.get("alignment", "RIGHT")),
            fmt=content_num.get("format", "decimal"),
            start=1,
        )
    else:
        _apply_page_numbering(
            first_section,
            _build_page_num_position(content_num.get("location", "HEADER"), content_num.get("alignment", "RIGHT")),
            fmt=content_num.get("format", "decimal"),
            start=1,
        )

    _render_proposal_body(document, doc_structure, page_layout, spacing, numbering, figures_tables, chunks, instructional_placeholders, typography)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    try:
        document.save(str(output_path))
    except PermissionError:
        from datetime import datetime
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        alt_path = output_path.parent / f"{output_path.stem}_{timestamp}{output_path.suffix}"
        document.save(str(alt_path))
        print(
            f"[docx] Peringatan: '{output_path.name}' sedang terbuka di aplikasi lain.\n"
            f"[docx] Dokumen disimpan sebagai: '{alt_path.name}'"
        )
        return alt_path
    return output_path


def _configure_page_layout(section, page_layout: dict) -> None:
    orientation = (page_layout.get("orientation") or "PORTRAIT").strip().upper()
    paper_width_cm, paper_height_cm = _get_paper_dimensions(page_layout.get("paper_size"))

    paper_width_mm = paper_width_cm * 10
    paper_height_mm = paper_height_cm * 10

    if orientation == "LANDSCAPE":
        section.orientation = WD_ORIENT.LANDSCAPE
        section.page_width  = Mm(paper_height_mm)
        section.page_height = Mm(paper_width_mm)
    else:
        section.orientation = WD_ORIENT.PORTRAIT
        section.page_width  = Mm(paper_width_mm)
        section.page_height = Mm(paper_height_mm)

    section.top_margin    = Cm(page_layout.get("margin_top_cm", 3.0))
    section.bottom_margin = Cm(page_layout.get("margin_bottom_cm", 3.0))
    section.left_margin   = Cm(page_layout.get("margin_left_cm", 4.0))
    section.right_margin  = Cm(page_layout.get("margin_right_cm", 3.0))


def _apply_base_styles(document: Document, typography: dict, spacing: dict, figures_tables: dict | None = None) -> None:
    body_font    = typography.get("font_family", "Times New Roman")
    body_size    = typography.get("font_size_body_pt", 12)
    heading_size  = typography.get("font_size_heading_pt", body_size)
    h1_case = (typography.get("heading_1_case") or "").upper()
    h2_case = (typography.get("heading_2_case") or "").upper()
    line_spacing  = spacing.get("line_spacing", 1.15)
    alignment_str = (spacing.get("paragraph_alignment") or "JUSTIFY").upper()

    normal_style = document.styles["Normal"]
    normal_style.font.name = body_font
    normal_style.font.size = Pt(body_size)
    normal_style.font.color.rgb = RGBColor(0, 0, 0)
    normal_style._element.rPr.rFonts.set(qn("w:ascii"), body_font)
    normal_style._element.rPr.rFonts.set(qn("w:hAnsi"), body_font)
    _apply_line_spacing(normal_style.paragraph_format, spacing)
    normal_style.paragraph_format.alignment    = _map_alignment(alignment_str)
    normal_style.paragraph_format.space_before = Pt(0)
    normal_style.paragraph_format.space_after  = Pt(0)

    for style_name in ("Heading 1", "Heading 2", "Heading 3", "Heading 4"):
        try:
            h = document.styles[style_name]
        except KeyError:
            continue
        h.font.name      = body_font
        h.font.size      = Pt(heading_size)
        if style_name == "Heading 1":
            h.font.all_caps = (h1_case == "UPPERCASE")
        elif style_name == "Heading 2":
            h.font.all_caps = (h2_case == "UPPERCASE")
        else:
            h.font.all_caps = False
        h.font.color.rgb = RGBColor(0, 0, 0)
        # H1 = CENTER, H2–H4 = JUSTIFY (ikut body)
        if style_name == "Heading 1":
            h.paragraph_format.alignment = WD_ALIGN_PARAGRAPH.CENTER
        else:
            h.paragraph_format.alignment = _map_alignment(alignment_str)
        h.paragraph_format.space_before = Pt(0)
        h.paragraph_format.space_after  = Pt(0)

        style_el = h._element
        rPr = style_el.find(qn("w:rPr"))
        if rPr is None:
            rPr = OxmlElement("w:rPr")
            style_el.append(rPr)
        rFonts = rPr.find(qn("w:rFonts"))
        if rFonts is None:
            rFonts = OxmlElement("w:rFonts")
            rPr.insert(0, rFonts)
        for theme_attr in (qn("w:asciiTheme"), qn("w:hAnsiTheme"), qn("w:cstheme"), qn("w:eastAsiaTheme")):
            if theme_attr in rFonts.attrib:
                del rFonts.attrib[theme_attr]
        rFonts.set(qn("w:ascii"), body_font)
        rFonts.set(qn("w:hAnsi"), body_font)
        rFonts.set(qn("w:cs"), body_font)

    try:
        caption_style = document.styles["Caption"]
    except KeyError:
        caption_style = document.styles.add_style("Caption", WD_STYLE_TYPE.PARAGRAPH)
    caption_style.font.name      = body_font
    caption_style.font.size      = Pt(body_size)
    caption_style.font.bold      = False
    caption_style.font.italic    = False
    caption_style.font.color.rgb = RGBColor(0, 0, 0)
    _ft = figures_tables or {}
    caption_style.paragraph_format.alignment    = _map_alignment((_ft.get("caption_alignment_figure") or "CENTER").upper())
    caption_style.paragraph_format.space_before = Pt(3)
    caption_style.paragraph_format.space_after  = Pt(6)


def _force_paragraph_runs_black(paragraph) -> None:
    for run in paragraph.runs:
        run.font.color.rgb = RGBColor(0, 0, 0)


def _has_preliminary_pages(doc_structure: dict) -> bool:
    prelim_types = {"daftar_isi", "daftar_gambar", "daftar_tabel", "daftar_lampiran"}
    return any(s["type"] in prelim_types for s in doc_structure.get("sections", []))


def _render_preliminary_pages(
    document: Document,
    doc_structure: dict,
    page_layout: dict,
    typography: dict,
    instructional_placeholders: dict[str, str],
    figures_tables: dict | None = None,
) -> None:
    prelim_entries: list[tuple[str, str, str]] = []

    for section in doc_structure.get("sections", []):
        if section["type"] in ("daftar_isi", "daftar_gambar", "daftar_tabel", "daftar_lampiran"):
            fallback = section["type"].upper().replace("_", " ")
            title = (section.get("title") or fallback).strip()
            prelim_entries.append((make_instruction_key(section["type"], title), title, section["type"]))

    for index, (instruction_key, title, sec_type) in enumerate(prelim_entries):
        heading = document.add_heading(_apply_heading_case(title, typography.get("heading_1_case")), level=1)
        heading.alignment = WD_ALIGN_PARAGRAPH.CENTER
        _force_paragraph_runs_black(heading)
        _add_bookmark_to_paragraph(heading, _bookmark_id(sec_type), _bookmark_name(sec_type))

        empty = document.add_paragraph()
        empty.paragraph_format.space_before = Pt(0)
        empty.paragraph_format.space_after  = Pt(0)

        if sec_type == "daftar_isi":
            _render_daftar_isi_example(document, doc_structure, page_layout, typography)
        elif sec_type == "daftar_gambar":
            _render_daftar_gambar_example(document, page_layout, typography, figures_tables)
        elif sec_type == "daftar_tabel":
            _render_daftar_tabel_example(document, page_layout, typography, figures_tables)
        elif sec_type == "daftar_lampiran":
            _render_daftar_lampiran_example(document, page_layout, typography, figures_tables)
        else:
            placeholder_text = instructional_placeholders.get(
                instruction_key,
                f"Instruksi pengisian untuk {title}: lengkapi bagian ini sesuai panduan dokumen.",
            )
            placeholder = document.add_paragraph(placeholder_text)
            _force_paragraph_runs_black(placeholder)

        if index < len(prelim_entries) - 1:
            document.add_page_break()


def _render_daftar_isi_example(
    document: Document,
    doc_structure: dict,
    page_layout: dict,
    typography: dict,
) -> None:
    paper_width, _ = _get_paper_dimensions(page_layout.get("paper_size"))
    text_width_cm = paper_width - page_layout.get("margin_left_cm", 4.0) - page_layout.get("margin_right_cm", 3.0)
    body_font = typography.get("font_family", "Times New Roman")
    body_size = typography.get("font_size_body_pt", 12)

    entries: list[tuple[str, str, str]] = []
    prelim_counter = 1


    h1_case = typography.get("heading_1_case")
    h2_case = typography.get("heading_2_case")

    body_counter = 1
    for sec in doc_structure.get("sections", []):
        sec_type = sec["type"]
        title    = sec.get("title") or sec_type.upper().replace("_", " ")

        if sec_type in ("daftar_isi", "daftar_gambar", "daftar_tabel", "daftar_lampiran"):
            entries.append((_apply_heading_case(title, h1_case), _to_roman(prelim_counter), _bookmark_name(sec_type)))
            prelim_counter += 1
        elif sec_type == "bab":
            num = sec.get("number", "")
            label = f"BAB {num}. {title}".strip() if num else f"BAB {title}".strip()
            entries.append((_apply_heading_case(label, h1_case), str(body_counter), _bookmark_name("bab", num)))
            body_counter += 2
        elif sec_type == "sub_bab":
            sub_num = sec.get("sub_number") or ""
            raw_sub_title = (sec.get("title") or "").title()
            label = _apply_heading_case(f"{sub_num} {raw_sub_title}".strip(), h2_case)
            bookmark = _bookmark_name("sub_bab", sub_num)
            entries.append((label, str(body_counter), bookmark))
            body_counter += 1
        elif sec_type in ("daftar_pustaka", "lampiran"):
            entries.append((_apply_heading_case(title, h1_case), str(body_counter), _bookmark_name(sec_type)))
            body_counter += 1

    for entry_text, page_num, anchor in entries:
        p = document.add_paragraph()
        p.paragraph_format.tab_stops.add_tab_stop(
            Cm(text_width_cm), WD_TAB_ALIGNMENT.RIGHT, WD_TAB_LEADER.DOTS,
        )
        _add_toc_hyperlink(p, f"{entry_text}\t{page_num}", anchor, body_font, body_size)


def _add_toc_hyperlink(paragraph, text: str, anchor: str, font_name: str, font_size: int) -> None:
    """Tambahkan run sebagai w:hyperlink ke bookmark internal."""
    hyperlink = OxmlElement("w:hyperlink")
    hyperlink.set(qn("w:anchor"), anchor)

    run_el = OxmlElement("w:r")
    rPr_el = OxmlElement("w:rPr")

    rFonts_el = OxmlElement("w:rFonts")
    rFonts_el.set(qn("w:ascii"), font_name)
    rFonts_el.set(qn("w:hAnsi"), font_name)
    rPr_el.append(rFonts_el)

    sz_el = OxmlElement("w:sz")
    sz_el.set(qn("w:val"), str(int(font_size) * 2))
    rPr_el.append(sz_el)

    b_el = OxmlElement("w:b")
    rPr_el.append(b_el)

    color_el = OxmlElement("w:color")
    color_el.set(qn("w:val"), "000000")
    rPr_el.append(color_el)

    run_el.append(rPr_el)

    t_el = OxmlElement("w:t")
    t_el.set(qn("xml:space"), "preserve")
    t_el.text = text
    run_el.append(t_el)

    hyperlink.append(run_el)
    paragraph._p.append(hyperlink)


def _parse_caption_format(format_template: str | None, prefix: str) -> str:
    """Parse caption format dari database atau gunakan default.

    Args:
        format_template: Format string seperti "Gambar {num}. {caption}" atau None
        prefix: Default prefix ("Gambar" atau "Tabel")

    Returns:
        Sample entry dengan format yang sesuai
    """
    if not format_template:
        return f"{prefix} 1.1 [Contoh judul {prefix.lower()} pada BAB 1]"

    return f"{prefix} 1.1 [Contoh judul {prefix.lower()} pada BAB 1]"


def _render_daftar_gambar_example(
    document: Document,
    page_layout: dict,
    typography: dict,
    figures_tables: dict | None = None,
) -> None:
    paper_width, _ = _get_paper_dimensions(page_layout.get("paper_size"))
    text_width_cm = paper_width - page_layout.get("margin_left_cm", 4.0) - page_layout.get("margin_right_cm", 3.0)
    body_font = typography.get("font_family", "Times New Roman")
    body_size = typography.get("font_size_body_pt", 12)

    caption_format = None
    if figures_tables:
        caption_format = figures_tables.get("caption_format_figure")

    sample_entries = [
        (_parse_caption_format(caption_format, "Gambar"), "1"),
        ("Gambar 2.1 [Contoh judul gambar pada BAB 2]", "3"),
        ("Gambar 3.1 [Contoh judul gambar pada BAB 3]", "6"),
        ("Gambar 4.1 [Contoh gambar terkait biaya/kegiatan]", "8"),
    ]
    for entry_text, page_num in sample_entries:
        p = document.add_paragraph()
        p.paragraph_format.tab_stops.add_tab_stop(
            Cm(text_width_cm), WD_TAB_ALIGNMENT.RIGHT, WD_TAB_LEADER.DOTS,
        )
        run = p.add_run(f"{entry_text}\t{page_num}")
        run.font.name      = body_font
        run.font.size      = Pt(body_size)
        run.font.color.rgb = RGBColor(0, 0, 0)


def _render_daftar_tabel_example(
    document: Document,
    page_layout: dict,
    typography: dict,
    figures_tables: dict | None = None,
) -> None:
    paper_width, _ = _get_paper_dimensions(page_layout.get("paper_size"))
    text_width_cm = paper_width - page_layout.get("margin_left_cm", 4.0) - page_layout.get("margin_right_cm", 3.0)
    body_font = typography.get("font_family", "Times New Roman")
    body_size = typography.get("font_size_body_pt", 12)

    caption_format = None
    if figures_tables:
        caption_format = figures_tables.get("caption_format_table")

    sample_entries = [
        (_parse_caption_format(caption_format, "Tabel"), "2"),
        ("Tabel 2.1 [Contoh judul tabel pada BAB 2]", "4"),
        ("Tabel 4.1 Rincian Anggaran Biaya", "7"),
        ("Tabel 4.2 Jadwal Pelaksanaan Kegiatan", "8"),
    ]
    for entry_text, page_num in sample_entries:
        p = document.add_paragraph()
        p.paragraph_format.tab_stops.add_tab_stop(
            Cm(text_width_cm), WD_TAB_ALIGNMENT.RIGHT, WD_TAB_LEADER.DOTS,
        )
        run = p.add_run(f"{entry_text}\t{page_num}")
        run.font.name      = body_font
        run.font.size      = Pt(body_size)
        run.font.color.rgb = RGBColor(0, 0, 0)


def _render_daftar_lampiran_example(
    document: Document,
    page_layout: dict,
    typography: dict,
    figures_tables: dict | None = None,
) -> None:
    paper_width, _ = _get_paper_dimensions(page_layout.get("paper_size"))
    text_width_cm = paper_width - page_layout.get("margin_left_cm", 4.0) - page_layout.get("margin_right_cm", 3.0)
    body_font = typography.get("font_family", "Times New Roman")
    body_size = typography.get("font_size_body_pt", 12)

    fmt = None
    if figures_tables:
        fmt = figures_tables.get("caption_format_lampiran")
    if not fmt:
        fmt = "Lampiran {n}. {title}"

    sample_titles = [
        "Biodata Ketua dan Anggota Tim",
        "Justifikasi Anggaran Kegiatan",
        "Surat Pernyataan Ketua Pelaksana",
    ]
    sample_pages = ["11", "12", "13"]
    sample_entries = [
        (fmt.replace("{n}", str(i + 1)).replace("{title}", f"[{title}]"), page)
        for i, (title, page) in enumerate(zip(sample_titles, sample_pages))
    ]

    for entry_text, page_num in sample_entries:
        p = document.add_paragraph()
        p.paragraph_format.tab_stops.add_tab_stop(
            Cm(text_width_cm), WD_TAB_ALIGNMENT.RIGHT, WD_TAB_LEADER.DOTS,
        )
        run = p.add_run(f"{entry_text}\t{page_num}")
        run.font.name      = body_font
        run.font.size      = Pt(body_size)
        run.font.color.rgb = RGBColor(0, 0, 0)


def _to_roman(n: int) -> str:
    vals = [
        (1000, "m"), (900, "cm"), (500, "d"), (400, "cd"),
        (100, "c"),  (90, "xc"),  (50, "l"),  (40, "xl"),
        (10, "x"),   (9, "ix"),   (5, "v"),   (4, "iv"),   (1, "i"),
    ]
    result = ""
    for val, sym in vals:
        while n >= val:
            result += sym
            n -= val
    return result


def _render_proposal_body(
    document: Document,
    doc_structure: dict,
    page_layout: dict,
    spacing: dict,
    numbering: dict,
    figures_tables: dict,
    chunks: list[ChunkSource],
    instructional_placeholders: dict[str, str],
    typography: dict | None = None,
) -> None:
    # Separator antara nomor dan judul lampiran — dibaca dari doc_structure,
    # fallback ke "." jika tidak ada (paling umum di PKM).
    lampiran_sep = doc_structure.get("lampiran_heading_separator")
    if lampiran_sep is None:
        lampiran_sep = "."
    typography = typography or {}
    for section in doc_structure.get("sections", []):
        if section["type"] == "bab":
            _render_bab_section(document, section, page_layout, spacing, numbering, figures_tables, chunks, instructional_placeholders, typography)
        elif section["type"] == "daftar_pustaka":
            _render_named_section(
                document, section["type"],
                section.get("title") or "DAFTAR PUSTAKA",
                spacing, chunks, instructional_placeholders,
                doc_structure, typography,
            )
        elif section["type"] == "lampiran":
            _render_named_section(
                document, section["type"],
                section.get("title") or "LAMPIRAN",
                spacing, chunks, instructional_placeholders,
                doc_structure, typography,
            )
        elif section["type"] == "sub_bab":
            _render_sub_bab_section(document, section, page_layout, spacing, figures_tables, instructional_placeholders, typography)
        elif section["type"] == "item_lampiran":
            _render_item_lampiran_section(document, section, page_layout, spacing, instructional_placeholders, typography, lampiran_sep, figures_tables)


def _render_bab_section(
    document: Document,
    section: dict,
    page_layout: dict,
    spacing: dict,
    numbering: dict,
    figures_tables: dict,
    chunks: list[ChunkSource],
    instructional_placeholders: dict[str, str],
    typography: dict | None = None,
) -> None:
    typography = typography or {}
    chapter_fmt  = numbering.get("chapter_format", "BAB {n}")
    title        = section.get("title") or "[JUDUL_BAB_BELUM_TERDETEKSI]"
    num          = section.get("number")
    bab_label    = chapter_fmt.replace("{n}", str(num)) if num else "BAB"
    heading_text = _apply_heading_case(f"{bab_label} {title}".strip(), typography.get("heading_1_case"))

    sep = document.add_paragraph()
    sep.paragraph_format.space_before = Pt(0)
    sep.paragraph_format.space_after  = Pt(0)
    _apply_line_spacing(sep.paragraph_format, spacing)

    heading = document.add_heading(heading_text, level=1)
    heading.alignment = WD_ALIGN_PARAGRAPH.CENTER
    _force_paragraph_runs_black(heading)
    _add_bookmark_to_paragraph(heading, _bookmark_id("bab", num), _bookmark_name("bab", num))

    note = document.add_paragraph(_SECTION_DELETE_NOTE)
    note.runs[0].italic     = True
    note.runs[0].font.size  = Pt(10)
    note.paragraph_format.space_after = Pt(0)
    note.paragraph_format.alignment = WD_ALIGN_PARAGRAPH.LEFT
    _force_paragraph_runs_black(note)

    body_placeholder = document.add_paragraph(
        instructional_placeholders.get(
            make_instruction_key("bab", heading_text, number=num),
            f"Instruksi pengisian untuk {heading_text}: lengkapi isi bagian ini sesuai panduan.",
        )
    )
    _apply_line_spacing(body_placeholder.paragraph_format, spacing)
    body_placeholder.paragraph_format.alignment    = _map_alignment(
        (spacing.get("paragraph_alignment") or "JUSTIFY").upper()
    )
    body_placeholder.paragraph_format.space_after = Pt(0)
    _force_paragraph_runs_black(body_placeholder)

    if str(num) == "1":
        empty = document.add_paragraph()
        empty.paragraph_format.space_before = Pt(0)
        empty.paragraph_format.space_after  = Pt(0)
        fig_caption = figures_tables.get("caption_format_figure")
        if fig_caption:
            fig_caption = (
                fig_caption
                .replace("{n}", "1.1")
                .replace("{title}", "Contoh Gambar")
                .replace("{source}", "Sumber Contoh")
            )
        _add_example_figure(document, fig_caption, page_layout, figures_tables)

    if "BIAYA" in title.upper():
        bab_num = int(num) if num else 4
        placeholder = document.add_paragraph(
            instructional_placeholders.get(
                make_instruction_key("bab", f"BAB {bab_num}"),
                f"BAB {bab_num} ini memiliki 2 sub bab: 4.1 Anggaran Biaya dan 4.2 Jadwal Kegiatan. "
                f"Lengkapi kedua sub bab tersebut sesuai panduan dokumen."
            )
        )
        _apply_line_spacing(placeholder.paragraph_format, spacing)
        placeholder.paragraph_format.alignment    = _map_alignment(
            (spacing.get("paragraph_alignment") or "JUSTIFY").upper()
        )
        placeholder.paragraph_format.space_after = Pt(0)
        _force_paragraph_runs_black(placeholder)

    sources = match_sources_for_section(
        chunks=chunks,
        section_label=bab_label,
        section_title=section.get("title"),
    )
    _render_source_block(document, sources)


def _render_named_section(
    document: Document,
    section_type: str,
    title: str,
    spacing: dict,
    chunks: list[ChunkSource],
    instructional_placeholders: dict[str, str],
    doc_structure: dict | None = None,
    typography: dict | None = None,
) -> None:
    typography = typography or {}
    document.add_page_break()

    heading = document.add_heading(_apply_heading_case(title, typography.get("heading_1_case")), level=1)
    heading.alignment = WD_ALIGN_PARAGRAPH.CENTER
    _force_paragraph_runs_black(heading)
    _add_bookmark_to_paragraph(heading, _bookmark_id(section_type), _bookmark_name(section_type))

    note = document.add_paragraph(_SECTION_DELETE_NOTE)
    note.runs[0].italic     = True
    note.runs[0].font.size  = Pt(10)
    note.paragraph_format.alignment = WD_ALIGN_PARAGRAPH.LEFT
    _force_paragraph_runs_black(note)

    if section_type == "daftar_pustaka":
        bibliography_style = None
        if doc_structure:
            for section in doc_structure.get("sections", []):
                if section["type"] == "daftar_pustaka":
                    bibliography_style = section.get("bibliography_style")
                    break
        placeholder_text = _get_bibliography_placeholder(bibliography_style)
        paragraphs = placeholder_text.strip().split("\n\n")
        for para_text in paragraphs:
            lines = para_text.strip().split("\n")
            for line in lines:
                p = document.add_paragraph(line.strip())
                _apply_line_spacing(p.paragraph_format, spacing)
                p.paragraph_format.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
                p.paragraph_format.space_after = Pt(0)
                p.paragraph_format.left_indent = Cm(0.5)
                p.paragraph_format.first_line_indent = Cm(-0.5)
                _force_paragraph_runs_black(p)
    else:
        placeholder_text = instructional_placeholders.get(
            make_instruction_key(section_type, title),
            f"Instruksi pengisian untuk {title}: lengkapi bagian ini sesuai panduan dokumen.",
        )
        placeholder = document.add_paragraph(placeholder_text)
        _apply_line_spacing(placeholder.paragraph_format, spacing)
        _force_paragraph_runs_black(placeholder)

    sources = match_sources_for_section(chunks=chunks, section_label=title, section_title=title)
    _render_source_block(document, sources)


def _render_sub_bab_section(
    document: Document,
    section: dict,
    page_layout: dict,
    spacing: dict,
    figures_tables: dict,
    instructional_placeholders: dict[str, str],
    typography: dict | None = None,
) -> None:
    typography = typography or {}
    sub_num  = section.get("sub_number") or "?"
    raw_title = (section.get("title") or "[SUB_BAB_TANPA_JUDUL]").title()
    heading_text = _apply_heading_case(f"{sub_num} {raw_title}".strip(), typography.get("heading_2_case"))

    sep = document.add_paragraph()
    sep.paragraph_format.space_before = Pt(0)
    sep.paragraph_format.space_after  = Pt(0)
    _apply_line_spacing(sep.paragraph_format, spacing)

    heading = document.add_heading(heading_text, level=2)
    heading.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
    _force_paragraph_runs_black(heading)
    bm_id = _bookmark_id("sub_bab")
    bm_name = _bookmark_name("sub_bab", sub_num)
    _add_bookmark_to_paragraph(heading, bm_id, bm_name)

    note = document.add_paragraph(_SECTION_DELETE_NOTE)
    note.runs[0].italic     = True
    note.runs[0].font.size  = Pt(10)
    note.paragraph_format.space_after = Pt(0)
    note.paragraph_format.alignment = WD_ALIGN_PARAGRAPH.LEFT
    _force_paragraph_runs_black(note)

    bab_num = 4
    if sub_num and "." in str(sub_num):
        try:
            bab_num = int(str(sub_num).split(".")[0])
        except (ValueError, IndexError):
            bab_num = 4

    table_caption_pos   = (figures_tables.get("table_caption_position") or "ABOVE").upper()
    table_caption_align = _map_alignment((figures_tables.get("caption_alignment_table") or "CENTER").upper())

    if sub_num and bab_num == 4 and str(sub_num).endswith(".1"):
        body_placeholder = document.add_paragraph(
            instructional_placeholders.get(
                make_instruction_key("sub_bab", heading_text),
                f"Instruksi pengisian untuk {heading_text}: lengkapi isi bagian ini sesuai panduan.",
            )
        )
        _apply_line_spacing(body_placeholder.paragraph_format, spacing)
        body_placeholder.paragraph_format.alignment = _map_alignment(
            (spacing.get("paragraph_alignment") or "JUSTIFY").upper()
        )
        body_placeholder.paragraph_format.space_after = Pt(0)
        _force_paragraph_runs_black(body_placeholder)

        sep_table = document.add_paragraph()
        sep_table.paragraph_format.space_before = Pt(0)
        sep_table.paragraph_format.space_after  = Pt(0)
        sep_table.paragraph_format.line_spacing_rule = WD_LINE_SPACING.MULTIPLE
        sep_table.paragraph_format.line_spacing = 1.15

        fmt = figures_tables.get("caption_format_table") or "Tabel {bab}.{n}. {title}"
        caption_text = (
            fmt.replace("{bab}", str(bab_num)).replace("{n}", "1")
               .replace("{title}", "Rincian Anggaran Biaya")
        )
        if table_caption_pos != "BELOW":
            cap_p = document.add_paragraph(caption_text, style="Caption")
            cap_p.alignment = table_caption_align
            cap_p.paragraph_format.space_after = Pt(0)
            _force_paragraph_runs_black(cap_p)

        _add_budget_table(document, bab_num, figures_tables)

        if table_caption_pos == "BELOW":
            cap_p = document.add_paragraph(caption_text, style="Caption")
            cap_p.alignment = table_caption_align
            cap_p.paragraph_format.space_after = Pt(0)
            _force_paragraph_runs_black(cap_p)

    elif sub_num and bab_num == 4 and str(sub_num).endswith(".2"):
        fmt = figures_tables.get("caption_format_table") or "Tabel {bab}.{n}. {title}"
        caption_text = (
            fmt.replace("{bab}", str(bab_num)).replace("{n}", "2")
               .replace("{title}", "Jadwal Pelaksanaan Kegiatan")
        )
        if table_caption_pos != "BELOW":
            cap_p = document.add_paragraph(caption_text, style="Caption")
            cap_p.alignment = table_caption_align
            cap_p.paragraph_format.space_after = Pt(0)
            _force_paragraph_runs_black(cap_p)

        _add_schedule_table(document, bab_num, figures_tables, page_layout)

        if table_caption_pos == "BELOW":
            cap_p = document.add_paragraph(caption_text, style="Caption")
            cap_p.alignment = table_caption_align
            cap_p.paragraph_format.space_after = Pt(0)
            _force_paragraph_runs_black(cap_p)

    is_table_sub_bab = sub_num and bab_num == 4 and (str(sub_num).endswith(".1") or str(sub_num).endswith(".2"))
    if not is_table_sub_bab:
        body_placeholder = document.add_paragraph(
            instructional_placeholders.get(
                make_instruction_key("sub_bab", heading_text),
                f"Instruksi pengisian untuk {heading_text}: lengkapi isi bagian ini sesuai panduan.",
            )
        )
        _apply_line_spacing(body_placeholder.paragraph_format, spacing)
        body_placeholder.paragraph_format.alignment   = _map_alignment(
            (spacing.get("paragraph_alignment") or "JUSTIFY").upper()
        )
        body_placeholder.paragraph_format.space_after = Pt(0)
        _force_paragraph_runs_black(body_placeholder)


def _render_item_lampiran_section(
    document: Document,
    section: dict,
    page_layout: dict,
    spacing: dict,
    instructional_placeholders: dict[str, str],
    typography: dict | None = None,
    lampiran_separator: str = ".",
    figures_tables: dict | None = None,
) -> None:
    typography = typography or {}
    lampiran_number_raw = (section.get("lampiran_number") or "Lampiran ?").title()
    title               = (section.get("title") or "[LAMPIRAN_TANPA_JUDUL]").title()

    lampiran_fmt = (figures_tables or {}).get("caption_format_lampiran")
    if lampiran_fmt:
        # Ekstrak ordinal dari "Lampiran 1" → "1", "Lampiran A" → "A"
        parts = lampiran_number_raw.strip().split(None, 1)
        ordinal = parts[1] if len(parts) == 2 and parts[0].upper() == "LAMPIRAN" else lampiran_number_raw
        heading_text = _apply_heading_case(
            lampiran_fmt.replace("{n}", ordinal).replace("{title}", title),
            typography.get("heading_2_case"),
        )
    else:
        sep_str = f"{lampiran_separator} " if lampiran_separator else " "
        heading_text = _apply_heading_case(
            f"{lampiran_number_raw}{sep_str}{title}".strip(),
            typography.get("heading_2_case"),
        )

    sep = document.add_paragraph()
    sep.paragraph_format.space_before = Pt(0)
    sep.paragraph_format.space_after  = Pt(0)
    _apply_line_spacing(sep.paragraph_format, spacing)

    lampiran_align = _map_alignment(((figures_tables or {}).get("caption_alignment_lampiran") or "JUSTIFY").upper())
    heading = document.add_heading(heading_text, level=2)
    heading.alignment = lampiran_align
    _force_paragraph_runs_black(heading)
    bm_id = _bookmark_id("lampiran")
    bm_name = _bookmark_name("lampiran", lampiran_number_raw)
    _add_bookmark_to_paragraph(heading, bm_id, bm_name)

    note = document.add_paragraph(_SECTION_DELETE_NOTE)
    note.runs[0].italic     = True
    note.runs[0].font.size  = Pt(10)
    note.paragraph_format.space_after = Pt(0)
    note.paragraph_format.alignment = WD_ALIGN_PARAGRAPH.LEFT
    _force_paragraph_runs_black(note)

    body_placeholder = document.add_paragraph(
        instructional_placeholders.get(
            make_instruction_key("item_lampiran", heading_text),
            f"Instruksi pengisian untuk {heading_text}: lengkapi isi bagian ini sesuai panduan.",
        )
    )
    _apply_line_spacing(body_placeholder.paragraph_format, spacing)
    body_placeholder.paragraph_format.alignment    = _map_alignment(
        (spacing.get("paragraph_alignment") or "JUSTIFY").upper()
    )
    body_placeholder.paragraph_format.space_after = Pt(0)
    _force_paragraph_runs_black(body_placeholder)


def _render_source_block(document: Document, sources: list[ChunkSource]) -> None:
    if not sources:
        p = document.add_paragraph("Sumber: [BELUM DITEMUKAN]")
        p.runs[0].italic     = True
        p.runs[0].font.size  = Pt(10)
        _force_paragraph_runs_black(p)
        return

    parts = [format_source_line(s) for s in sources]
    p = document.add_paragraph(f"Sumber: {' | '.join(parts)}")
    p.runs[0].italic     = True
    p.runs[0].font.size  = Pt(10)
    _force_paragraph_runs_black(p)


def _add_budget_table(document: Document, bab_number: int, figures_tables: dict) -> None:
    budget_rules = figures_tables.get("budget_format_rules")

    if budget_rules and budget_rules.get("budget_items"):
        items = []
        for i, item in enumerate(budget_rules["budget_items"][:4], start=1):
            desc = item.get("jenis_pengeluaran", "")
            if item.get("persentase_maksimum"):
                desc += f" maksimum {item['persentase_maksimum']}% dari jumlah dana yang diusulkan"
            if item.get("contoh"):
                desc = f"{desc} ({item['contoh']})"
            items.append((str(i), desc))
        sumber_dana = budget_rules.get("sumber_dana_options", ["Belmawa", "Perguruan Tinggi", "Instansi Lain (jika ada)"])
    else:
        items = [
            ("1", "Bahan habis pakai (contoh: ATK, kertas, bahan, dan lain lain) "
                  "maksimum 60% dari jumlah dana yang diusulkan"),
            ("2", "Sewa dan jasa (sewa/jasa alat; jasa pembuatan produk pihak ketiga, "
                  "dan lain lain), maksimum 15% dari jumlah dana yang diusulkan"),
            ("3", "Transportasi lokal maksimum 30% dari jumlah dana yang diusulkan"),
            ("4", "Lain-lain (contoh: biaya komunikasi, biaya bayar akses publikasi, "
                  "biaya adsense media sosial, dan lain-lain) maksimum 15% dari jumlah dana yang diusulkan"),
        ]
        sumber_dana = ["Belmawa", "Perguruan Tinggi", "Instansi Lain (jika ada)"]

    num_items = len(items)
    table_rows = 2 + (num_items * 3) + 1 + 1
    table = document.add_table(rows=table_rows, cols=4)
    table.style = "Table Grid"

    hdr = table.rows[0].cells
    for i, text in enumerate(["No", "Jenis Pengeluaran", "Sumber Dana", "Besaran Dana\n(Rp)"]):
        hdr[i].text = text
        hdr[i].paragraphs[0].alignment = WD_ALIGN_PARAGRAPH.CENTER
        hdr[i].paragraphs[0].runs[0].bold = True

    for i, (num, desc) in enumerate(items):
        base = 1 + i * 3
        table.cell(base, 0).text = num
        table.cell(base, 0).paragraphs[0].alignment = WD_ALIGN_PARAGRAPH.CENTER
        table.cell(base, 1).text = desc
        for j, sd in enumerate(sumber_dana):
            if base + j < table_rows:
                table.cell(base + j, 2).text = sd

    jumlah_row = 1 + num_items * 3
    table.cell(jumlah_row, 0).text = "Jumlah"
    table.cell(jumlah_row, 0).paragraphs[0].alignment = WD_ALIGN_PARAGRAPH.CENTER

    rekap_row = jumlah_row + 1
    table.cell(rekap_row, 0).text = "Rekap Sumber Dana"
    table.cell(rekap_row, 0).paragraphs[0].alignment = WD_ALIGN_PARAGRAPH.CENTER
    for j, sd in enumerate([*sumber_dana, "Jumlah"]):
        if rekap_row + j < table_rows:
            table.cell(rekap_row + j, 2).text = sd

    for i in range(num_items):
        base = 1 + i * 3
        table.cell(base, 0).merge(table.cell(base + 2, 0))
        table.cell(base, 0).vertical_alignment = WD_ALIGN_VERTICAL.CENTER
        table.cell(base, 1).merge(table.cell(base + 2, 1))
        table.cell(base, 1).vertical_alignment = WD_ALIGN_VERTICAL.CENTER

    table.cell(jumlah_row, 0).merge(table.cell(jumlah_row, 2))
    table.cell(jumlah_row, 0).vertical_alignment = WD_ALIGN_VERTICAL.CENTER

    table.cell(rekap_row, 0).merge(table.cell(rekap_row, 1))
    table.cell(rekap_row, 0).vertical_alignment = WD_ALIGN_VERTICAL.CENTER

    col_widths = [Cm(1.5), Cm(6.0), Cm(4.0), Cm(2.5)]
    for row in table.rows:
        for ci, width in enumerate(col_widths):
            if ci < len(row.cells):
                row.cells[ci].width = width

    additional_rules = None
    if budget_rules:
        additional_rules = budget_rules.get("additional_rules")
    if additional_rules:
        rules_text = (
            "; ".join(additional_rules)
            if isinstance(additional_rules, list)
            else additional_rules
        )
        note_p = document.add_paragraph(rules_text)
        note_p.runs[0].italic = True
        note_p.runs[0].font.size = Pt(10)
        note_p.paragraph_format.space_after = Pt(0)
        _force_paragraph_runs_black(note_p)


def _add_schedule_table(document: Document, bab_number: int, figures_tables: dict, page_layout: dict) -> None:
    paper_width, _ = _get_paper_dimensions(page_layout.get("paper_size"))
    text_width_cm = paper_width - page_layout.get("margin_left_cm", 4.0) - page_layout.get("margin_right_cm", 3.0)
    table = document.add_table(rows=7, cols=7)
    table.style = "Table Grid"

    total_fixed = Cm(1.0) + Cm(1.0) * 4 + Cm(3.5)
    remaining = Cm(text_width_cm) - total_fixed
    jenis_kegiatan_width = remaining if remaining > Cm(0) else Cm(4.5)

    widths = [Cm(1.0), jenis_kegiatan_width, Cm(1.0), Cm(1.0), Cm(1.0), Cm(1.0), Cm(3.5)]
    for ri in range(7):
        for ci, width in enumerate(widths):
            table.cell(ri, ci).width = width

    for ci, txt in enumerate(["No", "Jenis Kegiatan", "Bulan", "", "", "", "Penanggung Jawab"]):
        if txt:
            table.cell(0, ci).text = txt

    for m, label in enumerate(["1", "2", "3", "4"]):
        table.cell(1, 2 + m).text = label
        table.cell(1, 2 + m).paragraphs[0].alignment = WD_ALIGN_PARAGRAPH.CENTER

    for i in range(5):
        table.cell(2 + i, 0).text = str(i + 1)
        table.cell(2 + i, 0).paragraphs[0].alignment = WD_ALIGN_PARAGRAPH.CENTER
        table.cell(2 + i, 1).text = f"[Jenis Kegiatan {i + 1}]"
        table.cell(2 + i, 6).text = "[Penanggung Jawab]"

    table.cell(0, 0).merge(table.cell(1, 0))
    table.cell(0, 0).vertical_alignment = WD_ALIGN_VERTICAL.CENTER
    table.cell(0, 0).paragraphs[0].alignment = WD_ALIGN_PARAGRAPH.CENTER

    table.cell(0, 1).merge(table.cell(1, 1))
    table.cell(0, 1).vertical_alignment = WD_ALIGN_VERTICAL.CENTER
    table.cell(0, 1).paragraphs[0].alignment = WD_ALIGN_PARAGRAPH.CENTER

    table.cell(0, 2).merge(table.cell(0, 5))
    table.cell(0, 2).vertical_alignment = WD_ALIGN_VERTICAL.CENTER
    table.cell(0, 2).paragraphs[0].alignment = WD_ALIGN_PARAGRAPH.CENTER

    table.cell(0, 6).merge(table.cell(1, 6))
    table.cell(0, 6).vertical_alignment = WD_ALIGN_VERTICAL.CENTER
    table.cell(0, 6).paragraphs[0].alignment = WD_ALIGN_PARAGRAPH.CENTER

    for ci in [0, 1, 2, 6]:
        para = table.cell(0, ci).paragraphs[0]
        if para.runs:
            para.runs[0].bold = True

    empty = document.add_paragraph()
    empty.paragraph_format.space_before = Pt(0)
    empty.paragraph_format.space_after  = Pt(0)


def _add_example_figure(
    document: Document,
    caption: str | None = None,
    page_layout: dict | None = None,
    figures_tables: dict | None = None,
) -> None:
    """Add example figure from data/images.jpg if available."""
    if page_layout:
        paper_width, _ = _get_paper_dimensions(page_layout.get("paper_size"))
        img_width = Cm(paper_width - page_layout.get("margin_left_cm", 4.0) - page_layout.get("margin_right_cm", 3.0))
    else:
        img_width = Cm(10)

    caption_pos      = (figures_tables.get("figure_caption_position") or "BELOW").upper() if figures_tables else "BELOW"
    caption_align    = _map_alignment(((figures_tables or {}).get("caption_alignment_figure") or "CENTER").upper())

    possible_paths = [
        Path(__file__).parent.parent.parent / "data" / "images.jpg",
        Path(__file__).parent.parent / "data" / "images.jpg",
        Path("ai/data/images.jpg"),
        Path("data/images.jpg"),
    ]
    figure_image_path = None
    for p in possible_paths:
        if p.exists() and p.is_file():
            figure_image_path = p
            break

    if caption and caption_pos == "ABOVE":
        caption_p = document.add_paragraph(caption, style="Caption")
        caption_p.alignment = caption_align
        caption_p.paragraph_format.space_after = Pt(0)
        _force_paragraph_runs_black(caption_p)

    if figure_image_path:
        document.add_picture(str(figure_image_path), width=img_width)
        document.paragraphs[-1].alignment = WD_ALIGN_PARAGRAPH.CENTER
    else:
        placeholder_p = document.add_paragraph("[Gambar: sisipkan gambar yang relevan di sini]")
        placeholder_p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        placeholder_p.runs[0].italic = True
        _force_paragraph_runs_black(placeholder_p)

    if caption and caption_pos != "ABOVE":
        caption_p = document.add_paragraph(caption, style="Caption")
        caption_p.alignment = caption_align
        caption_p.paragraph_format.space_after = Pt(0)
        _force_paragraph_runs_black(caption_p)

    empty = document.add_paragraph()
    empty.paragraph_format.space_before = Pt(0)
    empty.paragraph_format.space_after  = Pt(0)


def _add_seq_caption(document: Document, label: str, template: str) -> None:
    paragraph = document.add_paragraph(style="Caption")
    prefix, suffix = _split_caption_template(template, label)
    paragraph.add_run(prefix)
    _append_field(paragraph, f" SEQ {label} \\* ARABIC ")
    paragraph.add_run(suffix)
    _force_paragraph_runs_black(paragraph)


def _split_caption_template(template: str, label: str) -> tuple[str, str]:
    normalized = (
        template
        .replace("{title}", "[JUDUL]")
        .replace("{source}", "[ISI_SUMBER]")
        .replace("{bab}.", "[BAB_PREFIX].")
        .replace("[Judul Gambar]", "[JUDUL]")
        .replace("[Judul Tabel]", "[JUDUL]")
        .replace("([Sumber jika ada])", "(Sumber: [ISI_SUMBER])")
    )
    for marker in ("{n}", "[N.N]", "[N]"):
        if marker in normalized:
            before, after = normalized.split(marker, maxsplit=1)
            return before, after
    return f"{label} ", ". [JUDUL]"


_LINE_SPACING_GRUP_A: dict[str, float] = {
    "SINGLE": 1.0,
    "ONE_POINT_FIVE": 1.5,
    "DOUBLE": 2.0,
}


def _apply_line_spacing(paragraph_format, spacing: dict) -> None:
    """Terapkan spasi baris sesuai aturan MS Word.

    Grup A (SINGLE/ONE_POINT_FIVE/DOUBLE):
        Multiplier statis — line_spacing di data diabaikan.
    Grup B (MULTIPLE):
        line_spacing = desimal pengali (contoh: 1.15). Default 1.15 jika null.
    Grup C (AT_LEAST/EXACTLY):
        line_spacing = nilai pt absolut. Default 12.0 jika null.
    """
    _RULE_COMPAT = {"EXACT": "EXACTLY", "AT LEAST": "AT_LEAST"}
    rule = _RULE_COMPAT.get(
        (spacing.get("line_spacing_rule") or "MULTIPLE").upper(),
        (spacing.get("line_spacing_rule") or "MULTIPLE").upper(),
    )

    if rule in _LINE_SPACING_GRUP_A:
        paragraph_format.line_spacing_rule = WD_LINE_SPACING.MULTIPLE
        paragraph_format.line_spacing = _LINE_SPACING_GRUP_A[rule]
    elif rule == "MULTIPLE":
        multiplier = float(spacing.get("line_spacing") or 1.15)
        paragraph_format.line_spacing_rule = WD_LINE_SPACING.MULTIPLE
        paragraph_format.line_spacing = multiplier
    elif rule == "EXACTLY":
        pt_val = float(spacing.get("line_spacing") or 12.0)
        paragraph_format.line_spacing_rule = WD_LINE_SPACING.EXACTLY
        paragraph_format.line_spacing = Pt(pt_val)
    elif rule == "AT_LEAST":
        pt_val = float(spacing.get("line_spacing") or 12.0)
        paragraph_format.line_spacing_rule = WD_LINE_SPACING.AT_LEAST
        paragraph_format.line_spacing = Pt(pt_val)
    else:
        paragraph_format.line_spacing_rule = WD_LINE_SPACING.MULTIPLE
        paragraph_format.line_spacing = 1.15


def _map_alignment(value: str) -> WD_ALIGN_PARAGRAPH:
    mapping = {
        "LEFT":    WD_ALIGN_PARAGRAPH.LEFT,
        "CENTER":  WD_ALIGN_PARAGRAPH.CENTER,
        "RIGHT":   WD_ALIGN_PARAGRAPH.RIGHT,
        "JUSTIFY": WD_ALIGN_PARAGRAPH.JUSTIFY,
    }
    return mapping.get(value, WD_ALIGN_PARAGRAPH.JUSTIFY)


def _build_page_num_position(location: str, alignment: str) -> str:
    return f"{(location or 'FOOTER').lower()}_{(alignment or 'RIGHT').lower()}"


def _apply_page_numbering(section, position: str, fmt: str, start: int) -> None:
    section.header.is_linked_to_previous = False
    section.footer.is_linked_to_previous = False

    target    = section.header if position.startswith("header_") else section.footer
    alignment = _position_alignment(position)
    paragraph = target.paragraphs[0] if target.paragraphs else target.add_paragraph()
    paragraph.alignment = alignment
    _clear_paragraph(paragraph)
    _append_field(paragraph, " PAGE ")
    _set_page_number_type(section, fmt=fmt, start=start)


def _position_alignment(position: str) -> WD_ALIGN_PARAGRAPH:
    if position.endswith("_left"):
        return WD_ALIGN_PARAGRAPH.LEFT
    if position.endswith("_center"):
        return WD_ALIGN_PARAGRAPH.CENTER
    return WD_ALIGN_PARAGRAPH.RIGHT


def _set_page_number_type(section, fmt: str, start: int) -> None:
    sect_pr = section._sectPr
    pg_num_type = sect_pr.find(qn("w:pgNumType"))
    if pg_num_type is None:
        pg_num_type = OxmlElement("w:pgNumType")
        sect_pr.append(pg_num_type)
    pg_num_type.set(qn("w:fmt"), fmt)
    pg_num_type.set(qn("w:start"), str(start))


def _append_field(paragraph, instruction: str) -> None:
    run = paragraph.add_run()
    run.font.color.rgb = RGBColor(0, 0, 0)
    begin = OxmlElement("w:fldChar")
    begin.set(qn("w:fldCharType"), "begin")

    instr = OxmlElement("w:instrText")
    instr.set(qn("xml:space"), "preserve")
    instr.text = instruction

    separate = OxmlElement("w:fldChar")
    separate.set(qn("w:fldCharType"), "separate")
    text = OxmlElement("w:t")
    text.text = "1"

    end = OxmlElement("w:fldChar")
    end.set(qn("w:fldCharType"), "end")

    run._r.append(begin)
    run._r.append(instr)
    run._r.append(separate)
    run._r.append(text)
    run._r.append(end)


def _clear_paragraph(paragraph) -> None:
    for run in paragraph.runs:
        run.clear()


def render_proposal_docx_bytes(
    output_data: dict,
    chunks: list,
    instructional_placeholders: dict[str, str],
) -> bytes:
    """
    Render DOCX dan return sebagai bytes.
    Menggantikan versi yang menyimpan ke file — tidak ada filesystem lokal.
    """
    doc: Document = Document()
    first_section = doc.sections[0]
    _configure_page_layout(first_section, output_data["page_layout"])
    _apply_base_styles(doc, output_data["typography"], output_data["spacing"], output_data.get("figures_and_tables"))

    typography = output_data["typography"]
    page_layout = output_data["page_layout"]
    spacing = output_data["spacing"]
    numbering = output_data["numbering"]
    figures_tables = output_data["figures_and_tables"]
    doc_structure = output_data["document_structure_proposal"]

    prelim_num = numbering.get("preliminary") or {}
    content_num = numbering.get("content") or {}

    has_preliminary = _has_preliminary_pages(doc_structure)
    if has_preliminary:
        _render_preliminary_pages(doc, doc_structure, page_layout, typography, instructional_placeholders, figures_tables)
        _apply_page_numbering(
            first_section,
            _build_page_num_position(prelim_num.get("location", "FOOTER"), prelim_num.get("alignment", "RIGHT")),
            fmt=prelim_num.get("format", "lowerRoman"),
            start=1,
        )
        content_section = doc.add_section(WD_SECTION_START.NEW_PAGE)
        _configure_page_layout(content_section, page_layout)
        _apply_page_numbering(
            content_section,
            _build_page_num_position(content_num.get("location", "HEADER"), content_num.get("alignment", "RIGHT")),
            fmt=content_num.get("format", "decimal"),
            start=1,
        )
    else:
        _apply_page_numbering(
            first_section,
            _build_page_num_position(content_num.get("location", "HEADER"), content_num.get("alignment", "RIGHT")),
            fmt=content_num.get("format", "decimal"),
            start=1,
        )

    _render_proposal_body(doc, doc_structure, page_layout, spacing, numbering, figures_tables, chunks, instructional_placeholders, typography)

    format_nama_file = doc_structure.get("format_nama_file")
    if format_nama_file:
        doc.core_properties.subject = f"Format nama file: {format_nama_file}"
        note_p = doc.add_paragraph(f"Catatan format nama file pengumpulan: {format_nama_file}")
        note_p.runs[0].italic = True
        note_p.runs[0].font.size = Pt(10)
        _force_paragraph_runs_black(note_p)

    buf = BytesIO()
    doc.save(buf)
    buf.seek(0)
    return buf.getvalue()
