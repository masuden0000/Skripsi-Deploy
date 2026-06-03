"""
Fungsi: FastAPI router untuk validasi format dokumen DOCX proposal mahasiswa.

Pipeline validasi (dipanggil oleh reviewer):
  1. Terima file DOCX + schema_id + tahun dari frontend via Express proxy
  2. Cari project referensi (skema + tahun) dari tabel projects
  3. Muat payload document_metadata sebagai ground truth aturan format
  4. Jalankan validator Python terhadap file DOCX yang diupload
  5. Kembalikan ValidationResult (status, issues, checks) ke frontend

schema_id adalah value dari PKM_SCHEMES di frontend (mis. "PKM-KC"),
yang harus cocok persis dengan kolom projects.skema di database.

Digunakan oleh: backend/src/routes/pkm.routes.js (sebagai proxy)
"""
import json
import os
import tempfile

from fastapi import APIRouter, File, Form, HTTPException, UploadFile

from services.database import get_supabase

router = APIRouter()


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
    # Validasi tipe file
    if not (file.filename or "").lower().endswith(".docx"):
        raise HTTPException(status_code=400, detail="File harus berformat DOCX (.docx).")

    if not tahun.strip():
        raise HTTPException(status_code=400, detail="Parameter tahun tidak boleh kosong.")

    try:
        supabase = get_supabase()

        skema_slug = schema_id
        year = tahun.strip()

        # 1. Cari project untuk skema + tahun (ambil yang terbaru)
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

        # 2. Ambil payload document_metadata
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
        if isinstance(payload, str):
            payload = json.loads(payload)

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Gagal mengambil data dari database: {str(e)}",
        )

    # 3. Simpan DOCX ke temp file, jalankan validator, hapus temp
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
        raise HTTPException(
            status_code=500,
            detail=f"Gagal menjalankan validasi dokumen: {str(e)}",
        )
    finally:
        if tmp_path and os.path.exists(tmp_path):
            os.unlink(tmp_path)

    # 4. Ubah ValidationResult ke dict dengan field `valid` tambahan
    result_dict = result.to_dict()
    result_dict["valid"] = result_dict.get("status") == "pass"

    # Ubah summary string → object sesuai validationSummarySchema di frontend
    passed = result_dict.pop("passed_count", 0)
    failed = result_dict.pop("error_count", 0)
    warnings = result_dict.pop("warning_count", 0)
    skipped = result_dict.pop("skipped_count", 0)
    result_dict["summary"] = {
        "total_checks": passed + failed + warnings + skipped,
        "passed": passed,
        "failed": failed,
        "warnings": warnings,
        "errors": failed,
    }

    return result_dict
