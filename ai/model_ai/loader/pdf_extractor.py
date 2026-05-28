"""
Fungsi: Mengambil konten PDF mentah dan metadata halaman sebagai input chunking.

Digunakan oleh: manage.py

Tujuan: Menyediakan data dasar dokumen dari PDF untuk pipeline ingest.
"""
import json
from pathlib import Path
from typing import Optional  # dipakai untuk pdf_path

import pymupdf4llm

if __package__:
    from .chunk_builder import build_chunks
else:
    import sys

    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
    from model_ai.loader.chunk_builder import build_chunks

APP_DIR = Path(__file__).resolve().parents[2]
PROJECT_DIR = APP_DIR.parent


def get_page_chunks(pdf_path: Path) -> list[dict]:
    page_chunks_result = pymupdf4llm.to_markdown(str(pdf_path), page_chunks=True)
    if isinstance(page_chunks_result, str):
        raise TypeError(
            "pymupdf4llm.to_markdown() mengembalikan string. Gunakan page_chunks=True agar hasilnya berupa daftar halaman."
        )
    return page_chunks_result


def extract_chunks(
    project_id: str,
    pdf_path: Optional[Path] = None,
) -> tuple[int, Path]:
    project_data_dir = APP_DIR / "data" / project_id
    project_data_dir.mkdir(parents=True, exist_ok=True)

    source_pdf = pdf_path or (project_data_dir / "source.pdf")
    output_path = project_data_dir / "output_chunks.json"
    markdown_output_path = project_data_dir / "output.md"

    if not source_pdf.exists():
        raise FileNotFoundError(f"File PDF tidak ditemukan: {source_pdf}")

    page_chunks = get_page_chunks(source_pdf)

    markdown_text = "\n\n".join(
        page.get("text", "").strip() for page in page_chunks if page.get("text", "").strip()
    )
    with open(markdown_output_path, "w", encoding="utf-8") as f:
        f.write(markdown_text)

    payload = build_chunks(page_chunks)

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)

    return len(payload), output_path


def main() -> None:
    total_chunks, output_path = extract_chunks()
    print(f"Berhasil menulis {total_chunks} chunk ke: {output_path}")


if __name__ == "__main__":
    main()
