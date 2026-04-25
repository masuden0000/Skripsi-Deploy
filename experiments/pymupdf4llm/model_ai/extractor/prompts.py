"""Registry prompt untuk pipeline ekstraksi dokumen PKM.

Source of truth ada di file .md dalam folder prompts/ — edit di sana
untuk mengubah konten prompt, query, atau top_k.

File ini hanya memuat setiap .md dan mengeksposnya sebagai PromptConfig
agar doc_extractor.py bisa mengimport tanpa tahu detail path atau format.

Cara menambah prompt baru:
  1. Buat file .md di folder prompts/ dengan frontmatter query/queries dan top_k (opsional)
  2. Tambahkan baris _load("nama_file.md") di bawah dengan komentar penggunaannya
"""

from dataclasses import dataclass
from pathlib import Path

import frontmatter as fm

_PROMPTS_DIR = Path(__file__).parent / "prompts"


@dataclass
class PromptConfig:
    queries: list[str]
    template: str
    top_k: int = 0  # 0 → gunakan nilai RAG_TOP_K dari .env


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
DOCUMENT_STRUCTURE_LAPORAN_KEMAJUAN = _load("document_structure_laporan_kemajuan.md")
DOCUMENT_STRUCTURE_LAPORAN_AKHIR = _load("document_structure_laporan_akhir.md")
NUMBERING = _load("numbering.md")
FIGURES_AND_TABLES = _load("figures_and_tables.md")
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
