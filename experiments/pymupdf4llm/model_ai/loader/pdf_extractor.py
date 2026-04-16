import json
from pathlib import Path

import pymupdf4llm
from langchain_text_splitters import MarkdownTextSplitter

# Fleksibilitas saat eksekusi modul langsung atau dari `manage.py`.
if __package__:
    from .chunk_builder import build_payload, build_sections
else:
    import sys

    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
    from model_ai.loader.chunk_builder import build_payload, build_sections

APP_DIR = Path(__file__).resolve().parents[2]
PROJECT_DIR = APP_DIR.parent.parent


def get_page_chunks() -> list[dict]:
    pdf_path = PROJECT_DIR / "file.pdf"
    page_chunks_result = pymupdf4llm.to_markdown(str(pdf_path), page_chunks=True)
    if isinstance(page_chunks_result, str):
        raise TypeError(
            "pymupdf4llm.to_markdown() mengembalikan string. Gunakan page_chunks=True agar hasilnya berupa daftar halaman."
        )
    return page_chunks_result


def extract_chunks() -> tuple[int, Path]:
    # Menentukan lokasi PDF sumber dan file output.
    # Blok ini menjadi titik awal dan titik akhir alur kerja extractor.
    pdf_path = PROJECT_DIR / "file.pdf"
    output_path = APP_DIR / "data" / "output_chunks.json"
    markdown_output_path = APP_DIR / "data" / "output.md"

    # Mengekstrak PDF ke markdown per halaman.
    # Output per halaman diperlukan oleh `build_sections()` agar kita bisa
    # mempertahankan informasi BAB dan nomor halaman saat masuk ke proses chunking.
    page_chunks = get_page_chunks()

    # Menyimpan hasil markdown mentah pada file terpisah agar mudah dibaca
    # dan berada di folder data yang sama dengan output JSON.
    markdown_text = "\n\n".join(
        page.get("text", "").strip() for page in page_chunks if page.get("text", "").strip()
    )
    with open(markdown_output_path, "w", encoding="utf-8") as f:
        f.write(markdown_text)

    # Menyiapkan splitter yang akan dipakai oleh `build_payload()`.
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
