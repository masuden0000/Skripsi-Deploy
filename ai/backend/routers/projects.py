"""
FastAPI Router untuk Projects.
Entry point dari Express Backend ke pipeline AI. Mengelola lifecycle project di Supabase
dan memicu run_pipeline (fase ekstraksi) serta run_docx_pipeline (fase generate DOCX) sebagai background tasks.

Dipakai oleh: Express Backend (sebagai proxy internal — tidak diakses langsung dari frontend)
Keyword: automated document generation
"""
from fastapi import APIRouter, UploadFile, File, Form, BackgroundTasks, Query
from fastapi.responses import JSONResponse
from typing import Optional, Any
from services.database import get_supabase
from services.storage import upload_file, delete_file, delete_folder, BUCKET_SOURCE, BUCKET_OUTPUT
from services.pipeline import run_pipeline, run_docx_pipeline
from schemas.project_schema import Project, ProjectStatus
from datetime import datetime

router = APIRouter()


def map_project_row(row: dict[str, Any]) -> Project:
    """Map Supabase row to Project model."""
    status_value = row.get("status", "pending")
    try:
        status = ProjectStatus(status_value)
    except ValueError:
        status = ProjectStatus.PENDING

    return Project(
        id=row.get("id", ""),
        skema=row.get("skema", ""),
        tahun=row.get("tahun", ""),
        source_file=row.get("source_file"),
        source_url=row.get("source_url"),
        status=status,
        error_message=row.get("error_message"),
        result_url=row.get("result_url"),
        created_at=row.get("created_at", datetime.now()),
        updated_at=row.get("updated_at", datetime.now()),
    )


@router.post("/")
async def create_project(
    background_tasks: BackgroundTasks,
    skema: str = Form(...),
    tahun: str = Form(...),
    file: Optional[UploadFile] = File(None),
):
    skema = skema.upper()
    """
    Create or update a project.
    If a project with the same skema and tahun already exists, update it instead.
    Called by Express Backend only - not directly from frontend.
    """
    supabase = get_supabase()

    # Check if project with same skema and tahun already exists
    existing = supabase.table("projects").select("id, status").eq("skema", skema).eq("tahun", tahun).execute()

    project_id: str
    is_update = False

    if existing.data:
        # Update existing project
        is_update = True
        project_id = existing.data[0]["id"]

        # Hapus file lama dari storage agar upload baru tidak terkena error Duplicate
        if file:
            old_source_file = existing.data[0].get("source_file")
            if old_source_file:
                try:
                    await delete_file(BUCKET_SOURCE, f"{project_id}/{old_source_file}")
                except Exception:
                    pass

        # Reset status to pending if it's completed or failed (allow re-run)
        current_status = existing.data[0].get("status", "")
        if current_status in ("completed", "failed", "completed_with_errors"):
            supabase.table("projects").update({
                "status": "pending",
                "error_message": None,
                "result_url": None,
            }).eq("id", project_id).execute()

    else:
        # Create new project
        project_data = {
            "judul": f"Proposal {skema.upper()} {tahun}",
            "skema": skema,
            "tahun": tahun,
            "status": "pending",
        }

        result = supabase.table("projects").insert(project_data).execute()

        if not result.data:
            return JSONResponse(
                status_code=500,
                content={"success": False, "error": "Failed to create project"}
            )

        project_id = result.data[0]["id"]

    source_url = None
    source_file = None

    if file:
        source_file = file.filename or "unnamed_file"
        file_content = await file.read()

        try:
            source_url = await upload_file(BUCKET_SOURCE, file_content, source_file, project_id)
        except Exception as e:
            if not is_update:
                supabase.table("projects").delete().eq("id", project_id).execute()
            return JSONResponse(
                status_code=500,
                content={"success": False, "error": f"Failed to upload file: {str(e)}"}
            )

        supabase.table("projects").update({
            "source_file": source_file,
            "source_url": source_url,
            "status": "uploading"
        }).eq("id", project_id).execute()

    # Start background pipeline
    if source_url and source_file:
        background_tasks.add_task(run_pipeline, project_id, source_url, source_file)

    updated_result = supabase.table("projects").select("*").eq("id", project_id).execute()
    updated_project = map_project_row(updated_result.data[0]) if updated_result.data else None

    if not updated_project:
        return JSONResponse(
            status_code=500,
            content={"success": False, "error": "Failed to retrieve updated project"}
        )

    return JSONResponse(
        status_code=201 if not is_update else 200,
        content={
            "success": True,
            "data": updated_project.model_dump(mode="json"),
            "message": "Project created successfully" if not is_update else "Project updated successfully"
        }
    )


@router.get("/")
async def list_projects():
    """
    List all projects.
    """
    try:
        supabase = get_supabase()
        result = supabase.table("projects").select("*").order("created_at", desc=True).execute()
        projects = [map_project_row(row) for row in result.data]
        return {
            "success": True,
            "data": [p.model_dump(mode="json") for p in projects]
        }
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"success": False, "error": f"Gagal mengambil daftar project: {str(e)}"}
        )


@router.get("/{project_id}")
async def get_project(project_id: str):
    """
    Get project details by ID (for polling status).
    """
    try:
        supabase = get_supabase()
        result = supabase.table("projects").select("*").eq("id", project_id).execute()

        if not result.data:
            return JSONResponse(
                status_code=404,
                content={"success": False, "data": None, "error": "Project not found"}
            )

        project = map_project_row(result.data[0])

        return {
            "success": True,
            "data": project.model_dump(mode="json")
        }
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"success": False, "data": None, "error": f"Gagal mengambil data project: {str(e)}"}
        )


@router.get("/{project_id}/logs")
async def get_project_logs(project_id: str, since_id: int = Query(0, ge=0)):
    """
    Get log entries for a project.
    Pass since_id to return only logs with id > since_id (for current-run filtering).
    """
    try:
        supabase = get_supabase()

        # Verify project exists
        project_result = supabase.table("projects").select("id").eq("id", project_id).execute()
        if not project_result.data:
            return JSONResponse(
                status_code=404,
                content={"success": False, "error": "Project not found"}
            )

        # Get logs ordered by timestamp, optionally filtered by since_id
        query = supabase.table("project_logs").select("*").eq("project_id", project_id)
        if since_id > 0:
            query = query.gt("id", since_id)
        result = query.order("timestamp", desc=False).execute()

        return {
            "success": True,
            "data": result.data or []
        }
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"success": False, "error": f"Gagal mengambil log project: {str(e)}"}
        )


@router.post("/{project_id}/generate")
async def generate_document(project_id: str, background_tasks: BackgroundTasks):
    """
    Trigger DOCX generation for a project that has already been extracted.
    Called by Express Backend after user reviews and saves extraction results.
    Frontend → Express Backend → AI Backend (internal only).
    """
    try:
        supabase = get_supabase()

        result = supabase.table("projects").select("id, status").eq("id", project_id).execute()

        if not result.data:
            return JSONResponse(
                status_code=404,
                content={"success": False, "error": "Project not found"}
            )

        current_status = result.data[0].get("status", "")
        if current_status != "extracted":
            return JSONResponse(
                status_code=400,
                content={
                    "success": False,
                    "error": f"Project harus dalam status 'extracted' untuk generate dokumen, status saat ini: '{current_status}'"
                }
            )

        background_tasks.add_task(run_docx_pipeline, project_id)

        return JSONResponse(
            status_code=200,
            content={"success": True, "message": "Document generation started"}
        )
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"success": False, "error": f"Gagal memulai generate dokumen: {str(e)}"}
        )


@router.get("/{project_id}/placeholders")
async def get_placeholders(project_id: str):
    """
    Baca generated_placeholders dan user_placeholders dari DB.
    generated_placeholders disimpan saat pipeline docx selesai — tidak di-generate ulang di sini.
    """
    try:
        supabase = get_supabase()
        result = (
            supabase.table("document_metadata")
            .select("payload")
            .eq("project_id", project_id)
            .single()
            .execute()
        )

        if not result.data:
            return JSONResponse(
                status_code=404,
                content={"success": False, "error": "Metadata project tidak ditemukan"},
            )

        payload: dict = result.data.get("payload") or {}
        doc_structure: dict = payload.get("document_structure_proposal") or {}

        generated: dict = doc_structure.get("generated_placeholders") or {}
        user_overrides: dict = doc_structure.get("user_placeholders") or {}

        return JSONResponse(content={
            "success": True,
            "data": {"generated": generated, "user_overrides": user_overrides},
        })
    except Exception as e:
        import traceback
        return JSONResponse(
            status_code=500,
            content={"success": False, "error": str(e), "detail": traceback.format_exc()},
        )


@router.delete("/{project_id}")
async def delete_project(project_id: str):
    """
    Delete a project and its associated data.
    """
    try:
        supabase = get_supabase()

        result = supabase.table("projects").select("*").eq("id", project_id).execute()

        if not result.data:
            return JSONResponse(
                status_code=404,
                content={"success": False, "error": "Project not found"}
            )

        project = result.data[0]

        if project.get("source_url"):
            source_path = f"{project_id}/{project.get('source_file', 'file')}"
            await delete_file(BUCKET_SOURCE, source_path)

        result_url = project.get("result_url")
        if result_url:
            # Ekstrak path dari URL: .../object/public/{bucket}/{path}
            marker = f"/{BUCKET_OUTPUT}/"
            idx = result_url.find(marker)
            if idx != -1:
                output_path = result_url[idx + len(marker):]
                await delete_file(BUCKET_OUTPUT, output_path)
            else:
                # Fallback: hapus seluruh folder project di bucket output
                await delete_folder(BUCKET_OUTPUT, project_id)
        else:
            # Belum ada result_url (status extracted/failed), tetap bersihkan folder output
            await delete_folder(BUCKET_OUTPUT, project_id)

        supabase.table("projects").delete().eq("id", project_id).execute()

        return {"success": True, "message": "Project deleted successfully"}
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"success": False, "error": f"Gagal menghapus project: {str(e)}"}
        )
