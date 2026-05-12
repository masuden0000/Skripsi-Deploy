"""
Fungsi: Orkestrator utama pembuatan DOCX proposal dari output.json, chunk, dan instructional placeholders.

Digunakan oleh: manage.py; tests/docx/test_docx_generator.py

Tujuan: Menyediakan alur end-to-end agar perintah docx menghasilkan file final konsisten.
"""
import json
from pathlib import Path

from model_ai.docx.chunk_loader import load_chunk_sources
from model_ai.docx.docx_renderer import render_proposal_docx
from model_ai.docx.instructional_placeholder_builder import (
    build_instructional_placeholder_map,
)
from model_ai.docx.metadata_loader import coerce_document_metadata


# ---------------------------------------------------------------------------
# Digunakan oleh: manage.py
# Menjalankan fungsi `generate_proposal_docx` sebagai bagian alur `generator`.
# ---------------------------------------------------------------------------
def generate_proposal_docx(
    output_json_path: Path,
    chunks_path: Path,
    output_path: Path,
    use_llm_instructional_placeholders: bool = True,
) -> Path:
    with open(output_json_path, encoding="utf-8") as f:
        output_data = json.load(f)

    # metadata masih dibutuhkan oleh build_instructional_placeholder_map
    metadata = coerce_document_metadata(output_data)

    # Override output filename dengan format_nama_file dari database jika ada
    doc_structure = output_data.get("document_structure_proposal", {})
    format_nama_file = doc_structure.get("format_nama_file")
    if format_nama_file:
        output_path = output_path.parent / f"{format_nama_file}.docx"

    chunks = load_chunk_sources(chunks_path)
    instructional_placeholders = build_instructional_placeholder_map(
        metadata=metadata,
        chunks=chunks,
        use_llm=use_llm_instructional_placeholders,
    )
    return render_proposal_docx(
        output_data=output_data,
        chunks=chunks,
        instructional_placeholders=instructional_placeholders,
        output_path=output_path,
    )
