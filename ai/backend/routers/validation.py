"""
Fungsi: FastAPI router untuk validasi format dokumen DOCX proposal mahasiswa.

Endpoint:
  POST /run   — validasi satu dokumen (synchronous, hasil langsung dikembalikan)
  POST /bulk  — validasi banyak dokumen (async, kembalikan job_id, proses di background)
  GET  /jobs/{job_id} — cek status + hasil validasi bulk

Digunakan oleh: backend/src/routes/pkm.routes.js (sebagai proxy)
"""
import json
import os
import tempfile
from datetime import datetime, timezone

from fastapi import APIRouter, BackgroundTasks, File, Form, HTTPException, Request, UploadFile

from services.database import get_supabase
from services.job_processor import process_bulk_job, save_temp_file

router = APIRouter()


def _utcnow() -> str:
    return datetime.now(timezone.utc).isoformat()


# ─── Helper bersama: ambil metadata validasi dari Supabase ───────────────────

async def _fetch_metadata(schema_id: str, tahun: str) -> dict:
    """Ambil payload document_metadata untuk skema + tahun tertentu."""
    supabase = get_supabase()

    proj = (
        supabase.table("projects")
        .select("id")
        .eq("skema", schema_id)
        .eq("tahun", tahun)
        .order("created_at", desc=True)
        .limit(1)
        .execute()
    )
    if not proj.data:
        raise HTTPException(
            status_code=404,
            detail=f"Data referensi untuk {schema_id} tahun {tahun} belum tersedia.",
        )

    meta_row = (
        supabase.table("document_metadata")
        .select("payload")
        .eq("project_id", proj.data[0]["id"])
        .limit(1)
        .execute()
    )
    if not meta_row.data:
        raise HTTPException(
            status_code=404,
            detail="Metadata format dokumen belum tersedia. Pastikan pipeline ekstraksi sudah selesai.",
        )

    payload = meta_row.data[0]["payload"]
    if isinstance(payload, str):
        payload = json.loads(payload)
    return payload


def _build_result_dict(result) -> dict:
    """Konversi ValidationResult ke dict dengan format yang diharapkan frontend."""
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


# ─── POST /run — validasi satu dokumen ───────────────────────────────────────

@router.post("/run")
async def run_validation(
    schema_id: str = Form(...),
    tahun: str = Form(...),
    file: UploadFile = File(...),
):
    """
    Validasi format DOCX proposal mahasiswa terhadap aturan yang tersimpan
    di document_metadata untuk skema dan tahun yang dipilih reviewer.

    schema_id: slug PKM (mis. "PKM-KC") yang cocok dengan projects.skema.
    tahun: tahun referensi (mis. "2025") yang cocok dengan projects.tahun.
    """
    if not (file.filename or "").lower().endswith(".docx"):
        raise HTTPException(status_code=400, detail="File harus berformat DOCX (.docx).")

    if not tahun.strip():
        raise HTTPException(status_code=400, detail="Parameter tahun tidak boleh kosong.")

    try:
        payload = await _fetch_metadata(schema_id.strip(), tahun.strip())
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Gagal mengambil data dari database: {str(e)}")

    content = await file.read()
    tmp_path = None
    try:
        with tempfile.NamedTemporaryFile(suffix=".docx", delete=False) as tmp:
            tmp.write(content)
            tmp_path = tmp.name

        from model_ai.validation import validate_document  # noqa: PLC0415
        result = validate_document(tmp_path, metadata_dict=payload)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Gagal menjalankan validasi dokumen: {str(e)}")
    finally:
        if tmp_path and os.path.exists(tmp_path):
            os.unlink(tmp_path)

    return _build_result_dict(result)


# ─── POST /bulk — validasi banyak dokumen (async) ────────────────────────────

@router.post("/bulk")
async def run_bulk_validation(request: Request, background_tasks: BackgroundTasks):
    """
    Terima sejumlah file DOCX beserta metadata-nya, buat validation job,
    simpan file ke storage sementara, dan jalankan validasi di background.

    Frontend mengirim FormData dengan field:
      count          : jumlah dokumen
      schema_id_{i}  : schema_id dokumen ke-i
      tahun_{i}      : tahun dokumen ke-i
      file_{i}       : UploadFile dokumen ke-i

    Kembalikan: { job_id: string }
    """
    try:
        form = await request.form()
        count = int(form.get("count") or 0)
    except Exception:
        raise HTTPException(status_code=400, detail="Format form data tidak valid.")

    if count < 1:
        raise HTTPException(status_code=400, detail="Minimal satu dokumen harus diupload.")

    if count > 20:
        raise HTTPException(status_code=400, detail="Maksimal 20 dokumen per batch.")

    # Validasi dan baca semua file sebelum membuat job
    items_bytes: list[dict] = []
    for i in range(count):
        schema_id = str(form.get(f"schema_id_{i}") or "").strip()
        tahun     = str(form.get(f"tahun_{i}")     or "").strip()
        upload    = form.get(f"file_{i}")

        if not schema_id:
            raise HTTPException(status_code=400, detail=f"schema_id dokumen ke-{i + 1} kosong.")
        if not tahun:
            raise HTTPException(status_code=400, detail=f"tahun dokumen ke-{i + 1} kosong.")
        if upload is None:
            raise HTTPException(status_code=400, detail=f"File dokumen ke-{i + 1} tidak ditemukan.")

        filename = getattr(upload, "filename", "") or f"dokumen_{i + 1}.docx"
        if not filename.lower().endswith(".docx"):
            raise HTTPException(
                status_code=400,
                detail=f"Dokumen ke-{i + 1} ({filename}) harus berformat DOCX.",
            )

        content = await upload.read()
        items_bytes.append({
            "position":  i,
            "file_name": filename,
            "schema_id": schema_id,
            "tahun":     tahun,
            "content":   content,
        })

    # Buat job + items di Supabase
    supabase = get_supabase()
    now = _utcnow()

    job_row = (
        supabase.table("validation_jobs")
        .insert({
            "status":         "pending",
            "total_items":    count,
            "completed_items": 0,
            "created_at":     now,
            "updated_at":     now,
        })
        .execute()
    )
    if not job_row.data:
        raise HTTPException(status_code=500, detail="Gagal membuat validation job di database.")

    job_id = job_row.data[0]["id"]

    # Buat baris per item
    item_rows = [
        {
            "job_id":    job_id,
            "position":  item["position"],
            "file_name": item["file_name"],
            "schema_id": item["schema_id"],
            "tahun":     item["tahun"],
            "status":    "pending",
            "created_at": now,
            "updated_at": now,
        }
        for item in items_bytes
    ]
    supabase.table("validation_job_items").insert(item_rows).execute()

    # Simpan file ke storage sementara
    for item in items_bytes:
        save_temp_file(job_id, item["position"], item["content"])

    # Jadwalkan background task
    items_meta = [
        {
            "position":  item["position"],
            "file_name": item["file_name"],
            "schema_id": item["schema_id"],
            "tahun":     item["tahun"],
        }
        for item in items_bytes
    ]
    background_tasks.add_task(process_bulk_job, job_id, items_meta)

    return {"job_id": job_id}


# ─── GET /jobs/{job_id} — status + hasil validasi bulk ───────────────────────

@router.get("/jobs/{job_id}")
async def get_job_status(job_id: str):
    """
    Kembalikan status job dan semua item-nya.
    Frontend polling endpoint ini setiap beberapa detik untuk update progres.
    """
    supabase = get_supabase()

    job_row = (
        supabase.table("validation_jobs")
        .select("*")
        .eq("id", job_id)
        .limit(1)
        .execute()
    )
    if not job_row.data:
        raise HTTPException(status_code=404, detail="Job tidak ditemukan.")

    job = job_row.data[0]

    items_row = (
        supabase.table("validation_job_items")
        .select("*")
        .eq("job_id", job_id)
        .order("position", desc=False)
        .execute()
    )

    return {
        "id":              job["id"],
        "status":          job["status"],
        "total_items":     job["total_items"],
        "completed_items": job["completed_items"],
        "created_at":      job["created_at"],
        "updated_at":      job["updated_at"],
        "items": [
            {
                "id":            item["id"],
                "position":      item["position"],
                "file_name":     item["file_name"],
                "schema_id":     item["schema_id"],
                "tahun":         item["tahun"],
                "status":        item["status"],
                "result":        item["result"],
                "error_message": item["error_message"],
            }
            for item in items_row.data
        ],
    }
