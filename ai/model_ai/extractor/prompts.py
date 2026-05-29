"""Registry prompt yang memuat file markdown prompt menjadi PromptConfig siap pakai. Posisi pipeline: dipakai oleh doc_extractor."""
from dataclasses import dataclass
from pathlib import Path

import frontmatter as fm

_PROMPTS_DIR = Path(__file__).parent / "prompts"


@dataclass
class PromptConfig:
    queries: list[str]
    template: str
    top_k: int = 0
    section_focus: list[str] | None = None


def _load(filename: str) -> PromptConfig:
    """Muat satu prompt dari file .md di folder prompts/."""
    post = fm.load(str(_PROMPTS_DIR / filename))
    meta: dict[str, object] = post.metadata

    if "queries" in meta:
        raw = meta["queries"]
        queries: list[str] = [str(raw)] if isinstance(raw, str) else [str(q) for q in raw]
    elif "query" in meta:
        queries = [str(meta["query"])]
    else:
        raise ValueError(f"{filename} wajib punya field 'query' atau 'queries'.")

    raw_focus = meta.get("section_focus")
    if raw_focus is None:
        section_focus: list[str] | None = None
    elif isinstance(raw_focus, str):
        section_focus = [raw_focus]
    else:
        section_focus = [str(f) for f in raw_focus]

    return PromptConfig(
        queries=queries,
        template=str(post.content),
        top_k=int(meta.get("top_k", 0)),
        section_focus=section_focus,
    )


TYPOGRAPHY = _load("typography.md")
PAGE_LAYOUT = _load("page_layout.md")
SPACING = _load("spacing.md")
DOCUMENT_STRUCTURE_PROPOSAL = _load("document_structure_proposal.md")
NUMBERING = _load("numbering.md")
FIGURES_AND_TABLES = _load("figures_and_tables.md")
PAGE_COUNT_LIMITS = _load("page_count_limits.md")

DOCUMENT_TYPE = _load("document_type.md")
