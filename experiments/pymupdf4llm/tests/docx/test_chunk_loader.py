from model_ai.docx.chunk_loader import ChunkSource, format_source_line, match_sources_for_section


def test_match_sources_deduplicates_page_and_header():
    chunks = [
        ChunkSource(
            chunk_parent="BAB 1. PENDAHULUAN",
            page_start=8,
            page_end=8,
            content="Konten A",
        ),
        ChunkSource(
            chunk_parent="BAB 1. PENDAHULUAN",
            page_start=8,
            page_end=8,
            content="Konten B duplikat source",
        ),
    ]

    matched = match_sources_for_section(
        chunks=chunks,
        section_label="BAB 1",
        section_title="PENDAHULUAN",
    )
    assert len(matched) == 1


def test_formatted_source_line_does_not_include_chunk_index():
    source = ChunkSource(
        chunk_parent="Sistematika Penulisan Proposal",
        page_start=8,
        page_end=9,
        content="dummy",
    )
    line = format_source_line(source)
    assert line == "Sumber: Hal. 8-9 | Header: Sistematika Penulisan Proposal"
    assert "chunk_index" not in line
