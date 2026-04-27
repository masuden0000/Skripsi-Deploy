from pathlib import Path

from docx import Document
from docx.enum.section import WD_ORIENT, WD_SECTION_START
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Cm, Mm, Pt

from model_ai.docx.chunk_loader import (
    ChunkSource,
    format_source_line,
    match_sources_for_section,
)
from model_ai.docx.style_translator_llm import DocxStyleConfig
from model_ai.extractor.models import DocumentMetadata, SectionItem


def render_proposal_docx(
    metadata: DocumentMetadata,
    chunks: list[ChunkSource],
    style_config: DocxStyleConfig,
    output_path: Path,
) -> Path:
    document = Document()
    first_section = document.sections[0]
    _configure_page_layout(first_section, metadata)
    _apply_base_styles(document, metadata, style_config)

    has_preliminary = _has_preliminary_pages(metadata)
    if has_preliminary:
        _render_preliminary_pages(document, metadata)
        _apply_page_numbering(
            first_section,
            style_config.page_number_prelim_pos,
            fmt="lowerRoman",
            start=1,
        )

        content_section = document.add_section(WD_SECTION_START.NEW_PAGE)
        _configure_page_layout(content_section, metadata)
        _apply_page_numbering(
            content_section,
            style_config.page_number_content_pos,
            fmt="decimal",
            start=1,
        )
    else:
        _apply_page_numbering(
            first_section,
            style_config.page_number_content_pos,
            fmt="decimal",
            start=1,
        )

    _render_proposal_body(document, metadata, chunks)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    document.save(str(output_path))
    return output_path


def _configure_page_layout(section, metadata: DocumentMetadata) -> None:
    orientation = (metadata.page_layout.orientation or "PORTRAIT").strip().upper()
    if orientation == "LANDSCAPE":
        section.orientation = WD_ORIENT.LANDSCAPE
        section.page_width = Mm(297)
        section.page_height = Mm(210)
    else:
        section.orientation = WD_ORIENT.PORTRAIT
        section.page_width = Mm(210)
        section.page_height = Mm(297)

    section.top_margin = Cm(metadata.page_layout.margin_top_cm or 3.0)
    section.bottom_margin = Cm(metadata.page_layout.margin_bottom_cm or 3.0)
    section.left_margin = Cm(metadata.page_layout.margin_left_cm or 4.0)
    section.right_margin = Cm(metadata.page_layout.margin_right_cm or 3.0)


def _apply_base_styles(
    document: Document,
    metadata: DocumentMetadata,
    style_config: DocxStyleConfig,
) -> None:
    body_font = metadata.typography.font_family or "Times New Roman"
    body_size = metadata.typography.font_size_body_pt or 12
    heading_size = metadata.typography.font_size_heading_pt or body_size

    normal_style = document.styles["Normal"]
    normal_style.font.name = body_font
    normal_style.font.size = Pt(body_size)
    normal_style._element.rPr.rFonts.set(qn("w:ascii"), body_font)
    normal_style._element.rPr.rFonts.set(qn("w:hAnsi"), body_font)
    normal_style.paragraph_format.line_spacing = metadata.spacing.line_spacing or 1.15
    normal_style.paragraph_format.alignment = _map_alignment(style_config.paragraph_alignment)

    for style_name in ("Heading 1", "Heading 2"):
        heading_style = document.styles[style_name]
        heading_style.font.name = body_font
        heading_style.font.size = Pt(heading_size)
        heading_style.font.bold = style_config.heading_bold
        heading_style.font.all_caps = style_config.heading_all_caps
        heading_style._element.rPr.rFonts.set(qn("w:ascii"), body_font)
        heading_style._element.rPr.rFonts.set(qn("w:hAnsi"), body_font)


def _render_preliminary_pages(document: Document, metadata: DocumentMetadata) -> None:
    structure = metadata.document_structure_proposal
    prelim_titles: list[str] = []

    if structure.halaman_sampul:
        prelim_titles.append("HALAMAN SAMPUL")
    if structure.halaman_pengesahan:
        prelim_titles.append("HALAMAN PENGESAHAN")
    if structure.ringkasan:
        prelim_titles.append("RINGKASAN")
    for section in structure.sections:
        if section.type in ("daftar_isi", "daftar_gambar", "daftar_tabel", "daftar_lampiran"):
            if section.required is not False:
                prelim_titles.append(section.type.upper().replace("_", " "))

    for index, title in enumerate(prelim_titles):
        document.add_heading(title, level=1)
        document.add_paragraph(f"[PLACEHOLDER_{title.replace(' ', '_')}]")
        if index < len(prelim_titles) - 1:
            document.add_page_break()


def _render_proposal_body(
    document: Document,
    metadata: DocumentMetadata,
    chunks: list[ChunkSource],
) -> None:
    proposal = metadata.document_structure_proposal

    for section in proposal.sections:
        if section.type == "bab":
            _render_bab_section(document, section, chunks, metadata)
        elif section.type == "daftar_pustaka":
            _render_named_section(document, "DAFTAR PUSTAKA", chunks)
        elif section.type == "lampiran":
            _render_named_section(document, "LAMPIRAN", chunks)


def _render_bab_section(
    document: Document,
    section: SectionItem,
    chunks: list[ChunkSource],
    metadata: DocumentMetadata,
) -> None:
    title = section.title or "[JUDUL_BAB_BELUM_TERDETEKSI]"
    bab_number = f"BAB {section.number}" if section.number else "BAB"
    heading_text = f"{bab_number} {title}".strip()
    document.add_heading(heading_text, level=1)
    document.add_paragraph(
        f"[PLACEHOLDER_ISI] Isi bagian ini untuk {heading_text} sesuai aturan panduan."
    )

    sources = match_sources_for_section(
        chunks=chunks,
        section_label=bab_number,
        section_title=section.title,
    )
    _render_source_block(document, sources)
    _render_caption_examples(document, metadata)


def _render_named_section(
    document: Document,
    title: str,
    chunks: list[ChunkSource],
) -> None:
    document.add_heading(title, level=1)
    document.add_paragraph(f"[PLACEHOLDER_{title.replace(' ', '_')}]")
    sources = match_sources_for_section(
        chunks=chunks,
        section_label=title,
        section_title=title,
    )
    _render_source_block(document, sources)


def _render_source_block(document: Document, sources: list[ChunkSource]) -> None:
    if not sources:
        document.add_paragraph("Sumber: [BELUM DITEMUKAN]")
        return

    for source in sources:
        document.add_paragraph(format_source_line(source))


def _render_caption_examples(document: Document, metadata: DocumentMetadata) -> None:
    figure_template = (
        metadata.figures_and_tables.caption_format_figure
        or "Gambar {n}. {title} ({source})"
    )
    table_template = (
        metadata.figures_and_tables.caption_format_table
        or "Tabel {bab}.{n} {title}"
    )

    table_pos = (metadata.figures_and_tables.table_caption_position or "ABOVE").upper()
    figure_pos = (metadata.figures_and_tables.figure_caption_position or "BELOW").upper()

    if table_pos == "ABOVE":
        _add_seq_caption(document, "Table", table_template)
        document.add_paragraph("[PLACEHOLDER_TABEL]")
    else:
        document.add_paragraph("[PLACEHOLDER_TABEL]")
        _add_seq_caption(document, "Table", table_template)

    if figure_pos == "BELOW":
        document.add_paragraph("[PLACEHOLDER_GAMBAR]")
        _add_seq_caption(document, "Figure", figure_template)
    else:
        _add_seq_caption(document, "Figure", figure_template)
        document.add_paragraph("[PLACEHOLDER_GAMBAR]")


def _add_seq_caption(document: Document, label: str, template: str) -> None:
    paragraph = document.add_paragraph()
    prefix, suffix = _split_caption_template(template, label)
    paragraph.add_run(prefix)
    _append_field(paragraph, f" SEQ {label} \\* ARABIC ")
    paragraph.add_run(suffix)


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


def _map_alignment(value: str) -> WD_ALIGN_PARAGRAPH:
    mapping = {
        "LEFT": WD_ALIGN_PARAGRAPH.LEFT,
        "CENTER": WD_ALIGN_PARAGRAPH.CENTER,
        "RIGHT": WD_ALIGN_PARAGRAPH.RIGHT,
        "JUSTIFY": WD_ALIGN_PARAGRAPH.JUSTIFY,
    }
    return mapping.get(value, WD_ALIGN_PARAGRAPH.JUSTIFY)


def _apply_page_numbering(section, position: str, fmt: str, start: int) -> None:
    section.header.is_linked_to_previous = False
    section.footer.is_linked_to_previous = False

    target = section.header if position.startswith("header_") else section.footer
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


def _has_preliminary_pages(metadata: DocumentMetadata) -> bool:
    structure = metadata.document_structure_proposal
    if structure.halaman_sampul or structure.halaman_pengesahan or structure.ringkasan:
        return True
    prelim_types = {"daftar_isi", "daftar_gambar", "daftar_tabel", "daftar_lampiran"}
    return any(s.type in prelim_types for s in structure.sections)