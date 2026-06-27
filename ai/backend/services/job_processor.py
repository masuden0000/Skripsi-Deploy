"""
Background job processor untuk validasi dokumen bulk.

Alur:
  1. Caller menyimpan file ke jobs_temp via save_temp_file()
  2. Caller membuat baris di validation_sessions + validation_results via Supabase
  3. FastAPI BackgroundTasks memanggil process_bulk_session()
  4. process_bulk_session() memproses semua item secara paralel (maks 5 serentak,
     sisanya antri) menggunakan asyncio.Semaphore.
  5. Setiap item memperbarui completed_items setelah selesai.
  6. Session ditandai 'completed' setelah semua task selesai.
Keyword: automated document validation
"""
import asyncio
import json
import logging
import os
from datetime import datetime, timezone
from pathlib import Path

from services.database import get_supabase

logger = logging.getLogger(__name__)

JOBS_TEMP_DIR = Path(__file__).resolve().parent.parent / "jobs_temp"

_BULK_SEMAPHORE = asyncio.Semaphore(5)


def _utcnow() -> str:
    return datetime.now(timezone.utc).isoformat()


def _temp_path(session_id: str, position: int) -> Path:
    return JOBS_TEMP_DIR / f"{session_id}_{position}.docx"


def save_temp_file(session_id: str, position: int, content: bytes) -> None:
    """Simpan bytes file ke folder sementara sebelum diproses background task."""
    JOBS_TEMP_DIR.mkdir(parents=True, exist_ok=True)
    _temp_path(session_id, position).write_bytes(content)


def _delete_temp(session_id: str, position: int) -> None:
    p = _temp_path(session_id, position)
    if p.exists():
        p.unlink()


def build_validation_dict(result) -> dict:
    """Konversi ValidationResult ke dict format frontend.

    Dipakai oleh validation.py (POST /run) dan _run_validation_sync (POST /bulk)
    agar format response konsisten antara single dan bulk validation.
    """
    d = result.to_dict()
    d["valid"] = d.get("status") == "pass"

    passed   = d.pop("passed_count",  0)
    failed   = d.pop("error_count",   0)
    warnings = d.pop("warning_count", 0)
    skipped  = d.pop("skipped_count", 0)
    d["summary"] = {
        "total_checks": passed + failed + warnings + skipped,
        "passed":       passed,
        "failed":       failed,
        "warnings":     warnings,
    }
    return d


def _run_validation_sync(tmp_path: str, payload: dict) -> dict:
    """Wrapper sinkron untuk validate_document — dipanggil via asyncio.to_thread()."""
    from model_ai.validation import validate_document  # noqa: PLC0415

    result = validate_document(tmp_path, metadata_dict=payload)
    return build_validation_dict(result)


async def _validate_item(session_id: str, meta: dict, sb) -> None:
    """Validasi satu dokumen; maks 5 berjalan serentak via _BULK_SEMAPHORE."""
    pos       = meta["position"]
    schema_id = meta["schema_id"]
    tahun     = meta["tahun"]

    def _upd(fields: dict) -> None:
        sb.table("validation_results").update(
            {**fields, "updated_at": _utcnow()}
        ).eq("session_id", session_id).eq("position", pos).execute()

    _upd({"status": "processing"})
    try:
        proj = (
            sb.table("projects")
            .select("id")
            .eq("skema", schema_id)
            .eq("tahun", tahun)
            .order("created_at", desc=True)
            .limit(1)
            .execute()
        )
        if not proj.data:
            raise ValueError(
                f"Data referensi untuk {schema_id} tahun {tahun} belum tersedia."
            )

        meta_row = (
            sb.table("document_metadata")
            .select("payload")
            .eq("project_id", proj.data[0]["id"])
            .limit(1)
            .execute()
        )
        if not meta_row.data:
            raise ValueError("Metadata format dokumen belum tersedia.")

        payload = meta_row.data[0]["payload"]
        if isinstance(payload, str):
            payload = json.loads(payload)

        tmp = str(_temp_path(session_id, pos))
        if not os.path.exists(tmp):
            raise ValueError("File sementara tidak ditemukan di server.")

        async with _BULK_SEMAPHORE:
            result = await asyncio.to_thread(_run_validation_sync, tmp, payload)

        _upd({"status": "completed", "result": result})

    except Exception as exc:
        _upd({"status": "failed", "error_message": str(exc)})

    finally:
        _delete_temp(session_id, pos)

    rows = (
        sb.table("validation_results")
        .select("status")
        .eq("session_id", session_id)
        .execute()
    )
    done = sum(1 for r in rows.data if r["status"] in ("completed", "failed"))
    sb.table("validation_sessions").update(
        {"completed_items": done, "updated_at": _utcnow()}
    ).eq("id", session_id).execute()


async def process_bulk_session(session_id: str, items_meta: list[dict]) -> None:
    """
    Background task: validasi semua item secara paralel, maks 5 serentak.
    Dokumen ke-6 dan seterusnya akan antri hingga slot tersedia.

    items_meta: list of { position, file_name, schema_id, tahun }
    """
    sb = get_supabase()

    def _upd_session(fields: dict) -> None:
        sb.table("validation_sessions").update(
            {**fields, "updated_at": _utcnow()}
        ).eq("id", session_id).execute()

    try:
        _upd_session({"status": "processing"})

        tasks = [_validate_item(session_id, meta, sb) for meta in items_meta]
        await asyncio.gather(*tasks)

        _upd_session({"status": "completed"})

    except Exception as exc:
        logger.exception(
            "process_bulk_session gagal untuk session_id=%s: %s", session_id, exc
        )
        _upd_session({"status": "failed"})
