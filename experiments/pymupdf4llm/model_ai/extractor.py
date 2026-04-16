import json
from pathlib import Path

import pymupdf4llm
from langchain_text_splitters import MarkdownTextSplitter

if __package__:
    from .chunking import build_payload, build_sections
else:
    from chunking import build_payload, build_sections

APP_DIR = Path(__file__).resolve().parent.parent
PROJECT_DIR = APP_DIR.parent.parent


def extract_chunks() -> tuple[int, Path]:
    # Menentukan lokasi PDF sumber dan file output.
    # Blok ini menjadi titik awal dan titik akhir alur kerja extractor.
    pdf_path = PROJECT_DIR / "file.pdf"
    output_path = APP_DIR / "data" / "output_chunks.json"

    # Mengekstrak PDF ke markdown per halaman.
    # Output per halaman diperlukan oleh `build_sections()` agar kita bisa
    # mempertahankan informasi BAB dan nomor halaman saat masuk ke proses chunking.
    page_chunks_result = pymupdf4llm.to_markdown(str(pdf_path), page_chunks=True)
    if isinstance(page_chunks_result, str):
        raise TypeError(
            "pymupdf4llm.to_markdown() mengembalikan string. Gunakan page_chunks=True agar hasilnya berupa daftar halaman."
        )
    page_chunks = page_chunks_result

    # Menyiapkan splitter yang akan dipakai oleh `build_payload()`.
    # Nilai chunk_size dan chunk_overlap tetap dipertahankan dari versi sebelumnya.
    splitter = MarkdownTextSplitter(chunk_size=1000, chunk_overlap=150)

    # Tahap 1: ubah markdown per halaman menjadi section/BAB yang terstruktur.
    # Tahap 2: pecah section menjadi chunk final dengan parent, prev/next, dan page range.
    sections = build_sections(page_chunks)
    payload = build_payload(sections, splitter)

    # Menulis hasil akhir ke JSON agar bisa dicek atau dipakai proses berikutnya.
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)

    return len(payload), output_path


def main() -> None:
    total_chunks, output_path = extract_chunks()
    print(f"Berhasil menulis {total_chunks} chunk ke: {output_path}")


if __name__ == "__main__":
    main()
