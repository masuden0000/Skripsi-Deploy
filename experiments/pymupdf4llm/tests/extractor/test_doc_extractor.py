import pytest

from model_ai.extractor.doc_extractor import build_sources, render_prompt
from model_ai.extractor.models import PageCountExtracted, Source, TypographyExtracted


SAMPLE_CHUNKS = [
    {
        "chunk_index": 3,
        "page_start": 2,
        "page_end": 3,
        "chunk_parent": "Format Penulisan",
        "content": "Dokumen menggunakan font Times New Roman ukuran 12pt untuk body text dan heading.",
        "similarity": 0.91,
    }
]


def test_build_sources_maps_chunk_fields_to_source():
    sources = build_sources(SAMPLE_CHUNKS)
    assert len(sources) == 1
    s = sources[0]
    assert s.chunk_index == 3
    assert s.page_start == 2
    assert s.page_end == 3
    assert s.header == "Format Penulisan"
    assert "Times New Roman" in s.snippet


def test_build_sources_snippet_truncated_to_100_chars():
    long_chunks = [
        {
            "chunk_index": 1,
            "page_start": 1,
            "page_end": 1,
            "chunk_parent": "H",
            "content": "A" * 200,
            "similarity": 0.8,
        }
    ]
    sources = build_sources(long_chunks)
    assert len(sources[0].snippet) <= 100


def test_build_sources_empty_chunks_returns_empty_list():
    assert build_sources([]) == []


def test_render_prompt_joins_chunk_contents():
    template = "## Context\n{context}\n"
    chunks = [
        {"content": "Chunk satu."},
        {"content": "Chunk dua."},
    ]
    result = render_prompt(template, chunks)
    assert "Chunk satu." in result
    assert "Chunk dua." in result
    assert "---" in result  # separator antara chunks


def test_render_prompt_with_no_chunks_yields_empty_context():
    template = "## Context\n{context}\n"
    result = render_prompt(template, [])
    assert "{context}" not in result
    assert result == "## Context\n\n"


def test_typography_extracted_normalizes_legacy_heading_font_size_string():
    extracted = TypographyExtracted(font_size_heading_pt="12pt (sama dengan body, bold untuk BAB)")
    assert extracted.font_size_heading_pt == 12


def test_page_count_extracted_maps_legacy_catatan_key():
    extracted = PageCountExtracted(catatan="Lampiran tidak dihitung dalam batas 10 halaman")
    assert extracted.definisi_halaman_inti == "Lampiran tidak dihitung dalam batas 10 halaman"
