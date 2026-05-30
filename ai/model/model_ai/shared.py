"""Konstanta domain dan utilitas yang digunakan bersama di seluruh model_ai."""

# ─── Domain ───────────────────────────────────────────────────────────────────

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

EMBED_MAX_RETRY_CYCLES: int = 5
EMBED_RATE_LIMIT_WAIT: int = 60  # detik

# ─── Batch / Rate-limit Pause ─────────────────────────────────────────────────

BATCH_PAUSE_EVERY: int = 2
BATCH_PAUSE_SECONDS: int = 30  # detik

# ─── Utilities ────────────────────────────────────────────────────────────────

def format_vector(values: list[float]) -> str:
    """Format embedding vector ke string PostgreSQL-compatible: [0.12345678,...]"""
    return "[" + ",".join(f"{v:.8f}" for v in values) + "]"
