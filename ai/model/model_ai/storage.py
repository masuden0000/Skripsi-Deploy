"""Upload file DOCX ke Supabase Storage. Posisi pipeline: generator → storage (upload output akhir). Keyword: automated document generation"""
from model_ai.shared import get_supabase_client

BUCKET_OUTPUT = "ai-output-files"


def upload_docx_to_storage(file_bytes: bytes, file_name: str, project_id: str) -> str:
    """
    Upload DOCX bytes langsung ke Supabase Storage.
    Bucket dibuat via migration SQL — tidak perlu dibuat di sini.
    """
    client = get_supabase_client()

    storage_path = f"{project_id}/{file_name}"

    client.storage.from_(BUCKET_OUTPUT).upload(
        path=storage_path,
        file=file_bytes,
        file_options={
            "content-type": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            "x-upsert": "true",
        },
    )

    return client.storage.from_(BUCKET_OUTPUT).get_public_url(storage_path)