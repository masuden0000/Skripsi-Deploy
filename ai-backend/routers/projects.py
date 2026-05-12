"""
FastAPI Router for Projects
Dipakai oleh: Express Backend (sebagai internal API)
Semua HTTP communication masuk melalui Express, FastAPI hanya untuk AI pipeline
"""
from fastapi import APIRouter, UploadFile, File, Form, BackgroundTasks
from fastapi.responses import JSONResponse
from typing import Optional, Any
from services.database import get_supabase
from services.storage import upload_file, delete_file, create_signed_upload_url, BUCKET_SOURCE, BUCKET_OUTPUT
from services.pipeline import run_pipeline
from schemas.project_schema import Project, ProjectStatus
from datetime import datetime
import os

router = APIRouter()


def map_project_row(row: dict[str, Any]) -> Project:
    """Map Supabase row to Project model."""
    return Project(
        id=row.get("id", ""),
        skema=row.get("skema", ""),
        tahun=row.get("tahun", ""),
        judul=row.get("judul", ""),
        source_file=row.get("source_file"),
        source_url=row.get("source_url"),
        status=ProjectStatus(row.get("status", "pending")),
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
    judul: str = Form(...),
    file: Optional[UploadFile] = File(None),
):
    """
    Create a new project.
    Called by Express Backend only - not directly from frontend.
    """
    supabase = get_supabase()

    project_data = {
        "skema": skema,
        "tahun": tahun,
        "judul": judul,
        "status": "pending",
    }

    result = supabase.table("projects").insert(project_data).execute()

    if not result.data:
        return JSONResponse(
            status_code=500,
            content={"success": False, "error": "Failed to create project"}
        )

    project = result.data[0]
    project_id = project["id"]

    source_url = None
    source_file = None

    if file:
        source_file = file.filename or "unnamed_file"
        file_content = await file.read()

        try:
            source_url = await upload_file(BUCKET_SOURCE, file_content, source_file, project_id)
        except Exception as e:
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
    if source_url:
        background_tasks.add_task(run_pipeline, project_id, source_url)

    updated_result = supabase.table("projects").select("*").eq("id", project_id).execute()
    updated_project = map_project_row(updated_result.data[0]) if updated_result.data else map_project_row(project)

    return JSONResponse(
        status_code=201,
        content={
            "success": True,
            "data": updated_project.model_dump(mode="json"),
            "message": "Project created successfully"
        }
    )


@router.post("/upload-url")
async def create_project_with_upload_url(
    skema: str = Form(...),
    tahun: str = Form(...),
    judul: str = Form(...),
    file_name: str = Form(...),
):
    """
    Create a new project and return signed URL for direct upload to Supabase Storage.
    Frontend uploads file directly to Supabase, then calls /confirm-upload to trigger pipeline.
    """
    supabase = get_supabase()

    # Create project with pending_upload status
    project_data = {
        "skema": skema,
        "tahun": tahun,
        "judul": judul,
        "status": "pending_upload",
    }

    result = supabase.table("projects").insert(project_data).execute()

    if not result.data:
        return JSONResponse(
            status_code=500,
            content={"success": False, "error": "Failed to create project"}
        )

    project = result.data[0]
    project_id = project["id"]

    # Generate signed upload URL
    storage_path = f"{project_id}/{file_name}"
    signed_url_data = await create_signed_upload_url(BUCKET_SOURCE, storage_path)

    return JSONResponse(
        status_code=200,
        content={
            "success": True,
            "data": {
                "project_id": project_id,
                "signed_url": signed_url_data.get("signed_url") or signed_url_data.get("url"),
                "token": signed_url_data.get("token"),
                "storage_path": storage_path,
            },
            "message": "Use signed URL to upload file directly to Supabase Storage"
        }
    )


@router.post("/confirm-upload")
async def confirm_upload(
    background_tasks: BackgroundTasks,
    project_id: str = Form(...),
    file_name: str = Form(...),
):
    """
    Confirm that file upload is complete and trigger the AI pipeline.
    Called by frontend after successful upload to Supabase Storage.
    """
    supabase = get_supabase()

    # Get project
    result = supabase.table("projects").select("*").eq("id", project_id).execute()

    if not result.data:
        return JSONResponse(
            status_code=404,
            content={"success": False, "error": "Project not found"}
        )

    project = result.data[0]

    # Update project with file info and status
    storage_path = f"{project_id}/{file_name}"

    # Get actual public URL from Supabase
    try:
        client = supabase
        public_url = client.storage.from_(BUCKET_SOURCE).get_public_url(storage_path)
    except Exception:
        # Fallback to constructed URL
        supabase_url = os.getenv("SUPABASE_URL", "")
        public_url = f"{supabase_url}/storage/v1/object/public/{BUCKET_SOURCE}/{storage_path}"

    supabase.table("projects").update({
        "source_file": file_name,
        "source_url": public_url,
        "status": "uploading"
    }).eq("id", project_id).execute()

    # Start background pipeline
    background_tasks.add_task(run_pipeline, project_id, public_url)

    updated_result = supabase.table("projects").select("*").eq("id", project_id).execute()
    updated_project = map_project_row(updated_result.data[0]) if updated_result.data else map_project_row(project)

    return JSONResponse(
        status_code=200,
        content={
            "success": True,
            "data": updated_project.model_dump(mode="json"),
            "message": "Upload confirmed, pipeline started"
        }
    )


@router.get("/")
async def list_projects():
    """
    List all projects.
    """
    supabase = get_supabase()
    result = supabase.table("projects").select("*").order("created_at", desc=True).execute()

    projects = [map_project_row(row) for row in result.data]

    return {
        "success": True,
        "data": [p.model_dump(mode="json") for p in projects]
    }


@router.get("/{project_id}")
async def get_project(project_id: str):
    """
    Get project details by ID (for polling status).
    """
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


@router.delete("/{project_id}")
async def delete_project(project_id: str):
    """
    Delete a project and its associated data.
    """
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

    if project.get("result_url"):
        result_url_str = project.get("result_url")
        if result_url_str:
            await delete_file(BUCKET_OUTPUT, str(result_url_str))

    supabase.table("projects").delete().eq("id", project_id).execute()

    return {"success": True, "message": "Project deleted successfully"}
