"""
Fungsi: Orkestrator pipeline AI untuk pembuatan DOCX proposal PKM secara otomatis.

Digunakan oleh: routers/projects.py (dijalankan sebagai background task)

Tujuan: Mengeksekusi 4 langkah pipeline secara berurutan —
  run_setup → run_extraction → generate-placeholders → run_docx_pipeline —
  masing-masing sebagai subprocess ke ai/manage.py.

Keyword: automated document generation
"""
import asyncio
import os
import shutil
import sys
from pathlib import Path
from typing import Sequence

from .database import get_supabase
from .storage import download_file

BUCKET_SOURCE = "ai-source-files"
BUCKET_OUTPUT = "ai-output-files"

# Root of the ai/ service (parent of backend/)
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
# Model directory (where manage.py and model_ai/ live)
AI_DIR = os.path.join(PROJECT_ROOT, "model")
AI_PATH = Path(AI_DIR)

PROJECT_LOGS_ENABLED = True


def log_console(step: str, message: str) -> None:
    """Print log message to console immediately."""
    print(f"[{step.upper()}] {message}", flush=True)


def persist_project_log(project_id: str, step: str, message: str) -> None:
    """Persist log lines so the frontend SSE log panel can stream them."""
    global PROJECT_LOGS_ENABLED

    if not PROJECT_LOGS_ENABLED:
        return

    try:
        supabase = get_supabase()
        supabase.table("project_logs").insert({
            "project_id": project_id,
            "step": step,
            "message": message,
        }).execute()
    except Exception as exc:
        PROJECT_LOGS_ENABLED = False
        log_console("log", f"Warning: gagal simpan project log, streaming frontend dimatikan: {exc}")


def log_event(step: str, message: str, project_id: str | None = None) -> None:
    """Write the same log line to terminal and optional project log storage."""
    cleaned_message = message.strip()
    if not cleaned_message:
        return

    log_console(step, cleaned_message)
    if project_id:
        persist_project_log(project_id, step, cleaned_message)


async def stream_manage_command(
    step: str,
    command: Sequence[str],
    project_id: str,
    timeout_seconds: int,
) -> tuple[bool, str]:
    """Run manage.py and stream stdout/stderr live to terminal and project_logs."""
    env = os.environ.copy()
    env["PYTHONUNBUFFERED"] = "1"
    env["PYTHONIOENCODING"] = "utf-8"

    process = await asyncio.create_subprocess_exec(
        *command,
        cwd=AI_DIR,
        env=env,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )

    stdout_lines: list[str] = []
    stderr_lines: list[str] = []

    async def read_stream(
        stream: asyncio.StreamReader | None,
        is_stderr: bool = False,
    ) -> None:
        if stream is None:
            return

        while True:
            raw_line = await stream.readline()
            if not raw_line:
                break

            line = raw_line.decode(errors="replace").rstrip()
            if not line:
                continue

            if is_stderr:
                stderr_lines.append(line)
                log_event(step, f"[stderr] {line}", project_id)
            else:
                stdout_lines.append(line)
                log_event(step, line, project_id)

    stdout_task = asyncio.create_task(read_stream(process.stdout))
    stderr_task = asyncio.create_task(read_stream(process.stderr, is_stderr=True))

    try:
        return_code = await asyncio.wait_for(process.wait(), timeout=timeout_seconds)
    except asyncio.TimeoutError:
        process.kill()
        await process.wait()
        await asyncio.gather(stdout_task, stderr_task, return_exceptions=True)
        return False, f"Timeout setelah {timeout_seconds} detik"

    await asyncio.gather(stdout_task, stderr_task)

    if return_code != 0:
        error_output = stderr_lines[-1] if stderr_lines else ""
        if not error_output and stdout_lines:
            error_output = stdout_lines[-1]
        if not error_output:
            error_output = f"Command exited with code {return_code}"
        return False, error_output

    return True, "\n".join(stdout_lines)


async def download_source_file(source_url: str, project_id: str, source_file: str) -> str:
    """
    Download the source file from Supabase Storage to the local ai/data/{project_id} directory.
    The downloaded file is normalized to source.pdf so the downstream AI pipeline keeps working.
    """
    project_dir = AI_PATH / "data" / project_id
    project_dir.mkdir(parents=True, exist_ok=True)

    local_path = project_dir / "source.pdf"
    storage_path = f"{project_id}/{source_file}"

    log_event("download", f"Mendownload file dari storage: {source_url}", project_id)
    file_content = await download_file(BUCKET_SOURCE, storage_path)
    local_path.write_bytes(file_content)

    log_event("download", f"File disimpan ke: {local_path}", project_id)
    return str(local_path)


async def run_setup(project_id: str) -> bool:
    """
    Run the setup pipeline (extract chunks + ingest to Supabase).
    """
    log_event("setup", "Memulai setup pipeline...", project_id)

    try:
        supabase = get_supabase()
        supabase.table("projects").update({
            "status": "uploading",
            "error_message": None,
        }).eq("id", project_id).execute()
    except Exception as exc:
        log_event("setup", f"Warning: Gagal update status: {exc}", project_id)

    command = [sys.executable, "manage.py", "setup", "--project-id", project_id]
    log_event("setup", f"Menjalankan: {' '.join(command)}", project_id)

    success, error_message = await stream_manage_command(
        step="setup",
        command=command,
        project_id=project_id,
        timeout_seconds=300,
    )

    if not success:
        log_event("setup", f"ERROR: Setup gagal - {error_message}", project_id)
        try:
            supabase = get_supabase()
            supabase.table("projects").update({
                "status": "failed",
                "error_message": f"Setup failed: {error_message[:200]}",
            }).eq("id", project_id).execute()
        except Exception:
            pass
        return False

    log_event("setup", "Setup selesai.", project_id)
    return True


def _get_project_skema(project_id: str) -> str:
    """Ambil nilai skema dari tabel projects berdasarkan project_id."""
    try:
        supabase = get_supabase()
        result = supabase.table("projects").select("skema").eq("id", project_id).single().execute()
        return (result.data or {}).get("skema") or "PKM-KC"
    except Exception as exc:
        log_console("pipeline", f"Warning: Gagal baca skema dari DB, pakai default PKM-KC: {exc}")
        return "PKM-KC"


async def run_extraction(project_id: str, skema: str = "PKM-KC") -> bool:
    """
    Run the AI extraction pipeline (extract metadata from chunks).
    """
    log_event("extraction", f"Memulai ekstraksi metadata (skema: {skema})...", project_id)

    supabase = get_supabase()
    try:
        supabase.table("projects").update({
            "status": "extracting",
            "error_message": None,
        }).eq("id", project_id).execute()
    except Exception as exc:
        log_event("extraction", f"Warning: Gagal update status: {exc}", project_id)

    command = [
        sys.executable, "manage.py", "extract",
        "--project-id", project_id,
        "--skema", skema,
    ]
    log_event("extraction", f"Menjalankan: {' '.join(command)}", project_id)

    success, error_message = await stream_manage_command(
        step="extraction",
        command=command,
        project_id=project_id,
        timeout_seconds=1800,
    )

    if not success:
        log_event("extraction", f"ERROR: Ekstraksi gagal - {error_message}", project_id)
        try:
            supabase = get_supabase()
            supabase.table("projects").update({
                "status": "failed",
                "error_message": f"Extraction failed: {error_message[:200]}",
            }).eq("id", project_id).execute()
        except Exception:
            pass
        return False

    log_event("extraction", "Ekstraksi selesai.", project_id)
    return True


async def run_docx_generation(project_id: str, skema: str = "PKM-KC") -> bool:
    """
    Run DOCX generation. manage.py handles upload ke Supabase Storage langsung.
    Pipeline backend hanya perlu parse RESULT_URL dari stdout.
    """
    log_event("docx", f"Memulai generate DOCX (skema: {skema})...", project_id)

    try:
        supabase = get_supabase()
        supabase.table("projects").update({
            "status": "generating",
            "error_message": None,
        }).eq("id", project_id).execute()
    except Exception as exc:
        log_event("docx", f"Warning: Gagal update status: {exc}", project_id)

    command = [
        sys.executable,
        "manage.py",
        "docx",
        "--type",
        "proposal",
        "--project-id",
        project_id,
        "--skema",
        skema,
    ]
    log_event("docx", f"Menjalankan: {' '.join(command)}", project_id)

    success, error_message = await stream_manage_command(
        step="docx",
        command=command,
        project_id=project_id,
        timeout_seconds=600,
    )

    if not success:
        log_event("docx", f"ERROR: DOCX generation gagal - {error_message}", project_id)
        try:
            supabase = get_supabase()
            supabase.table("projects").update({
                "status": "failed",
                "error_message": f"DOCX generation failed: {error_message[:200]}",
            }).eq("id", project_id).execute()
        except Exception:
            pass
        return False

    # Parse RESULT_URL from manage.py stdout
    result_url = None
    for line in error_message.splitlines():
        if "RESULT_URL=" in line:
            result_url = line.split("RESULT_URL=", 1)[1].strip()
            break

    if not result_url:
        log_event("docx", "ERROR: RESULT_URL tidak ditemukan di output manage.py", project_id)
        try:
            supabase = get_supabase()
            supabase.table("projects").update({
                "status": "failed",
                "error_message": "RESULT_URL tidak ditemukan di output.",
            }).eq("id", project_id).execute()
        except Exception:
            pass
        return False

    log_event("docx", f"Output uploaded ke storage: {result_url}", project_id)

    try:
        supabase = get_supabase()
        supabase.table("projects").update({
            "status": "completed",
            "result_url": result_url,
        }).eq("id", project_id).execute()
    except Exception:
        pass

    log_event("docx", "DOCX generation selesai.", project_id)
    return True


async def run_pipeline(project_id: str, source_url: str, source_file: str) -> bool:
    """
    Run extraction pipeline: download -> setup -> extraction.
    Stops at 'extracted' status — DOCX generation is triggered separately via /generate endpoint.
    """
    log_event("pipeline", "=" * 60, project_id)
    log_event("pipeline", f"MULAI PIPELINE untuk project: {project_id}", project_id)
    log_event("pipeline", "=" * 60, project_id)

    # Baca skema dari DB sebelum memulai pipeline
    skema = _get_project_skema(project_id)
    log_event("pipeline", f"Skema PKM terdeteksi: {skema}", project_id)

    # Step 1: Download source file from storage
    try:
        log_event("pipeline", "Step 1/3: Download file dari Supabase Storage...", project_id)
        await download_source_file(source_url, project_id, source_file)
        log_event("pipeline", "Step 1/3: Download selesai.", project_id)
    except Exception as exc:
        log_event("pipeline", f"ERROR Step 1: Download gagal - {exc}", project_id)
        try:
            supabase = get_supabase()
            supabase.table("projects").update({
                "status": "failed",
                "error_message": f"Download failed: {str(exc)[:200]}",
            }).eq("id", project_id).execute()
        except Exception:
            pass
        return False

    # Step 2: Run setup (extract chunks + ingest)
    log_event("pipeline", "Step 2/3: Setup (chunk extraction + ingest)...", project_id)
    setup_success = await run_setup(project_id)
    if not setup_success:
        log_event("pipeline", "Pipeline berhenti karena setup gagal.", project_id)
        return False
    log_event("pipeline", "Step 2/3: Setup selesai.", project_id)

    # Step 3: Run extraction
    log_event("pipeline", "Step 3/3: Ekstraksi metadata (RAG + LLM)...", project_id)
    extraction_success = await run_extraction(project_id, skema=skema)
    if not extraction_success:
        log_event("pipeline", "Pipeline berhenti karena ekstraksi gagal.", project_id)
        return False
    log_event("pipeline", "Step 3/3: Ekstraksi selesai.", project_id)

    # Step 4: Generate placeholder hints (LLM) dan simpan ke DB
    log_event("pipeline", "Step 4/4: Generate instructional placeholder...", project_id)
    command_ph = [
        sys.executable, "manage.py", "generate-placeholders",
        "--project-id", project_id,
        "--skema", skema,
    ]
    ph_success, ph_error = await stream_manage_command(
        step="placeholder",
        command=command_ph,
        project_id=project_id,
        timeout_seconds=600,
    )
    if not ph_success:
        log_event("pipeline", f"WARNING: Generate placeholder gagal: {ph_error}. Lanjut ke konfirmasi user.", project_id)
    else:
        log_event("pipeline", "Step 4/4: Placeholder tersimpan ke DB.", project_id)

    # Mark as extracted — user reviews and confirms before DOCX generation
    try:
        supabase = get_supabase()
        supabase.table("projects").update({"status": "extracted"}).eq("id", project_id).execute()
    except Exception:
        pass

    log_event("pipeline", "Ekstraksi selesai. Menunggu konfirmasi user untuk generate dokumen.", project_id)
    return True


async def run_docx_pipeline(project_id: str) -> bool:
    """
    Run DOCX generation and cleanup. Called after user confirms extraction results.
    """
    log_event("pipeline", "=" * 60, project_id)
    log_event("pipeline", f"MULAI GENERATE DOCX untuk project: {project_id}", project_id)
    log_event("pipeline", "=" * 60, project_id)

    skema = _get_project_skema(project_id)
    log_event("pipeline", f"Skema PKM terdeteksi: {skema}", project_id)

    docx_success = await run_docx_generation(project_id, skema=skema)
    if docx_success:
        log_event("pipeline", "=" * 60, project_id)
        log_event("pipeline", "DOCX GENERATION SELESAI BERHASIL!", project_id)
        log_event("pipeline", "=" * 60, project_id)
    else:
        log_event("pipeline", "DOCX generation gagal.", project_id)

    _cleanup_project_data(project_id)
    return docx_success


def _cleanup_project_data(project_id: str) -> None:
    project_dir = AI_PATH / "data" / project_id
    if project_dir.exists():
        try:
            shutil.rmtree(project_dir)
            log_event("cleanup", f"Folder lokal dihapus: {project_dir}", project_id)
        except Exception as exc:
            log_event("cleanup", f"Warning: Gagal hapus folder lokal - {exc}", project_id)
