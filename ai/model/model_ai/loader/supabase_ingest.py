"""Mengirim chunk dan metadata ke Supabase untuk retrieval RAG. Posisi pipeline: chunk_builder → supabase_ingest → doc_extractor."""
import json
import time
from pathlib import Path

from langchain_google_genai import GoogleGenerativeAIEmbeddings
from pydantic import BaseModel
from supabase import Client

from model_ai.config import get_config
from model_ai.shared import (
    EMBED_INTER_BATCH_DELAY,
    EMBED_MAX_RETRY_CYCLES,
    EMBED_RATE_LIMIT_WAIT,
    EMBEDDING_DIMENSION,
    format_vector,
    get_supabase_client,
)

APP_DIR = Path(__file__).resolve().parents[2]
CONFIG = get_config()
EMBEDDING_MODEL_NAME = CONFIG.embedding_model_name
BATCH_SIZE = 20


def get_chunks_file(project_id: str) -> Path:
    return APP_DIR / "data" / project_id / "output_chunks.json"


class PageRange(BaseModel):
    start: int | None
    end: int | None


class ChunkRecord(BaseModel):
    chunk_index: int
    content: str
    chunk_parent: str
    chunk_prev: int | None
    chunk_next: int | None
    page: PageRange


def load_chunks(path: Path) -> list[ChunkRecord]:
    if not path.exists():
        raise FileNotFoundError(f"File chunk tidak ditemukan: {path}")

    with path.open("r", encoding="utf-8") as file:
        raw_chunks = json.load(file)

    if not isinstance(raw_chunks, list):
        raise TypeError("output_chunks.json harus berisi array of objects.")

    return [ChunkRecord.model_validate(item) for item in raw_chunks]


def build_supabase_client() -> Client:
    return get_supabase_client()


def build_embedder() -> GoogleGenerativeAIEmbeddings:
    return GoogleGenerativeAIEmbeddings(
        model=EMBEDDING_MODEL_NAME,
        google_api_key=CONFIG.get_google_key(),
    )


def _embed_documents_with_retry(contents: list[str]) -> list[list[float]]:
    """Embed batch dokumen dengan key rotation + retry saat rate limit.

    Siklus: coba semua Google key satu per satu → jika semua exhausted, tunggu
    EMBED_RATE_LIMIT_WAIT detik → ulangi. Max EMBED_MAX_RETRY_CYCLES siklus.
    """
    num_keys = len(CONFIG.google_api_keys)
    for cycle in range(EMBED_MAX_RETRY_CYCLES):
        for key_attempt in range(num_keys):
            try:
                embedder = build_embedder()
                return embedder.embed_documents(contents, output_dimensionality=EMBEDDING_DIMENSION)
            except Exception as e:
                err_str = str(e)
                is_rate_limit = (
                    "ResourceExhausted" in type(e).__name__
                    or "429" in err_str
                    or "RESOURCE_EXHAUSTED" in err_str
                )
                if not is_rate_limit:
                    raise
                if key_attempt < num_keys - 1:
                    CONFIG.rotate_google_key()
                    print(f"[ingest] Key {key_attempt + 1}/{num_keys} exhausted, rotate ke key berikutnya...")
        if cycle < EMBED_MAX_RETRY_CYCLES - 1:
            print(
                f"[ingest] Semua {num_keys} Google key exhausted "
                f"(cycle {cycle + 1}/{EMBED_MAX_RETRY_CYCLES}). "
                f"Menunggu {EMBED_RATE_LIMIT_WAIT} detik..."
            )
            time.sleep(EMBED_RATE_LIMIT_WAIT)
    raise RuntimeError(
        f"Embedding batch gagal setelah {EMBED_MAX_RETRY_CYCLES} siklus × {num_keys} key."
    )



def batched(items: list[ChunkRecord], size: int) -> list[list[ChunkRecord]]:
    return [items[index : index + size] for index in range(0, len(items), size)]


def build_rows(
    chunks: list[ChunkRecord],
    embeddings: list[list[float]],
    source_file: str,
    project_id: str,
) -> list[dict]:
    rows: list[dict] = []

    for chunk, embedding in zip(chunks, embeddings, strict=True):
        row = {
            "project_id": project_id,
            "source_file": source_file,
            "chunk_index": chunk.chunk_index,
            "content": chunk.content,
            "chunk_parent": chunk.chunk_parent,
            "chunk_prev": chunk.chunk_prev,
            "chunk_next": chunk.chunk_next,
            "page_start": chunk.page.start,
            "page_end": chunk.page.end,
            "embedding": format_vector(embedding),
        }
        rows.append(row)

    return rows


def upsert_embeddings(project_id: str) -> int:
    chunks_file = get_chunks_file(project_id)
    chunks = load_chunks(chunks_file)
    if not chunks:
        return 0

    client = build_supabase_client()

    source_file = f"{project_id}/source.pdf"

    all_batches = batched(chunks, BATCH_SIZE)
    total_rows = 0
    for batch_idx, chunk_batch in enumerate(all_batches):
        contents = [chunk.content for chunk in chunk_batch]
        embeddings = _embed_documents_with_retry(contents)
        rows = build_rows(chunk_batch, embeddings, source_file, project_id)
        client.table("document_chunks").upsert(
            rows,
            on_conflict="project_id,chunk_index",
        ).execute()
        total_rows += len(rows)
        if batch_idx < len(all_batches) - 1:
            time.sleep(EMBED_INTER_BATCH_DELAY)

    return total_rows


