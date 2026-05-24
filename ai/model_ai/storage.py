"""
Fungsi: Upload dan download file ke/dari Supabase Storage.
Digunakan oleh: model_ai/docx/generator.py, manage.py
Tujuan: Langsung stream file ke/dari Supabase Storage tanpa menyimpan ke filesystem lokal.
Keyword: automated document generation
"""
from pathlib import Path

from supabase import create_client
from model_ai.config import get_config

BUCKET_OUTPUT = "ai-output-files"
BUCKET_SOURCE = "ai-source-files"


def upload_docx_to_storage(file_bytes: bytes, file_name: str, project_id: str) -> str:
    """
    Upload DOCX bytes langsung ke Supabase Storage.
    Bucket dibuat via migration SQL — tidak perlu dibuat di sini.
    """
    config = get_config()
    client = create_client(config.supabase_url, config.supabase_service_role_key.get_secret_value())

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


def download_source_pdf(project_id: str, dest_path: Path) -> None:
    """
    Download source.pdf dari Supabase Storage bucket ai-source-files
    ke dest_path lokal. Dipakai oleh run_setup() sebelum chunking.
    """
    config = get_config()
    client = create_client(config.supabase_url, config.supabase_service_role_key.get_secret_value())

    storage_path = f"{project_id}/source.pdf"
    file_bytes: bytes = client.storage.from_(BUCKET_SOURCE).download(storage_path)

    dest_path.parent.mkdir(parents=True, exist_ok=True)
    dest_path.write_bytes(file_bytes)
