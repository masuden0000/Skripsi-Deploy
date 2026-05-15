"""
Fungsi: Orkestrator ekstraksi aturan dokumen berbasis RAG + LLM ke schema terstruktur.

Digunakan oleh: manage.py; model_ai/extractor/schema_differ.py; tests/extractor/test_doc_extractor.py

Tujuan: Mengubah konteks chunk menjadi metadata dokumen yang bisa divalidasi dan dipakai downstream.
"""
from pathlib import Path
import json
import re
import time
from typing import Any, Type

from langchain_google_genai import GoogleGenerativeAIEmbeddings
from langchain_groq import ChatGroq
from pydantic import BaseModel
from supabase import Client, create_client

from model_ai.config import get_config
from model_ai.extractor.models import (
    DocumentMetadata,
    DocumentStructureExtracted,
    DocumentStructureInfo,
    FiguresTablesExtracted,
    FiguresTablesInfo,
    NumberingExtracted,
    NumberingInfo,
    PageCountExtracted,
    PageCountInfo,
    PageLayoutExtracted,
    PageLayoutInfo,
    Source,
    SpacingExtracted,
    SpacingInfo,
    TypographyExtracted,
    TypographyInfo,
)
from model_ai.metadata_repository import upsert_document_metadata
from model_ai.extractor.prompts import (
    DOCUMENT_STRUCTURE_PROPOSAL,
    DOCUMENT_TYPE,
    FIGURES_AND_TABLES,
    NUMBERING,
    PAGE_COUNT_LIMITS,
    PAGE_LAYOUT,
    SPACING,
    TYPOGRAPHY,
    PromptConfig,
)

# ---------------------------------------------------------------------------
# Digunakan oleh: Dipakai oleh fungsi-fungsi di modul ini dan modul terkait saat import runtime.
# Blok konstanta `APP_DIR` untuk menyimpan konfigurasi/registry yang dipakai berulang.
# ---------------------------------------------------------------------------
APP_DIR = Path(__file__).resolve().parents[2]
# ---------------------------------------------------------------------------
# Digunakan oleh: Dipakai oleh fungsi-fungsi di modul ini dan modul terkait saat import runtime.
# Blok konstanta `EMBEDDING_DIMENSION` untuk menyimpan konfigurasi/registry yang dipakai berulang.
# ---------------------------------------------------------------------------
EMBEDDING_DIMENSION = 768
# ---------------------------------------------------------------------------
# Digunakan oleh: Dipakai oleh fungsi-fungsi di modul ini dan modul terkait saat import runtime.
# Blok konstanta `BATCH_PAUSE_EVERY` untuk menyimpan konfigurasi/registry yang dipakai berulang.
# ---------------------------------------------------------------------------
BATCH_PAUSE_EVERY = 2
# ---------------------------------------------------------------------------
# Digunakan oleh: Dipakai oleh fungsi-fungsi di modul ini dan modul terkait saat import runtime.
# Blok konstanta `BATCH_PAUSE_SECONDS` untuk menyimpan konfigurasi/registry yang dipakai berulang.
# ---------------------------------------------------------------------------
BATCH_PAUSE_SECONDS = 60

# ---------------------------------------------------------------------------
# Digunakan oleh: Dipakai oleh fungsi-fungsi di modul ini dan modul terkait saat import runtime.
# Blok konstanta `CONFIG` untuk menyimpan konfigurasi/registry yang dipakai berulang.
# ---------------------------------------------------------------------------
CONFIG = get_config()
# ---------------------------------------------------------------------------
# Digunakan oleh: Dipakai oleh fungsi-fungsi di modul ini dan modul terkait saat import runtime.
# Blok konstanta `LLM_MODEL` untuk menyimpan konfigurasi/registry yang dipakai berulang.
# ---------------------------------------------------------------------------
LLM_MODEL = CONFIG.model_name

KEY_REGISTRY: list[tuple[str, PromptConfig, Type[BaseModel], Type[BaseModel]]] = [
    ("typography", TYPOGRAPHY, TypographyExtracted, TypographyInfo),
    ("page_layout", PAGE_LAYOUT, PageLayoutExtracted, PageLayoutInfo),
    ("spacing", SPACING, SpacingExtracted, SpacingInfo),
    ("document_structure_proposal", DOCUMENT_STRUCTURE_PROPOSAL, DocumentStructureExtracted, DocumentStructureInfo),
    ("numbering", NUMBERING, NumberingExtracted, NumberingInfo),
    ("figures_and_tables", FIGURES_AND_TABLES, FiguresTablesExtracted, FiguresTablesInfo),
    ("page_count_limits", PAGE_COUNT_LIMITS, PageCountExtracted, PageCountInfo),
]


# ---------------------------------------------------------------------------
# Digunakan oleh: Dipakai oleh fungsi-fungsi di modul ini dan modul terkait saat import runtime.
# Blok konstanta `_BOLD_HEADING_PATTERNS` untuk menyimpan konfigurasi/registry yang dipakai berulang.
# ---------------------------------------------------------------------------
_BOLD_HEADING_PATTERNS = (
    re.compile(r"\*\*\s*BAB\b", re.IGNORECASE),
    re.compile(r"\*\*\s*DAFTAR\b", re.IGNORECASE),
    re.compile(r"\*\*\s*RINGKASAN\b", re.IGNORECASE),
)
# ---------------------------------------------------------------------------
# Digunakan oleh: Dipakai oleh fungsi-fungsi di modul ini dan modul terkait saat import runtime.
# Blok konstanta `_EXPLICIT_NOT_BOLD_PATTERN` untuk menyimpan konfigurasi/registry yang dipakai berulang.
# ---------------------------------------------------------------------------
_EXPLICIT_NOT_BOLD_PATTERN = re.compile(
    r"(judul|heading|bab).{0,40}(tidak|bukan).{0,20}(bold|tebal)|"
    r"(judul|heading|bab).{0,40}cetak normal",
    re.IGNORECASE,
)


# ---------------------------------------------------------------------------
# Digunakan oleh: Dipakai internal di file ini atau dipanggil dari entrypoint runtime.
# Menjalankan fungsi `build_sources` sebagai bagian alur `doc_extractor`.
# ---------------------------------------------------------------------------
def build_sources(chunks: list[dict]) -> list[Source]:
    return [
        Source(
            chunk_index=c["chunk_index"],
            page_start=c["page_start"],
            page_end=c["page_end"],
            header=c["chunk_parent"],
            snippet=c["content"][:100],
        )
        for c in chunks
    ]


# ---------------------------------------------------------------------------
# Digunakan oleh: model_ai/extractor/schema_differ.py
# Menjalankan fungsi `render_prompt` sebagai bagian alur `doc_extractor`.
# ---------------------------------------------------------------------------
def render_prompt(template: str, chunks: list[dict]) -> str:
    """Ganti {context} di template dengan gabungan teks chunks."""
    context = "\n\n---\n\n".join(c["content"] for c in chunks)
    return template.replace("{context}", context)


# ---------------------------------------------------------------------------
# Digunakan oleh: Dipakai internal di file ini atau dipanggil dari entrypoint runtime.
# Menjalankan fungsi `_context_has_markdown_bold_heading` sebagai bagian alur `doc_extractor`.
# ---------------------------------------------------------------------------
def _context_has_markdown_bold_heading(chunks: list[dict]) -> bool:
    for chunk in chunks:
        content = str(chunk.get("content", ""))
        for pattern in _BOLD_HEADING_PATTERNS:
            if pattern.search(content):
                return True
    return False


# ---------------------------------------------------------------------------
# Digunakan oleh: Dipakai internal di file ini atau dipanggil dari entrypoint runtime.
# Menjalankan fungsi `_context_explicitly_says_heading_not_bold` sebagai bagian alur `doc_extractor`.
# ---------------------------------------------------------------------------
def _context_explicitly_says_heading_not_bold(chunks: list[dict]) -> bool:
    for chunk in chunks:
        content = str(chunk.get("content", ""))
        if _EXPLICIT_NOT_BOLD_PATTERN.search(content):
            return True
    return False


# ---------------------------------------------------------------------------
# Digunakan oleh: Dipakai internal di file ini atau dipanggil dari entrypoint runtime.
# Menjalankan fungsi `_apply_typography_heading_bold_heuristic` sebagai bagian alur `doc_extractor`.
# ---------------------------------------------------------------------------
def _apply_typography_heading_bold_heuristic(payload: dict[str, Any], chunks: list[dict]) -> dict[str, Any]:
    """Force heading_bold=True when markdown heading markers imply bold styling.

    Why: beberapa panduan tidak menulis kata "bold" secara eksplisit, tapi
    struktur BAB/DAFTAR ditulis dalam markdown tebal (`**...**`). Itu dipakai
    sebagai sinyal deterministik untuk heading style.
    """
    if payload.get("heading_bold") is True:
        return payload
    if _context_explicitly_says_heading_not_bold(chunks):
        return payload
    if not _context_has_markdown_bold_heading(chunks):
        return payload

    patched = dict(payload)
    patched["heading_bold"] = True
    return patched


# ---------------------------------------------------------------------------
# Digunakan oleh: Dipakai internal di file ini atau dipanggil dari entrypoint runtime.
# Menjalankan fungsi `_apply_typography_caps_heuristic` sebagai bagian alur `doc_extractor`.
# ---------------------------------------------------------------------------
def _apply_typography_caps_heuristic(payload: dict[str, Any], chunks: list[dict]) -> dict[str, Any]:
    """Force heading_all_caps=True when BAB headings are written in ALL CAPS.

    Why: beberapa panduan menulis BAB dalam format ALL CAPS (misal "BAB 1. PENDAHULUAN").
    Jika konteks mengandung heading BAB dengan huruf besar semua, maka set heading_all_caps=True.
    Ini heuristic tambahan karena tidak semua panduan menulis eksplisit aturan uppercase.
    """
    if payload.get("heading_all_caps") is True:
        return payload

    # Pattern untuk mendeteksi BAB dalam format ALL CAPS
    # Contoh: "BAB 1. PENDAHULUAN", "**BAB 2. TINJAUAN PUSTAKA**", "BAB 3.TAHAP PELAKSANAAN"
    import re
    caps_pattern = re.compile(
        r"(?:^|\s|\*+)BAB\s+[\dIVX]+\.?\s+[A-Z]{2,}",
        re.MULTILINE
    )
    for chunk in chunks:
        content = str(chunk.get("content", ""))
        if caps_pattern.search(content):
            patched = dict(payload)
            patched["heading_all_caps"] = True
            return patched

    return payload


# ---------------------------------------------------------------------------
# Digunakan oleh: model_ai/extractor/schema_differ.py
# Menjalankan fungsi `_format_vector` sebagai bagian alur `doc_extractor`.
# ---------------------------------------------------------------------------
def _format_vector(values: list[float]) -> str:
    return "[" + ",".join(f"{v:.8f}" for v in values) + "]"


# ---------------------------------------------------------------------------
# Digunakan oleh: model_ai/extractor/schema_differ.py
# Menjalankan fungsi `_build_embedder` sebagai bagian alur `doc_extractor`.
# ---------------------------------------------------------------------------
def _build_embedder() -> GoogleGenerativeAIEmbeddings:
    CONFIG.disable_blackhole_proxies()
    return GoogleGenerativeAIEmbeddings(
        model=CONFIG.embedding_model_name,
        google_api_key=CONFIG.require_google_api_key(),
    )


# ---------------------------------------------------------------------------
# Digunakan oleh: model_ai/extractor/schema_differ.py
# Menjalankan fungsi `_build_supabase` sebagai bagian alur `doc_extractor`.
# ---------------------------------------------------------------------------
def _build_supabase() -> Client:
    return create_client(
        CONFIG.supabase_url,
        CONFIG.supabase_service_role_key.get_secret_value(),
    )


# ---------------------------------------------------------------------------
# Digunakan oleh: model_ai/extractor/schema_differ.py
# Menjalankan fungsi `_expand_to_full_headers` sebagai bagian alur `doc_extractor`.
# ---------------------------------------------------------------------------
def _expand_to_full_headers(seed_chunks: list[dict], client: Client) -> list[dict]:
    """Expand seed chunks ke seluruh chunk dalam header (chunk_parent) yang sama.

    Setelah vector search menemukan chunk yang relevan, fungsi ini mengambil
    semua chunk lain yang berada dalam section (chunk_parent) yang sama dari
    Supabase. Ini memastikan konteks satu section tidak terpotong oleh chunking.
    """
    if not seed_chunks:
        return seed_chunks

    headers: list[str] = list({str(c["chunk_parent"]) for c in seed_chunks})
    source_file: str | None = seed_chunks[0].get("source_file")  # type: ignore[assignment]

    query = client.table("document_chunks").select(
        "chunk_index, content, chunk_parent, chunk_prev, chunk_next, page_start, page_end"
    ).in_("chunk_parent", headers)

    if source_file:
        query = query.eq("source_file", source_file)

    expanded = query.execute().data or []

    seen: dict[int, dict] = {int(c["chunk_index"]): c for c in seed_chunks}
    for chunk in expanded:
        idx = int(chunk["chunk_index"])  # type: ignore[arg-type]
        if idx not in seen:
            seen[idx] = chunk  # type: ignore[assignment]

    return sorted(seen.values(), key=lambda c: c["chunk_index"])


# ---------------------------------------------------------------------------
# Digunakan oleh: Dipakai internal di file ini atau dipanggil dari entrypoint runtime.
# Menjalankan fungsi `_retrieve_chunks_multi` sebagai bagian alur `doc_extractor`.
# ---------------------------------------------------------------------------
def _retrieve_chunks_multi(queries: list[str], top_k: int) -> list[dict]:
    """Embed setiap query, retrieve top-K chunks dari Supabase, lalu expand per header.

    Alur:
    1. Untuk setiap query: embed → vector RPC → kumpulkan chunk unik (dedup by chunk_index)
    2. Expand: untuk setiap chunk yang ditemukan, ambil semua chunk lain dalam
       chunk_parent yang sama sehingga satu section selalu utuh.
    3. Sort by chunk_index agar konteks berurutan.
    """
    embedder = _build_embedder()
    client = _build_supabase()

    seen: dict[int, dict] = {}
    for query in queries:
        vector = embedder.embed_query(query, output_dimensionality=EMBEDDING_DIMENSION)
        formatted = _format_vector(vector)
        result = client.rpc(
            "match_document_chunks",
            {"query_embedding": formatted, "match_count": top_k},
        ).execute()
        for chunk in (result.data or []):
            idx = chunk["chunk_index"]
            if idx not in seen:
                seen[idx] = chunk

    seed_chunks = sorted(seen.values(), key=lambda c: c["chunk_index"])
    return _expand_to_full_headers(seed_chunks, client)


# ---------------------------------------------------------------------------
# Digunakan oleh: model_ai/extractor/prompts.py
# Menjalankan fungsi `_extract_key` sebagai bagian alur `doc_extractor`.
# ---------------------------------------------------------------------------
def _extract_key(
    prompt_cfg: PromptConfig,
    extracted_cls: Type[BaseModel],
    info_cls: Type[BaseModel],
) -> Any:
    """Jalankan satu siklus ekstraksi: retrieve → prompt → LLM → merge sources."""
    top_k = prompt_cfg.top_k if prompt_cfg.top_k > 0 else CONFIG.rag_top_k
    chunks = _retrieve_chunks_multi(prompt_cfg.queries, top_k)
    prompt = render_prompt(prompt_cfg.template, chunks)

    CONFIG.disable_blackhole_proxies()
    llm = ChatGroq(
        model=LLM_MODEL,
        api_key=CONFIG.groq_api_key.get_secret_value(),
    )
    chain = llm.with_structured_output(extracted_cls)

    max_retries = 5
    for attempt in range(max_retries):
        try:
            extracted = chain.invoke(prompt)
            break
        except Exception as e:
            err_str = str(e)
            if "429" in err_str or "rate_limit_exceeded" in err_str:
                import re
                wait_match = re.search(r"try again in (\d+)m(\d+(?:\.\d+)?)s", err_str)
                if wait_match:
                    wait_secs = int(wait_match.group(1)) * 60 + float(wait_match.group(2)) + 5
                else:
                    wait_secs = 60 * (2 ** attempt)
                print(f"[extract] Rate limit hit. Menunggu {wait_secs:.0f} detik (percobaan {attempt + 1}/{max_retries})...")
                time.sleep(wait_secs)
            else:
                raise
    else:
        raise RuntimeError(f"Gagal setelah {max_retries} percobaan karena rate limit.")

    payload = extracted.model_dump()
    if extracted_cls is TypographyExtracted:
        payload = _apply_typography_heading_bold_heuristic(payload, chunks)
        payload = _apply_typography_caps_heuristic(payload, chunks)

    sources = build_sources(chunks)
    return info_cls(**payload, sources=sources)


# ---------------------------------------------------------------------------
# Digunakan oleh: Dipakai internal di file ini atau dipanggil dari entrypoint runtime.
# Menjalankan fungsi `_pause_after_batch` sebagai bagian alur `doc_extractor`.
# ---------------------------------------------------------------------------
def _pause_after_batch(processed_count: int, total_count: int) -> None:
    # Jeda hanya dipakai setelah tiap 2 proses selesai dan bukan di item terakhir.
    if processed_count % BATCH_PAUSE_EVERY != 0 or processed_count >= total_count:
        return

    print(
        f"[extract] {processed_count}/{total_count} proses selesai. "
        f"Jeda {BATCH_PAUSE_SECONDS} detik untuk mengurangi risiko rate limit..."
    )
    time.sleep(BATCH_PAUSE_SECONDS)


# ---------------------------------------------------------------------------
# Digunakan oleh: model_ai/extractor/prompts.py
# Menjalankan fungsi `_extract_document_type` sebagai bagian alur `doc_extractor`.
# ---------------------------------------------------------------------------
def _extract_document_type() -> str | None:
    """Identifikasi jenis dokumen dari judul/konteks header dokumen."""
    top_k = DOCUMENT_TYPE.top_k if DOCUMENT_TYPE.top_k > 0 else CONFIG.rag_top_k
    chunks = _retrieve_chunks_multi(DOCUMENT_TYPE.queries, top_k)
    if not chunks:
        return None

    prompt = render_prompt(DOCUMENT_TYPE.template, chunks)
    CONFIG.disable_blackhole_proxies()
    llm = ChatGroq(model=LLM_MODEL, api_key=CONFIG.groq_api_key.get_secret_value())
    result = llm.invoke(prompt)
    text = str(result.content).strip().strip('"')
    return None if text.lower() == "null" else text


# ---------------------------------------------------------------------------
# Digunakan oleh: Dipakai internal di file ini atau dipanggil dari entrypoint runtime.
# Menjalankan fungsi `extract_document_metadata` sebagai bagian alur `doc_extractor`.
# ---------------------------------------------------------------------------
def extract_document_metadata() -> DocumentMetadata:
    results: dict[str, Any] = {}
    total_keys = len(KEY_REGISTRY)
    for index, (key, prompt_cfg, extracted_cls, info_cls) in enumerate(KEY_REGISTRY, start=1):
        print(f"[extract] Memproses: {key} ...")
        results[key] = _extract_key(prompt_cfg, extracted_cls, info_cls)
        print(f"[extract] Selesai:   {key}")
        _pause_after_batch(index, total_keys)

    print("[extract] Memproses: document_type ...")
    results["document_type"] = _extract_document_type()
    print(f"[extract] Selesai:   document_type → {results['document_type']}")

    results["source_document"] = Path(APP_DIR.parent / "file.pdf").name
    return DocumentMetadata(**results)


# ---------------------------------------------------------------------------
# Digunakan oleh: Dipakai internal di file ini atau dipanggil dari entrypoint runtime.
# Menjalankan fungsi `save_to_supabase` sebagai bagian alur `doc_extractor`.
# ---------------------------------------------------------------------------
def save_to_supabase(metadata: DocumentMetadata, project_id: str | None = None) -> None:
    source_doc = upsert_document_metadata(metadata, project_id)
    print(f"[extract] Supabase upsert: source_doc={source_doc}")


# ---------------------------------------------------------------------------
# Digunakan oleh: manage.py
# Menjalankan fungsi `run_extraction` sebagai bagian alur `doc_extractor`.
# ---------------------------------------------------------------------------
def run_extraction(project_id: str | None = None) -> None:
    metadata = extract_document_metadata()
    if project_id:
        project_dir = APP_DIR / "data" / project_id
        project_dir.mkdir(parents=True, exist_ok=True)
        output_path = project_dir / "output.json"
    else:
        output_path = APP_DIR / "data" / "output.json"

    output_path.write_text(
        json.dumps(metadata.model_dump(exclude_none=True), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(f"[extract] Output lokal: {output_path}")
    save_to_supabase(metadata, project_id)
