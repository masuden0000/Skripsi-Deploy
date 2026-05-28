"""
Fungsi: Registry prompt yang memuat file markdown prompt menjadi PromptConfig siap pakai.

Digunakan oleh: model_ai/extractor/doc_extractor.py; model_ai/extractor/schema_differ.py

Tujuan: Menjadikan prompt sebagai source of truth terpusat agar extractor dan schema-diff konsisten.
"""
from dataclasses import dataclass
from pathlib import Path

import frontmatter as fm

# ---------------------------------------------------------------------------
# Digunakan oleh: Dipakai oleh fungsi-fungsi di modul ini dan modul terkait saat import runtime.
# Blok konstanta `_PROMPTS_DIR` untuk menyimpan konfigurasi/registry yang dipakai berulang.
# ---------------------------------------------------------------------------
_PROMPTS_DIR = Path(__file__).parent / "prompts"


# ---------------------------------------------------------------------------
# Digunakan oleh: model_ai/extractor/doc_extractor.py
# Mendefinisikan class `PromptConfig` untuk kebutuhan modul `prompts`.
# ---------------------------------------------------------------------------
@dataclass
class PromptConfig:
    queries: list[str]
    template: str
    top_k: int = 0  # 0 -> gunakan nilai RAG_TOP_K dari ai/.env


# ---------------------------------------------------------------------------
# Digunakan oleh: Dipakai internal di file ini atau dipanggil dari entrypoint runtime.
# Menjalankan fungsi `_load` sebagai bagian alur `prompts`.
# ---------------------------------------------------------------------------
def _load(filename: str) -> PromptConfig:
    """Muat satu prompt dari file .md di folder prompts/."""
    post = fm.load(str(_PROMPTS_DIR / filename))
    meta: dict[str, object] = post.metadata  # type: ignore[assignment]

    if "queries" in meta:
        raw = meta["queries"]
        queries: list[str] = [str(raw)] if isinstance(raw, str) else [str(q) for q in raw]  # type: ignore[union-attr]
    elif "query" in meta:
        queries = [str(meta["query"])]
    else:
        raise ValueError(f"{filename} wajib punya field 'query' atau 'queries'.")

    return PromptConfig(
        queries=queries,
        template=str(post.content),
        top_k=int(meta.get("top_k", 0)),  # type: ignore[arg-type]
    )


# ---------------------------------------------------------------------------
# Digunakan oleh: KEY_REGISTRY → _extract_key() di doc_extractor.py
# ---------------------------------------------------------------------------
TYPOGRAPHY = _load("typography.md")
PAGE_LAYOUT = _load("page_layout.md")
SPACING = _load("spacing.md")
DOCUMENT_STRUCTURE_PROPOSAL = _load("document_structure_proposal.md")
# ---------------------------------------------------------------------------
# Digunakan oleh: Dipakai oleh fungsi-fungsi di modul ini dan modul terkait saat import runtime.
# Blok konstanta `NUMBERING` untuk menyimpan konfigurasi/registry yang dipakai berulang.
# ---------------------------------------------------------------------------
NUMBERING = _load("numbering.md")
# ---------------------------------------------------------------------------
# Digunakan oleh: Dipakai oleh fungsi-fungsi di modul ini dan modul terkait saat import runtime.
# Blok konstanta `FIGURES_AND_TABLES` untuk menyimpan konfigurasi/registry yang dipakai berulang.
# ---------------------------------------------------------------------------
FIGURES_AND_TABLES = _load("figures_and_tables.md")
# ---------------------------------------------------------------------------
# Digunakan oleh: Dipakai oleh fungsi-fungsi di modul ini dan modul terkait saat import runtime.
# Blok konstanta `PAGE_COUNT_LIMITS` untuk menyimpan konfigurasi/registry yang dipakai berulang.
# ---------------------------------------------------------------------------
PAGE_COUNT_LIMITS = _load("page_count_limits.md")

# ---------------------------------------------------------------------------
# Digunakan oleh: _extract_document_type() di doc_extractor.py
# top_k=3 sengaja override global — identifikasi jenis dokumen cukup
# dari beberapa chunk header, tidak perlu konteks panjang.
# ---------------------------------------------------------------------------
DOCUMENT_TYPE = _load("document_type.md")

# ---------------------------------------------------------------------------
# Digunakan oleh: free_extract_all_rules() di schema_differ.py
# Prompt untuk ekstraksi bebas semua aturan dokumen tanpa batasan schema.
# ---------------------------------------------------------------------------
FREE_EXTRACTION = _load("free_extraction.md")
