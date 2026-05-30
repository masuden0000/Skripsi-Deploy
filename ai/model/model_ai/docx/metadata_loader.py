"""Memuat metadata hasil ekstraksi proposal dari Supabase berdasarkan project_id. Posisi pipeline: metadata_repository → metadata_loader → generator."""
from typing import Any

from model_ai.extractor.models import DocumentMetadata
from model_ai.metadata_repository import (
    load_document_metadata_payload as load_document_metadata_payload_from_supabase,
    validate_document_metadata_payload,
)


def load_document_metadata_payload(project_id: str) -> dict[str, Any]:
    return load_document_metadata_payload_from_supabase(project_id)


def load_document_metadata(project_id: str) -> DocumentMetadata:
    payload = load_document_metadata_payload(project_id)
    return validate_document_metadata_payload(payload)


def coerce_document_metadata(payload: dict[str, Any]) -> DocumentMetadata:
    return validate_document_metadata_payload(payload)