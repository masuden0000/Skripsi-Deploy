"""
Fungsi: Mengirim chunk dan metadata ke Supabase (vector/data store) untuk retrieval.

Digunakan oleh: manage.py

Tujuan: Menyimpan hasil preprocessing ke storage terpusat yang dipakai query RAG.
"""
import json
import time
from pathlib import Path

from langchain_google_genai import GoogleGenerativeAIEmbeddings
from pydantic import BaseModel
from supabase import Client, create_client

from model_ai.config import get_config

# ---------------------------------------------------------------------------
# Digunakan oleh: Dipakai oleh fungsi-fungsi di modul ini dan modul terkait saat import runtime.
# Blok konstanta `APP_DIR` untuk menyimpan konfigurasi/registry yang dipakai berulang.
# ---------------------------------------------------------------------------
APP_DIR = Path(__file__).resolve().parents[2]
# ---------------------------------------------------------------------------
# Digunakan oleh: Dipakai oleh fungsi-fungsi di modul ini dan modul terkait saat import runtime.
# Blok konstanta `CONFIG` untuk menyimpan konfigurasi/registry yang dipakai berulang.
# ---------------------------------------------------------------------------
CONFIG = get_config()
# ---------------------------------------------------------------------------
# Digunakan oleh: Dipakai oleh fungsi-fungsi di modul ini dan modul terkait saat import runtime.
# Blok konstanta `EMBEDDING_MODEL_NAME` untuk menyimpan konfigurasi/registry yang dipakai berulang.
# ---------------------------------------------------------------------------
EMBEDDING_MODEL_NAME = CONFIG.embedding_model_name
# ---------------------------------------------------------------------------
# Digunakan oleh: Dipakai oleh fungsi-fungsi di modul ini dan modul terkait saat import runtime.
# Blok konstanta `EMBEDDING_DIMENSION` untuk menyimpan konfigurasi/registry yang dipakai berulang.
# ---------------------------------------------------------------------------
EMBEDDING_DIMENSION = 768
# ---------------------------------------------------------------------------
# Digunakan oleh: Dipakai oleh fungsi-fungsi di modul ini dan modul terkait saat import runtime.
# Blok konstanta `BATCH_SIZE` untuk menyimpan konfigurasi/registry yang dipakai berulang.
# ---------------------------------------------------------------------------
BATCH_SIZE = 20

EMBED_MAX_RETRY_CYCLES = 5
EMBED_RATE_LIMIT_WAIT = 60  # detik, tunggu saat semua Google key exhausted


def get_chunks_file(project_id: str) -> Path:
    return APP_DIR / "data" / project_id / "output_chunks.json"


# ---------------------------------------------------------------------------
# Digunakan oleh: Dipakai internal di file ini atau dipanggil dari entrypoint runtime.
# Mendefinisikan class `PageRange` untuk kebutuhan modul `supabase_ingest`.
# ---------------------------------------------------------------------------
class PageRange(BaseModel):
    start: int
    end: int


# ---------------------------------------------------------------------------
# Digunakan oleh: Dipakai internal di file ini atau dipanggil dari entrypoint runtime.
# Mendefinisikan class `ChunkRecord` untuk kebutuhan modul `supabase_ingest`.
# ---------------------------------------------------------------------------
class ChunkRecord(BaseModel):
    chunk_index: int
    content: str
    chunk_parent: str
    chunk_prev: int | None
    chunk_next: int | None
    page: PageRange


# ---------------------------------------------------------------------------
# Digunakan oleh: Dipakai internal di file ini atau dipanggil dari entrypoint runtime.
# Menjalankan fungsi `load_chunks` sebagai bagian alur `supabase_ingest`.
# ---------------------------------------------------------------------------
def load_chunks(path: Path) -> list[ChunkRecord]:
    if not path.exists():
        raise FileNotFoundError(f"File chunk tidak ditemukan: {path}")

    with path.open("r", encoding="utf-8") as file:
        raw_chunks = json.load(file)

    if not isinstance(raw_chunks, list):
        raise TypeError("output_chunks.json harus berisi array of objects.")

    return [ChunkRecord.model_validate(item) for item in raw_chunks]


# ---------------------------------------------------------------------------
# Digunakan oleh: Dipakai internal modul ingest dan caller retrieval lain.
# Menjalankan fungsi `build_supabase_client` sebagai bagian alur `supabase_ingest`.
# ---------------------------------------------------------------------------
def build_supabase_client() -> Client:
    return create_client(
        CONFIG.supabase_url,
        CONFIG.supabase_service_role_key.get_secret_value(),
    )


# ---------------------------------------------------------------------------
# Digunakan oleh: Dipakai internal modul ingest dan caller retrieval lain.
# Menjalankan fungsi `build_embedder` sebagai bagian alur `supabase_ingest`.
# ---------------------------------------------------------------------------
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


# ---------------------------------------------------------------------------
# Digunakan oleh: Dipakai internal modul ingest dan caller retrieval lain.
# Menjalankan fungsi `format_vector` sebagai bagian alur `supabase_ingest`.
# ---------------------------------------------------------------------------
def format_vector(values: list[float]) -> str:
    return "[" + ",".join(f"{value:.8f}" for value in values) + "]"


# ---------------------------------------------------------------------------
# Digunakan oleh: Dipakai internal di file ini atau dipanggil dari entrypoint runtime.
# Menjalankan fungsi `batched` sebagai bagian alur `supabase_ingest`.
# ---------------------------------------------------------------------------
def batched(items: list[ChunkRecord], size: int) -> list[list[ChunkRecord]]:
    return [items[index : index + size] for index in range(0, len(items), size)]


# ---------------------------------------------------------------------------
# Digunakan oleh: Dipakai internal di file ini atau dipanggil dari entrypoint runtime.
# Menjalankan fungsi `build_rows` sebagai bagian alur `supabase_ingest`.
# ---------------------------------------------------------------------------
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


# ---------------------------------------------------------------------------
# Digunakan oleh: manage.py
# Menjalankan fungsi `upsert_embeddings` sebagai bagian alur `supabase_ingest`.
# ---------------------------------------------------------------------------
def upsert_embeddings(project_id: str) -> int:
    chunks_file = get_chunks_file(project_id)
    chunks = load_chunks(chunks_file)
    if not chunks:
        return 0

    client = build_supabase_client()

    source_file = f"{project_id}/source.pdf"

    total_rows = 0
    for chunk_batch in batched(chunks, BATCH_SIZE):
        contents = [chunk.content for chunk in chunk_batch]
        embeddings = _embed_documents_with_retry(contents)
        rows = build_rows(chunk_batch, embeddings, source_file, project_id)
        client.table("document_chunks").upsert(
            rows,
            on_conflict="project_id,chunk_index",
        ).execute()
        total_rows += len(rows)

    return total_rows


# ---------------------------------------------------------------------------
# Digunakan oleh: manage.py; model_ai/loader/pdf_extractor.py
# Menjalankan fungsi `main` sebagai bagian alur `supabase_ingest`.
# ---------------------------------------------------------------------------
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
