import textwrap
from pathlib import Path

import pytest

from model_ai.extractor.doc_extractor import build_sources, load_prompt, render_prompt
from model_ai.extractor.models import Source


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


def test_load_prompt_single_query(tmp_path: Path):
    prompt_file = tmp_path / "test.md"
    prompt_file.write_text(
        textwrap.dedent("""\
            ---
            query: "font huruf ukuran tipografi"
            ---

            # Task

            ## Context
            {context}

            ## Output
            Ekstrak font.
        """)
    )
    queries, template, top_k = load_prompt(prompt_file)
    assert queries == ["font huruf ukuran tipografi"]
    assert "{context}" in template
    assert "# Task" in template
    assert top_k == 0  # no override → gunakan global config


def test_load_prompt_multiple_queries(tmp_path: Path):
    prompt_file = tmp_path / "multi.md"
    prompt_file.write_text(
        textwrap.dedent("""\
            ---
            queries:
              - "query satu"
              - "query dua"
            top_k: 10
            ---

            # Task
            {context}
        """)
    )
    queries, template, top_k = load_prompt(prompt_file)
    assert queries == ["query satu", "query dua"]
    assert top_k == 10
    assert "{context}" in template


def test_load_prompt_missing_query_raises(tmp_path: Path):
    prompt_file = tmp_path / "bad.md"
    prompt_file.write_text("---\ntitle: no query here\n---\nbody")
    with pytest.raises(ValueError, match="wajib punya field"):
        load_prompt(prompt_file)


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
