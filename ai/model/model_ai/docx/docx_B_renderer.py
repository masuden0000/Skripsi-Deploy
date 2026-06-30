"""Renderer Type B: menulis konten terstruktur ke dokumen .docx khusus PKM-AI (artikel ilmiah). Urutan eksekusi mengikuti Sistematika C panduan PKM-AI: judul_abstrak (halaman 1, spasi 1.0) → bab artikel (spasi 1.15) → daftar_pustaka (Harvard hanging indent) → lampiran. Posisi pipeline: instructional_placeholder_builder → docx_B_renderer → DOCX output. Keyword: automated document generation"""
from io import BytesIO
from pathlib import Path

from docx import Document
from docx.enum.style import WD_STYLE_TYPE
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


def _spacing_bibliography(spacing: dict) -> dict:
    rule = spacing.get("line_spacing_rule_bibliography")
    ls   = spacing.get("line_spacing_bibliography")
    if not rule:
        return _spacing_body(spacing)
    rule = rule.upper()
    if rule not in {"SINGLE", "ONE_POINT_FIVE", "DOUBLE", "MULTIPLE", "AT_LEAST", "EXACTLY"}:
        return _spacing_body(spacing)
    if rule == "MULTIPLE" and ls is None:
        ls = 1.15
    return {"line_spacing_rule": rule, "line_spacing": ls}


def _spacing_title_abstract(spacing: dict) -> dict:
    _VALID = {"SINGLE", "ONE_POINT_FIVE", "DOUBLE", "MULTIPLE", "AT_LEAST", "EXACTLY"}
    rule = (spacing.get("line_spacing_rule_title_abstract") or "").upper()
    ls   = spacing.get("line_spacing_title_abstract")
    if rule in _VALID:
        if rule in {"SINGLE", "ONE_POINT_FIVE", "DOUBLE"}:
            return {"line_spacing_rule": rule, "line_spacing": None}
        if rule == "MULTIPLE" and ls is None:
            ls = 1.0
        return {"line_spacing_rule": rule, "line_spacing": ls}
    # fallback: gunakan nilai numerik saja
    if ls is None:
        return _spacing_single()
    try:
        val = float(ls)
    except (TypeError, ValueError):
        return _spacing_single()
    return _spacing_single() if val == 1.0 else {"line_spacing_rule": "MULTIPLE", "line_spacing": val}


def _apply_base_styles_artikel(document: Document, typography: dict, spacing: dict, figures_tables: dict | None = None) -> None:
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

    ft = figures_tables or {}
    caption_size = ft.get("caption_font_size") or body_size
    caption_ls   = ft.get("caption_line_spacing") or 1.0
    _VALID_RULES_SET = {"SINGLE", "ONE_POINT_FIVE", "DOUBLE", "MULTIPLE", "AT_LEAST", "EXACTLY"}
    caption_rule = (ft.get("caption_line_spacing_rule") or "").upper()
    if caption_rule in _VALID_RULES_SET:
        cap_spacing = {
            "line_spacing_rule": caption_rule,
            "line_spacing": caption_ls if caption_rule not in {"SINGLE", "ONE_POINT_FIVE", "DOUBLE"} else None,
        }
    else:
        cap_spacing = (
            {"line_spacing_rule": "SINGLE", "line_spacing": None}
            if caption_ls == 1.0
            else {"line_spacing_rule": "MULTIPLE", "line_spacing": caption_ls}
        )
    try:
        caption_style = document.styles["Caption"]
    except KeyError:
        caption_style = document.styles.add_style("Caption", WD_STYLE_TYPE.PARAGRAPH)
    caption_style.font.name      = body_font
    caption_style.font.size      = Pt(caption_size)
    caption_style.font.bold      = False
    caption_style.font.italic    = False
    caption_style.font.color.rgb = RGBColor(0, 0, 0)
    caption_style.paragraph_format.alignment    = _map_alignment(
        (ft.get("caption_alignment_figure") or "CENTER").upper()
    )
    caption_style.paragraph_format.space_before = Pt(0)
    caption_style.paragraph_format.space_after  = Pt(0)
    _apply_line_spacing(caption_style.paragraph_format, cap_spacing)


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


def _format_caption_artikel(format_template: str | None, prefix: str, num: int, title: str) -> str:
    """Format string caption menggunakan template dari metadata atau default."""
    if not format_template:
        return f"{prefix} {num}. {title}"
    return (
        format_template
        .replace("{n}", str(num))
        .replace("{num}", str(num))
        .replace("{bab}", "1")
        .replace("{title}", title)
        .replace("{caption}", title)
        .replace("{source}", "Sumber: Dokumentasi Penelitian")
    )


def _add_example_figure_artikel(
    document: Document,
    caption: str | None,
    figures_tables: dict,
    body_font: str,
    body_size: int,
) -> None:
    """Sisipkan contoh gambar dengan caption sesuai posisi dan alignment dari metadata."""
    caption_pos   = (figures_tables.get("figure_caption_position") or "BELOW").upper()
    caption_align = _map_alignment((figures_tables.get("caption_alignment_figure") or "CENTER").upper())

    sep = document.add_paragraph()
    sep.paragraph_format.space_before = Pt(0)
    sep.paragraph_format.space_after  = Pt(0)

    if caption and caption_pos == "ABOVE":
        cap_p = document.add_paragraph(caption, style="Caption")
        cap_p.alignment = caption_align
        cap_p.paragraph_format.space_before = Pt(0)
        cap_p.paragraph_format.space_after  = Pt(0)
        _force_paragraph_runs_black(cap_p)

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

    if figure_image_path:
        document.add_picture(str(figure_image_path), width=Cm(10))
        document.paragraphs[-1].alignment = WD_ALIGN_PARAGRAPH.CENTER
    else:
        ph = document.add_paragraph("[Gambar: sisipkan gambar yang relevan di sini]")
        ph.alignment = WD_ALIGN_PARAGRAPH.CENTER
        if ph.runs:
            ph.runs[0].italic = True
            ph.runs[0].font.name = body_font
            ph.runs[0].font.size = Pt(body_size)
        _force_paragraph_runs_black(ph)

    if caption and caption_pos != "ABOVE":
        cap_p = document.add_paragraph(caption, style="Caption")
        cap_p.alignment = caption_align
        cap_p.paragraph_format.space_before = Pt(0)
        cap_p.paragraph_format.space_after  = Pt(0)
        _force_paragraph_runs_black(cap_p)


def _add_example_table_artikel(
    document: Document,
    caption: str | None,
    figures_tables: dict,
    body_font: str,
    body_size: int,
) -> None:
    """Sisipkan contoh tabel dengan caption sesuai posisi dan alignment dari metadata."""
    caption_pos   = (figures_tables.get("table_caption_position") or "ABOVE").upper()
    caption_align = _map_alignment((figures_tables.get("caption_alignment_table") or "CENTER").upper())

    sep = document.add_paragraph()
    sep.paragraph_format.space_before = Pt(0)
    sep.paragraph_format.space_after  = Pt(0)

    if caption and caption_pos != "BELOW":
        cap_p = document.add_paragraph(caption, style="Caption")
        cap_p.alignment = caption_align
        cap_p.paragraph_format.space_before = Pt(0)
        cap_p.paragraph_format.space_after  = Pt(0)
        _force_paragraph_runs_black(cap_p)

    table = document.add_table(rows=4, cols=3)
    table.style = "Table Grid"
    headers = ["No", "Variabel / Indikator", "Nilai / Keterangan"]
    for ci, header_text in enumerate(headers):
        cell = table.rows[0].cells[ci]
        cell.text = header_text
        cell.paragraphs[0].alignment = WD_ALIGN_PARAGRAPH.CENTER
        if cell.paragraphs[0].runs:
            cell.paragraphs[0].runs[0].bold = True
            cell.paragraphs[0].runs[0].font.name = body_font
            cell.paragraphs[0].runs[0].font.size = Pt(body_size)

    sample_rows = [
        ("1", "Contoh variabel pertama", "[nilai]"),
        ("2", "Contoh variabel kedua",   "[nilai]"),
        ("3", "Contoh variabel ketiga",  "[nilai]"),
    ]
    for ri, (no, var, val) in enumerate(sample_rows, start=1):
        row = table.rows[ri]
        for ci, cell_text in enumerate((no, var, val)):
            row.cells[ci].text = cell_text
            if ci == 0:
                row.cells[ci].paragraphs[0].alignment = WD_ALIGN_PARAGRAPH.CENTER
            if row.cells[ci].paragraphs[0].runs:
                row.cells[ci].paragraphs[0].runs[0].font.name = body_font
                row.cells[ci].paragraphs[0].runs[0].font.size = Pt(body_size)

    if caption and caption_pos == "BELOW":
        cap_p = document.add_paragraph(caption, style="Caption")
        cap_p.alignment = caption_align
        cap_p.paragraph_format.space_before = Pt(0)
        cap_p.paragraph_format.space_after  = Pt(0)
        _force_paragraph_runs_black(cap_p)


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
    title_is_bold  = spacing.get("title_bold", True)
    title_case_raw = (spacing.get("title_case") or "UPPERCASE").upper()
    title_is_upper = title_case_raw == "UPPERCASE"
    title_align    = _map_alignment((spacing.get("title_alignment") or "CENTER").upper())

    title_text = "JUDUL DIBUAT RINGKAS MAKSIMUM 20 KATA DENGAN MENONJOLKAN KATA KUNCI KEGIATAN ILMIAH DAN HASIL UTAMANYA, HURUF KAPITAL, HINDARI ADANYA SINGKATAN"
    if not title_is_upper:
        title_text = title_text.title()

    p_title = _add_styled_paragraph(document, title_align, title_spacing, space_after_pt=0)
    _add_run(p_title, title_text, body_font, title_size, bold=title_is_bold)
    _add_bookmark_to_paragraph(p_title, _bookmark_id_artikel("judul_abstrak"), _bookmark_name_artikel("judul_abstrak"))

    p_authors = _add_styled_paragraph(document, WD_ALIGN_PARAGRAPH.CENTER, title_spacing)
    _add_run(p_authors, "Penulis Satu", body_font, author_size)
    _add_run(p_authors, "1)", body_font, author_size, superscript=True)
    _add_run(p_authors, ", Penulis Dua", body_font, author_size)
    _add_run(p_authors, "1)", body_font, author_size, superscript=True)
    _add_run(p_authors, ", Penulis Tiga", body_font, author_size)
    _add_run(p_authors, "2)", body_font, author_size, superscript=True)
    _add_run(p_authors, ", Penulis Terakhir", body_font, author_size)
    _add_run(p_authors, "2)*", body_font, author_size, superscript=True)

    p_inst1 = _add_styled_paragraph(document, WD_ALIGN_PARAGRAPH.CENTER, title_spacing)
    _add_run(p_inst1, "1", body_font, author_size, superscript=True)
    _add_run(p_inst1, "Nama institusi dan alamat institusi dari penulis satu dan dua", body_font, author_size)

    p_inst2 = _add_styled_paragraph(document, WD_ALIGN_PARAGRAPH.CENTER, title_spacing)
    _add_run(p_inst2, "2", body_font, author_size, superscript=True)
    _add_run(p_inst2, "Nama institusi dan alamat institusi dari penulis tiga dan terakhir", body_font, author_size)

    p_corr = _add_styled_paragraph(document, WD_ALIGN_PARAGRAPH.CENTER, title_spacing, space_after_pt=0)
    _add_run(p_corr, "*Penulis korespondensi: penulis_terakhir@univ.ac.id", body_font, author_size)

    _add_section_note(document, body_font)
    instr_key = make_instruction_key("judul_abstrak", section.get("title") or "JUDUL DAN ABSTRAK")
    instr_text = instructional_placeholders.get(
        instr_key,
        "tulis judul artikel, nama seluruh penulis beserta afiliasi institusi, "
        "serta abstrak dalam bahasa Indonesia dan Inggris disertai kata kunci.",
    )
    p_note = _add_styled_paragraph(document, WD_ALIGN_PARAGRAPH.JUSTIFY, title_spacing, space_after_pt=0)
    _add_run(p_note, f"Instruksi: {instr_text}", body_font, 10, italic=True)

    p_abstrak_head = _add_styled_paragraph(document, WD_ALIGN_PARAGRAPH.CENTER, title_spacing)
    _add_run(p_abstrak_head, "ABSTRAK", body_font, abstract_sz, bold=False)

    p_abstrak_body = _add_styled_paragraph(document, WD_ALIGN_PARAGRAPH.JUSTIFY, title_spacing, space_after_pt=0)
    _add_run(
        p_abstrak_body,
        "[Tulis abstrak dalam Bahasa Indonesia di sini dalam format satu paragraf, "
        "cetak tegak, perataan rata kiri dan kanan, maksimum 250 kata. Abstrak memuat "
        "latar belakang, tujuan, metode (termasuk cara analisis data jika ada data primer), "
        "hasil utama secara ringkas dan runtut, serta kesimpulan yang selaras dengan tujuan.]",
        body_font, abstract_sz,
    )

    p_kata_kunci = _add_styled_paragraph(document, WD_ALIGN_PARAGRAPH.JUSTIFY, title_spacing, space_after_pt=0)
    _add_run(p_kata_kunci, "Kata-kata kunci: ", body_font, abstract_sz, bold=True)
    _add_run(p_kata_kunci, "[latar belakang], [tujuan], [metode], [hasil], [kesimpulan]. (3-5 kata/frasa)", body_font, abstract_sz)

    p_abstract_head = _add_styled_paragraph(document, WD_ALIGN_PARAGRAPH.CENTER, title_spacing)
    _add_run(p_abstract_head, "ABSTRACT", body_font, abstract_sz, italic=True)

    p_abstract_body = _add_styled_paragraph(document, WD_ALIGN_PARAGRAPH.JUSTIFY, title_spacing, space_after_pt=0)
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
    figures_tables: dict | None = None,
) -> None:
    """Render satu bab artikel: heading Heading 1 "{n}. {title}" + body placeholder + contoh gambar/tabel."""
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
    p_head = document.add_paragraph(style="Heading 1")
    p_head.paragraph_format.space_before = Pt(0)
    p_head.paragraph_format.space_after  = Pt(0)
    _apply_line_spacing(p_head.paragraph_format, body_spacing)
    _add_run(p_head, heading_text, body_font, body_size, bold=True)
    _add_bookmark_to_paragraph(p_head, _bookmark_id_artikel("bab", num), _bookmark_name_artikel("bab", num))

    _add_section_note(document, body_font)

    body_text = instructional_placeholders.get(
        make_instruction_key("bab", heading_text, number=num),
        f"Instruksi pengisian untuk {heading_text}: lengkapi isi bagian ini sesuai panduan PKM-AI.",
    )
    p_body = _add_styled_paragraph(document, align_body, body_spacing)
    _add_run(p_body, body_text, body_font, body_size)

    ft = figures_tables or {}
    if num and str(num) == "1":
        fig_fmt = ft.get("caption_format_figure")
        fig_caption = _format_caption_artikel(fig_fmt, "Gambar", 1, "Contoh Gambar Penelitian")
        _add_example_figure_artikel(document, fig_caption, ft, body_font, body_size)

    if num and str(num) == "2":
        tbl_fmt = ft.get("caption_format_table")
        tbl_caption = _format_caption_artikel(tbl_fmt, "Tabel", 1, "Contoh Data Penelitian")
        _add_example_table_artikel(document, tbl_caption, ft, body_font, body_size)


def _render_artikel_daftar_pustaka(
    document: Document,
    section: dict,
    typography: dict,
    spacing: dict,
) -> None:
    """Render Daftar Pustaka artikel: heading bold, isi Harvard style dengan hanging indent."""
    body_font  = typography.get("font_family") or "Times New Roman"
    body_size  = typography.get("font_size_body_pt") or 12
    body_spacing = _spacing_bibliography(spacing)

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
    p_head = _add_styled_paragraph(document, WD_ALIGN_PARAGRAPH.LEFT, body_spacing, space_after_pt=0)
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
    p_body = _add_styled_paragraph(document, align_body, body_spacing, space_after_pt=0)
    _add_run(p_body, body_text, body_font, body_size)


def _render_artikel_body(
    document: Document,
    doc_structure: dict,
    typography: dict,
    spacing: dict,
    numbering: dict,
    instructional_placeholders: dict[str, str],
    figures_tables: dict | None = None,
) -> None:
    """Iterasi seluruh section setelah judul_abstrak mengikuti urutan Sistematika C.

    Urutan yang dikenal: bab → daftar_pustaka → lampiran_utama → item_lampiran.
    """
    lampiran_sep = doc_structure.get("lampiran_heading_separator")
    if lampiran_sep is None:
        lampiran_sep = "."

    ft = figures_tables or {}
    for section in doc_structure.get("sections", []):
        sec_type = section.get("type")
        if sec_type == "judul_abstrak":
            continue
        if sec_type == "bab":
            _render_artikel_bab_section(document, section, typography, spacing, numbering, instructional_placeholders, ft)
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
    figures_tables = output_data.get("figures_and_tables") or {}

    document = Document()
    first_section = document.sections[0]
    _configure_page_layout(first_section, page_layout)
    _apply_base_styles_artikel(document, typography, spacing, figures_tables)

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

    _render_artikel_body(document, doc_structure, typography, spacing, numbering, instructional_placeholders, figures_tables)

    format_nama_file = doc_structure.get("format_nama_file")
    if format_nama_file:
        document.core_properties.subject = f"Format nama file: {format_nama_file}"

    buf = BytesIO()
    document.save(buf)
    buf.seek(0)
    return buf.getvalue()
