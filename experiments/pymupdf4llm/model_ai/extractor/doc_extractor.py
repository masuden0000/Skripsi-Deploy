import json
import os
from pathlib import Path
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
from model_ai.extractor.prompts import (
    DOCUMENT_STRUCTURE_LAPORAN_AKHIR,
    DOCUMENT_STRUCTURE_LAPORAN_KEMAJUAN,
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

APP_DIR = Path(__file__).resolve().parents[2]
OUTPUT_PATH = APP_DIR / "data" / "output.json"
EMBEDDING_DIMENSION = 768
BATCH_PAUSE_EVERY = 2
BATCH_PAUSE_SECONDS = 60

CONFIG = get_config()
LLM_MODEL = CONFIG.model_name

KEY_REGISTRY: list[tuple[str, PromptConfig, Type[BaseModel], Type[BaseModel]]] = [
    ("typography", TYPOGRAPHY, TypographyExtracted, TypographyInfo),
    ("page_layout", PAGE_LAYOUT, PageLayoutExtracted, PageLayoutInfo),
    ("spacing", SPACING, SpacingExtracted, SpacingInfo),
    ("document_structure_proposal", DOCUMENT_STRUCTURE_PROPOSAL, DocumentStructureExtracted, DocumentStructureInfo),
    ("document_structure_laporan_kemajuan", DOCUMENT_STRUCTURE_LAPORAN_KEMAJUAN, DocumentStructureExtracted, DocumentStructureInfo),
    ("document_structure_laporan_akhir", DOCUMENT_STRUCTURE_LAPORAN_AKHIR, DocumentStructureExtracted, DocumentStructureInfo),
    ("numbering", NUMBERING, NumberingExtracted, NumberingInfo),
    ("figures_and_tables", FIGURES_AND_TABLES, FiguresTablesExtracted, FiguresTablesInfo),
    ("page_count_limits", PAGE_COUNT_LIMITS, PageCountExtracted, PageCountInfo),
]


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


def render_prompt(template: str, chunks: list[dict]) -> str:
    """Ganti {context} di template dengan gabungan teks chunks."""
    context = "\n\n---\n\n".join(c["content"] for c in chunks)
    return template.replace("{context}", context)


def _format_vector(values: list[float]) -> str:
    return "[" + ",".join(f"{v:.8f}" for v in values) + "]"


def _build_embedder() -> GoogleGenerativeAIEmbeddings:
    CONFIG.disable_blackhole_proxies()
    return GoogleGenerativeAIEmbeddings(
        model=CONFIG.embedding_model_name,
        google_api_key=CONFIG.require_google_api_key(),
    )


def _build_supabase() -> Client:
    return create_client(
        CONFIG.supabase_url,
        CONFIG.supabase_service_role_key.get_secret_value(),
    )


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

    sources = build_sources(chunks)
    return info_cls(**extracted.model_dump(), sources=sources)


def _pause_after_batch(processed_count: int, total_count: int) -> None:
    # Jeda hanya dipakai setelah tiap 2 proses selesai dan bukan di item terakhir.
    if processed_count % BATCH_PAUSE_EVERY != 0 or processed_count >= total_count:
        return

    print(
        f"[extract] {processed_count}/{total_count} proses selesai. "
        f"Jeda {BATCH_PAUSE_SECONDS} detik untuk mengurangi risiko rate limit..."
    )
    time.sleep(BATCH_PAUSE_SECONDS)


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


def save_to_json(metadata: DocumentMetadata) -> None:
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(metadata.model_dump(), f, ensure_ascii=False, indent=4)
    print(f"[extract] JSON disimpan: {OUTPUT_PATH}")


def save_to_supabase(metadata: DocumentMetadata) -> None:
    supabase = create_client(os.environ["SUPABASE_URL"], os.environ["SUPABASE_SERVICE_ROLE_KEY"])
    payload = metadata.model_dump()
    source_doc = payload.get("source_document") or "unknown"
    supabase.table("document_metadata").upsert(
        {"source_doc": source_doc, "payload": payload},
        on_conflict="source_doc",
    ).execute()
    print(f"[extract] Supabase upsert: source_doc={source_doc}")


def run_extraction() -> None:
    metadata = extract_document_metadata()
    save_to_json(metadata)
    save_to_supabase(metadata)
