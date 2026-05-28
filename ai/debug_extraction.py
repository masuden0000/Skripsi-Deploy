"""
Fungsi: Debug RAG retrieval dan raw LLM output sebelum Pydantic parsing.
Digunakan oleh: Developer menjalankan langsung via command line.
Tujuan: Melihat hasil retrieval dan output LLM mentah untuk troubleshooting pipeline.
Keyword: automated document generation
"""

import argparse
import json
import sys
import textwrap
import time
from datetime import datetime
from pathlib import Path


from model_ai.extractor.doc_extractor import (
    CONFIG,
    _build_llm,
    _retrieve_chunks_multi,
    render_prompt,
)
from model_ai.extractor.prompts import (
    PromptConfig,
    load_prompts,
)

_PROMPT_KEYS = [
    "typography",
    "page_layout",
    "spacing",
    "document_structure",
    "numbering",
    "figures_and_tables",
    "page_count_limits",
]


def _collect_one(
    key: str,
    prompt_cfg: PromptConfig,
    project_id: str | None,
    timestamp: str,
) -> dict:
    """
    Jalankan satu siklus debug dan kumpulkan semua data ke dalam dict.
    Tidak ada I/O ke file di sini — hanya kumpulkan dan kembalikan.
    """
    result: dict = {
        "meta": {
            "key": key,
            "timestamp": timestamp,
            "project_id": project_id,
        },
        "rag_queries": prompt_cfg.queries,
        "top_k": prompt_cfg.top_k or "menggunakan RAG_TOP_K dari .env",
        "chunks": [],
        "rendered_prompt": None,
        "llm_raw_response": None,
        "summary": {
            "chunks_retrieved": 0,
            "prompt_length": 0,
            "response_length": 0,
            "error": None,
        },
    }

    try:
        chunks = _retrieve_chunks_multi(
            prompt_cfg.queries,
            prompt_cfg.top_k or 8,
            project_id=project_id,
        )
    except Exception as e:
        result["summary"]["error"] = f"RAG retrieval gagal: {e}"
        print(f"  [ERROR] {result['summary']['error']}")
        return result

    for i, chunk in enumerate(chunks, 1):
        content = str(chunk.get("content", ""))
        result["chunks"].append({
            "index": i,
            "chunk_index": chunk.get("chunk_index"),
            "chunk_parent": chunk.get("chunk_parent"),
            "page_start": chunk.get("page_start"),
            "page_end": chunk.get("page_end"),
            "content_length": len(content),
            "content_snippet": content[:300],
            "content_full": content,
        })

    result["summary"]["chunks_retrieved"] = len(chunks)
    print(f"        → {len(chunks)} chunk ditemukan")

    rendered = render_prompt(prompt_cfg.template, chunks)
    result["rendered_prompt"] = rendered
    result["summary"]["prompt_length"] = len(rendered)
    print(f"        → {len(rendered):,} karakter")

    max_retries = len(CONFIG.groq_api_keys) + 1  # coba semua Groq key + 1 buffer
    raw_text = None
    for attempt in range(max_retries):
        try:
            llm = _build_llm()
            raw_response = llm.invoke(rendered)
            raw_text = str(raw_response.content)
            break
        except Exception as e:
            err_str = str(e)
            is_rate_limit = (
                "429" in err_str
                or "rate_limit_exceeded" in err_str
                or "quota" in err_str.lower()
            )
            if is_rate_limit and attempt < max_retries - 1:
                CONFIG.rotate_groq_key()
                print(f"  [rate limit] Key exhausted, rotasi ke Groq key berikutnya (percobaan {attempt + 1}/{max_retries})...")
                time.sleep(5)
            else:
                result["summary"]["error"] = f"LLM gagal: {e}"
                print(f"  [ERROR] {result['summary']['error']}")
                return result

    if raw_text is None:
        result["summary"]["error"] = f"LLM gagal setelah {max_retries} percobaan karena rate limit."
        print(f"  [ERROR] {result['summary']['error']}")
        return result

    result["llm_raw_response"] = raw_text
    result["summary"]["response_length"] = len(raw_text)
    print(f"        → {len(raw_text):,} karakter response")

    return result


def _save_json(data: dict, out_path: Path) -> None:
    """Simpan dict sebagai file JSON dengan indentasi 2 spasi."""
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f"\n[debug] Output disimpan ke: {out_path}")


def run_debug(key: str, prompt_registry: dict[str, PromptConfig], project_id: str | None, save: bool) -> None:
    """Debug satu prompt, simpan sebagai JSON jika --save."""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    print(f"\n[debug] Memproses prompt: '{key}'")
    result = _collect_one(key, prompt_registry[key], project_id, timestamp)

    s = result["summary"]
    print(f"\n{'─' * 50}")
    print(f"  RINGKASAN — '{key}'")
    print(f"{'─' * 50}")
    print(f"  Chunks retrieved : {s['chunks_retrieved']}")
    print(f"  Prompt length    : {s['prompt_length']:,} karakter")
    print(f"  Response length  : {s['response_length']:,} karakter")
    print(f"  Status           : {'ERROR: ' + s['error'] if s['error'] else 'OK'}")
    print(f"{'─' * 50}")

    if save:
        out_dir = Path(__file__).parent / "debug_output"
        out_dir.mkdir(exist_ok=True)
        _save_json(result, out_dir / f"{key}_{timestamp}.json")


def run_debug_all(prompt_registry: dict[str, PromptConfig], project_id: str | None, save: bool) -> None:
    """Debug semua prompt, simpan semua dalam satu file JSON gabungan."""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    keys = list(prompt_registry.keys())

    all_results: dict = {
        "meta": {
            "timestamp": timestamp,
            "project_id": project_id,
            "total_prompts": len(keys),
        },
        "results": {},
        "summary": [],
    }

    print(f"\n[debug] Mode --all: memproses {len(keys)} prompt\n")

    for idx, key in enumerate(keys, 1):
        print(f"{'=' * 50}")
        print(f"  ({idx}/{len(keys)}) Prompt: '{key}'")
        print(f"{'=' * 50}")

        result = _collect_one(key, prompt_registry[key], project_id, timestamp)
        all_results["results"][key] = result

        s = result["summary"]
        all_results["summary"].append({
            "key": key,
            "chunks_retrieved": s["chunks_retrieved"],
            "prompt_length": s["prompt_length"],
            "response_length": s["response_length"],
            "status": "ERROR: " + s["error"] if s["error"] else "OK",
        })

    print(f"\n{'=' * 60}")
    print(f"  RINGKASAN SEMUA PROMPT")
    print(f"{'=' * 60}")
    print(f"  {'KEY':<35} {'CHUNKS':>6}  {'PROMPT':>10}  {'RESPONSE':>10}  STATUS")
    print(f"  {'─' * 58}")
    for s in all_results["summary"]:
        print(
            f"  {s['key']:<35} {s['chunks_retrieved']:>6}  "
            f"{s['prompt_length']:>9,}  {s['response_length']:>9,}  {s['status']}"
        )
    print(f"  {'─' * 58}")

    if save:
        out_dir = Path(__file__).parent / "debug_output"
        out_dir.mkdir(exist_ok=True)
        _save_json(all_results, out_dir / f"ALL_{timestamp}.json")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Debug RAG retrieval dan raw LLM output sebelum Pydantic.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=textwrap.dedent("""\
            Contoh penggunaan:
              python debug_extraction.py
              python debug_extraction.py --key typography
              python debug_extraction.py --all
              python debug_extraction.py --all --project-id abc-123 --save
              python debug_extraction.py --skema pkm-kc --key document_structure
        """),
    )
    parser.add_argument(
        "--key",
        default="document_structure",
        choices=_PROMPT_KEYS,
        help="Prompt key yang ingin di-debug (default: document_structure)",
    )
    parser.add_argument(
        "--skema",
        default="pkm-kc",
        metavar="SKEMA",
        help="Slug skema PKM untuk memilih folder prompt (default: pkm-kc)",
    )
    parser.add_argument(
        "--all",
        action="store_true",
        help="Debug semua prompt sekaligus dalam satu file JSON (mengabaikan --key)",
    )
    parser.add_argument(
        "--project-id",
        default=None,
        metavar="UUID",
        help="Filter chunks berdasarkan project_id di Supabase (opsional)",
    )
    parser.add_argument(
        "--save",
        action="store_true",
        help="Simpan output ke file JSON di folder debug_output/",
    )

    args = parser.parse_args()
    prompt_registry = load_prompts(args.skema)

    if args.all:
        run_debug_all(prompt_registry=prompt_registry, project_id=args.project_id, save=args.save)
    else:
        run_debug(key=args.key, prompt_registry=prompt_registry, project_id=args.project_id, save=args.save)


if __name__ == "__main__":
    main()
