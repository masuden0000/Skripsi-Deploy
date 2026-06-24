"""Shared Supabase client untuk ai-backend. Single source of truth untuk koneksi Supabase."""
import os
from pathlib import Path

from dotenv import load_dotenv
from supabase import Client, create_client

_AI_ROOT = Path(__file__).resolve().parent.parent.parent
load_dotenv(_AI_ROOT / ".env")
load_dotenv(Path(__file__).resolve().parent.parent / ".env", override=False)


def _require_env(name: str) -> str:
    value = os.getenv(name, "").strip()
    if not value:
        raise ValueError(f"{name} belum di-set di file ai/.env.")
    return value


SUPABASE_URL = _require_env("SUPABASE_URL")
SUPABASE_KEY = _require_env("SUPABASE_SERVICE_ROLE_KEY")

supabase_client: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
