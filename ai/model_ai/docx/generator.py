"""
Fungsi: Orkestrator utama pembuatan DOCX proposal dari output.json, chunk, dan instructional placeholders.

Digunakan oleh: manage.py; tests/docx/test_docx_generator.py

Tujuan: Menyediakan alur end-to-end agar perintah docx menghasilkan file final konsisten.

Input: output.json (dari extract), chunks (dari Supabase)
Output: bytes DOCX — tidak disimpan ke filesystem lokal.
"""
from pathlib import Path

from model_ai.docx.chunk_loader import load_chunk_sources
from model_ai.docx.docx_renderer import render_proposal_docx_bytes
from model_ai.docx.instructional_placeholder_builder import (
    build_instructional_placeholder_map,
)
from model_ai.metadata_repository import load_document_metadata, save_generated_placeholders


def generate_proposal_docx_bytes(
    project_id: str,
    use_llm_instructional_placeholders: bool = True,
) -> tuple[bytes, str]:
    """
    Load metadata dari Supabase, chunks dari Supabase, generate DOCX bytes.
    Tidak ada file yang disimpan ke filesystem lokal.
    """
    metadata = load_document_metadata(project_id)

    file_name = f"{metadata.document_structure_proposal.format_nama_file or project_id}.docx"
    if metadata.document_structure_proposal.format_nama_file:
        file_name = f"{Path(metadata.document_structure_proposal.format_nama_file).stem}.docx"

    chunks = load_chunk_sources(project_id)

    # Gunakan placeholder yang sudah tersimpan di DB (dari step pipeline sebelumnya)
    existing_placeholders = (
        metadata.document_structure_proposal.generated_placeholders
        if metadata.document_structure_proposal
        else {}
    ) or {}

    if existing_placeholders:
        print(f"[docx] Menggunakan {len(existing_placeholders)} placeholder dari DB (tidak generate ulang).", flush=True)
        instructional_placeholders = existing_placeholders
    else:
        print("[docx] Placeholder belum ada di DB. Memulai generate instructional placeholder...", flush=True)
        instructional_placeholders = build_instructional_placeholder_map(
            metadata=metadata,
            chunks=chunks,
            use_llm=use_llm_instructional_placeholders,
        )
        print(f"[docx] Placeholder selesai ({len(instructional_placeholders)} section). Menyimpan ke DB...", flush=True)
        try:
            save_generated_placeholders(project_id, instructional_placeholders)
            print("[docx] Placeholder tersimpan ke DB.", flush=True)
        except Exception as exc:
            print(f"[docx] WARNING: Gagal menyimpan placeholder ke DB: {exc}", flush=True)

    # User-edited placeholders override LLM-generated
    user_placeholders = (
        metadata.document_structure_proposal.user_placeholders
        if metadata.document_structure_proposal
        else {}
    ) or {}
    if user_placeholders:
        instructional_placeholders = {**instructional_placeholders, **user_placeholders}

    doc_bytes = render_proposal_docx_bytes(
        output_data=metadata.model_dump(),
        chunks=chunks,
        instructional_placeholders=instructional_placeholders,
    )
    return doc_bytes, file_name
