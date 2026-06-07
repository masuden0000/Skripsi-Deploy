"""
Fungsi: FastAPI router untuk validasi format dokumen DOCX proposal mahasiswa.

Endpoint:
  POST /run              — validasi satu dokumen (synchronous, hasil langsung dikembalikan)
  POST /bulk             — validasi banyak dokumen (async, kembalikan session_id, proses di background)
  GET  /sessions/{id}    — cek status + hasil validasi bulk

Digunakan oleh: backend/src/routes/pkm.routes.js (sebagai proxy)
"""
import json
import os
import tempfile
from datetime import datetime, timezone

from fastapi import APIRouter, BackgroundTasks, File, Form, HTTPException, Request, UploadFile

from services.database import get_supabase
from services.job_processor import process_bulk_session, save_temp_file

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

    result_dict = _build_result_dict(result)

    # Simpan hasil ke Supabase (session tunggal)
    try:
        supabase = get_supabase()
        now = _utcnow()

        session_row = (
            supabase.table("validation_sessions")
            .insert({
                "type":            "single",
                "status":          "completed",
                "total_items":     1,
                "completed_items": 1,
                "created_at":      now,
                "updated_at":      now,
            })
            .execute()
        )

        if session_row.data:
            session_id = session_row.data[0]["id"]
            supabase.table("validation_results").insert({
                "session_id":  session_id,
                "position":    0,
                "file_name":   file.filename or "dokumen.docx",
                "schema_id":   schema_id.strip(),
                "tahun":       tahun.strip(),
                "status":      "completed",
                "result":      result_dict,
                "created_at":  now,
                "updated_at":  now,
            }).execute()
    except Exception:
        # Gagal menyimpan ke DB tidak boleh menggagalkan response ke frontend
        pass

    return result_dict


# ─── POST /bulk — validasi banyak dokumen (async) ────────────────────────────

@router.post("/bulk")
async def run_bulk_validation(request: Request, background_tasks: BackgroundTasks):
    """
    Terima sejumlah file DOCX beserta metadata-nya, buat validation session,
    simpan file ke storage sementara, dan jalankan validasi di background.

    Frontend mengirim FormData dengan field:
      count          : jumlah dokumen
      schema_id_{i}  : schema_id dokumen ke-i
      tahun_{i}      : tahun dokumen ke-i
      file_{i}       : UploadFile dokumen ke-i

    Kembalikan: { session_id: string }
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

    # Validasi dan baca semua file sebelum membuat session
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

    # Buat session + result rows di Supabase
    supabase = get_supabase()
    now = _utcnow()

    session_row = (
        supabase.table("validation_sessions")
        .insert({
            "type":            "bulk",
            "status":          "pending",
            "total_items":     count,
            "completed_items": 0,
            "created_at":      now,
            "updated_at":      now,
        })
        .execute()
    )
    if not session_row.data:
        raise HTTPException(status_code=500, detail="Gagal membuat validation session di database.")

    session_id = session_row.data[0]["id"]

    # Buat baris per item di validation_results
    result_rows = [
        {
            "session_id": session_id,
            "position":   item["position"],
            "file_name":  item["file_name"],
            "schema_id":  item["schema_id"],
            "tahun":      item["tahun"],
            "status":     "pending",
            "created_at": now,
            "updated_at": now,
        }
        for item in items_bytes
    ]
    supabase.table("validation_results").insert(result_rows).execute()

    # Simpan file ke storage sementara
    for item in items_bytes:
        save_temp_file(session_id, item["position"], item["content"])

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
    background_tasks.add_task(process_bulk_session, session_id, items_meta)

    return {"session_id": session_id}


# ─── GET /sessions/{session_id} — status + hasil validasi bulk ───────────────

@router.get("/sessions/{session_id}")
async def get_session_status(session_id: str):
    """
    Kembalikan status session dan semua result-nya.
    Frontend polling endpoint ini setiap beberapa detik untuk update progres.
    """
    supabase = get_supabase()

    session_row = (
        supabase.table("validation_sessions")
        .select("*")
        .eq("id", session_id)
        .limit(1)
        .execute()
    )
    if not session_row.data:
        raise HTTPException(status_code=404, detail="Session tidak ditemukan.")

    session = session_row.data[0]

    results_row = (
        supabase.table("validation_results")
        .select("*")
        .eq("session_id", session_id)
        .order("position", desc=False)
        .execute()
    )

    return {
        "id":              session["id"],
        "type":            session["type"],
        "status":          session["status"],
        "total_items":     session["total_items"],
        "completed_items": session["completed_items"],
        "created_at":      session["created_at"],
        "updated_at":      session["updated_at"],
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
            for item in results_row.data
        ],
    }
