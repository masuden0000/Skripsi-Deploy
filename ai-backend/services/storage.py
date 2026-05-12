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


def ensure_bucket_exists_and_public(bucket_name: str) -> None:
    """
    Ensure bucket exists and is public.
    Creates the bucket if it doesn't exist, or updates it to public if it exists.
    """
    client = get_supabase_client()

    try:
        buckets = client.storage.list_buckets()
        bucket_names = [b.name for b in buckets]

        if bucket_name not in bucket_names:
            # Create new bucket as public
            client.storage.create_bucket(
                id=bucket_name,
                name=bucket_name,
                options={"public": True, "file_size_limit": 104857600}
            )
            print(f"[Storage] Created bucket: {bucket_name}")
        else:
            # Update existing bucket to be public
            client.storage.update_bucket(bucket_name, {"public": True})
            print(f"[Storage] Updated bucket to public: {bucket_name}")
    except Exception as e:
        print(f"[Storage] Warning: Could not ensure bucket {bucket_name}: {e}")


async def upload_file(bucket_name: str, file_content: bytes, file_name: str, project_id: str) -> str:
    """
    Upload file to Supabase Storage.
    Returns the public URL of the uploaded file.
    """
    client = get_supabase_client()

    # Ensure bucket exists and is public before upload
    ensure_bucket_exists_and_public(bucket_name)

    # Create folder structure: {bucket}/{project_id}/{file_name}
    storage_path = f"{project_id}/{file_name}"

    # Upload the file
    client.storage.from_(bucket_name).upload(
        path=storage_path,
        file=file_content,
        file_options={"content-type": "application/octet-stream"}
    )

    # Get public URL
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
    ensure_bucket_exists_and_public(bucket_name)
    result = client.storage.from_(bucket_name).create_signed_upload_url(file_path)
    # TypedDict uses bracket notation - convert to regular dict
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
    # create_signed_url returns dict with 'signedUrl' key
    return response["signedUrl"] if isinstance(response, dict) else response
