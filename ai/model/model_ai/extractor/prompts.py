"""Registry prompt yang memuat file markdown prompt menjadi PromptConfig siap pakai. Posisi pipeline: dipakai oleh doc_extractor."""
from dataclasses import dataclass
from pathlib import Path

import frontmatter as fm

from model_ai.shared import get_renderer_type

_PROMPTS_ROOT = Path(__file__).parent / "prompts"

_PROMPT_FILES = [
    "typography.md",
    "page_layout.md",
    "spacing.md",
    "document_structure_proposal.md",
    "numbering.md",
    "figures_and_tables.md",
    "page_count_limits.md",
]


@dataclass
class PromptConfig:
    queries: list[str]
    template: str
    top_k: int = 0
    section_focus: list[str] | None = None


def _load_from_dir(filename: str, folder: Path) -> PromptConfig:
    """Muat satu prompt dari file .md di folder yang ditentukan."""
    post = fm.load(str(folder / filename))
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


def load_prompts_for_skema(skema: str) -> dict[str, PromptConfig]:
    """Muat semua PromptConfig untuk skema yang diberikan.

    Type B (PKM-AI): kembalikan dict kosong — renderer-nya berbeda.
    Type A (semua lainnya): muat dari folder skema. Error jika folder kosong atau tidak ada.
    """
    if get_renderer_type(skema) == "B":
        return {}

    folder = _PROMPTS_ROOT / skema.upper()
    if not folder.is_dir() or not any(folder.glob("*.md")):
        raise FileNotFoundError(
            f"Prompt untuk skema '{skema}' belum tersedia. "
            f"Folder '{folder}' tidak ditemukan atau kosong."
        )

    result: dict[str, PromptConfig] = {}
    for filename in _PROMPT_FILES:
        if (folder / filename).exists():
            key = filename.removesuffix(".md")
            result[key] = _load_from_dir(filename, folder)
    return result


