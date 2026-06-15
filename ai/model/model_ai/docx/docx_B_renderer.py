"""Renderer Type B: menulis konten terstruktur ke dokumen .docx khusus PKM-AI (artikel ilmiah). Urutan eksekusi mengikuti Sistematika C panduan PKM-AI: judul_abstrak (halaman 1, spasi 1.0) → bab artikel (spasi 1.15) → daftar_pustaka (Harvard hanging indent) → lampiran. Posisi pipeline: instructional_placeholder_builder → docx_B_renderer → DOCX output. Keyword: automated document generation"""
from io import BytesIO

from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.shared import Cm, Pt, RGBColor
from docx.text.paragraph import Paragraph
from docx.oxml.ns import qn
from docx.oxml import OxmlElement

from model_ai.docx.docx_A_renderer import (
    _add_bookmark_to_paragraph,
    _apply_line_spacing,
    _apply_page_numbering,
    _build_page_num_position,
    _configure_page_layout,
    _force_paragraph_runs_black,
    _get_bibliography_placeholder,
    _map_alignment,
)
from model_ai.docx.instructional_placeholder_builder import make_instruction_key


_SECTION_DELETE_NOTE = "(Catatan: bagian ini boleh dihapus)"

_BOOKMARK_IDS_ARTIKEL: dict[str, int] = {
    "judul_abstrak":  1,
    "daftar_pustaka": 50,
    "lampiran_utama": 51,
}


def _bookmark_name_artikel(section_type: str, number=None) -> str:
    if section_type == "bab" and number:
        return f"bab_{number}"
    if section_type == "item_lampiran" and number:
        ordinal = str(number).strip().replace("Lampiran", "").strip()
        return f"lampiran_{ordinal}" if ordinal else "lampiran_item"
    return section_type


def _bookmark_id_artikel(section_type: str, number=None) -> int:
    if section_type == "bab" and number:
        try:
            return 100 + int(number)
        except (TypeError, ValueError):
            return 100
    if section_type == "item_lampiran" and number:
        try:
            ordinal = int(str(number).strip().replace("Lampiran", "").strip())
            return 200 + ordinal
        except ValueError:
            return 200
    return _BOOKMARK_IDS_ARTIKEL.get(section_type, 99)


def _spacing_single() -> dict:
    return {"line_spacing_rule": "SINGLE", "line_spacing": None}


def _spacing_body(spacing: dict) -> dict:
    rule = (spacing.get("line_spacing_rule") or "MULTIPLE").upper()
    ls = spacing.get("line_spacing")
    if rule == "MULTIPLE" and ls is None:
        ls = 1.15
    return {"line_spacing_rule": rule, "line_spacing": ls}


def _spacing_title_abstract(spacing: dict) -> dict:
    raw = spacing.get("line_spacing_title_abstract")
    if raw is None:
        return _spacing_single()
    try:
        val = float(raw)
    except (TypeError, ValueError):
        return _spacing_single()
    if val == 1.0:
        return _spacing_single()
    return {"line_spacing_rule": "MULTIPLE", "line_spacing": val}


def _apply_base_styles_artikel(document: Document, typography: dict, spacing: dict) -> None:
    """Style dasar artikel ilmiah PKM-AI: TNR 12 body, 1.15 spasi, justify."""
    body_font = typography.get("font_family") or "Times New Roman"
    body_size = typography.get("font_size_body_pt") or 12

    normal = document.styles["Normal"]
    normal.font.name = body_font
    normal.font.size = Pt(body_size)
    normal.font.color.rgb = RGBColor(0, 0, 0)
    normal._element.rPr.rFonts.set(qn("w:ascii"), body_font)
    normal._element.rPr.rFonts.set(qn("w:hAnsi"), body_font)
    _apply_line_spacing(normal.paragraph_format, _spacing_body(spacing))
    normal.paragraph_format.alignment = _map_alignment((spacing.get("paragraph_alignment") or "JUSTIFY").upper())
    normal.paragraph_format.space_before = Pt(0)
    normal.paragraph_format.space_after = Pt(0)

    # Heading 1 = judul section artikel (TNR 12 bold, kiri, tidak ALL CAPS)
    try:
        h1 = document.styles["Heading 1"]
        h1.font.name = body_font
        h1.font.size = Pt(body_size)
        h1.font.bold = True
        h1.font.all_caps = False
        h1.font.color.rgb = RGBColor(0, 0, 0)
        h1.paragraph_format.alignment = WD_ALIGN_PARAGRAPH.LEFT
        h1.paragraph_format.space_before = Pt(0)
        h1.paragraph_format.space_after = Pt(0)
        style_el = h1._element
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
    except KeyError:
        pass


def _add_run(paragraph, text: str, font_name: str, size_pt: int,
             bold: bool = False, italic: bool = False, superscript: bool = False) -> None:
    run = paragraph.add_run(text)
    run.font.name = font_name
    run.font.size = Pt(size_pt)
    run.font.bold = bold
    run.font.italic = italic
    run.font.color.rgb = RGBColor(0, 0, 0)
    if superscript:
        run.font.superscript = True
    rPr = run._element.get_or_add_rPr()
    rFonts = rPr.find(qn("w:rFonts"))
    if rFonts is None:
        rFonts = OxmlElement("w:rFonts")
        rPr.insert(0, rFonts)
    rFonts.set(qn("w:ascii"), font_name)
    rFonts.set(qn("w:hAnsi"), font_name)
    rFonts.set(qn("w:cs"), font_name)


def _add_styled_paragraph(document: Document, alignment: WD_ALIGN_PARAGRAPH,
                          spacing_dict: dict, space_after_pt: float = 0) -> Paragraph:
    p = document.add_paragraph()
    p.paragraph_format.alignment = alignment
    p.paragraph_format.space_before = Pt(0)
    p.paragraph_format.space_after = Pt(space_after_pt)
    _apply_line_spacing(p.paragraph_format, spacing_dict)
    return p


def _add_section_note(document: Document, body_font: str) -> None:
    note = document.add_paragraph(_SECTION_DELETE_NOTE)
    note.paragraph_format.alignment = WD_ALIGN_PARAGRAPH.LEFT
    note.paragraph_format.space_after = Pt(0)
    if note.runs:
        note.runs[0].italic = True
        note.runs[0].font.size = Pt(10)
        note.runs[0].font.name = body_font
    _force_paragraph_runs_black(note)


def _render_judul_abstrak(
    document: Document,
    typography: dict,
    spacing: dict,
    instructional_placeholders: dict[str, str],
    section: dict,
) -> None:
    """Render halaman pertama artikel: judul, penulis, abstrak Indonesia + Inggris.
    Spasi seluruh halaman = 1.0 (line_spacing_title_abstract).
    """
    body_font    = typography.get("font_family") or "Times New Roman"
    body_size    = typography.get("font_size_body_pt") or 12
    title_size   = typography.get("font_size_title_pt") or 12
    author_size  = typography.get("font_size_author_pt") or 10
    abstract_sz  = typography.get("font_size_abstract_pt") or 11
    title_spacing = _spacing_title_abstract(spacing)
    title_style_raw = (typography.get("title_style") or "BOLD_UPPERCASE").upper()
    title_is_bold = "BOLD" in title_style_raw
    title_is_upper = "UPPERCASE" in title_style_raw

    title_text = "JUDUL DIBUAT RINGKAS MAKSIMUM 20 KATA DENGAN MENONJOLKAN KATA KUNCI KEGIATAN ILMIAH DAN HASIL UTAMANYA, HURUF KAPITAL, HINDARI ADANYA SINGKATAN"
    if not title_is_upper:
        title_text = title_text.title()

    p_title = _add_styled_paragraph(document, WD_ALIGN_PARAGRAPH.CENTER, title_spacing, space_after_pt=6)
    _add_run(p_title, title_text, body_font, title_size, bold=title_is_bold)
    _add_bookmark_to_paragraph(p_title, _bookmark_id_artikel("judul_abstrak"), _bookmark_name_artikel("judul_abstrak"))

    # Baris penulis
    p_authors = _add_styled_paragraph(document, WD_ALIGN_PARAGRAPH.CENTER, title_spacing)
    _add_run(p_authors, "Penulis Satu", body_font, author_size)
    _add_run(p_authors, "1)", body_font, author_size, superscript=True)
    _add_run(p_authors, ", Penulis Dua", body_font, author_size)
    _add_run(p_authors, "1)", body_font, author_size, superscript=True)
    _add_run(p_authors, ", Penulis Tiga", body_font, author_size)
    _add_run(p_authors, "2)", body_font, author_size, superscript=True)
    _add_run(p_authors, ", Penulis Terakhir", body_font, author_size)
    _add_run(p_authors, "2)*", body_font, author_size, superscript=True)

    # Alamat institusi 1
    p_inst1 = _add_styled_paragraph(document, WD_ALIGN_PARAGRAPH.CENTER, title_spacing)
    _add_run(p_inst1, "1", body_font, author_size, superscript=True)
    _add_run(p_inst1, "Nama institusi dan alamat institusi dari penulis satu dan dua", body_font, author_size)

    # Alamat institusi 2
    p_inst2 = _add_styled_paragraph(document, WD_ALIGN_PARAGRAPH.CENTER, title_spacing)
    _add_run(p_inst2, "2", body_font, author_size, superscript=True)
    _add_run(p_inst2, "Nama institusi dan alamat institusi dari penulis tiga dan terakhir", body_font, author_size)

    # Penulis korespondensi
    p_corr = _add_styled_paragraph(document, WD_ALIGN_PARAGRAPH.CENTER, title_spacing, space_after_pt=6)
    _add_run(p_corr, "*Penulis korespondensi: penulis_terakhir@univ.ac.id", body_font, author_size)

    # Note instruksi (LLM-generated)
    _add_section_note(document, body_font)
    instr_key = make_instruction_key("judul_abstrak", section.get("title") or "JUDUL DAN ABSTRAK")
    instr_text = instructional_placeholders.get(
        instr_key,
        "tulis judul artikel, nama seluruh penulis beserta afiliasi institusi, "
        "serta abstrak dalam bahasa Indonesia dan Inggris disertai kata kunci.",
    )
    p_note = _add_styled_paragraph(document, WD_ALIGN_PARAGRAPH.JUSTIFY, title_spacing, space_after_pt=6)
    _add_run(p_note, f"Instruksi: {instr_text}", body_font, 10, italic=True)

    # ABSTRAK (Bahasa Indonesia)
    p_abstrak_head = _add_styled_paragraph(document, WD_ALIGN_PARAGRAPH.CENTER, title_spacing)
    _add_run(p_abstrak_head, "ABSTRAK", body_font, abstract_sz, bold=False)

    p_abstrak_body = _add_styled_paragraph(document, WD_ALIGN_PARAGRAPH.JUSTIFY, title_spacing, space_after_pt=6)
    _add_run(
        p_abstrak_body,
        "[Tulis abstrak dalam Bahasa Indonesia di sini dalam format satu paragraf, "
        "cetak tegak, perataan rata kiri dan kanan, maksimum 250 kata. Abstrak memuat "
        "latar belakang, tujuan, metode (termasuk cara analisis data jika ada data primer), "
        "hasil utama secara ringkas dan runtut, serta kesimpulan yang selaras dengan tujuan.]",
        body_font, abstract_sz,
    )

    p_kata_kunci = _add_styled_paragraph(document, WD_ALIGN_PARAGRAPH.JUSTIFY, title_spacing, space_after_pt=12)
    _add_run(p_kata_kunci, "Kata-kata kunci: ", body_font, abstract_sz, bold=True)
    _add_run(p_kata_kunci, "[latar belakang], [tujuan], [metode], [hasil], [kesimpulan]. (3-5 kata/frasa)", body_font, abstract_sz)

    # ABSTRACT (Bahasa Inggris, italic)
    p_abstract_head = _add_styled_paragraph(document, WD_ALIGN_PARAGRAPH.CENTER, title_spacing)
    _add_run(p_abstract_head, "ABSTRACT", body_font, abstract_sz, italic=True)

    p_abstract_body = _add_styled_paragraph(document, WD_ALIGN_PARAGRAPH.JUSTIFY, title_spacing, space_after_pt=6)
    _add_run(
        p_abstract_body,
        "[Write the abstract in English here as a single paragraph, italic style, "
        "justified alignment, maximum 250 words. The Abstract contains a brief background, "
        "aims and objectives, sequential methods (with the analysis performed for primary "
        "data if applicable), concise results in the order of the method, and a conclusion "
        "according to the objectives of the study.]",
        body_font, abstract_sz, italic=True,
    )

    p_keywords = _add_styled_paragraph(document, WD_ALIGN_PARAGRAPH.JUSTIFY, title_spacing)
    _add_run(p_keywords, "Keywords: ", body_font, abstract_sz, bold=True, italic=True)
    _add_run(p_keywords, "[background], [objectives], [methods], [results], [conclusion]. (3-5 words/phrases)", body_font, abstract_sz, italic=True)


def _render_artikel_bab_section(
    document: Document,
    section: dict,
    typography: dict,
    spacing: dict,
    numbering: dict,
    instructional_placeholders: dict[str, str],
) -> None:
    """Render satu bab artikel: heading "{n}. {title}" bold + body placeholder."""
    body_font   = typography.get("font_family") or "Times New Roman"
    body_size   = typography.get("font_size_body_pt") or 12
    chapter_fmt = numbering.get("chapter_format") or "{n}."
    body_spacing = _spacing_body(spacing)
    align_body   = _map_alignment((spacing.get("paragraph_alignment") or "JUSTIFY").upper())

    title = section.get("title") or "[JUDUL_BAB_BELUM_TERDETEKSI]"
    num   = section.get("number")
    bab_label = chapter_fmt.replace("{n}", str(num)) if num else ""
    heading_text = f"{bab_label} {title}".strip()

    _add_styled_paragraph(document, WD_ALIGN_PARAGRAPH.LEFT, body_spacing)
    p_head = _add_styled_paragraph(document, WD_ALIGN_PARAGRAPH.LEFT, body_spacing)
    _add_run(p_head, heading_text, body_font, body_size, bold=True)
    _add_bookmark_to_paragraph(p_head, _bookmark_id_artikel("bab", num), _bookmark_name_artikel("bab", num))

    # Catatan instruksi
    _add_section_note(document, body_font)

    # Body placeholder
    body_text = instructional_placeholders.get(
        make_instruction_key("bab", heading_text, number=num),
        f"Instruksi pengisian untuk {heading_text}: lengkapi isi bagian ini sesuai panduan PKM-AI.",
    )
    p_body = _add_styled_paragraph(document, align_body, body_spacing, space_after_pt=6)
    _add_run(p_body, body_text, body_font, body_size)


def _render_artikel_daftar_pustaka(
    document: Document,
    section: dict,
    typography: dict,
    spacing: dict,
) -> None:
    """Render Daftar Pustaka artikel: heading bold, isi Harvard style dengan hanging indent 1,15 spasi."""
    body_font = typography.get("font_family") or "Times New Roman"
    body_size = typography.get("font_size_body_pt") or 12
    body_spacing = _spacing_body(spacing)

    document.add_page_break()

    title = section.get("title") or "Daftar Pustaka"
    p_head = _add_styled_paragraph(document, WD_ALIGN_PARAGRAPH.LEFT, body_spacing)
    _add_run(p_head, title, body_font, body_size, bold=True)
    _add_bookmark_to_paragraph(p_head, _bookmark_id_artikel("daftar_pustaka"), _bookmark_name_artikel("daftar_pustaka"))

    _add_section_note(document, body_font)

    bibliography_style = section.get("bibliography_style") or "HARVARD"
    placeholder_text = _get_bibliography_placeholder(bibliography_style)
    for para_block in placeholder_text.strip().split("\n\n"):
        for line in para_block.strip().split("\n"):
            p = _add_styled_paragraph(document, WD_ALIGN_PARAGRAPH.JUSTIFY, body_spacing)
            p.paragraph_format.left_indent = Cm(1.0)
            p.paragraph_format.first_line_indent = Cm(-1.0)
            _add_run(p, line.strip(), body_font, body_size)


def _render_artikel_lampiran_utama(
    document: Document,
    section: dict,
    typography: dict,
    spacing: dict,
) -> None:
    """Render heading pembuka bagian Lampiran artikel."""
    body_font = typography.get("font_family") or "Times New Roman"
    body_size = typography.get("font_size_body_pt") or 12
    body_spacing = _spacing_body(spacing)

    document.add_page_break()

    title = section.get("title") or "LAMPIRAN"
    p_head = _add_styled_paragraph(document, WD_ALIGN_PARAGRAPH.LEFT, body_spacing, space_after_pt=6)
    _add_run(p_head, title, body_font, body_size, bold=True)
    _add_bookmark_to_paragraph(p_head, _bookmark_id_artikel("lampiran_utama"), _bookmark_name_artikel("lampiran_utama"))


def _render_artikel_item_lampiran(
    document: Document,
    section: dict,
    typography: dict,
    spacing: dict,
    instructional_placeholders: dict[str, str],
    lampiran_separator: str,
) -> None:
    """Render satu item lampiran artikel: heading "Lampiran N. Title" + body placeholder."""
    body_font = typography.get("font_family") or "Times New Roman"
    body_size = typography.get("font_size_body_pt") or 12
    body_spacing = _spacing_body(spacing)
    align_body   = _map_alignment((spacing.get("paragraph_alignment") or "JUSTIFY").upper())

    lampiran_number = (section.get("lampiran_number") or "Lampiran ?").strip()
    title           = (section.get("title") or "[LAMPIRAN_TANPA_JUDUL]").strip()
    sep_str = f"{lampiran_separator} " if lampiran_separator else " "
    heading_text = f"{lampiran_number}{sep_str}{title}".strip()

    _add_styled_paragraph(document, WD_ALIGN_PARAGRAPH.LEFT, body_spacing)
    p_head = _add_styled_paragraph(document, WD_ALIGN_PARAGRAPH.LEFT, body_spacing)
    _add_run(p_head, heading_text, body_font, body_size, bold=True)
    _add_bookmark_to_paragraph(
        p_head,
        _bookmark_id_artikel("item_lampiran", lampiran_number),
        _bookmark_name_artikel("item_lampiran", lampiran_number),
    )

    _add_section_note(document, body_font)

    body_text = instructional_placeholders.get(
        make_instruction_key("item_lampiran", heading_text),
        f"Instruksi pengisian untuk {heading_text}: lengkapi sesuai ketentuan panduan PKM-AI.",
    )
    p_body = _add_styled_paragraph(document, align_body, body_spacing, space_after_pt=6)
    _add_run(p_body, body_text, body_font, body_size)


def _render_artikel_body(
    document: Document,
    doc_structure: dict,
    typography: dict,
    spacing: dict,
    numbering: dict,
    instructional_placeholders: dict[str, str],
) -> None:
    """Iterasi seluruh section setelah judul_abstrak mengikuti urutan Sistematika C.

    Urutan yang dikenal: bab → daftar_pustaka → lampiran_utama → item_lampiran.
    """
    lampiran_sep = doc_structure.get("lampiran_heading_separator")
    if lampiran_sep is None:
        lampiran_sep = "."

    for section in doc_structure.get("sections", []):
        sec_type = section.get("type")
        if sec_type == "judul_abstrak":
            continue  # sudah dirender di halaman pertama
        if sec_type == "bab":
            _render_artikel_bab_section(document, section, typography, spacing, numbering, instructional_placeholders)
        elif sec_type == "daftar_pustaka":
            _render_artikel_daftar_pustaka(document, section, typography, spacing)
        elif sec_type == "lampiran_utama":
            _render_artikel_lampiran_utama(document, section, typography, spacing)
        elif sec_type == "item_lampiran":
            _render_artikel_item_lampiran(document, section, typography, spacing, instructional_placeholders, lampiran_sep)


def render_article_docx_bytes(
    output_data: dict,
    chunks: list,
    instructional_placeholders: dict[str, str],
) -> bytes:
    """Render DOCX artikel ilmiah PKM-AI dan kembalikan sebagai bytes.

    Urutan eksekusi mengikuti Sistematika C panduan PKM-AI:
      1. Halaman 1: judul_abstrak (spasi 1.0) — judul, penulis, institusi, abstrak ID/EN
      2. Bagian inti: bab artikel berurutan (spasi 1.15, format "{n}. {title}" bold)
      3. Daftar Pustaka (Harvard hanging indent, spasi 1.15)
      4. Lampiran (jika ada): heading lampiran_utama + setiap item_lampiran
    Penomoran halaman: angka arab di header kanan, mulai halaman 1.
    """
    typography     = output_data.get("typography") or {}
    page_layout    = output_data.get("page_layout") or {}
    spacing        = output_data.get("spacing") or {}
    numbering      = output_data.get("numbering") or {}
    doc_structure  = output_data.get("document_structure_artikel") or {}

    document = Document()
    first_section = document.sections[0]
    _configure_page_layout(first_section, page_layout)
    _apply_base_styles_artikel(document, typography, spacing)

    content_num = numbering.get("content") or {}
    _apply_page_numbering(
        first_section,
        _build_page_num_position(
            content_num.get("location", "HEADER"),
            content_num.get("alignment", "RIGHT"),
        ),
        fmt=content_num.get("format", "decimal"),
        start=1,
    )

    judul_section = next(
        (s for s in doc_structure.get("sections", []) if s.get("type") == "judul_abstrak"),
        None,
    )
    if judul_section is not None:
        _render_judul_abstrak(document, typography, spacing, instructional_placeholders, judul_section)
        document.add_page_break()

    _render_artikel_body(document, doc_structure, typography, spacing, numbering, instructional_placeholders)

    format_nama_file = doc_structure.get("format_nama_file")
    if format_nama_file:
        document.core_properties.subject = f"Format nama file: {format_nama_file}"

    buf = BytesIO()
    document.save(buf)
    buf.seek(0)
    return buf.getvalue()
