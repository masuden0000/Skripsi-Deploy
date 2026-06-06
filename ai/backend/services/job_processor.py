"""
Background job processor untuk validasi dokumen bulk.

Alur:
  1. Caller menyimpan file ke jobs_temp via save_temp_file()
  2. Caller membuat baris di validation_jobs + validation_job_items via Supabase
  3. FastAPI BackgroundTasks memanggil process_bulk_job()
  4. process_bulk_job() memproses setiap item secara berurut:
     - Update status item → 'processing'
     - Ambil metadata dari Supabase (sama seperti validasi tunggal)
     - Jalankan validasi di thread terpisah (CPU-bound)
     - Simpan hasil / pesan error ke DB
     - Hapus file sementara
  5. Update completed_items dan status job setelah semua selesai
"""
import asyncio
import json
import os
from datetime import datetime, timezone
from pathlib import Path

from services.database import get_supabase

JOBS_TEMP_DIR = Path(__file__).resolve().parent.parent / "jobs_temp"


def _utcnow() -> str:
    return datetime.now(timezone.utc).isoformat()


def _temp_path(job_id: str, position: int) -> Path:
    return JOBS_TEMP_DIR / f"{job_id}_{position}.docx"


def save_temp_file(job_id: str, position: int, content: bytes) -> None:
    """Simpan bytes file ke folder sementara sebelum diproses background task."""
    JOBS_TEMP_DIR.mkdir(parents=True, exist_ok=True)
    _temp_path(job_id, position).write_bytes(content)


def _delete_temp(job_id: str, position: int) -> None:
    p = _temp_path(job_id, position)
    if p.exists():
        p.unlink()


def _run_validation_sync(tmp_path: str, payload: dict) -> dict:
    """
    Wrapper sinkron untuk validate_document — dipanggil via asyncio.to_thread()
    agar tidak memblokir event loop FastAPI.
    """
    from model_ai.validation import validate_document  # noqa: PLC0415

    result = validate_document(tmp_path, metadata_dict=payload)
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
        "errors":       failed,
    }
    return d


async def process_bulk_job(job_id: str, items_meta: list[dict]) -> None:
    """
    Background task: validasi setiap item secara berurut.

    items_meta: list of { position, file_name, schema_id, tahun }
    """
    sb = get_supabase()

    def _upd_job(fields: dict) -> None:
        sb.table("validation_jobs").update(
            {**fields, "updated_at": _utcnow()}
        ).eq("id", job_id).execute()

    def _upd_item(position: int, fields: dict) -> None:
        sb.table("validation_job_items").update(
            {**fields, "updated_at": _utcnow()}
        ).eq("job_id", job_id).eq("position", position).execute()

    def _refresh_completed_count() -> None:
        rows = (
            sb.table("validation_job_items")
            .select("status")
            .eq("job_id", job_id)
            .execute()
        )
        done = sum(
            1 for r in rows.data
            if r["status"] in ("completed", "failed")
        )
        _upd_job({"completed_items": done})

    try:
        _upd_job({"status": "processing"})

        for meta in sorted(items_meta, key=lambda x: x["position"]):
            pos       = meta["position"]
            schema_id = meta["schema_id"]
            tahun     = meta["tahun"]

            _upd_item(pos, {"status": "processing"})

            try:
                # 1. Cari project referensi
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

                # 2. Ambil payload document_metadata
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

                # 3. Jalankan validasi di thread terpisah
                tmp = str(_temp_path(job_id, pos))
                if not os.path.exists(tmp):
                    raise ValueError("File sementara tidak ditemukan di server.")

                result = await asyncio.to_thread(_run_validation_sync, tmp, payload)
                _upd_item(pos, {"status": "completed", "result": result})

            except Exception as exc:
                _upd_item(pos, {"status": "failed", "error_message": str(exc)})

            finally:
                _delete_temp(job_id, pos)

            _refresh_completed_count()

        _upd_job({"status": "completed"})

    except Exception:
        _upd_job({"status": "failed"})
