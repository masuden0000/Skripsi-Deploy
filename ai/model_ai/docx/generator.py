"""
Fungsi: Orkestrator utama pembuatan DOCX proposal dari metadata, chunk, dan style translator.

Digunakan oleh: manage.py; tests/docx/test_docx_generator.py

Tujuan: Menyediakan alur end-to-end agar perintah docx menghasilkan file final konsisten.
"""
from pathlib import Path

from model_ai.docx.chunk_loader import load_chunk_sources
from model_ai.docx.docx_renderer import render_proposal_docx
from model_ai.docx.instructional_placeholder_builder import (
    build_instructional_placeholder_map,
)
from model_ai.docx.metadata_loader import (
    coerce_document_metadata,
    load_document_metadata_payload,
)
from model_ai.docx.style_mapping_pipeline import translate_docx_style_config


# ---------------------------------------------------------------------------
# Digunakan oleh: manage.py
# Menjalankan fungsi `generate_proposal_docx` sebagai bagian alur `generator`.
# ---------------------------------------------------------------------------
def generate_proposal_docx(
    source_doc: str,
    chunks_path: Path,
    output_path: Path,
    use_llm_normalization: bool = True,
    use_llm_instructional_placeholders: bool = True,
) -> Path:
    metadata_payload = load_document_metadata_payload(source_doc)
    metadata = coerce_document_metadata(metadata_payload)
    chunks = load_chunk_sources(chunks_path)
    style_config = translate_docx_style_config(
        metadata=metadata,
        extracted_payload=metadata_payload,
        use_llm_mapper=use_llm_normalization,
        with_embeddings=use_llm_normalization,
    )
    # Susun instruksi per section lebih dulu agar renderer tidak lagi memakai placeholder kosong.
    instructional_placeholders = build_instructional_placeholder_map(
        metadata=metadata,
        chunks=chunks,
        use_llm=use_llm_instructional_placeholders,
    )
    return render_proposal_docx(
        metadata=metadata,
        chunks=chunks,
        style_config=style_config,
        instructional_placeholders=instructional_placeholders,
        output_path=output_path,
    )
