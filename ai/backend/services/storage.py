"""
Fungsi: Wrapper Supabase Storage untuk ai-backend.

Digunakan oleh: routers/projects.py
Tujuan: Upload/download file DOCX proposal ke/dari bucket Supabase Storage.
  - ai-source-files : DOCX sumber yang diupload reviewer/admin (input pipeline)
  - ai-output-files : DOCX hasil generate AI (output pipeline)
"""
from ._supabase import supabase_client

BUCKET_SOURCE = "ai-source-files"
BUCKET_OUTPUT = "ai-output-files"


def get_supabase_client():
    return supabase_client


async def upload_file(bucket_name: str, file_content: bytes, file_name: str, project_id: str) -> str:
    """
    Upload file to Supabase Storage.
    Bucket dibuat via migration SQL — tidak perlu dibuat di sini.
    Returns the public URL of the uploaded file.
    """
    try:
        client = get_supabase_client()
        storage_path = f"{project_id}/{file_name}"
        try:
            client.storage.from_(bucket_name).upload(
                path=storage_path,
                file=file_content,
                file_options={"content-type": "application/octet-stream"}
            )
        except Exception as e:
            if "Duplicate" in str(e) or "already exists" in str(e):
                client.storage.from_(bucket_name).remove([storage_path])
                client.storage.from_(bucket_name).upload(
                    path=storage_path,
                    file=file_content,
                    file_options={"content-type": "application/octet-stream"}
                )
            else:
                raise
        public_url = client.storage.from_(bucket_name).get_public_url(storage_path)
        return public_url
    except Exception as e:
        raise Exception(f"Gagal upload file ke storage '{bucket_name}': {str(e)}")


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


async def delete_folder(bucket_name: str, folder_prefix: str) -> bool:
    """
    Delete all files under a folder prefix in a bucket.
    folder_prefix: e.g. "{project_id}/" — lists and removes every file inside.
    """
    try:
        client = get_supabase_client()
        files = client.storage.from_(bucket_name).list(folder_prefix)
        if files:
            paths = [f"{folder_prefix}/{f['name']}" for f in files]
            client.storage.from_(bucket_name).remove(paths)
        return True
    except Exception as e:
        print(f"Error deleting folder {folder_prefix}: {e}")
        return False


async def download_file(bucket_name: str, file_path: str) -> bytes:
    """
    Download file from Supabase Storage.
    Returns file content as bytes.
    """
    try:
        client = get_supabase_client()
        response = client.storage.from_(bucket_name).download(file_path)
        return response
    except Exception as e:
        raise Exception(f"Gagal download file '{file_path}' dari storage '{bucket_name}': {str(e)}")


async def get_signed_url(bucket_name: str, file_path: str, expires_in: int = 3600) -> str:
    """
    Get a signed URL for downloading a file.
    """
    try:
        client = get_supabase_client()
        response = client.storage.from_(bucket_name).create_signed_url(file_path, expires_in)
        return response["signedUrl"] if isinstance(response, dict) else response
    except Exception as e:
        raise Exception(f"Gagal membuat signed URL untuk '{file_path}': {str(e)}")
