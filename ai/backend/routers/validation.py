"""
Fungsi: FastAPI router untuk validasi format dokumen DOCX proposal mahasiswa.

Pipeline validasi (dipanggil oleh reviewer):
  1. Terima file DOCX + schema_slug dari frontend via Express proxy
  2. Tentukan tahun aktif dari pkm_review_periods
  3. Cari project referensi (skema + tahun) dari tabel projects
  4. Muat payload document_metadata sebagai ground truth aturan format
  5. Jalankan validator Python terhadap file DOCX yang diupload
  6. Kembalikan ValidationResult (status, issues, checks) ke frontend

schema_slug adalah value dari PKM_SCHEMES di frontend (mis. "pkm-re"),
yang harus cocok persis dengan kolom projects.skema di database.

Digunakan oleh: backend/src/routes/pkm.routes.js (sebagai proxy)
"""
import os
import tempfile
from datetime import date

from fastapi import APIRouter, File, Form, HTTPException, UploadFile

from services.database import get_supabase

router = APIRouter()


@router.post("/run")
async def run_validation(
    schema_id: str = Form(...),
    file: UploadFile = File(...),
):
    """
    Validasi format DOCX proposal mahasiswa terhadap aturan yang tersimpan
    di document_metadata untuk skema dan tahun periode review aktif.

    schema_id: slug PKM (mis. "pkm-re") yang cocok dengan projects.skema.
    """
    # Validasi tipe file
    if not (file.filename or "").lower().endswith(".docx"):
        raise HTTPException(status_code=400, detail="File harus berformat DOCX (.docx).")

    supabase = get_supabase()
    today = date.today().isoformat()

    # 1. Fetch active review period → ambil tahun dari tanggal_mulai
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

    # schema_id IS the slug (e.g. "pkm-re") — matches projects.skema directly
    skema_slug = schema_id

    # 2. Cari project untuk skema + tahun (ambil yang terbaru)
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

    # 4. Ambil payload document_metadata
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

    # 5. Simpan DOCX ke temp file, jalankan validator, hapus temp
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

    # 6. Ubah ValidationResult ke dict dengan field `valid` tambahan
    result_dict = result.to_dict()
    result_dict["valid"] = result_dict.get("status") == "pass"
    return result_dict
