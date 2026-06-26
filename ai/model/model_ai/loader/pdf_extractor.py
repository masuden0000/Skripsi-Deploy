"""Mengambil konten PDF mentah dan metadata halaman sebagai input chunking. Posisi pipeline: PDF input → pdf_extractor → chunk_builder."""
import json
from pathlib import Path
from typing import Optional

import pymupdf4llm
from langchain_text_splitters import MarkdownTextSplitter

if __package__:
    from .chunk_builder import build_payload, build_sections, build_sections_from_ranges
    from .toc_extractor import extract_bab_ranges
else:
    import sys

    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
    from model_ai.loader.chunk_builder import build_payload, build_sections, build_sections_from_ranges
    from model_ai.loader.toc_extractor import extract_bab_ranges

APP_DIR = Path(__file__).resolve().parents[2]


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

    splitter = MarkdownTextSplitter(chunk_size=1000, chunk_overlap=150)

    bab_ranges, jalur, toc_page_idx = extract_bab_ranges(page_chunks, pdf_path=source_pdf)
    if bab_ranges:
        sections = build_sections_from_ranges(page_chunks, bab_ranges, toc_page_idx)
        print(f"[setup] chunk_parent sumber: TOC ({jalur}), {len(bab_ranges)} entri ditemukan")
    else:
        sections = build_sections(page_chunks)
        print("[setup] chunk_parent sumber: HEADING_PATTERN (fallback total)")

    payload = build_payload(sections, splitter)

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)

    return len(payload), output_path


