"""
Fungsi: Memuat metadata hasil ekstraksi proposal dari Supabase berdasarkan `project_id`.

Digunakan oleh: model_ai/docx/generator.py

Tujuan: Menjadikan `document_metadata.payload` sebagai sumber metadata yang konsisten untuk pipeline DOCX.
"""
from typing import Any

from model_ai.extractor.models import DocumentMetadata
from model_ai.metadata_repository import (
    load_document_metadata_payload as load_document_metadata_payload_from_supabase,
    validate_document_metadata_payload,
)


# ---------------------------------------------------------------------------
# Digunakan oleh: model_ai/docx/generator.py
# Menjalankan fungsi `load_document_metadata_payload` sebagai bagian alur `metadata_loader`.
# ---------------------------------------------------------------------------
def load_document_metadata_payload(project_id: str) -> dict[str, Any]:
    return load_document_metadata_payload_from_supabase(project_id)


# ---------------------------------------------------------------------------
# Digunakan oleh: model_ai/docx/generator.py
# Menjalankan fungsi `load_document_metadata` sebagai bagian alur `metadata_loader`.
# ---------------------------------------------------------------------------
def load_document_metadata(project_id: str) -> DocumentMetadata:
    payload = load_document_metadata_payload(project_id)
    return validate_document_metadata_payload(payload)


# ---------------------------------------------------------------------------
# Digunakan oleh: model_ai/docx/generator.py
# Menjalankan fungsi `coerce_document_metadata` saat payload sudah tersedia di memori.
# ---------------------------------------------------------------------------
def coerce_document_metadata(payload: dict[str, Any]) -> DocumentMetadata:
    return validate_document_metadata_payload(payload)