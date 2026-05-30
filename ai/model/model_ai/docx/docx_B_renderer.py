"""Renderer Type B: menulis konten terstruktur ke dokumen .docx khusus PKM-AI (artikel ilmiah). Posisi pipeline: instructional_placeholder_builder → docx_B_renderer → DOCX output. Belum diimplementasi."""


def render_article_docx_bytes(
    output_data: dict,
    chunks: list,
    instructional_placeholders: dict[str, str],
) -> bytes:
    """Render DOCX artikel ilmiah untuk PKM-AI dan kembalikan sebagai bytes. Belum diimplementasi."""
    raise NotImplementedError("Renderer PKM-AI (Type B) belum diimplementasi.")
