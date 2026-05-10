"""
Fungsi: Renderer yang menulis konten terstruktur ke dokumen .docx (paragraph, style, tabel).

Digunakan oleh: model_ai/docx/generator.py

Tujuan: Memisahkan logika render dokumen dari orkestrasi generator.
"""
from pathlib import Path

from docx import Document
from docx.enum.section import WD_ORIENT, WD_SECTION_START
from docx.enum.style import WD_STYLE_TYPE
from docx.enum.table import WD_ALIGN_VERTICAL
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_TAB_ALIGNMENT, WD_TAB_LEADER
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Cm, Mm, Pt, RGBColor

from model_ai.docx.chunk_loader import (
    ChunkSource,
    format_source_line,
    match_sources_for_section,
)
from model_ai.docx.instructional_placeholder_builder import make_instruction_key


# ---------------------------------------------------------------------------
# ID bookmark tetap per section type agar TOC dan heading selalu sinkron
# ---------------------------------------------------------------------------
_BOOKMARK_IDS: dict[str, int] = {
    "halaman_sampul": 1, "halaman_pengesahan": 2, "ringkasan": 3,
    "daftar_isi": 4,    "daftar_gambar": 5,      "daftar_tabel": 6,
    "daftar_lampiran": 7, "daftar_pustaka": 20,  "lampiran": 21,
}


def _bookmark_name(section_type: str, number=None) -> str:
    if section_type == "bab" and number:
        return f"bab_{number}"
    return section_type


def _bookmark_id(section_type: str, number=None) -> int:
    if section_type == "bab" and number:
        return 10 + int(number)
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


# ---------------------------------------------------------------------------
# Digunakan oleh: model_ai/docx/generator.py
# ---------------------------------------------------------------------------
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
    _apply_base_styles(document, typography, spacing)

    prelim_num  = numbering.get("preliminary") or {}
    content_num = numbering.get("content") or {}

    has_preliminary = _has_preliminary_pages(doc_structure)
    if has_preliminary:
        _render_preliminary_pages(document, doc_structure, page_layout, typography, instructional_placeholders)
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

    _render_proposal_body(document, doc_structure, page_layout, spacing, numbering, figures_tables, chunks, instructional_placeholders)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    document.save(str(output_path))
    return output_path


# ---------------------------------------------------------------------------
def _configure_page_layout(section, page_layout: dict) -> None:
    orientation = (page_layout.get("orientation") or "PORTRAIT").strip().upper()
    if orientation == "LANDSCAPE":
        section.orientation = WD_ORIENT.LANDSCAPE
        section.page_width  = Mm(297)
        section.page_height = Mm(210)
    else:
        section.orientation = WD_ORIENT.PORTRAIT
        section.page_width  = Mm(210)
        section.page_height = Mm(297)

    section.top_margin    = Cm(page_layout.get("margin_top_cm", 3.0))
    section.bottom_margin = Cm(page_layout.get("margin_bottom_cm", 3.0))
    section.left_margin   = Cm(page_layout.get("margin_left_cm", 4.0))
    section.right_margin  = Cm(page_layout.get("margin_right_cm", 3.0))


# ---------------------------------------------------------------------------
def _apply_base_styles(document: Document, typography: dict, spacing: dict) -> None:
    body_font    = typography.get("font_family", "Times New Roman")
    body_size    = typography.get("font_size_body_pt", 12)
    heading_size = typography.get("font_size_heading_pt", body_size)
    heading_bold = typography.get("heading_bold", True)
    heading_caps = typography.get("heading_all_caps", True)
    line_spacing  = spacing.get("line_spacing", 1.15)
    alignment_str = (spacing.get("paragraph_alignment") or "JUSTIFY").upper()

    normal_style = document.styles["Normal"]
    normal_style.font.name = body_font
    normal_style.font.size = Pt(body_size)
    normal_style.font.color.rgb = RGBColor(0, 0, 0)
    normal_style._element.rPr.rFonts.set(qn("w:ascii"), body_font)
    normal_style._element.rPr.rFonts.set(qn("w:hAnsi"), body_font)
    normal_style.paragraph_format.line_spacing = line_spacing
    normal_style.paragraph_format.alignment    = _map_alignment(alignment_str)

    # Perbaikan: hapus theme font override (w:asciiTheme/w:hAnsiTheme) agar
    # Times New Roman benar-benar diterapkan pada semua heading level.
    for style_name in ("Heading 1", "Heading 2", "Heading 3", "Heading 4"):
        try:
            h = document.styles[style_name]
        except KeyError:
            continue
        h.font.name      = body_font
        h.font.size      = Pt(heading_size)
        h.font.bold      = heading_bold
        h.font.all_caps  = heading_caps
        h.font.color.rgb = RGBColor(0, 0, 0)
        h.paragraph_format.alignment = WD_ALIGN_PARAGRAPH.CENTER

        # Paksa font di level XML — hapus theme font yang bisa menimpa explicit font
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

    # Style tersendiri untuk caption gambar/tabel
    try:
        caption_style = document.styles["Caption"]
    except KeyError:
        caption_style = document.styles.add_style("Caption", WD_STYLE_TYPE.PARAGRAPH)
    caption_style.font.name      = body_font
    caption_style.font.size      = Pt(body_size)
    caption_style.font.bold      = False
    caption_style.font.italic    = True
    caption_style.font.color.rgb = RGBColor(0, 0, 0)
    caption_style.paragraph_format.alignment    = WD_ALIGN_PARAGRAPH.CENTER
    caption_style.paragraph_format.space_before = Pt(3)
    caption_style.paragraph_format.space_after  = Pt(6)


# ---------------------------------------------------------------------------
def _force_paragraph_runs_black(paragraph) -> None:
    for run in paragraph.runs:
        run.font.color.rgb = RGBColor(0, 0, 0)


# ---------------------------------------------------------------------------
def _has_preliminary_pages(doc_structure: dict) -> bool:
    if doc_structure.get("halaman_sampul") or doc_structure.get("halaman_pengesahan") or doc_structure.get("ringkasan"):
        return True
    prelim_types = {"daftar_isi", "daftar_gambar", "daftar_tabel", "daftar_lampiran"}
    return any(s["type"] in prelim_types for s in doc_structure.get("sections", []))


# ---------------------------------------------------------------------------
def _render_preliminary_pages(
    document: Document,
    doc_structure: dict,
    page_layout: dict,
    typography: dict,
    instructional_placeholders: dict[str, str],
) -> None:
    prelim_entries: list[tuple[str, str, str]] = []  # (instruction_key, title, section_type)

    if doc_structure.get("halaman_sampul"):
        title = "HALAMAN SAMPUL"
        prelim_entries.append((make_instruction_key("halaman_sampul", title), title, "halaman_sampul"))
    if doc_structure.get("halaman_pengesahan"):
        title = "HALAMAN PENGESAHAN"
        prelim_entries.append((make_instruction_key("halaman_pengesahan", title), title, "halaman_pengesahan"))
    if doc_structure.get("ringkasan"):
        title = "RINGKASAN"
        prelim_entries.append((make_instruction_key("ringkasan", title), title, "ringkasan"))

    for section in doc_structure.get("sections", []):
        if section["type"] in ("daftar_isi", "daftar_gambar", "daftar_tabel", "daftar_lampiran"):
            fallback = section["type"].upper().replace("_", " ")
            title = (section.get("title") or fallback).strip()
            prelim_entries.append((make_instruction_key(section["type"], title), title, section["type"]))

    for index, (instruction_key, title, sec_type) in enumerate(prelim_entries):
        heading = document.add_heading(title, level=1)
        heading.alignment = WD_ALIGN_PARAGRAPH.CENTER
        _force_paragraph_runs_black(heading)
        _add_bookmark_to_paragraph(heading, _bookmark_id(sec_type), _bookmark_name(sec_type))

        # Enter 1x sebelum body (space_after = 0)
        empty = document.add_paragraph()
        empty.paragraph_format.space_after = Pt(0)

        # Pilih renderer contoh sesuai tipe
        if sec_type == "daftar_isi":
            _render_daftar_isi_example(document, doc_structure, page_layout, typography)
        elif sec_type == "daftar_gambar":
            _render_daftar_gambar_example(document, page_layout, typography)
        elif sec_type == "daftar_tabel":
            _render_daftar_tabel_example(document, page_layout, typography)
        elif sec_type == "daftar_lampiran":
            _render_daftar_lampiran_example(document, page_layout, typography)
        else:
            placeholder_text = instructional_placeholders.get(
                instruction_key,
                f"Instruksi pengisian untuk {title}: lengkapi bagian ini sesuai panduan dokumen.",
            )
            placeholder = document.add_paragraph(placeholder_text)
            _force_paragraph_runs_black(placeholder)

        if index < len(prelim_entries) - 1:
            document.add_page_break()


# ---------------------------------------------------------------------------
# Daftar Isi dengan hyperlink ke tiap section
# ---------------------------------------------------------------------------
def _render_daftar_isi_example(
    document: Document,
    doc_structure: dict,
    page_layout: dict,
    typography: dict,
) -> None:
    text_width_cm = 21.0 - page_layout.get("margin_left_cm", 4.0) - page_layout.get("margin_right_cm", 3.0)
    body_font = typography.get("font_family", "Times New Roman")
    body_size = typography.get("font_size_body_pt", 12)

    entries: list[tuple[str, str, str]] = []  # (teks, nomor, anchor_bookmark)
    prelim_counter = 1

    if doc_structure.get("halaman_sampul"):
        entries.append(("HALAMAN SAMPUL", _to_roman(prelim_counter), _bookmark_name("halaman_sampul")))
        prelim_counter += 1
    if doc_structure.get("halaman_pengesahan"):
        entries.append(("HALAMAN PENGESAHAN", _to_roman(prelim_counter), _bookmark_name("halaman_pengesahan")))
        prelim_counter += 1
    if doc_structure.get("ringkasan"):
        entries.append(("RINGKASAN", _to_roman(prelim_counter), _bookmark_name("ringkasan")))
        prelim_counter += 1

    body_counter = 1
    for sec in doc_structure.get("sections", []):
        sec_type = sec["type"]
        title    = sec.get("title") or sec_type.upper().replace("_", " ")

        # Semua prelim entries (termasuk daftar isi) pakai roman numeral
        if sec_type in ("daftar_isi", "daftar_gambar", "daftar_tabel", "daftar_lampiran"):
            entries.append((title, _to_roman(prelim_counter), _bookmark_name(sec_type)))
            prelim_counter += 1
        elif sec_type == "bab":
            num = sec.get("number", "")
            label = f"BAB {num}. {title}".strip() if num else f"BAB {title}".strip()
            entries.append((label, str(body_counter), _bookmark_name("bab", num)))
            body_counter += 2
        elif sec_type in ("daftar_pustaka", "lampiran"):
            entries.append((title, str(body_counter), _bookmark_name(sec_type)))
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

    # Warna hitam (bukan biru default hyperlink)
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


# ---------------------------------------------------------------------------
# Daftar Gambar — contoh entri
# ---------------------------------------------------------------------------
def _render_daftar_gambar_example(document: Document, page_layout: dict, typography: dict) -> None:
    text_width_cm = 21.0 - page_layout.get("margin_left_cm", 4.0) - page_layout.get("margin_right_cm", 3.0)
    body_font = typography.get("font_family", "Times New Roman")
    body_size = typography.get("font_size_body_pt", 12)

    sample_entries = [
        ("Gambar 1.1 [Contoh judul gambar pada BAB 1]", "1"),
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


# ---------------------------------------------------------------------------
# Daftar Tabel — contoh entri
# ---------------------------------------------------------------------------
def _render_daftar_tabel_example(document: Document, page_layout: dict, typography: dict) -> None:
    text_width_cm = 21.0 - page_layout.get("margin_left_cm", 4.0) - page_layout.get("margin_right_cm", 3.0)
    body_font = typography.get("font_family", "Times New Roman")
    body_size = typography.get("font_size_body_pt", 12)

    sample_entries = [
        ("Tabel 1.1 [Contoh judul tabel pada BAB 1]", "2"),
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


# ---------------------------------------------------------------------------
# Daftar Lampiran — contoh entri
# ---------------------------------------------------------------------------
def _render_daftar_lampiran_example(document: Document, page_layout: dict, typography: dict) -> None:
    text_width_cm = 21.0 - page_layout.get("margin_left_cm", 4.0) - page_layout.get("margin_right_cm", 3.0)
    body_font = typography.get("font_family", "Times New Roman")
    body_size = typography.get("font_size_body_pt", 12)

    sample_entries = [
        ("Lampiran 1 [Judul Lampiran Pertama]", "11"),
        ("Lampiran 2 [Judul Lampiran Kedua]", "12"),
        ("Lampiran 3 [Judul Lampiran Ketiga]", "13"),
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


# ---------------------------------------------------------------------------
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


# ---------------------------------------------------------------------------
def _render_proposal_body(
    document: Document,
    doc_structure: dict,
    page_layout: dict,
    spacing: dict,
    numbering: dict,
    figures_tables: dict,
    chunks: list[ChunkSource],
    instructional_placeholders: dict[str, str],
) -> None:
    for section in doc_structure.get("sections", []):
        if section["type"] == "bab":
            _render_bab_section(document, section, page_layout, spacing, numbering, figures_tables, chunks, instructional_placeholders)
        elif section["type"] == "daftar_pustaka":
            _render_named_section(
                document, section["type"],
                section.get("title") or "DAFTAR PUSTAKA",
                spacing, chunks, instructional_placeholders,
            )
        elif section["type"] == "lampiran":
            _render_named_section(
                document, section["type"],
                section.get("title") or "LAMPIRAN",
                spacing, chunks, instructional_placeholders,
            )


# ---------------------------------------------------------------------------
def _render_bab_section(
    document: Document,
    section: dict,
    page_layout: dict,
    spacing: dict,
    numbering: dict,
    figures_tables: dict,
    chunks: list[ChunkSource],
    instructional_placeholders: dict[str, str],
) -> None:
    chapter_fmt  = numbering.get("chapter_format", "BAB {n}")
    title        = section.get("title") or "[JUDUL_BAB_BELUM_TERDETEKSI]"
    num          = section.get("number")
    bab_label    = chapter_fmt.replace("{n}", str(num)) if num else "BAB"
    heading_text = f"{bab_label} {title}".strip()

    heading = document.add_heading(heading_text, level=1)
    heading.alignment = WD_ALIGN_PARAGRAPH.CENTER
    _force_paragraph_runs_black(heading)
    _add_bookmark_to_paragraph(heading, _bookmark_id("bab", num), _bookmark_name("bab", num))

    # Spasi kosong 1 baris enter antara header dan body (space_after = 0)
    empty = document.add_paragraph()
    empty.paragraph_format.space_after = Pt(0)

    note = document.add_paragraph("(Catatan: bagian ini boleh dihapus)")
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
    body_placeholder.paragraph_format.line_spacing = spacing.get("line_spacing", 1.15)
    body_placeholder.paragraph_format.alignment    = _map_alignment(
        (spacing.get("paragraph_alignment") or "JUSTIFY").upper()
    )
    body_placeholder.paragraph_format.space_after = Pt(0)
    _force_paragraph_runs_black(body_placeholder)

    # Tambah contoh gambar + caption di BAB 1
    if num == "1":
        fig_p = document.add_paragraph("[PLACEHOLDER_GAMBAR: Sertakan diagram alur penelitian atau ilustrasi terkait penelitian]")
        fig_p.paragraph_format.space_after = Pt(0)
        _force_paragraph_runs_black(fig_p)
        fig_fmt = figures_tables.get("caption_format_figure", "Gambar {n}. {title} ({source})")
        fig_caption_text = (
            fig_fmt
            .replace("{n}", "1.1")
            .replace("{title}", "Diagram Alur Penelitian")
            .replace(" ({source})", "").replace("()", "").strip()
        )
        fig_cap_p = document.add_paragraph(fig_caption_text, style="Caption")
        fig_cap_p.paragraph_format.space_after = Pt(0)
        _force_paragraph_runs_black(fig_cap_p)
        # Enter 1x setelah caption
        empty2 = document.add_paragraph()
        empty2.paragraph_format.space_after = Pt(0)

    # Khusus bab BIAYA: tabel anggaran + contoh gambar + tabel jadwal (poin 4 & 5)
    if "BIAYA" in title.upper():
        bab_num = int(num) if num else 4
        _add_budget_table(document, bab_num, figures_tables)
        # Contoh gambar + caption di bawahnya (poin 4)
        fig_p = document.add_paragraph("[PLACEHOLDER_GAMBAR]")
        fig_p.paragraph_format.space_after = Pt(0)
        _force_paragraph_runs_black(fig_p)
        fig_fmt = figures_tables.get("caption_format_figure", "Gambar {n}. {title} ({source})")
        fig_caption_text = (
            fig_fmt
            .replace("{n}", "4.1")
            .replace("{title}", "[Judul Gambar Sesuai Konteks]")
            .replace(" ({source})", "").replace("()", "").strip()
        )
        fig_cap_p = document.add_paragraph(fig_caption_text, style="Caption")
        fig_cap_p.paragraph_format.space_after = Pt(0)
        _force_paragraph_runs_black(fig_cap_p)
        # Tabel jadwal dengan caption di bawahnya (poin 5)
        _add_schedule_table(document, bab_num, figures_tables, page_layout)

    sources = match_sources_for_section(
        chunks=chunks,
        section_label=bab_label,
        section_title=section.get("title"),
    )
    _render_source_block(document, sources)
    # Caption tidak ditampilkan di setiap bab (poin 3)


# ---------------------------------------------------------------------------
def _render_named_section(
    document: Document,
    section_type: str,
    title: str,
    spacing: dict,
    chunks: list[ChunkSource],
    instructional_placeholders: dict[str, str],
) -> None:
    heading = document.add_heading(title, level=1)
    heading.alignment = WD_ALIGN_PARAGRAPH.CENTER
    _force_paragraph_runs_black(heading)
    _add_bookmark_to_paragraph(heading, _bookmark_id(section_type), _bookmark_name(section_type))

    # Enter 1x sebelum body (space_after = 0)
    empty = document.add_paragraph()
    empty.paragraph_format.space_after = Pt(0)

    note = document.add_paragraph("(Catatan: bagian ini boleh dihapus)")
    note.runs[0].italic     = True
    note.runs[0].font.size  = Pt(10)
    note.paragraph_format.alignment = WD_ALIGN_PARAGRAPH.LEFT
    _force_paragraph_runs_black(note)

    if section_type == "daftar_pustaka":
        placeholder_text = (
            "Tuliskan daftar pustaka menggunakan format Harvard style:\n\n"
            "Lastname, F. (Tahun). Judul buku. Penerbit.\n"
            "Lastname, F., & Lastname2, G. (Tahun). Judul artikel. Nama Jurnal, Vol(No), hal. XX-XX. "
            "https://doi.org/xxxxx\n\n"
            "Contoh:\n"
            "Wicaksono, H. R. (2024). Sistem Kecerdasan Buatan untuk Evaluasi Dokumen. Universitas Indonesia.\n"
            "Doe, J., & Smith, A. (2023). Deep learning in NLP tasks. Journal of AI Research, 5(2), 45-78."
        )
        # Multiple paragraphs - full width, justify, no indent
        paragraphs = placeholder_text.strip().split("\n\n")
        for para_text in paragraphs:
            lines = para_text.strip().split("\n")
            for line in lines:
                p = document.add_paragraph(line.strip())
                p.paragraph_format.line_spacing = spacing.get("line_spacing", 1.15)
                p.paragraph_format.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
                p.paragraph_format.space_after = Pt(0)
                _force_paragraph_runs_black(p)
    else:
        placeholder_text = instructional_placeholders.get(
            make_instruction_key(section_type, title),
            f"Instruksi pengisian untuk {title}: lengkapi bagian ini sesuai panduan dokumen.",
        )
        placeholder = document.add_paragraph(placeholder_text)
        placeholder.paragraph_format.line_spacing = spacing.get("line_spacing", 1.15)
        _force_paragraph_runs_black(placeholder)

    sources = match_sources_for_section(chunks=chunks, section_label=title, section_title=title)
    _render_source_block(document, sources)


# ---------------------------------------------------------------------------
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


# ---------------------------------------------------------------------------
# Tabel anggaran biaya — caption di bawah (poin 4)
# ---------------------------------------------------------------------------
def _add_budget_table(document: Document, bab_number: int, figures_tables: dict) -> None:
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

    table = document.add_table(rows=18, cols=4)
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
            table.cell(base + j, 2).text = sd

    table.cell(13, 0).text = "Jumlah"
    table.cell(13, 0).paragraphs[0].alignment = WD_ALIGN_PARAGRAPH.CENTER

    table.cell(14, 0).text = "Rekap Sumber Dana"
    table.cell(14, 0).paragraphs[0].alignment = WD_ALIGN_PARAGRAPH.CENTER
    for j, sd in enumerate([*sumber_dana, "Jumlah"]):
        table.cell(14 + j, 2).text = sd

    for i in range(4):
        base = 1 + i * 3
        table.cell(base, 0).merge(table.cell(base + 2, 0))
        table.cell(base, 0).vertical_alignment = WD_ALIGN_VERTICAL.CENTER
        table.cell(base, 1).merge(table.cell(base + 2, 1))
        table.cell(base, 1).vertical_alignment = WD_ALIGN_VERTICAL.CENTER

    table.cell(13, 0).merge(table.cell(13, 2))
    table.cell(13, 0).vertical_alignment = WD_ALIGN_VERTICAL.CENTER

    table.cell(14, 0).merge(table.cell(17, 1))
    table.cell(14, 0).vertical_alignment = WD_ALIGN_VERTICAL.CENTER

    col_widths = [Cm(1.5), Cm(6.0), Cm(4.0), Cm(2.5)]
    for row in table.rows:
        for ci, width in enumerate(col_widths):
            if ci < len(row.cells):
                row.cells[ci].width = width

    # Caption di bawah tabel
    fmt = figures_tables.get("caption_format_table", "Tabel {bab}.{n}. {title}")
    caption_text = (
        fmt.replace("{bab}", str(bab_number)).replace("{n}", "1")
           .replace("{title}", "Rincian Anggaran Biaya")
    )
    p = document.add_paragraph(caption_text, style="Caption")
    p.paragraph_format.space_after = Pt(0)
    _force_paragraph_runs_black(p)

    # Enter 1x setelah caption tabel anggaran
    empty = document.add_paragraph()
    empty.paragraph_format.space_after = Pt(0)


# ---------------------------------------------------------------------------
# Tabel jadwal kegiatan sesuai format panduan — caption di bawah (poin 5)
# ---------------------------------------------------------------------------
def _add_schedule_table(document: Document, bab_number: int, figures_tables: dict, page_layout: dict) -> None:
    text_width_cm = 21.0 - page_layout.get("margin_left_cm", 4.0) - page_layout.get("margin_right_cm", 3.0)
    # Struktur: No | Jenis Kegiatan | Bulan (1-4) | Penanggung Jawab
    # 2 baris header + 5 baris data = 7 baris, 7 kolom
    table = document.add_table(rows=7, cols=7)
    table.style = "Table Grid"

    # Hitung lebar kolom proporsional berdasarkan text_width_cm
    # Kolom: No(1.0) + Jenis_Kegiatan(?) + Bulan1-4(1.0 each) + PJ(3.5) = text_width_cm
    total_fixed = Cm(1.0) + Cm(1.0) * 4 + Cm(3.5)  # 8.5 cm fixed
    remaining = Cm(text_width_cm) - total_fixed
    jenis_kegiatan_width = remaining if remaining > Cm(0) else Cm(4.5)

    widths = [Cm(1.0), jenis_kegiatan_width, Cm(1.0), Cm(1.0), Cm(1.0), Cm(1.0), Cm(3.5)]
    for ri in range(7):
        for ci, width in enumerate(widths):
            table.cell(ri, ci).width = width

    # Teks header baris 0
    for ci, txt in enumerate(["No", "Jenis Kegiatan", "Bulan", "", "", "", "Penanggung Jawab"]):
        if txt:
            table.cell(0, ci).text = txt

    # Sub-header baris 1: angka bulan
    for m, label in enumerate(["1", "2", "3", "4"]):
        table.cell(1, 2 + m).text = label
        table.cell(1, 2 + m).paragraphs[0].alignment = WD_ALIGN_PARAGRAPH.CENTER

    # Data baris
    for i in range(5):
        table.cell(2 + i, 0).text = str(i + 1)
        table.cell(2 + i, 0).paragraphs[0].alignment = WD_ALIGN_PARAGRAPH.CENTER
        table.cell(2 + i, 1).text = f"[Jenis Kegiatan {i + 1}]"
        table.cell(2 + i, 6).text = "[Penanggung Jawab]"

    # Merge: No (baris 0-1), Jenis Kegiatan (baris 0-1), PJ (baris 0-1)
    table.cell(0, 0).merge(table.cell(1, 0))
    table.cell(0, 0).vertical_alignment = WD_ALIGN_VERTICAL.CENTER
    table.cell(0, 0).paragraphs[0].alignment = WD_ALIGN_PARAGRAPH.CENTER

    table.cell(0, 1).merge(table.cell(1, 1))
    table.cell(0, 1).vertical_alignment = WD_ALIGN_VERTICAL.CENTER
    table.cell(0, 1).paragraphs[0].alignment = WD_ALIGN_PARAGRAPH.CENTER

    # Merge: "Bulan" melebar ke kolom 2-5 pada baris 0
    table.cell(0, 2).merge(table.cell(0, 5))
    table.cell(0, 2).vertical_alignment = WD_ALIGN_VERTICAL.CENTER
    table.cell(0, 2).paragraphs[0].alignment = WD_ALIGN_PARAGRAPH.CENTER

    table.cell(0, 6).merge(table.cell(1, 6))
    table.cell(0, 6).vertical_alignment = WD_ALIGN_VERTICAL.CENTER
    table.cell(0, 6).paragraphs[0].alignment = WD_ALIGN_PARAGRAPH.CENTER

    # Bold header utama (tanpa underline)
    for ci in [0, 1, 2, 6]:
        para = table.cell(0, ci).paragraphs[0]
        if para.runs:
            para.runs[0].bold = True

    # Caption di bawah tabel (poin 5)
    fmt = figures_tables.get("caption_format_table", "Tabel {bab}.{n}. {title}")
    caption_text = (
        fmt.replace("{bab}", str(bab_number)).replace("{n}", "2")
           .replace("{title}", "Jadwal Pelaksanaan Kegiatan")
    )
    p = document.add_paragraph(caption_text, style="Caption")
    p.paragraph_format.space_after = Pt(0)
    _force_paragraph_runs_black(p)

    # Enter 1x setelah caption tabel jadwal
    empty = document.add_paragraph()
    empty.paragraph_format.space_after = Pt(0)


# ---------------------------------------------------------------------------
def _add_seq_caption(document: Document, label: str, template: str) -> None:
    paragraph = document.add_paragraph(style="Caption")
    prefix, suffix = _split_caption_template(template, label)
    paragraph.add_run(prefix)
    _append_field(paragraph, f" SEQ {label} \\* ARABIC ")
    paragraph.add_run(suffix)
    _force_paragraph_runs_black(paragraph)


# ---------------------------------------------------------------------------
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


# ---------------------------------------------------------------------------
def _map_alignment(value: str) -> WD_ALIGN_PARAGRAPH:
    mapping = {
        "LEFT":    WD_ALIGN_PARAGRAPH.LEFT,
        "CENTER":  WD_ALIGN_PARAGRAPH.CENTER,
        "RIGHT":   WD_ALIGN_PARAGRAPH.RIGHT,
        "JUSTIFY": WD_ALIGN_PARAGRAPH.JUSTIFY,
    }
    return mapping.get(value, WD_ALIGN_PARAGRAPH.JUSTIFY)


# ---------------------------------------------------------------------------
def _build_page_num_position(location: str, alignment: str) -> str:
    return f"{(location or 'FOOTER').lower()}_{(alignment or 'RIGHT').lower()}"


# ---------------------------------------------------------------------------
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


# ---------------------------------------------------------------------------
def _position_alignment(position: str) -> WD_ALIGN_PARAGRAPH:
    if position.endswith("_left"):
        return WD_ALIGN_PARAGRAPH.LEFT
    if position.endswith("_center"):
        return WD_ALIGN_PARAGRAPH.CENTER
    return WD_ALIGN_PARAGRAPH.RIGHT


# ---------------------------------------------------------------------------
def _set_page_number_type(section, fmt: str, start: int) -> None:
    sect_pr = section._sectPr
    pg_num_type = sect_pr.find(qn("w:pgNumType"))
    if pg_num_type is None:
        pg_num_type = OxmlElement("w:pgNumType")
        sect_pr.append(pg_num_type)
    pg_num_type.set(qn("w:fmt"), fmt)
    pg_num_type.set(qn("w:start"), str(start))


# ---------------------------------------------------------------------------
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


# ---------------------------------------------------------------------------
def _clear_paragraph(paragraph) -> None:
    for run in paragraph.runs:
        run.clear()
