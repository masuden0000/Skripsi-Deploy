"""
Fungsi: Upload file ke Supabase Storage.

Digunakan oleh: model_ai/docx/generator.py

Tujuan: Langsung stream DOCX ke Supabase Storage tanpa menyimpan ke filesystem lokal.
"""
from supabase import create_client
from model_ai.config import get_config

BUCKET_OUTPUT = "ai-output-files"


def _ensure_bucket(client, bucket_name: str) -> None:
    """Buat bucket jika belum ada, atau update agar public jika sudah ada."""
    try:
        buckets = client.storage.list_buckets()
        bucket_names = [b.name for b in buckets]
        if bucket_name not in bucket_names:
            client.storage.create_bucket(
                id=bucket_name,
                name=bucket_name,
                options={"public": True, "file_size_limit": 104857600},
            )
            print(f"[Storage] Created bucket: {bucket_name}")
        else:
            client.storage.update_bucket(bucket_name, {"public": True})
            print(f"[Storage] Updated bucket to public: {bucket_name}")
    except Exception as e:
        print(f"[Storage] Warning: Could not ensure bucket {bucket_name}: {e}")


def upload_docx_to_storage(file_bytes: bytes, file_name: str, project_id: str) -> str:
    """
    Upload DOCX bytes langsung ke Supabase Storage.
    Menggantikan penyimpanan ke filesystem lokal.
    """
    config = get_config()
    client = create_client(config.supabase_url, config.supabase_service_role_key.get_secret_value())

    _ensure_bucket(client, BUCKET_OUTPUT)

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