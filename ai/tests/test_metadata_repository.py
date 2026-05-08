from __future__ import annotations

import sys
import unittest
from pathlib import Path
from unittest.mock import patch


APP_DIR = Path(__file__).resolve().parents[1]
if str(APP_DIR) not in sys.path:
    sys.path.insert(0, str(APP_DIR))

from model_ai.docx.metadata_loader import coerce_document_metadata
from model_ai.metadata_repository import (
    get_document_metadata_row,
    load_document_metadata_payload,
)


SAMPLE_PAYLOAD = {
    "document_type": "Proposal PKM-KC",
    "source_document": "file.pdf",
    "typography": {
        "sources": [],
        "font_family": "Times New Roman",
        "heading_bold": True,
        "heading_all_caps": False,
        "font_size_body_pt": 12,
        "font_size_heading_pt": 12,
    },
    "page_layout": {
        "sources": [],
        "columns": 1,
        "paper_size": "A4",
        "orientation": "Portrait",
        "margin_top_cm": 3,
        "margin_left_cm": 4,
        "margin_right_cm": 3,
        "margin_bottom_cm": 3,
    },
    "spacing": {
        "sources": [],
        "line_spacing": 1.15,
        "line_spacing_rule": "MULTIPLE",
        "paragraph_alignment": "JUSTIFY",
        "first_line_indent_cm": None,
        "references_hanging_indent": True,
    },
    "numbering": {
        "sources": [],
        "preliminary": {
            "format": "lowerRoman",
            "location": "FOOTER",
            "alignment": "RIGHT",
            "start_at_section": "DAFTAR ISI",
        },
        "content": {
            "format": "decimal",
            "location": "HEADER",
            "alignment": "RIGHT",
            "start_at_section": "BAB 1. PENDAHULUAN",
        },
        "table_format": None,
        "figure_format": None,
        "chapter_format": "BAB {n}",
        "sub_chapter_format": None,
    },
    "figures_and_tables": {
        "sources": [],
        "caption_format_table": "Tabel {bab}.{n}. {title}",
        "max_width_constraint": "within_margins",
        "caption_format_figure": "Gambar {n}. {title} ({source})",
        "table_caption_position": "ABOVE",
        "figure_caption_position": "ABOVE",
        "source_required_if_not_own": True,
    },
    "page_count_limits": {
        "sources": [],
        "judul_maks_kata": 20,
        "lampiran_excluded": True,
        "definisi_halaman_inti": "Bab Pendahuluan_to_Daftar Pustaka",
        "proposal_halaman_inti_maks": 10,
        "laporan_akhir_halaman_inti_maks": 10,
        "laporan_kemajuan_halaman_inti_maks": 10,
    },
    "document_structure_proposal": {
        "sources": [],
        "sections": [
            {
                "type": "daftar_isi",
                "title": "DAFTAR ISI",
                "number": None,
                "required": True,
                "is_major_section": True,
            },
            {
                "type": "bab",
                "title": "PENDAHULUAN",
                "number": 1,
                "required": None,
                "is_major_section": True,
            },
            {
                "type": "daftar_pustaka",
                "title": "DAFTAR PUSTAKA",
                "number": None,
                "required": True,
                "is_major_section": True,
            },
        ],
        "ringkasan": False,
        "halaman_sampul": False,
        "format_nama_file": "namaketua_namapt_PKM-KC.pdf",
        "max_halaman_inti": 10,
        "halaman_pengesahan": False,
    },
}


class _FakeResponse:
    def __init__(self, data):
        self.data = data


class _FakeTableQuery:
    def __init__(self, data):
        self._data = data

    def select(self, *_args, **_kwargs):
        return self

    def eq(self, *_args, **_kwargs):
        return self

    def limit(self, *_args, **_kwargs):
        return self

    def execute(self):
        return _FakeResponse(self._data)


class _FakeClient:
    def __init__(self, data):
        self._data = data
        self.requested_table: str | None = None

    def table(self, name: str):
        self.requested_table = name
        return _FakeTableQuery(self._data)


class MetadataRepositoryTests(unittest.TestCase):
    def test_get_document_metadata_row_raises_lookup_error_when_missing(self):
        fake_client = _FakeClient(data=[])
        with patch(
            "model_ai.metadata_repository.build_metadata_supabase_client",
            return_value=fake_client,
        ):
            with self.assertRaises(LookupError) as ctx:
                get_document_metadata_row("file.pdf")

        self.assertIn("file.pdf", str(ctx.exception))
        self.assertIn("document_metadata", str(ctx.exception))
        self.assertEqual(fake_client.requested_table, "document_metadata")

    @patch("model_ai.metadata_repository.get_document_metadata_row")
    def test_load_document_metadata_payload_returns_dict_payload(self, mock_get_row):
        mock_get_row.return_value = {"payload": SAMPLE_PAYLOAD}

        payload = load_document_metadata_payload("file.pdf")

        self.assertEqual(payload["source_document"], "file.pdf")
        self.assertEqual(payload["document_type"], "Proposal PKM-KC")

    @patch("model_ai.metadata_repository.get_document_metadata_row")
    def test_load_document_metadata_payload_rejects_non_object_payload(self, mock_get_row):
        mock_get_row.return_value = {"payload": "not-a-json-object"}

        with self.assertRaises(TypeError) as ctx:
            load_document_metadata_payload("file.pdf")

        self.assertIn("source_doc 'file.pdf'", str(ctx.exception))

    def test_coerce_document_metadata_validates_payload(self):
        metadata = coerce_document_metadata(SAMPLE_PAYLOAD)

        self.assertEqual(metadata.source_document, "file.pdf")
        self.assertEqual(metadata.typography.font_family, "Times New Roman")
        self.assertEqual(metadata.page_layout.margin_left_cm, 4)


if __name__ == "__main__":
    unittest.main()
