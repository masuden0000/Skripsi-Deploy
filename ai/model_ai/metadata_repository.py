"""
Fungsi: Helper terpusat untuk baca/tulis metadata dokumen di tabel Supabase `document_metadata`.

Digunakan oleh: model_ai/docx/metadata_loader.py; model_ai/extractor/doc_extractor.py; model_ai/extractor/schema_differ.py; testing ekstraksi.

Tujuan: Menjadikan `document_metadata.payload` sebagai source of truth metadata lintas runtime AI.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from supabase import Client, create_client

from model_ai.config import get_config
from model_ai.extractor.models import DocumentMetadata


# ---------------------------------------------------------------------------
# Digunakan oleh: Fungsi-fungsi repository metadata pada modul ini.
# Menyediakan client Supabase yang konsisten dengan konfigurasi runtime AI.
# ---------------------------------------------------------------------------
def build_metadata_supabase_client() -> Client:
    config = get_config()
    return create_client(
        config.supabase_url,
        config.supabase_service_role_key.get_secret_value(),
    )


# ---------------------------------------------------------------------------
# Digunakan oleh: Dipakai internal di file ini atau dipanggil dari entrypoint runtime.
# Menormalkan selector source_doc agar semua consumer memakai nilai yang eksplisit.
# ---------------------------------------------------------------------------
def _normalize_source_doc(source_doc: str) -> str:
    normalized = source_doc.strip()
    if not normalized:
        raise ValueError(
            "source_doc wajib diisi untuk membaca metadata dari tabel document_metadata."
        )
    return normalized


# ---------------------------------------------------------------------------
# Digunakan oleh: load_document_metadata_payload()
# Mengambil satu row metadata dari Supabase berdasarkan source_doc.
# ---------------------------------------------------------------------------
def get_document_metadata_row(source_doc: str) -> dict[str, Any]:
    normalized = _normalize_source_doc(source_doc)
    client = build_metadata_supabase_client()
    result = (
        client.table("document_metadata")
        .select("source_doc, payload, extracted_at")
        .eq("source_doc", normalized)
        .limit(1)
        .execute()
    )
    rows = result.data or []
    if not rows:
        raise LookupError(
            f"Metadata untuk source_doc '{normalized}' tidak ditemukan di tabel document_metadata."
        )

    row = rows[0]
    if not isinstance(row, dict):
        raise TypeError(
            f"Row metadata untuk source_doc '{normalized}' di document_metadata tidak valid."
        )
    return row


# ---------------------------------------------------------------------------
# Digunakan oleh: model_ai/docx/metadata_loader.py; schema_differ; testing ekstraksi.
# Mengambil raw payload JSON metadata berdasarkan source_doc.
# ---------------------------------------------------------------------------
def load_document_metadata_payload(source_doc: str) -> dict[str, Any]:
    normalized = _normalize_source_doc(source_doc)
    row = get_document_metadata_row(normalized)
    payload = row.get("payload")
    if not isinstance(payload, dict):
        raise TypeError(
            f"Kolom payload di document_metadata untuk source_doc '{normalized}' bukan JSON object."
        )
    return payload


# ---------------------------------------------------------------------------
# Digunakan oleh: model_ai/docx/metadata_loader.py
# Memvalidasi payload raw menjadi object DocumentMetadata yang aman dipakai runtime.
# ---------------------------------------------------------------------------
def validate_document_metadata_payload(payload: dict[str, Any]) -> DocumentMetadata:
    return DocumentMetadata.model_validate(payload)


# ---------------------------------------------------------------------------
# Digunakan oleh: model_ai/docx/metadata_loader.py
# Shortcut untuk memuat sekaligus memvalidasi metadata dari Supabase.
# ---------------------------------------------------------------------------
def load_document_metadata(source_doc: str) -> DocumentMetadata:
    payload = load_document_metadata_payload(source_doc)
    return validate_document_metadata_payload(payload)


# ---------------------------------------------------------------------------
# Digunakan oleh: model_ai/extractor/doc_extractor.py
# Upsert metadata hasil extract ke Supabase dan kembalikan source_doc yang dipakai.
# ---------------------------------------------------------------------------
def upsert_document_metadata(metadata: DocumentMetadata) -> str:
    payload = metadata.model_dump(exclude_none=True)
    source_doc = str(payload.get("source_document") or "").strip() or "unknown"
    client = build_metadata_supabase_client()
    client.table("document_metadata").upsert(
        {
            "source_doc": source_doc,
            "payload": payload,
            "extracted_at": datetime.now(timezone.utc).isoformat(),
        },
        on_conflict="source_doc",
    ).execute()
    return source_doc
