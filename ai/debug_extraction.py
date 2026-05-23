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
  --save        Simpan output ke file di debug_output/
                  Mode --key  : satu file per prompt  → debug_output/<key>_<timestamp>.txt
                  Mode --all  : satu file gabungan    → debug_output/ALL_<timestamp>.txt
"""

import argparse
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

SEPARATOR  = "=" * 80
SEP_THIN   = "-" * 80
SEP_PROMPT = "#" * 80   # pemisah antar-prompt saat mode --all


def _print(text: str, file=None) -> None:
    """Print ke console dan opsional ke file sekaligus."""
    print(text)
    if file:
        file.write(text + "\n")


def _debug_one(
    key: str,
    prompt_cfg: PromptConfig,
    project_id: str | None,
    timestamp: str,
    file=None,
) -> dict:
    """
    Jalankan satu siklus debug untuk satu prompt.
    Kembalikan dict ringkasan {key, chunks, prompt_len, response_len, error}.
    """
    f = file

    # ----------------------------------------------------------------
    # BAGIAN 1 — INFO SESI
    # ----------------------------------------------------------------
    _print(SEPARATOR, f)
    _print(f"  DEBUG EXTRACTION — key: '{key}'", f)
    _print(f"  Waktu     : {timestamp}", f)
    _print(f"  project_id: {project_id or '(tanpa filter)'}", f)
    _print(SEPARATOR, f)

    # ----------------------------------------------------------------
    # BAGIAN 2 — RAG QUERIES
    # ----------------------------------------------------------------
    _print("\n[1] RAG QUERIES yang digunakan:", f)
    _print(SEP_THIN, f)
    for i, q in enumerate(prompt_cfg.queries, 1):
        _print(f"  Query {i}: {q}", f)
    _print(f"  top_k   : {prompt_cfg.top_k or 'menggunakan RAG_TOP_K dari .env'}", f)

    # ----------------------------------------------------------------
    # BAGIAN 3 — CHUNKS HASIL RETRIEVAL
    # ----------------------------------------------------------------
    _print(f"\n[2] Menjalankan RAG retrieval...", f)
    _print(SEP_THIN, f)

    try:
        chunks = _retrieve_chunks_multi(
            prompt_cfg.queries,
            prompt_cfg.top_k or 8,
            project_id=project_id,
        )
    except Exception as e:
        _print(f"  [ERROR] RAG retrieval gagal: {e}", f)
        return {"key": key, "chunks": 0, "prompt_len": 0, "response_len": 0, "error": str(e)}

    _print(f"  Total chunk ditemukan: {len(chunks)}", f)
    _print("", f)

    for i, chunk in enumerate(chunks, 1):
        _print(f"  --- Chunk #{i} ---", f)
        _print(f"  chunk_index : {chunk.get('chunk_index')}", f)
        _print(f"  chunk_parent: {chunk.get('chunk_parent')}", f)
        _print(f"  page        : {chunk.get('page_start')} - {chunk.get('page_end')}", f)
        content      = str(chunk.get("content", ""))
        snippet      = content[:300].replace("\n", " ")
        has_more     = len(content) > 300
        _print(f"  snippet     : {snippet}{'...' if has_more else ''}", f)
        _print(f"  isi penuh   : {len(content):,} karakter total", f)
        _print("", f)

    # ----------------------------------------------------------------
    # BAGIAN 4 — RENDERED PROMPT
    # ----------------------------------------------------------------
    _print(f"\n[3] RENDERED PROMPT (template + context dari RAG):", f)
    _print(SEPARATOR, f)

    rendered = render_prompt(prompt_cfg.template, chunks)
    _print(rendered, f)
    _print(SEPARATOR, f)

    # ----------------------------------------------------------------
    # BAGIAN 5 — RAW LLM RESPONSE
    # ----------------------------------------------------------------
    _print(f"\n[4] RAW LLM RESPONSE (sebelum diproses Pydantic):", f)
    _print(SEPARATOR, f)
    _print("  Memanggil LLM tanpa structured output...", f)
    _print("", f)

    try:
        llm          = _build_llm()
        raw_response = llm.invoke(rendered)
        raw_text     = str(raw_response.content)
    except Exception as e:
        _print(f"  [ERROR] LLM gagal: {e}", f)
        return {"key": key, "chunks": len(chunks), "prompt_len": len(rendered), "response_len": 0, "error": str(e)}

    _print(raw_text, f)
    _print(SEPARATOR, f)

    # ----------------------------------------------------------------
    # BAGIAN 6 — RINGKASAN PER PROMPT
    # ----------------------------------------------------------------
    _print(f"\n[5] RINGKASAN — '{key}':", f)
    _print(SEP_THIN, f)
    _print(f"  Chunks retrieved : {len(chunks)}", f)
    _print(f"  Prompt length    : {len(rendered):,} karakter", f)
    _print(f"  Response length  : {len(raw_text):,} karakter", f)
    _print(SEP_THIN, f)

    return {
        "key": key,
        "chunks": len(chunks),
        "prompt_len": len(rendered),
        "response_len": len(raw_text),
        "error": None,
    }


def run_debug(key: str, project_id: str | None, save: bool) -> None:
    """Debug satu prompt."""
    prompt_cfg = PROMPT_REGISTRY[key]
    timestamp  = datetime.now().strftime("%Y%m%d_%H%M%S")

    out_file = None
    if save:
        out_dir  = Path(__file__).parent / "debug_output"
        out_dir.mkdir(exist_ok=True)
        out_path = out_dir / f"{key}_{timestamp}.txt"
        out_file = open(out_path, "w", encoding="utf-8")
        print(f"[debug] Output disimpan ke: {out_path}")

    try:
        _debug_one(key, prompt_cfg, project_id, timestamp, file=out_file)
    finally:
        if out_file:
            out_file.close()


def run_debug_all(project_id: str | None, save: bool) -> None:
    """Debug semua prompt secara berurutan, output ke satu file gabungan."""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    keys      = list(PROMPT_REGISTRY.keys())

    out_file = None
    if save:
        out_dir  = Path(__file__).parent / "debug_output"
        out_dir.mkdir(exist_ok=True)
        out_path = out_dir / f"ALL_{timestamp}.txt"
        out_file = open(out_path, "w", encoding="utf-8")
        print(f"[debug] Output gabungan disimpan ke: {out_path}")

    summaries: list[dict] = []

    try:
        for idx, key in enumerate(keys, 1):
            print(f"\n[debug] ({idx}/{len(keys)}) Memproses prompt: '{key}' ...")

            # Pemisah antar-prompt di file gabungan
            if out_file and idx > 1:
                out_file.write("\n" + SEP_PROMPT + "\n")
                out_file.write(f"  PROMPT {idx}/{len(keys)}: {key}\n")
                out_file.write(SEP_PROMPT + "\n\n")

            summary = _debug_one(
                key,
                PROMPT_REGISTRY[key],
                project_id,
                timestamp,
                file=out_file,
            )
            summaries.append(summary)

        # ----------------------------------------------------------------
        # RINGKASAN AKHIR (hanya di mode --all)
        # ----------------------------------------------------------------
        print("\n" + SEP_PROMPT)
        print("  RINGKASAN SEMUA PROMPT")
        print(SEP_PROMPT)
        print(f"  {'KEY':<35} {'CHUNKS':>6}  {'PROMPT':>9}  {'RESPONSE':>9}  STATUS")
        print(SEP_THIN)
        for s in summaries:
            status = "ERROR: " + s["error"] if s["error"] else "OK"
            print(
                f"  {s['key']:<35} {s['chunks']:>6}  "
                f"{s['prompt_len']:>8,}k  {s['response_len']:>8,}k  {status}"
            )
        print(SEP_THIN)

        if out_file:
            out_file.write("\n" + SEP_PROMPT + "\n")
            out_file.write("  RINGKASAN SEMUA PROMPT\n")
            out_file.write(SEP_PROMPT + "\n")
            out_file.write(f"  {'KEY':<35} {'CHUNKS':>6}  {'PROMPT':>9}  {'RESPONSE':>9}  STATUS\n")
            out_file.write(SEP_THIN + "\n")
            for s in summaries:
                status = "ERROR: " + s["error"] if s["error"] else "OK"
                out_file.write(
                    f"  {s['key']:<35} {s['chunks']:>6}  "
                    f"{s['prompt_len']:>8,}k  {s['response_len']:>8,}k  {status}\n"
                )
            out_file.write(SEP_THIN + "\n")
            print(f"\n[debug] Semua output tersimpan di: {out_path}")

    finally:
        if out_file:
            out_file.close()


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
        help="Debug semua prompt sekaligus dalam satu file gabungan (mengabaikan --key)",
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
        help="Simpan output ke file di folder debug_output/",
    )

    args = parser.parse_args()

    if args.all:
        run_debug_all(project_id=args.project_id, save=args.save)
    else:
        run_debug(key=args.key, project_id=args.project_id, save=args.save)


if __name__ == "__main__":
    main()
