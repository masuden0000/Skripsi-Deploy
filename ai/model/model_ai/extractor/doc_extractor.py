"""Orkestrator ekstraksi aturan dokumen berbasis RAG + LLM ke schema terstruktur. Posisi pipeline: supabase_ingest → doc_extractor → metadata_repository."""
from pathlib import Path
import json
import re
import time
from typing import Any, Type

from langchain_google_genai import GoogleGenerativeAIEmbeddings
from langchain_groq import ChatGroq
from langchain_google_genai import ChatGoogleGenerativeAI
from pydantic import BaseModel
from supabase import Client

from model_ai.config import get_config
from model_ai.shared import (
    BATCH_PAUSE_EVERY,
    BATCH_PAUSE_SECONDS,
    EMBED_MAX_RETRY_CYCLES,
    EMBED_RATE_LIMIT_WAIT,
    EMBEDDING_DIMENSION,
    EXCLUDED_PARENTS,
    format_vector,
    get_supabase_client,
)
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
    PromptConfig,
    load_prompts_for_skema,
)

APP_DIR = Path(__file__).resolve().parents[2]

MAX_RATE_LIMIT_WAIT = 120

CONFIG = get_config()
LLM_MODEL = CONFIG.model_name

_MODEL_MAP: list[tuple[str, Type[BaseModel], Type[BaseModel]]] = [
    ("typography",                  TypographyExtracted,        TypographyInfo),
    ("page_layout",                 PageLayoutExtracted,        PageLayoutInfo),
    ("spacing",                     SpacingExtracted,           SpacingInfo),
    ("document_structure_proposal", DocumentStructureExtracted, DocumentStructureInfo),
    ("numbering",                   NumberingExtracted,         NumberingInfo),
    ("figures_and_tables",          FiguresTablesExtracted,     FiguresTablesInfo),
    ("page_count_limits",           PageCountExtracted,         PageCountInfo),
]


def _build_key_registry(
    skema: str,
) -> list[tuple[str, PromptConfig, Type[BaseModel], Type[BaseModel]]]:
    """Bangun registry ekstraksi berdasarkan skema PKM.

    Hanya key yang punya prompt tersedia yang dimasukkan ke registry.
    """
    prompts = load_prompts_for_skema(skema)
    return [
        (key, prompts[key], extracted_cls, info_cls)
        for key, extracted_cls, info_cls in _MODEL_MAP
        if key in prompts
    ]


_BOLD_HEADING_PATTERNS = (
    re.compile(r"\*\*\s*BAB\b", re.IGNORECASE),
    re.compile(r"\*\*\s*DAFTAR\b", re.IGNORECASE),
    re.compile(r"\*\*\s*RINGKASAN\b", re.IGNORECASE),
)
_EXPLICIT_NOT_BOLD_PATTERN = re.compile(
    r"(judul|heading|bab).{0,40}(tidak|bukan).{0,20}(bold|tebal)|"
    r"(judul|heading|bab).{0,40}cetak normal",
    re.IGNORECASE,
)


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


def _context_has_markdown_bold_heading(chunks: list[dict]) -> bool:
    for chunk in chunks:
        content = str(chunk.get("content", ""))
        for pattern in _BOLD_HEADING_PATTERNS:
            if pattern.search(content):
                return True
    return False


def _context_explicitly_says_heading_not_bold(chunks: list[dict]) -> bool:
    for chunk in chunks:
        content = str(chunk.get("content", ""))
        if _EXPLICIT_NOT_BOLD_PATTERN.search(content):
            return True
    return False


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


def _apply_typography_caps_heuristic(payload: dict[str, Any], chunks: list[dict]) -> dict[str, Any]:
    """Force heading_all_caps=True when BAB headings are written in ALL CAPS.

    Why: beberapa panduan menulis BAB dalam format ALL CAPS (misal "BAB 1. PENDAHULUAN").
    Jika konteks mengandung heading BAB dengan huruf besar semua, maka set heading_all_caps=True.
    Ini heuristic tambahan karena tidak semua panduan menulis eksplisit aturan uppercase.
    """
    if payload.get("heading_all_caps") is True:
        return payload

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



def _build_llm():
    """Build LLM client with Groq-first + Gemini fallback rotation."""
    CONFIG.disable_blackhole_proxies()
    api_key, model_name = CONFIG.get_llm_api_key()
    if model_name.startswith("gemini"):
        return ChatGoogleGenerativeAI(
            model=model_name,
            google_api_key=api_key,
            temperature=CONFIG.temperature,
        )
    return ChatGroq(
        model=model_name,
        api_key=api_key,
        temperature=CONFIG.temperature,
    )


def _build_embedder() -> GoogleGenerativeAIEmbeddings:
    CONFIG.disable_blackhole_proxies()
    return GoogleGenerativeAIEmbeddings(
        model=CONFIG.embedding_model_name,
        google_api_key=CONFIG.get_google_key(),
    )


def _embed_query_with_retry(query: str) -> list[float]:
    """Embed query dengan key rotation + retry saat rate limit.

    Siklus: coba semua Google key satu per satu → jika semua exhausted, tunggu
    EMBED_RATE_LIMIT_WAIT detik → ulangi. Max EMBED_MAX_RETRY_CYCLES siklus.
    """
    num_keys = len(CONFIG.google_api_keys)
    for cycle in range(EMBED_MAX_RETRY_CYCLES):
        for key_attempt in range(num_keys):
            try:
                embedder = _build_embedder()
                return embedder.embed_query(query, output_dimensionality=EMBEDDING_DIMENSION)
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
                    print(f"[embed] Key {key_attempt + 1}/{num_keys} exhausted, rotate ke key berikutnya...")
        if cycle < EMBED_MAX_RETRY_CYCLES - 1:
            print(
                f"[embed] Semua {num_keys} Google key exhausted "
                f"(cycle {cycle + 1}/{EMBED_MAX_RETRY_CYCLES}). "
                f"Menunggu {EMBED_RATE_LIMIT_WAIT} detik..."
            )
            time.sleep(EMBED_RATE_LIMIT_WAIT)
    raise RuntimeError(
        f"Embedding gagal setelah {EMBED_MAX_RETRY_CYCLES} siklus × {num_keys} key."
    )


def _build_supabase() -> Client:
    return get_supabase_client()


def _expand_to_full_headers(seed_chunks: list[dict], client: Client) -> list[dict]:
    """Expand seed chunks ke seluruh chunk dalam header (chunk_parent) yang sama.

    Setelah vector search menemukan chunk yang relevan, fungsi ini mengambil
    semua chunk lain yang berada dalam section (chunk_parent) yang sama dari
    Supabase. Ini memastikan konteks satu section tidak terpotong oleh chunking.
    """
    if not seed_chunks:
        return seed_chunks

    headers: list[str] = list({str(c["chunk_parent"]) for c in seed_chunks})
    project_id: str | None = seed_chunks[0].get("project_id")

    query = client.table("document_chunks").select(
        "chunk_index, content, chunk_parent, chunk_prev, chunk_next, page_start, page_end"
    ).in_("chunk_parent", headers)

    if project_id:
        query = query.eq("project_id", project_id)

    expanded = query.execute().data or []

    seen: dict[int, dict] = {int(c["chunk_index"]): c for c in seed_chunks}
    for chunk in expanded:
        idx = int(chunk["chunk_index"])
        if idx not in seen:
            seen[idx] = chunk

    return sorted(seen.values(), key=lambda c: c["chunk_index"])


def _retrieve_by_section_focus(
    section_focus: list[str],
    project_id: str | None,
) -> list[dict] | None:
    """Ambil semua chunk dari chunk_parent yang cocok dengan salah satu keyword section_focus.

    Returns None jika tidak ada parent yang cocok — caller harus fallback ke vector search.
    """
    client = _build_supabase()

    query = client.table("document_chunks").select("chunk_parent")
    if project_id:
        query = query.eq("project_id", project_id)
    rows = query.execute().data or []

    parents: set[str] = {r["chunk_parent"] for r in rows if r.get("chunk_parent")}

    matched: list[str] = []
    for focus in section_focus:
        focus_upper = focus.upper()
        for p in parents:
            if focus_upper in p.upper() and p not in matched:
                matched.append(p)

    if not matched:
        return None

    fetch = client.table("document_chunks").select(
        "chunk_index, content, chunk_parent, chunk_prev, chunk_next, page_start, page_end, project_id"
    ).in_("chunk_parent", matched)
    if project_id:
        fetch = fetch.eq("project_id", project_id)

    chunks = fetch.execute().data or []
    return sorted(chunks, key=lambda c: c["chunk_index"]) if chunks else None


def _retrieve_chunks_multi(queries: list[str], top_k: int, project_id: str | None = None) -> list[dict]:
    """Embed setiap query, retrieve top-K chunks dari Supabase.

    Alur:
    1. Untuk setiap query: embed → vector RPC → kumpulkan chunk unik (dedup by chunk_index)
    2. Sort by chunk_index agar konteks berurutan.

    Catatan: expand ke full chunk_parent dinonaktifkan — konteks dibatasi pada top_k chunk saja.
    """
    client = _build_supabase()

    rpc_params: dict = {
        "query_embedding": None,
        "match_count": top_k,
        "excluded_parents": list(EXCLUDED_PARENTS),
    }
    if project_id:
        rpc_params["filter_project_id"] = project_id

    seen: dict[int, dict] = {}
    for query in queries:
        vector = _embed_query_with_retry(query)
        rpc_params["query_embedding"] = format_vector(vector)
        result = client.rpc(
            "match_document_chunks",
            rpc_params,
        ).execute()
        for chunk in (result.data or []):
            idx = chunk["chunk_index"]
            if idx not in seen:
                seen[idx] = chunk

    return sorted(seen.values(), key=lambda c: c["chunk_index"])


def _extract_key(
    prompt_cfg: PromptConfig,
    extracted_cls: Type[BaseModel],
    info_cls: Type[BaseModel],
    project_id: str | None = None,
) -> Any:
    """Jalankan satu siklus ekstraksi: retrieve → prompt → LLM → merge sources."""
    top_k = prompt_cfg.top_k if prompt_cfg.top_k > 0 else CONFIG.rag_top_k

    chunks: list[dict] | None = None
    if prompt_cfg.section_focus:
        chunks = _retrieve_by_section_focus(prompt_cfg.section_focus, project_id)
        if chunks is None:
            print(f"[extract] section_focus {prompt_cfg.section_focus} tidak ditemukan di chunk_parent, fallback ke vector search.")

    if chunks is None:
        chunks = _retrieve_chunks_multi(prompt_cfg.queries, top_k, project_id=project_id)

    prompt = render_prompt(prompt_cfg.template, chunks)

    CONFIG.disable_blackhole_proxies()
    llm = _build_llm()
    chain = llm.with_structured_output(extracted_cls)

    groq_keys_tried = 0
    max_retries = len(CONFIG.groq_api_keys) + len(CONFIG.google_api_keys) + 2
    for attempt in range(max_retries):
        try:
            extracted = chain.invoke(prompt)
            break
        except Exception as e:
            err_str = str(e)
            if "429" in err_str or "rate_limit_exceeded" in err_str or "quota" in err_str.lower():
                import re
                wait_match = re.search(r"try again in (\d+)m(\d+(?:\.\d+)?)s", err_str)
                if wait_match:
                    wait_secs = int(wait_match.group(1)) * 60 + float(wait_match.group(2)) + 5
                else:
                    wait_secs = 30
                wait_secs = min(wait_secs, MAX_RATE_LIMIT_WAIT)

                if not CONFIG._groq_exhausted:
                    groq_keys_tried += 1
                    if groq_keys_tried < len(CONFIG.groq_api_keys):
                        CONFIG.rotate_groq_key()
                        print(f"[extract] Rate limit hit. Rotasi ke Groq key berikutnya ({groq_keys_tried}/{len(CONFIG.groq_api_keys)}) percobaan {attempt + 1}...")
                    else:
                        CONFIG._groq_exhausted = True
                        print(f"[extract] Semua {len(CONFIG.groq_api_keys)} Groq key exhausted, switch ke Gemini (percobaan {attempt + 1})...")
                else:
                    if len(CONFIG.google_api_keys) > 1:
                        CONFIG.rotate_google_key()
                    print(f"[extract] Rate limit hit pada Gemini. Menunggu {wait_secs:.0f} detik (percobaan {attempt + 1}/{max_retries})...")
                    time.sleep(wait_secs)

                llm = _build_llm()
                chain = llm.with_structured_output(extracted_cls)
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


def _pause_after_batch(processed_count: int, total_count: int) -> None:
    if processed_count % BATCH_PAUSE_EVERY != 0 or processed_count >= total_count:
        return

    print(
        f"[extract] {processed_count}/{total_count} proses selesai. "
        f"Jeda {BATCH_PAUSE_SECONDS} detik untuk mengurangi risiko rate limit..."
    )
    time.sleep(BATCH_PAUSE_SECONDS)


def extract_document_metadata(
    project_id: str | None = None,
    skema: str = "PKM-KC",
) -> DocumentMetadata:
    key_registry = _build_key_registry(skema)
    if not key_registry:
        print(f"[extract] Tidak ada prompt untuk skema '{skema}'. Metadata dikembalikan kosong.")
        return DocumentMetadata(source_document=f"{project_id}/source.pdf" if project_id else None)

    results: dict[str, Any] = {}
    total_keys = len(key_registry)
    for index, (key, prompt_cfg, extracted_cls, info_cls) in enumerate(key_registry, start=1):
        print(f"[extract] Memproses: {key} ...")
        results[key] = _extract_key(prompt_cfg, extracted_cls, info_cls, project_id=project_id)
        print(f"[extract] Selesai:   {key}")
        _pause_after_batch(index, total_keys)

    results["source_document"] = f"{project_id}/source.pdf" if project_id else None
    return DocumentMetadata(**results)


def save_to_supabase(metadata: DocumentMetadata, project_id: str | None = None) -> None:
    result = upsert_document_metadata(metadata, project_id)
    print(f"[extract] Supabase upsert: project_id={result}")


def run_extraction(project_id: str | None = None, skema: str = "PKM-KC") -> None:
    metadata = extract_document_metadata(project_id=project_id, skema=skema)
    save_to_supabase(metadata, project_id)
