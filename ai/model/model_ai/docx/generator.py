"""Orkestrator utama pembuatan DOCX dari metadata, chunk, dan instructional placeholders. Posisi pipeline: instructional_placeholder_builder → generator → docx_A_renderer / docx_B_renderer → DOCX output. Keyword: automated document generation"""
from pathlib import Path

from model_ai.docx.chunk_loader import load_chunk_sources
from model_ai.docx.docx_A_renderer import render_proposal_docx_bytes
from model_ai.docx.docx_B_renderer import render_article_docx_bytes
from model_ai.docx.instructional_placeholder_builder import (
    build_instructional_placeholder_map,
)
from model_ai.metadata_repository import load_document_metadata, save_generated_placeholders
from model_ai.shared import is_type_b


def generate_proposal_docx_bytes(
    project_id: str,
    skema: str = "PKM-KC",
    use_llm_instructional_placeholders: bool = True,
) -> tuple[bytes, str]:
    """Load metadata dari Supabase, chunks dari Supabase, generate DOCX bytes.

    Routing:
      Type A (semua PKM kecuali PKM-AI) → docx_A_renderer
      Type B (PKM-AI)                   → docx_B_renderer
    """
    metadata = load_document_metadata(project_id)

    # Routing struktur berdasarkan skema: Type B (PKM-AI) → artikel; Type A → proposal
    doc_structure = (
        metadata.document_structure_artikel
        if is_type_b(skema)
        else metadata.document_structure_proposal
    )
    format_nama_file = doc_structure.format_nama_file if doc_structure else None
    file_name = f"{format_nama_file or project_id}.docx"
    if format_nama_file:
        file_name = f"{Path(format_nama_file).stem}.docx"

    chunks = load_chunk_sources(project_id)

    existing_placeholders = (doc_structure.generated_placeholders if doc_structure else {}) or {}

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
            save_generated_placeholders(project_id, instructional_placeholders, skema=skema)
            print("[docx] Placeholder tersimpan ke DB.", flush=True)
        except Exception as exc:
            print(f"[docx] WARNING: Gagal menyimpan placeholder ke DB: {exc}", flush=True)

    user_placeholders = (doc_structure.user_placeholders if doc_structure else {}) or {}
    if user_placeholders:
        instructional_placeholders = {**instructional_placeholders, **user_placeholders}

    output_data = metadata.model_dump()

    if is_type_b(skema):
        print(f"[docx] Skema {skema} -> Type B renderer (PKM-AI).", flush=True)
        doc_bytes = render_article_docx_bytes(
            output_data=output_data,
            chunks=chunks,
            instructional_placeholders=instructional_placeholders,
        )
    else:
        print(f"[docx] Skema {skema} -> Type A renderer (proposal).", flush=True)
        doc_bytes = render_proposal_docx_bytes(
            output_data=output_data,
            chunks=chunks,
            instructional_placeholders=instructional_placeholders,
        )

    return doc_bytes, file_name
