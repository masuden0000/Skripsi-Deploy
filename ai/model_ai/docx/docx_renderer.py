"""
Fungsi: Renderer yang menulis konten terstruktur ke dokumen .docx (paragraph, style, tabel).

Digunakan oleh: model_ai/docx/generator.py

Tujuan: Memisahkan logika render dokumen dari orkestrasi generator.
"""
from pathlib import Path

from docx import Document
from docx.enum.section import WD_ORIENT, WD_SECTION_START
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Cm, Mm, Pt, RGBColor

from model_ai.docx.chunk_loader import (
    ChunkSource,
    format_source_line,
    match_sources_for_section,
)
from model_ai.docx.instructional_placeholder_builder import make_instruction_key
from model_ai.docx.style_mapping_pipeline import DocxStyleConfig
from model_ai.extractor.models import DocumentMetadata, SectionItem


# ---------------------------------------------------------------------------
# Digunakan oleh: model_ai/docx/generator.py
# Menjalankan fungsi `render_proposal_docx` sebagai bagian alur `docx_renderer`.
# ---------------------------------------------------------------------------
def render_proposal_docx(
    metadata: DocumentMetadata,
    chunks: list[ChunkSource],
    style_config: DocxStyleConfig,
    instructional_placeholders: dict[str, str],
    output_path: Path,
) -> Path:
    document = Document()
    first_section = document.sections[0]
    _configure_page_layout(first_section, metadata)
    _apply_base_styles(document, metadata, style_config)

    has_preliminary = _has_preliminary_pages(metadata)
    if has_preliminary:
        _render_preliminary_pages(document, metadata, instructional_placeholders)
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

    _render_proposal_body(document, metadata, chunks, instructional_placeholders)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    document.save(str(output_path))
    return output_path


# ---------------------------------------------------------------------------
# Digunakan oleh: Dipakai internal di file ini atau dipanggil dari entrypoint runtime.
# Menjalankan fungsi `_configure_page_layout` sebagai bagian alur `docx_renderer`.
# ---------------------------------------------------------------------------
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


# ---------------------------------------------------------------------------
# Digunakan oleh: Dipakai internal di file ini atau dipanggil dari entrypoint runtime.
# Menjalankan fungsi `_apply_base_styles` sebagai bagian alur `docx_renderer`.
# ---------------------------------------------------------------------------
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
    normal_style.font.color.rgb = RGBColor(0, 0, 0)
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
        heading_style.font.color.rgb = RGBColor(0, 0, 0)
        heading_style.paragraph_format.alignment = WD_ALIGN_PARAGRAPH.CENTER
        heading_style._element.rPr.rFonts.set(qn("w:ascii"), body_font)
        heading_style._element.rPr.rFonts.set(qn("w:hAnsi"), body_font)


# ---------------------------------------------------------------------------
# Digunakan oleh: Dipakai internal di file ini atau dipanggil dari entrypoint runtime.
# Menjalankan fungsi `_force_paragraph_runs_black` sebagai bagian alur `docx_renderer`.
# ---------------------------------------------------------------------------
def _force_paragraph_runs_black(paragraph) -> None:
    for run in paragraph.runs:
        run.font.color.rgb = RGBColor(0, 0, 0)


# ---------------------------------------------------------------------------
# Digunakan oleh: Dipakai internal di file ini atau dipanggil dari entrypoint runtime.
# Menjalankan fungsi `_render_preliminary_pages` sebagai bagian alur `docx_renderer`.
# ---------------------------------------------------------------------------
def _render_preliminary_pages(
    document: Document,
    metadata: DocumentMetadata,
    instructional_placeholders: dict[str, str],
) -> None:
    structure = metadata.document_structure_proposal
    prelim_entries: list[tuple[str, str]] = []

    if structure.halaman_sampul:
        title = "HALAMAN SAMPUL"
        prelim_entries.append((make_instruction_key("halaman_sampul", title), title))
    if structure.halaman_pengesahan:
        title = "HALAMAN PENGESAHAN"
        prelim_entries.append((make_instruction_key("halaman_pengesahan", title), title))
    if structure.ringkasan:
        title = "RINGKASAN"
        prelim_entries.append((make_instruction_key("ringkasan", title), title))
    for section in structure.sections:
        if section.type in ("daftar_isi", "daftar_gambar", "daftar_tabel", "daftar_lampiran"):
            if section.required is not False:
                # Prioritaskan title dari metadata; fallback ke format lama agar kompatibel.
                fallback = section.type.upper().replace("_", " ")
                title = (section.title or fallback).strip()
                prelim_entries.append((make_instruction_key(section.type, title), title))

    for index, (instruction_key, title) in enumerate(prelim_entries):
        heading = document.add_heading(title, level=1)
        heading.alignment = WD_ALIGN_PARAGRAPH.CENTER
        _force_paragraph_runs_black(heading)

        placeholder_text = instructional_placeholders.get(
            instruction_key,
            f"Instruksi pengisian untuk {title}: lengkapi bagian ini sesuai panduan dokumen.",
        )
        placeholder = document.add_paragraph(placeholder_text)
        _force_paragraph_runs_black(placeholder)
        if index < len(prelim_entries) - 1:
            document.add_page_break()


# ---------------------------------------------------------------------------
# Digunakan oleh: Dipakai internal di file ini atau dipanggil dari entrypoint runtime.
# Menjalankan fungsi `_render_proposal_body` sebagai bagian alur `docx_renderer`.
# ---------------------------------------------------------------------------
def _render_proposal_body(
    document: Document,
    metadata: DocumentMetadata,
    chunks: list[ChunkSource],
    instructional_placeholders: dict[str, str],
) -> None:
    proposal = metadata.document_structure_proposal

    for section in proposal.sections:
        if section.type == "bab":
            _render_bab_section(
                document,
                section,
                chunks,
                metadata,
                instructional_placeholders,
            )
        elif section.type == "daftar_pustaka":
            _render_named_section(
                document,
                section.type,
                section.title or "DAFTAR PUSTAKA",
                chunks,
                instructional_placeholders,
            )
        elif section.type == "lampiran":
            _render_named_section(
                document,
                section.type,
                section.title or "LAMPIRAN",
                chunks,
                instructional_placeholders,
            )


# ---------------------------------------------------------------------------
# Digunakan oleh: Dipakai internal di file ini atau dipanggil dari entrypoint runtime.
# Menjalankan fungsi `_render_bab_section` sebagai bagian alur `docx_renderer`.
# ---------------------------------------------------------------------------
def _render_bab_section(
    document: Document,
    section: SectionItem,
    chunks: list[ChunkSource],
    metadata: DocumentMetadata,
    instructional_placeholders: dict[str, str],
) -> None:
    title = section.title or "[JUDUL_BAB_BELUM_TERDETEKSI]"
    bab_number = f"BAB {section.number}" if section.number else "BAB"
    heading_text = f"{bab_number} {title}".strip()
    heading = document.add_heading(heading_text, level=1)
    heading.alignment = WD_ALIGN_PARAGRAPH.CENTER
    _force_paragraph_runs_black(heading)

    instruction_key = make_instruction_key("bab", heading_text, number=section.number)
    body_placeholder = document.add_paragraph(
        instructional_placeholders.get(
            instruction_key,
            f"Instruksi pengisian untuk {heading_text}: lengkapi isi bagian ini sesuai panduan.",
        )
    )
    _force_paragraph_runs_black(body_placeholder)

    sources = match_sources_for_section(
        chunks=chunks,
        section_label=bab_number,
        section_title=section.title,
    )
    _render_source_block(document, sources)
    _render_caption_examples(document, metadata)


# ---------------------------------------------------------------------------
# Digunakan oleh: Dipakai internal di file ini atau dipanggil dari entrypoint runtime.
# Menjalankan fungsi `_render_named_section` sebagai bagian alur `docx_renderer`.
# ---------------------------------------------------------------------------
def _render_named_section(
    document: Document,
    section_type: str,
    title: str,
    chunks: list[ChunkSource],
    instructional_placeholders: dict[str, str],
) -> None:
    heading = document.add_heading(title, level=1)
    heading.alignment = WD_ALIGN_PARAGRAPH.CENTER
    _force_paragraph_runs_black(heading)

    instruction_key = make_instruction_key(section_type, title)
    placeholder = document.add_paragraph(
        instructional_placeholders.get(
            instruction_key,
            f"Instruksi pengisian untuk {title}: lengkapi bagian ini sesuai panduan dokumen.",
        )
    )
    _force_paragraph_runs_black(placeholder)
    sources = match_sources_for_section(
        chunks=chunks,
        section_label=title,
        section_title=title,
    )
    _render_source_block(document, sources)


# ---------------------------------------------------------------------------
# Digunakan oleh: Dipakai internal di file ini atau dipanggil dari entrypoint runtime.
# Menjalankan fungsi `_render_source_block` sebagai bagian alur `docx_renderer`.
# ---------------------------------------------------------------------------
def _render_source_block(document: Document, sources: list[ChunkSource]) -> None:
    if not sources:
        paragraph = document.add_paragraph("Sumber: [BELUM DITEMUKAN]")
        _force_paragraph_runs_black(paragraph)
        return

    for source in sources:
        paragraph = document.add_paragraph(format_source_line(source))
        _force_paragraph_runs_black(paragraph)


# ---------------------------------------------------------------------------
# Digunakan oleh: Dipakai internal di file ini atau dipanggil dari entrypoint runtime.
# Menjalankan fungsi `_render_caption_examples` sebagai bagian alur `docx_renderer`.
# ---------------------------------------------------------------------------
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
        table_placeholder = document.add_paragraph("[PLACEHOLDER_TABEL]")
        _force_paragraph_runs_black(table_placeholder)
    else:
        table_placeholder = document.add_paragraph("[PLACEHOLDER_TABEL]")
        _force_paragraph_runs_black(table_placeholder)
        _add_seq_caption(document, "Table", table_template)

    if figure_pos == "BELOW":
        figure_placeholder = document.add_paragraph("[PLACEHOLDER_GAMBAR]")
        _force_paragraph_runs_black(figure_placeholder)
        _add_seq_caption(document, "Figure", figure_template)
    else:
        _add_seq_caption(document, "Figure", figure_template)
        figure_placeholder = document.add_paragraph("[PLACEHOLDER_GAMBAR]")
        _force_paragraph_runs_black(figure_placeholder)


# ---------------------------------------------------------------------------
# Digunakan oleh: Dipakai internal di file ini atau dipanggil dari entrypoint runtime.
# Menjalankan fungsi `_add_seq_caption` sebagai bagian alur `docx_renderer`.
# ---------------------------------------------------------------------------
def _add_seq_caption(document: Document, label: str, template: str) -> None:
    paragraph = document.add_paragraph()
    prefix, suffix = _split_caption_template(template, label)
    paragraph.add_run(prefix)
    _append_field(paragraph, f" SEQ {label} \\* ARABIC ")
    paragraph.add_run(suffix)
    _force_paragraph_runs_black(paragraph)


# ---------------------------------------------------------------------------
# Digunakan oleh: Dipakai internal di file ini atau dipanggil dari entrypoint runtime.
# Menjalankan fungsi `_split_caption_template` sebagai bagian alur `docx_renderer`.
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
# Digunakan oleh: Dipakai internal di file ini atau dipanggil dari entrypoint runtime.
# Menjalankan fungsi `_map_alignment` sebagai bagian alur `docx_renderer`.
# ---------------------------------------------------------------------------
def _map_alignment(value: str) -> WD_ALIGN_PARAGRAPH:
    mapping = {
        "LEFT": WD_ALIGN_PARAGRAPH.LEFT,
        "CENTER": WD_ALIGN_PARAGRAPH.CENTER,
        "RIGHT": WD_ALIGN_PARAGRAPH.RIGHT,
        "JUSTIFY": WD_ALIGN_PARAGRAPH.JUSTIFY,
    }
    return mapping.get(value, WD_ALIGN_PARAGRAPH.JUSTIFY)


# ---------------------------------------------------------------------------
# Digunakan oleh: Dipakai internal di file ini atau dipanggil dari entrypoint runtime.
# Menjalankan fungsi `_apply_page_numbering` sebagai bagian alur `docx_renderer`.
# ---------------------------------------------------------------------------
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


# ---------------------------------------------------------------------------
# Digunakan oleh: Dipakai internal di file ini atau dipanggil dari entrypoint runtime.
# Menjalankan fungsi `_position_alignment` sebagai bagian alur `docx_renderer`.
# ---------------------------------------------------------------------------
def _position_alignment(position: str) -> WD_ALIGN_PARAGRAPH:
    if position.endswith("_left"):
        return WD_ALIGN_PARAGRAPH.LEFT
    if position.endswith("_center"):
        return WD_ALIGN_PARAGRAPH.CENTER
    return WD_ALIGN_PARAGRAPH.RIGHT


# ---------------------------------------------------------------------------
# Digunakan oleh: Dipakai internal di file ini atau dipanggil dari entrypoint runtime.
# Menjalankan fungsi `_set_page_number_type` sebagai bagian alur `docx_renderer`.
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
# Digunakan oleh: Dipakai internal di file ini atau dipanggil dari entrypoint runtime.
# Menjalankan fungsi `_append_field` sebagai bagian alur `docx_renderer`.
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
# Digunakan oleh: Dipakai internal di file ini atau dipanggil dari entrypoint runtime.
# Menjalankan fungsi `_clear_paragraph` sebagai bagian alur `docx_renderer`.
# ---------------------------------------------------------------------------
def _clear_paragraph(paragraph) -> None:
    for run in paragraph.runs:
        run.clear()


# ---------------------------------------------------------------------------
# Digunakan oleh: Dipakai internal di file ini atau dipanggil dari entrypoint runtime.
# Menjalankan fungsi `_has_preliminary_pages` sebagai bagian alur `docx_renderer`.
# ---------------------------------------------------------------------------
def _has_preliminary_pages(metadata: DocumentMetadata) -> bool:
    structure = metadata.document_structure_proposal
    if structure.halaman_sampul or structure.halaman_pengesahan or structure.ringkasan:
        return True
    prelim_types = {"daftar_isi", "daftar_gambar", "daftar_tabel", "daftar_lampiran"}
    return any(s.type in prelim_types for s in structure.sections)
