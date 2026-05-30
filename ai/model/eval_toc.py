"""Evaluasi toc_extractor terhadap dokumen sampel."""
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")

AI_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(AI_DIR))

from model_ai.loader.pdf_extractor import get_page_chunks
from model_ai.loader.toc_extractor import (
    TOC_PAGE_LIMIT,
    find_toc_page,
    extract_bab_ranges,
)

PROJECT_ID = "9aaea6d7-298d-4ff8-b9d1-e9cd4a5dc18e"
PDF_PATH = AI_DIR / "data" / PROJECT_ID / "source.pdf"

PASS  = "[PASS]"
FAIL  = "[FAIL]"
INFO  = "[INFO]"


def main() -> None:
    print(f"\n{'='*60}")
    print(f"  EVALUASI TOC EXTRACTOR")
    print(f"  Dokumen: {PROJECT_ID}")
    print(f"{'='*60}\n")

    if not PDF_PATH.exists():
        print(f"{FAIL} File tidak ditemukan: {PDF_PATH}")
        sys.exit(1)

    print(f"{INFO} Membaca PDF: {PDF_PATH.name}")
    page_chunks = get_page_chunks(PDF_PATH)
    print(f"{INFO} Total halaman fisik: {len(page_chunks)}\n")

    # --- Lapis 1 ---
    print("[ LAPIS 1 — Deteksi Halaman Daftar Isi ]")
    toc_page, toc_page_idx = find_toc_page(page_chunks)
    if toc_page:
        phys_page = toc_page["metadata"]["page_number"] + 1
        print(f"{PASS} Halaman daftar isi ditemukan di halaman fisik ke-{phys_page} (limit: {TOC_PAGE_LIMIT})")
        preview = toc_page.get("text", "")[:200].replace("\n", " ")
        print(f"{INFO} Preview: {preview!r}\n")
    else:
        print(f"{FAIL} Halaman daftar isi TIDAK ditemukan dalam {TOC_PAGE_LIMIT} halaman pertama")
        print(f"     → Pipeline akan menggunakan Fallback Total (HEADING_PATTERN lama)\n")
        sys.exit(0)

    # --- Lapis 2 ---
    print("[ LAPIS 2 — Parse Entri BAB ]")
    bab_ranges, jalur = extract_bab_ranges(page_chunks)

    if jalur == "main":
        print(f"{PASS} Jalur Utama: titik-titik '.......' ditemukan + entri BAB berhasil diparsing")
    elif jalur == "fallback_2a":
        print(f"[WARN] Fallback 2A: tidak ada '.......' tapi entri BAB ditemukan via regex")
    else:
        print(f"{FAIL} Fallback Total: daftar isi ditemukan tapi tidak ada entri BAB")
        toc_text = toc_page.get("text", "")
        has_dots = bool(__import__("re").search(r"\.{4,}", toc_text))
        print(f"{INFO} Titik-titik '.......' ada di halaman TOC: {'YA' if has_dots else 'TIDAK'}")
        print(f"{INFO} Kemungkinan: dokumen ini tidak menggunakan struktur BAB")
        print(f"     → Pipeline akan menggunakan Fallback Total (HEADING_PATTERN lama)\n")
        sys.exit(0)

    # --- Hasil BAB Ranges ---
    print(f"\n[ HASIL — BAB Ranges yang Ditemukan ]")
    if bab_ranges:
        for r in bab_ranges:
            print(f"  • {r['heading']:<45} hal {r['page_start']:>3} – {r['page_end']:>3}")
    else:
        print("  (tidak ada)")

    print(f"\n{'='*60}")
    print(f"  KESIMPULAN: {'PASS via ' + jalur.upper().replace('_', ' ')}")
    print(f"{'='*60}\n")


if __name__ == "__main__":
    main()
