"""
Fungsi: Helper terpusat untuk baca/tulis metadata dokumen di tabel Supabase `document_metadata`.

Digunakan oleh: model_ai/docx/metadata_loader.py; model_ai/extractor/doc_extractor.py; model_ai/docx/generator.py

Tujuan: Menjadikan `document_metadata.payload` sebagai source of truth metadata lintas runtime AI.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from supabase import Client, create_client

from model_ai.config import get_config
from model_ai.extractor.models import DocumentMetadata


def build_metadata_supabase_client() -> Client:
    config = get_config()
    return create_client(
        config.supabase_url,
        config.supabase_service_role_key.get_secret_value(),
    )


def get_document_metadata_row(project_id: str) -> dict:
    client = build_metadata_supabase_client()
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


def load_document_metadata_payload(project_id: str) -> dict:
    row = get_document_metadata_row(project_id)
    payload = row.get("payload")
    if not isinstance(payload, dict):
        raise TypeError(
            f"Kolom payload di document_metadata untuk project_id '{project_id}' bukan JSON object."
        )
    return payload


def _normalize_payload_keys(payload: dict) -> dict:
    if "document_structure_proposal" in payload and "document_structure" not in payload:
        payload = dict(payload)
        payload["document_structure"] = payload.pop("document_structure_proposal")
    return payload


def validate_document_metadata_payload(payload: dict) -> DocumentMetadata:
    return DocumentMetadata.model_validate(payload)


def load_document_metadata(project_id: str) -> DocumentMetadata:
    payload = load_document_metadata_payload(project_id)
    return validate_document_metadata_payload(payload)


def upsert_document_metadata(metadata: DocumentMetadata, project_id: str | None = None) -> str:
    payload = metadata.model_dump(exclude_none=True)
    client = build_metadata_supabase_client()

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


def save_generated_placeholders(project_id: str, generated: dict[str, str]) -> None:
    """
    Update hanya field document_structure.generated_placeholders di payload
    tanpa menyentuh field lain di document_metadata.
    """
    client = build_metadata_supabase_client()

    result = client.table("document_metadata") \
        .select("payload") \
        .eq("project_id", project_id) \
        .single() \
        .execute()

    if not result.data:
        return

    payload: dict = _normalize_payload_keys(result.data.get("payload") or {})
    doc_structure: dict = payload.get("document_structure") or {}
    doc_structure["generated_placeholders"] = generated
    payload["document_structure"] = doc_structure

    client.table("document_metadata").update({"payload": payload}) \
        .eq("project_id", project_id) \
        .execute()


def migrate_all_payload_keys() -> tuple[int, int]:
    """Rename document_structure_proposal → document_structure di semua record.

    Return (total, migrated): jumlah total record dan yang berhasil dimigrasi.
    """
    client = build_metadata_supabase_client()
    result = client.table("document_metadata").select("project_id, payload").execute()
    rows = result.data or []

    migrated = 0
    for row in rows:
        project_id = row.get("project_id")
        payload = row.get("payload") or {}
        normalized = _normalize_payload_keys(payload)
        if normalized is not payload:
            client.table("document_metadata").update({"payload": normalized}) \
                .eq("project_id", project_id) \
                .execute()
            migrated += 1

    return len(rows), migrated
