"""
Fungsi: Orkestrator utama pembuatan DOCX proposal dari output.json, chunk, dan instructional placeholders.

Digunakan oleh: manage.py; tests/docx/test_docx_generator.py

Tujuan: Menyediakan alur end-to-end agar perintah docx menghasilkan file final konsisten.

Input: output.json (dari extract), chunks (dari Supabase)
Output: bytes DOCX — tidak disimpan ke filesystem lokal.
"""
from io import BytesIO
from pathlib import Path

from model_ai.docx.chunk_loader import load_chunk_sources
from model_ai.docx.docx_renderer import render_proposal_docx_bytes
from model_ai.docx.instructional_placeholder_builder import (
    build_instructional_placeholder_map,
)
from model_ai.metadata_repository import load_document_metadata


def generate_proposal_docx_bytes(
    project_id: str,
    source_doc: str,
    use_llm_instructional_placeholders: bool = True,
) -> tuple[bytes, str]:
    """
    Load metadata dari Supabase, chunks dari Supabase, generate DOCX bytes.
    Tidak ada file yang disimpan ke filesystem lokal.
    """
    metadata = load_document_metadata(source_doc)

    file_name = f"{metadata.document_structure_proposal.format_nama_file or project_id}.docx"
    if metadata.document_structure_proposal.format_nama_file:
        file_name = f"{Path(metadata.document_structure_proposal.format_nama_file).stem}.docx"

    chunks = load_chunk_sources(project_id)
    instructional_placeholders = build_instructional_placeholder_map(
        metadata=metadata,
        chunks=chunks,
        use_llm=use_llm_instructional_placeholders,
    )

    doc_bytes = render_proposal_docx_bytes(
        output_data=metadata.model_dump(),
        chunks=chunks,
        instructional_placeholders=instructional_placeholders,
    )
    return doc_bytes, file_name
