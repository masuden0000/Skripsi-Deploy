"""Orkestrator utama pembuatan DOCX proposal dari metadata, chunk, dan instructional placeholders. Posisi pipeline: instructional_placeholder_builder → generator → docx_renderer → DOCX output."""
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
