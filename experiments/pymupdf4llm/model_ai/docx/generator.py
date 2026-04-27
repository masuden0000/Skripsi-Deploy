from pathlib import Path

from model_ai.docx.chunk_loader import load_chunk_sources
from model_ai.docx.docx_renderer import render_proposal_docx
from model_ai.docx.metadata_loader import load_document_metadata
from model_ai.docx.style_translator_llm import translate_docx_style_config


def generate_proposal_docx(
    metadata_path: Path,
    chunks_path: Path,
    output_path: Path,
    use_llm_normalization: bool = True,
) -> Path:
    metadata = load_document_metadata(metadata_path)
    chunks = load_chunk_sources(chunks_path)
    style_config = translate_docx_style_config(metadata)
    return render_proposal_docx(
        metadata=metadata,
        chunks=chunks,
        style_config=style_config,
        output_path=output_path,
    )
