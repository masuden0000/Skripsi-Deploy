import subprocess
import os
from .database import get_supabase

BUCKET_SOURCE = "ai-source-files"
BUCKET_OUTPUT = "ai-output-files"


async def download_source_file(source_url: str, project_id: str) -> str:
    """
    Download the source file from Supabase Storage to local project directory.
    Returns the local file path.
    """
    from .storage import download_file

    # Create project directory
    ai_dir = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
    project_dir = os.path.join(ai_dir, "model_ai", "data", project_id)
    os.makedirs(project_dir, exist_ok=True)

    # Extract file path from URL
    # URL format: https://xxx.supabase.co/storage/v1/object/public/bucket/path
    local_path = os.path.join(project_dir, "source.pdf")

    # Download the file
    file_content = await download_file(BUCKET_SOURCE, f"{project_id}/source.pdf")
    with open(local_path, "wb") as f:
        f.write(file_content)

    return local_path


async def run_setup(project_id: str) -> bool:
    """
    Run the setup pipeline (extract chunks + ingest to Supabase).
    """
    print(f"[Pipeline] Starting setup for project {project_id}")

    supabase = get_supabase()
    supabase.table("projects").update({"status": "uploading"}).eq("id", project_id).execute()

    try:
        result = subprocess.run(
            [
                "python", "model_ai/manage.py",
                "setup",
                "--project-id", project_id,
            ],
            cwd=os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
            capture_output=True,
            text=True
        )

        if result.returncode != 0:
            print(f"[Pipeline] Setup error: {result.stderr}")
            supabase.table("projects").update({
                "status": "failed",
                "error_message": f"Setup failed: {result.stderr}"
            }).eq("id", project_id).execute()
            return False

        print(f"[Pipeline] Setup completed")
        return True
    except Exception as e:
        print(f"[Pipeline] Setup exception: {e}")
        supabase.table("projects").update({
            "status": "failed",
            "error_message": str(e)
        }).eq("id", project_id).execute()
        return False


async def run_extraction(project_id: str, source_url: str):
    """
    Run the AI extraction pipeline (extract metadata from chunks).
    """
    print(f"[Pipeline] Starting extraction for project {project_id}")

    # Update status to extracting
    supabase = get_supabase()
    supabase.table("projects").update({"status": "extracting"}).eq("id", project_id).execute()

    # Run the extraction command
    try:
        result = subprocess.run(
            [
                "python", "model_ai/manage.py",
                "extract",
                "--project-id", project_id,
            ],
            cwd=os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
            capture_output=True,
            text=True
        )

        if result.returncode != 0:
            print(f"[Pipeline] Extraction error: {result.stderr}")
            supabase.table("projects").update({
                "status": "failed",
                "error_message": f"Extraction failed: {result.stderr}"
            }).eq("id", project_id).execute()
            return False

        print(f"[Pipeline] Extraction completed")
        return True
    except Exception as e:
        print(f"[Pipeline] Extraction exception: {e}")
        supabase.table("projects").update({
            "status": "failed",
            "error_message": str(e)
        }).eq("id", project_id).execute()
        return False


async def run_docx_generation(project_id: str):
    """
    Run the DOCX generation pipeline.
    """
    print(f"[Pipeline] Starting DOCX generation for project {project_id}")

    # Update status to generating
    supabase = get_supabase()
    supabase.table("projects").update({"status": "generating"}).eq("id", project_id).execute()

    try:
        result = subprocess.run(
            [
                "python", "model_ai/manage.py",
                "docx",
                "--type", "proposal",
                "--project-id", project_id
            ],
            cwd=os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
            capture_output=True,
            text=True
        )

        if result.returncode != 0:
            print(f"[Pipeline] DOCX generation error: {result.stderr}")
            supabase.table("projects").update({
                "status": "failed",
                "error_message": f"DOCX generation failed: {result.stderr}"
            }).eq("id", project_id).execute()
            return False

        print(f"[Pipeline] DOCX generation completed")

        # Update status to completed
        ai_dir = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
        result_path = os.path.join(ai_dir, "model_ai", "data", project_id, "proposal_output.docx")
        result_url = f"ai-output-files/{project_id}/proposal_output.docx"

        supabase.table("projects").update({
            "status": "completed",
            "result_url": result_url
        }).eq("id", project_id).execute()

        return True
    except Exception as e:
        print(f"[Pipeline] DOCX generation exception: {e}")
        supabase.table("projects").update({
            "status": "failed",
            "error_message": str(e)
        }).eq("id", project_id).execute()
        return False


async def run_pipeline(project_id: str, source_url: str):
    """
    Run the complete pipeline: download -> setup -> extraction -> DOCX generation.
    """
    # Step 1: Download source file from storage
    try:
        await download_source_file(source_url, project_id)
    except Exception as e:
        print(f"[Pipeline] Download error: {e}")
        supabase = get_supabase()
        supabase.table("projects").update({
            "status": "failed",
            "error_message": f"Download failed: {str(e)}"
        }).eq("id", project_id).execute()
        return False

    # Step 2: Run setup (extract chunks + ingest)
    setup_success = await run_setup(project_id)
    if not setup_success:
        return False

    # Step 3: Run extraction
    extraction_success = await run_extraction(project_id, source_url)
    if not extraction_success:
        return False

    # Update status to extracted
    supabase = get_supabase()
    supabase.table("projects").update({"status": "extracted"}).eq("id", project_id).execute()

    # Step 4: Run DOCX generation
    docx_success = await run_docx_generation(project_id)

    return docx_success