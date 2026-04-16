import json
import os
from pathlib import Path

from dotenv import load_dotenv
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from pydantic import BaseModel
from supabase import Client, create_client

APP_DIR = Path(__file__).resolve().parents[2]
ENV_FILE = APP_DIR / ".env"
CHUNKS_FILE = APP_DIR / "data" / "output_chunks.json"

load_dotenv(dotenv_path=ENV_FILE)


def get_required_env(name: str) -> str:
    value = os.getenv(name, "").strip()
    if not value:
        raise ValueError(f"{name} belum di-set di file .env.")
    return value


def _validate_env_vars() -> None:
    """Validate required environment variables at module load time."""
    get_required_env("EMBEDDING_MODEL_NAME")


EMBEDDING_MODEL_NAME = get_required_env("EMBEDDING_MODEL_NAME")
EMBEDDING_DIMENSION = 768
BATCH_SIZE = 20

_validate_env_vars()


class PageRange(BaseModel):
    start: int
    end: int


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
    return create_client(
        get_required_env("SUPABASE_URL"),
        get_required_env("SUPABASE_SERVICE_ROLE_KEY"),
    )


def build_embedder() -> GoogleGenerativeAIEmbeddings:
    return GoogleGenerativeAIEmbeddings(
        model=EMBEDDING_MODEL_NAME,
        google_api_key=get_required_env("GOOGLE_API_KEY"),
    )


def format_vector(values: list[float]) -> str:
    return "[" + ",".join(f"{value:.8f}" for value in values) + "]"


def batched(items: list[ChunkRecord], size: int) -> list[list[ChunkRecord]]:
    return [items[index : index + size] for index in range(0, len(items), size)]


def build_rows(chunks: list[ChunkRecord], embeddings: list[list[float]]) -> list[dict]:
    source_file = CHUNKS_FILE.name
    rows: list[dict] = []

    for chunk, embedding in zip(chunks, embeddings, strict=True):
        rows.append(
            {
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
        )

    return rows


def upsert_embeddings() -> int:
    chunks = load_chunks(CHUNKS_FILE)
    if not chunks:
        return 0

    client = build_supabase_client()
    embedder = build_embedder()

    total_rows = 0
    for chunk_batch in batched(chunks, BATCH_SIZE):
        contents = [chunk.content for chunk in chunk_batch]
        embeddings = embedder.embed_documents(
            contents,
            output_dimensionality=EMBEDDING_DIMENSION,
        )
        rows = build_rows(chunk_batch, embeddings)
        client.table("document_chunks").upsert(
            rows,
            on_conflict="source_file,chunk_index",
        ).execute()
        total_rows += len(rows)

    return total_rows


def main() -> None:
    try:
        total_rows = upsert_embeddings()
        print(
            f"Berhasil upsert {total_rows} chunk dari {CHUNKS_FILE.name} ke tabel document_chunks."
        )
    except Exception as exc:
        print(f"Error saat mengirim embedding ke Supabase: {exc}")
        raise SystemExit(1) from exc


if __name__ == "__main__":
    main()
