"""
Fungsi: Registry prompt yang memuat file markdown prompt menjadi PromptConfig siap pakai.

Digunakan oleh: model_ai/extractor/doc_extractor.py

Tujuan: Menjadikan prompt sebagai source of truth terpusat, dipilih secara dinamis berdasarkan skema PKM.
"""
from dataclasses import dataclass
from pathlib import Path

import frontmatter as fm

_PROMPTS_DIR = Path(__file__).parent / "prompts"


@dataclass
class PromptConfig:
    queries: list[str]
    template: str
    top_k: int = 0  # 0 -> gunakan nilai RAG_TOP_K dari ai/.env


def _load(filename: str, skema_slug: str) -> PromptConfig:
    """Muat satu prompt dari subfolder prompts/{skema_slug}/{filename}."""
    path = _PROMPTS_DIR / skema_slug / filename
    post = fm.load(str(path))
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


def load_prompts(skema_slug: str) -> dict[str, PromptConfig]:
    """Load 7 prompt untuk satu skema dari subfolder prompts/{skema_slug}/."""
    return {
        "typography":         _load("typography.md", skema_slug),
        "page_layout":        _load("page_layout.md", skema_slug),
        "spacing":            _load("spacing.md", skema_slug),
        "document_structure": _load("document_structure.md", skema_slug),
        "numbering":          _load("numbering.md", skema_slug),
        "figures_and_tables": _load("figures_and_tables.md", skema_slug),
        "page_count_limits":  _load("page_count_limits.md", skema_slug),
    }
