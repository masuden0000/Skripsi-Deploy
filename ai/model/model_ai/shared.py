"""Konstanta domain dan utilitas yang digunakan bersama di seluruh model_ai."""
from supabase import Client, create_client

# ─── Domain ───────────────────────────────────────────────────────────────────

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

# ─── Embedding ────────────────────────────────────────────────────────────────

EMBEDDING_DIMENSION: int = 768

# 3 siklus × 30 detik = max 60 detik tunggu embedding → jauh di bawah 300s timeout subprocess
EMBED_MAX_RETRY_CYCLES: int = 3
EMBED_RATE_LIMIT_WAIT: int = 30  # detik; Google embedding reset per menit
EMBED_INTER_BATCH_DELAY: float = 2.0  # detik antar batch embedding (hindari burst)

# ─── LLM Rate-limit Interval ─────────────────────────────────────────────────

# Groq free: 12.000 TPM → ~3k token/panggilan → maks 4 panggilan/menit → 15 detik aman
GROQ_MIN_CALL_INTERVAL: float = 15.0
# Gemini 2.5 Flash free: 10 RPM → 1 panggilan per 6 detik → +1 detik buffer
GEMINI_MIN_CALL_INTERVAL: float = 7.0

# ─── Batch / Rate-limit Pause ─────────────────────────────────────────────────

BATCH_PAUSE_EVERY: int = 3
BATCH_PAUSE_SECONDS: int = 12  # detik; interval per-panggilan sudah ditangani di doc_extractor

# ─── Utilities ────────────────────────────────────────────────────────────────

def format_vector(values: list[float]) -> str:
    """Format embedding vector ke string PostgreSQL-compatible: [0.12345678,...]"""
    return "[" + ",".join(f"{v:.8f}" for v in values) + "]"


# ─── Supabase ─────────────────────────────────────────────────────────────────

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
