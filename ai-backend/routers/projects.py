from fastapi import APIRouter, UploadFile, File, Form, HTTPException, BackgroundTasks
from typing import Optional
from ..services.database import get_supabase
from ..services.storage import upload_file, delete_file, BUCKET_SOURCE, BUCKET_OUTPUT
from ..services.pipeline import run_pipeline
from ..models.schemas import ProjectStatus, ProjectResponse, ProjectListResponse
from datetime import datetime

router = APIRouter()


def map_project_row(row) -> ProjectStatus:
    """Map Supabase row to ProjectStatus model."""
    return ProjectStatus(
        id=row.get("id", ""),
        skema=row.get("skema", ""),
        tahun=row.get("tahun", ""),
        judul=row.get("judul", ""),
        source_file=row.get("source_file"),
        source_url=row.get("source_url"),
        status=row.get("status", "pending"),
        error_message=row.get("error_message"),
        result_url=row.get("result_url"),
        created_at=row.get("created_at", datetime.now()),
        updated_at=row.get("updated_at", datetime.now()),
    )


@router.post("/", response_model=ProjectResponse)
async def create_project(
    background_tasks: BackgroundTasks,
    skema: str = Form(...),
    tahun: str = Form(...),
    judul: str = Form(...),
    file: Optional[UploadFile] = File(None),
):
    """
    Create a new project with file upload and start pipeline.
    """
    supabase = get_supabase()

    # Create project record first
    project_data = {
        "skema": skema,
        "tahun": tahun,
        "judul": judul,
        "status": "pending",
    }

    # Insert project
    result = supabase.table("projects").insert(project_data).execute()

    if not result.data:
        raise HTTPException(status_code=500, detail="Failed to create project")

    project = result.data[0]
    project_id = project["id"]

    # Upload file if provided
    source_url = None
    source_file = None

    if file:
        source_file = file.filename
        file_content = await file.read()

        # Upload to storage
        try:
            source_url = await upload_file(BUCKET_SOURCE, file_content, file.filename, project_id)
        except Exception as e:
            # Clean up project and raise error
            supabase.table("projects").delete().eq("id", project_id).execute()
            raise HTTPException(status_code=500, detail=f"Failed to upload file: {str(e)}")

        # Update project with file info
        supabase.table("projects").update({
            "source_file": source_file,
            "source_url": source_url,
            "status": "uploading"
        }).eq("id", project_id).execute()

    # Start background pipeline
    background_tasks.add_task(run_pipeline, project_id, source_url)

    # Get updated project
    updated_result = supabase.table("projects").select("*").eq("id", project_id).execute()
    updated_project = map_project_row(updated_result.data[0]) if updated_result.data else map_project_row(project)

    return ProjectResponse(data=updated_project, message="Project created successfully")


@router.get("/", response_model=ProjectListResponse)
async def list_projects():
    """
    List all projects.
    """
    supabase = get_supabase()
    result = supabase.table("projects").select("*").order("created_at", ascending=False).execute()

    projects = [map_project_row(row) for row in result.data]

    return ProjectListResponse(data=projects)


@router.get("/{project_id}", response_model=ProjectResponse)
async def get_project(project_id: str):
    """
    Get project details by ID (for polling status).
    """
    supabase = get_supabase()
    result = supabase.table("projects").select("*").eq("id", project_id).execute()

    if not result.data:
        raise HTTPException(status_code=404, detail="Project not found")

    project = map_project_row(result.data[0])

    return ProjectResponse(data=project)


@router.delete("/{project_id}")
async def delete_project(project_id: str):
    """
    Delete a project and its associated data.
    """
    supabase = get_supabase()

    # Get project to find associated files
    result = supabase.table("projects").select("*").eq("id", project_id).execute()

    if not result.data:
        raise HTTPException(status_code=404, detail="Project not found")

    project = result.data[0]

    # Delete associated storage files
    if project.get("source_url"):
        # Extract path from URL
        source_path = f"{project_id}/{project.get('source_file', 'file')}"
        await delete_file(BUCKET_SOURCE, source_path)

    if project.get("result_url"):
        await delete_file(BUCKET_OUTPUT, project.get("result_url"))

    # Delete project (cascade will delete chunks and metadata)
    supabase.table("projects").delete().eq("id", project_id).execute()

    return {"message": "Project deleted successfully"}