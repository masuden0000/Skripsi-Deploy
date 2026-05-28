"""
File debugging untuk melihat hasil RAG retrieval dan output mentah LLM
SEBELUM diproses oleh Pydantic menjadi structured JSON.

Cara pakai:
  cd ai
  python debug_extraction.py                                         # debug document_structure_proposal
  python debug_extraction.py --key typography                        # debug satu prompt
  python debug_extraction.py --all                                   # debug semua prompt sekaligus
  python debug_extraction.py --all --project-id <uuid> --save       # semua prompt, simpan ke file

Argumen:
  --key         Nama prompt yang ingin di-debug (default: document_structure_proposal)
                Pilihan: typography, page_layout, spacing, document_structure_proposal,
                         numbering, figures_and_tables, page_count_limits
  --all         Jalankan debug untuk SEMUA prompt sekaligus (mengabaikan --key)
  --project-id  UUID project di Supabase (opsional, tanpa filter jika tidak diisi)
  --save        Simpan output ke file JSON di debug_output/
                  Mode --key  : satu file → debug_output/<key>_<timestamp>.json
                  Mode --all  : satu file → debug_output/ALL_<timestamp>.json

Struktur JSON output:
  {
    "meta": { key, timestamp, project_id },
    "rag_queries": [...],
    "top_k": int,
    "chunks": [
      {
        "index": int,
        "chunk_index": int,
        "chunk_parent": str,
        "page_start": int,
        "page_end": int,
        "content_length": int,
        "content_snippet": str,   ← 300 karakter pertama
        "content_full": str       ← isi lengkap
      }
    ],
    "rendered_prompt": str,
    "llm_raw_response": str,
    "summary": { chunks_retrieved, prompt_length, response_length, error }
  }
"""

import argparse
import json
import sys
import textwrap
from datetime import datetime
from pathlib import Path

# ---------------------------------------------------------------------------
# Pastikan working directory adalah folder ai/ agar import model_ai bisa jalan
# ---------------------------------------------------------------------------
sys.path.insert(0, str(Path(__file__).parent))

from model_ai.extractor.doc_extractor import (
    _build_llm,
    _retrieve_chunks_multi,
    render_prompt,
)
from model_ai.extractor.prompts import (
    DOCUMENT_STRUCTURE_PROPOSAL,
    FIGURES_AND_TABLES,
    NUMBERING,
    PAGE_COUNT_LIMITS,
    PAGE_LAYOUT,
    SPACING,
    TYPOGRAPHY,
    PromptConfig,
)

# ---------------------------------------------------------------------------
# Registry prompt — urutan ini juga urutan eksekusi saat --all
# ---------------------------------------------------------------------------
PROMPT_REGISTRY: dict[str, PromptConfig] = {
    "typography": TYPOGRAPHY,
    "page_layout": PAGE_LAYOUT,
    "spacing": SPACING,
    "document_structure_proposal": DOCUMENT_STRUCTURE_PROPOSAL,
    "numbering": NUMBERING,
    "figures_and_tables": FIGURES_AND_TABLES,
    "page_count_limits": PAGE_COUNT_LIMITS,
}


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

    # ----------------------------------------------------------------
    # RAG RETRIEVAL
    # ----------------------------------------------------------------
    print(f"  [1/3] RAG retrieval untuk '{key}'...")
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

    # Susun data setiap chunk
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

    # ----------------------------------------------------------------
    # RENDER PROMPT
    # ----------------------------------------------------------------
    print(f"  [2/3] Render prompt...")
    rendered = render_prompt(prompt_cfg.template, chunks)
    result["rendered_prompt"] = rendered
    result["summary"]["prompt_length"] = len(rendered)
    print(f"        → {len(rendered):,} karakter")

    # ----------------------------------------------------------------
    # PANGGIL LLM (tanpa Pydantic)
    # ----------------------------------------------------------------
    print(f"  [3/3] Memanggil LLM (raw, tanpa structured output)...")
    try:
        llm = _build_llm()
        raw_response = llm.invoke(rendered)
        raw_text = str(raw_response.content)
    except Exception as e:
        result["summary"]["error"] = f"LLM gagal: {e}"
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


def run_debug(key: str, project_id: str | None, save: bool) -> None:
    """Debug satu prompt, simpan sebagai JSON jika --save."""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    print(f"\n[debug] Memproses prompt: '{key}'")
    result = _collect_one(key, PROMPT_REGISTRY[key], project_id, timestamp)

    # Tampilkan ringkasan ke terminal
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


def run_debug_all(project_id: str | None, save: bool) -> None:
    """Debug semua prompt, simpan semua dalam satu file JSON gabungan."""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    keys = list(PROMPT_REGISTRY.keys())

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

        result = _collect_one(key, PROMPT_REGISTRY[key], project_id, timestamp)
        all_results["results"][key] = result

        s = result["summary"]
        all_results["summary"].append({
            "key": key,
            "chunks_retrieved": s["chunks_retrieved"],
            "prompt_length": s["prompt_length"],
            "response_length": s["response_length"],
            "status": "ERROR: " + s["error"] if s["error"] else "OK",
        })

    # Tampilkan ringkasan akhir ke terminal
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
        """),
    )
    parser.add_argument(
        "--key",
        default="document_structure_proposal",
        choices=list(PROMPT_REGISTRY.keys()),
        help="Prompt key yang ingin di-debug (default: document_structure_proposal)",
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

    if args.all:
        run_debug_all(project_id=args.project_id, save=args.save)
    else:
        run_debug(key=args.key, project_id=args.project_id, save=args.save)


if __name__ == "__main__":
    main()
