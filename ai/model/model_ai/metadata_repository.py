"""Helper terpusat untuk baca/tulis metadata dokumen di tabel Supabase document_metadata. Posisi pipeline: doc_extractor → metadata_repository → instructional_placeholder_builder."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from model_ai.extractor.models import DocumentMetadata
from model_ai.shared import get_supabase_client


def get_document_metadata_row(project_id: str) -> dict[str, Any]:
    client = get_supabase_client()
    result = (
        client.table("document_metadata")
        .select("project_id, payload, extracted_at")
        .eq("project_id", project_id)
        .limit(1)
        .execute()
    )
    rows = result.data or []
    if not rows:
        raise LookupError(
            f"Metadata untuk project_id '{project_id}' tidak ditemukan di tabel document_metadata."
        )

    row = rows[0]
    if not isinstance(row, dict):
        raise TypeError(
            f"Row metadata untuk project_id '{project_id}' di document_metadata tidak valid."
        )
    return row


def load_document_metadata_payload(project_id: str) -> dict[str, Any]:
    row = get_document_metadata_row(project_id)
    payload = row.get("payload")
    if not isinstance(payload, dict):
        raise TypeError(
            f"Kolom payload di document_metadata untuk project_id '{project_id}' bukan JSON object."
        )
    return payload


def validate_document_metadata_payload(payload: dict[str, Any]) -> DocumentMetadata:
    return DocumentMetadata.model_validate(payload)


def load_document_metadata(project_id: str) -> DocumentMetadata:
    payload = load_document_metadata_payload(project_id)
    return validate_document_metadata_payload(payload)


def upsert_document_metadata(metadata: DocumentMetadata, project_id: str | None = None) -> str:
    payload = metadata.model_dump(exclude_none=True)
    client = get_supabase_client()

    insert_data = {
        "payload": payload,
        "extracted_at": datetime.now(timezone.utc).isoformat(),
    }

    if project_id:
        insert_data["project_id"] = project_id

    client.table("document_metadata").upsert(
        insert_data,
        on_conflict="project_id",
    ).execute()
    return project_id or "unknown"


def save_generated_placeholders(project_id: str, generated: dict[str, str], skema: str = "PKM-KC") -> None:
    """Update hanya field generated_placeholders di struktur dokumen yang sesuai skema."""
    from model_ai.shared import is_type_b

    client = get_supabase_client()

    result = client.table("document_metadata") \
        .select("payload") \
        .eq("project_id", project_id) \
        .single() \
        .execute()

    if not result.data:
        return

    structure_key = "document_structure_artikel" if is_type_b(skema) else "document_structure_proposal"
    payload: dict = result.data.get("payload") or {}
    doc_structure: dict = payload.get(structure_key) or {}
    doc_structure["generated_placeholders"] = generated
    payload[structure_key] = doc_structure

    client.table("document_metadata").update({"payload": payload}) \
        .eq("project_id", project_id) \
        .execute()
