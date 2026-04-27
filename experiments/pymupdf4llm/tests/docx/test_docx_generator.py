import json
from pathlib import Path
from uuid import uuid4

import pytest

pytest.importorskip("docx")

from docx import Document

from model_ai.docx.generator import generate_proposal_docx


def _sample_output_json() -> dict:
    return {
        "document_type": "Panduan PKM-KC",
        "source_document": "file.pdf",
        "typography": {
            "font_family": "Times New Roman",
            "font_size_body_pt": 12,
            "heading_bold": True,
            "heading_all_caps": True,
            "sources": [],
        },
        "page_layout": {
            "margin_top_cm": 3,
            "margin_bottom_cm": 3,
            "margin_left_cm": 4,
            "margin_right_cm": 3,
            "paper_size": "A4",
            "orientation": "PORTRAIT",
            "columns": 1,
            "sources": [],
        },
        "spacing": {
            "line_spacing": 1.15,
            "line_spacing_rule": "MULTIPLE",
            "paragraph_alignment": "JUSTIFY",
            "sources": [],
        },
        "document_structure_proposal": {
            "sections": [
                {"type": "daftar_isi", "required": True},
                {"type": "bab", "number": 1, "title": "PENDAHULUAN"},
                {"type": "daftar_pustaka", "required": True},
                {"type": "lampiran", "required": True},
            ],
            "sources": [],
        },
        "document_structure_laporan_kemajuan": {"sections": [], "sources": []},
        "document_structure_laporan_akhir": {"sections": [], "sources": []},
        "numbering": {
            "preliminary": {
                "format": "lowerRoman",
                "location": "FOOTER",
                "alignment": "RIGHT",
                "start_at_section": "daftar_isi",
            },
            "content": {
                "format": "decimal",
                "location": "HEADER",
                "alignment": "RIGHT",
                "start_at_section": "BAB 1 PENDAHULUAN",
            },
            "sources": [],
        },
        "figures_and_tables": {
            "table_caption_position": "ABOVE",
            "figure_caption_position": "BELOW",
            "caption_format_figure": "Gambar {n}. {title} ({source})",
            "caption_format_table": "Tabel {bab}.{n} {title}",
            "source_required_if_not_own": True,
            "sources": [],
        },
        "page_count_limits": {"sources": []},
    }


def _sample_chunks_json() -> list[dict]:
    return [
        {
            "chunk_index": 21,
            "chunk_parent": "BAB 1. PENDAHULUAN",
            "content": "Pendahuluan menjelaskan latar belakang.",
            "page": {"start": 8, "end": 8},
        },
        {
            "chunk_index": 99,
            "chunk_parent": "BAB 1. PENDAHULUAN",
            "content": "Duplikat sumber dengan halaman sama.",
            "page": {"start": 8, "end": 8},
        },
    ]


def test_generate_proposal_docx_creates_file_with_source_lines():
    data_dir = Path(__file__).resolve().parents[2] / "data"
    run_id = uuid4().hex
    metadata_path = data_dir / f"test_output_{run_id}.json"
    chunks_path = data_dir / f"test_chunks_{run_id}.json"
    output_path = data_dir / f"test_proposal_{run_id}.docx"

    try:
        metadata_path.write_text(
            json.dumps(_sample_output_json(), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        chunks_path.write_text(
            json.dumps(_sample_chunks_json(), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

        generated = generate_proposal_docx(
            metadata_path=metadata_path,
            chunks_path=chunks_path,
            output_path=output_path,
        )

        assert generated.exists()
        assert generated.stat().st_size > 0

        doc = Document(str(generated))
        full_text = "\n".join(paragraph.text for paragraph in doc.paragraphs)
        assert "Sumber: Hal. 8-8 | Header: BAB 1. PENDAHULUAN" in full_text
        assert "chunk_index" not in full_text
    finally:
        for path in (metadata_path, chunks_path, output_path):
            if path.exists():
                path.unlink()
