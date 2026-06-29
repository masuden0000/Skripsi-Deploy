"""Konstanta domain dan utilitas yang digunakan bersama di seluruh model_ai."""
from supabase import Client, create_client


_SKEMA_TYPE_B: frozenset[str] = frozenset({"PKM-AI"})

EXCLUDED_PARENTS: frozenset[str] = frozenset({
    "DAFTAR ISI",
    "DAFTAR GAMBAR",
    "DAFTAR TABEL",
    "DAFTAR LAMPIRAN",
    "DAFTAR PUSTAKA",
})

TOC_SECTION_DENYLIST: frozenset[str] = frozenset({
    "DAFTAR PUSTAKA",
    "DAFTAR GAMBAR",
    "DAFTAR TABEL",
    "DAFTAR LAMPIRAN",
})


EMBEDDING_DIMENSION: int = 768

EMBED_MAX_RETRY_CYCLES: int = 3
EMBED_RATE_LIMIT_WAIT: int = 60
EMBED_INTER_BATCH_DELAY: float = 2.0


GROQ_MIN_CALL_INTERVAL: float = 15.0
GEMINI_MIN_CALL_INTERVAL: float = 7.0


BATCH_PAUSE_EVERY: int = 3
BATCH_PAUSE_SECONDS: int = 12


def format_vector(values: list[float]) -> str:
    """Format embedding vector ke string PostgreSQL-compatible: [0.12345678,...]"""
    return "[" + ",".join(f"{v:.8f}" for v in values) + "]"



def get_supabase_client() -> Client:
    """Buat dan kembalikan Supabase client menggunakan konfigurasi aktif."""
    from model_ai.config import get_config
    config = get_config()
    return create_client(
        config.supabase_url,
        config.supabase_service_role_key.get_secret_value(),
    )


def is_type_b(skema: str) -> bool:
    """Kembalikan True jika skema menggunakan renderer Type B (artikel ilmiah PKM-AI)."""
    return skema.upper() in _SKEMA_TYPE_B
