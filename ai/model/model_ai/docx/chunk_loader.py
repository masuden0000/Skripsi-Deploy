"""Memuat dan menormalkan data chunk dari Supabase sebagai sumber isi DOCX. Posisi pipeline: metadata_repository → chunk_loader → generator → docx_renderer. Keyword: automated document generation"""
import re
from dataclasses import dataclass

from model_ai.shared import get_supabase_client


@dataclass(frozen=True)
class ChunkSource:
    chunk_parent: str
    page_start: int | None
    page_end: int | None
    content: str


def load_chunk_sources(project_id: str) -> list[ChunkSource]:
    """
    Load chunks dari Supabase document_chunks table.
    Menggantikan load dari file lokal output_chunks.json.
    """
    client = get_supabase_client()

    result = client.table("document_chunks").select(
        "chunk_parent, page_start, page_end, content"
    ).eq("project_id", project_id).execute()

    if not result.data:
        raise FileNotFoundError(
            f"Tidak ada chunk di Supabase untuk project_id: {project_id}"
        )

    sources: list[ChunkSource] = []
    for item in result.data:
        parent = str(item.get("chunk_parent") or "").strip()
        content = str(item.get("content") or "").strip()
        raw_start = item.get("page_start")
        raw_end = item.get("page_end")
        start = int(raw_start) if raw_start is not None else None
        end = int(raw_end) if raw_end is not None else start
        if not parent:
            continue
        sources.append(ChunkSource(
            chunk_parent=parent,
            page_start=start,
            page_end=end,
            content=content,
        ))
    return sources


def format_source_line(source: ChunkSource) -> str:
    return (
        f"Sumber: Hal. {source.page_start}-{source.page_end} | "
        f"Header: {source.chunk_parent}"
    )


def match_sources_for_section(
    chunks: list[ChunkSource],
    section_label: str,
    section_title: str | None = None,
    limit: int = 6,
) -> list[ChunkSource]:
    norm_label = _normalize_text(section_label)
    norm_title = _normalize_text(section_title or "")
    title_tokens = set(_tokenize(norm_title))

    scored: list[tuple[int, ChunkSource]] = []
    for chunk in chunks:
        score = _score_chunk(chunk, norm_label, norm_title, title_tokens)
        if score > 0:
            scored.append((score, chunk))

    scored.sort(
        key=lambda item: (
            -item[0],
            item[1].page_start if item[1].page_start is not None else float("inf"),
            item[1].page_end if item[1].page_end is not None else float("inf"),
            item[1].chunk_parent,
        )
    )

    unique: list[ChunkSource] = []
    seen: set[tuple[int, int, str]] = set()
    for _, source in scored:
        dedupe_key = (source.page_start, source.page_end, source.chunk_parent)
        if dedupe_key in seen:
            continue
        seen.add(dedupe_key)
        unique.append(source)
        if len(unique) >= limit:
            break
    return unique


def _score_chunk(
    chunk: ChunkSource,
    norm_label: str,
    norm_title: str,
    title_tokens: set[str],
) -> int:
    header = _normalize_text(chunk.chunk_parent)
    content = _normalize_text(chunk.content)

    score = 0
    if norm_label and norm_label in header:
        score += 12
    elif norm_label and norm_label in content:
        score += 6

    if norm_title and norm_title in header:
        score += 10
    elif norm_title and norm_title in content:
        score += 5

    if title_tokens:
        header_tokens = set(_tokenize(header))
        token_overlap = len(title_tokens.intersection(header_tokens))
        score += token_overlap * 2

    return score


def _normalize_text(value: str) -> str:
    value = value.lower()
    value = re.sub(r"[^a-z0-9\s]", " ", value)
    return " ".join(value.split())


def _tokenize(value: str) -> list[str]:
    if not value:
        return []
    return [token for token in value.split() if token]
