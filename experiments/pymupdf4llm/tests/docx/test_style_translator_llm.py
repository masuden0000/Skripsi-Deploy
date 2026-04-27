from model_ai.docx.style_translator_llm import translate_docx_style_config
from model_ai.extractor.models import DocumentMetadata


def _sample_metadata() -> DocumentMetadata:
    return DocumentMetadata.model_validate(
        {
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
            "document_structure_proposal": {"sections": [], "sources": []},
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
            "figures_and_tables": {"sources": []},
            "page_count_limits": {"sources": []},
        }
    )


def test_translate_maps_bool_fields_directly():
    metadata = _sample_metadata()
    result = translate_docx_style_config(metadata)
    assert result.heading_bold is True
    assert result.heading_all_caps is True
    assert result.paragraph_alignment == "JUSTIFY"


def test_translate_maps_page_number_positions():
    metadata = _sample_metadata()
    result = translate_docx_style_config(metadata)
    assert result.page_number_prelim_pos == "footer_right"
    assert result.page_number_content_pos == "header_right"


def test_translate_defaults_when_numbering_is_null():
    metadata = _sample_metadata()
    metadata.numbering.preliminary = None
    metadata.numbering.content = None
    result = translate_docx_style_config(metadata)
    assert result.page_number_prelim_pos == "footer_right"
    assert result.page_number_content_pos == "header_right"
