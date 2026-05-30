"""
Fungsi: Wrapper Supabase Storage untuk ai-backend.

Digunakan oleh: routers/projects.py
Tujuan: Upload/download file DOCX proposal ke/dari bucket Supabase Storage.
  - ai-source-files : DOCX sumber yang diupload reviewer/admin (input pipeline)
  - ai-output-files : DOCX hasil generate AI (output pipeline)
"""
import os
from supabase import create_client
from dotenv import load_dotenv

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL", "")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "")

BUCKET_SOURCE = "ai-source-files"
BUCKET_OUTPUT = "ai-output-files"


def get_supabase_client():
    return create_client(SUPABASE_URL, SUPABASE_KEY)


async def upload_file(bucket_name: str, file_content: bytes, file_name: str, project_id: str) -> str:
    """
    Upload file to Supabase Storage.
    Bucket dibuat via migration SQL — tidak perlu dibuat di sini.
    Returns the public URL of the uploaded file.
    """
    client = get_supabase_client()

    storage_path = f"{project_id}/{file_name}"

    client.storage.from_(bucket_name).upload(
        path=storage_path,
        file=file_content,
        file_options={"content-type": "application/octet-stream"}
    )

    public_url = client.storage.from_(bucket_name).get_public_url(storage_path)

    return public_url


async def delete_file(bucket_name: str, file_path: str) -> bool:
    """
    Delete file from Supabase Storage.
    """
    try:
        client = get_supabase_client()
        client.storage.from_(bucket_name).remove([file_path])
        return True
    except Exception as e:
        print(f"Error deleting file: {e}")
        return False


async def create_signed_upload_url(bucket_name: str, file_path: str) -> dict:
    """
    Generate signed URL for direct upload to Supabase Storage.
    Returns dict with 'signedUrl' and 'token' for frontend upload.
    """
    client = get_supabase_client()
    try:
        result = client.storage.from_(bucket_name).create_signed_upload_url(file_path)
    except Exception as e:
        # Jika file sudah ada (Duplicate), hapus lalu coba lagi
        if "Duplicate" in str(e) or "already exists" in str(e):
            client.storage.from_(bucket_name).remove([file_path])
            result = client.storage.from_(bucket_name).create_signed_upload_url(file_path)
        else:
            raise
    return dict(result)


async def download_file(bucket_name: str, file_path: str) -> bytes:
    """
    Download file from Supabase Storage.
    Returns file content as bytes.
    """
    client = get_supabase_client()
    response = client.storage.from_(bucket_name).download(file_path)
    return response


async def get_signed_url(bucket_name: str, file_path: str, expires_in: int = 3600) -> str:
    """
    Get a signed URL for downloading a file.
    """
    client = get_supabase_client()
    response = client.storage.from_(bucket_name).create_signed_url(file_path, expires_in)
    return response["signedUrl"] if isinstance(response, dict) else response
