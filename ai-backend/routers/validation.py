"""
Fungsi: API route untuk validasi format dokumen DOCX proposal mahasiswa
Digunakan oleh: Express Backend (via POST /api/validation/run)
Tujuan: Memvalidasi dokumen DOCX terhadap aturan skema dan tahun periode review aktif
"""

import os
import sys
import tempfile
from datetime import date

from fastapi import APIRouter, File, Form, HTTPException, UploadFile

from services.database import get_supabase

_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
_AI_DIR = os.path.join(_PROJECT_ROOT, "ai")
if _AI_DIR not in sys.path:
    sys.path.insert(0, _AI_DIR)

router = APIRouter()


@router.post("/run")
async def run_validation(
    schema_id: str = Form(...),
    file: UploadFile = File(...),
):
    if not (file.filename or "").lower().endswith(".docx"):
        raise HTTPException(status_code=400, detail="File harus berformat DOCX (.docx).")

    supabase = get_supabase()
    today = date.today().isoformat()

    period_result = (
        supabase.table("pkm_review_periods")
        .select("id, nama, tanggal_mulai")
        .lte("tanggal_mulai", today)
        .gte("tanggal_selesai", today)
        .limit(1)
        .execute()
    )
    if not period_result.data:
        raise HTTPException(
            status_code=422,
            detail="Tidak ada periode review yang aktif saat ini.",
        )
    year = period_result.data[0]["tanggal_mulai"][:4]

    skema_slug = schema_id

    project_result = (
        supabase.table("projects")
        .select("id")
        .eq("skema", skema_slug)
        .eq("tahun", year)
        .order("created_at", desc=True)
        .limit(1)
        .execute()
    )
    if not project_result.data:
        raise HTTPException(
            status_code=404,
            detail=f"Data referensi untuk {skema_slug} tahun {year} belum tersedia.",
        )
    project_id = project_result.data[0]["id"]

    metadata_result = (
        supabase.table("document_metadata")
        .select("payload")
        .eq("project_id", project_id)
        .limit(1)
        .execute()
    )
    if not metadata_result.data:
        raise HTTPException(
            status_code=404,
            detail="Metadata format dokumen belum tersedia. Pastikan pipeline ekstraksi sudah selesai.",
        )
    payload = metadata_result.data[0]["payload"]

    content = await file.read()
    tmp_path = None
    try:
        with tempfile.NamedTemporaryFile(suffix=".docx", delete=False) as tmp:
            tmp.write(content)
            tmp_path = tmp.name

        from model_ai.validation import validate_document  # noqa: PLC0415
        result = validate_document(tmp_path, metadata_dict=payload)
    finally:
        if tmp_path and os.path.exists(tmp_path):
            os.unlink(tmp_path)

    result_dict = result.to_dict()
    result_dict["valid"] = result_dict.get("status") == "pass"
    return result_dict