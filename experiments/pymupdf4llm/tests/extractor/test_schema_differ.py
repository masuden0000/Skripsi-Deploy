import json
import sys
from unittest.mock import MagicMock, patch

from model_ai.extractor.schema_differ import (
    FieldChange,
    SchemaDiff,
    diff_schemas,
    flatten_schema,
    generate_report,
)


# --- diff_schemas() ---

def test_diff_schemas_matched():
    old = {"typography.font_family": "Times New Roman"}
    new = {"typography.font_family": "Times New Roman"}
    diff = diff_schemas(old, new)
    assert "typography.font_family" in diff.matched
    assert diff.changed == []
    assert diff.new_fields == []
    assert diff.removed == []


def test_diff_schemas_matched_case_insensitive_and_stripped():
    old = {"spacing.paragraph_alignment": "  Justify  "}
    new = {"spacing.paragraph_alignment": "justify"}
    diff = diff_schemas(old, new)
    assert "spacing.paragraph_alignment" in diff.matched


def test_diff_schemas_changed():
    old = {"spacing.line_spacing_body": "1.5"}
    new = {"spacing.line_spacing_body": "2.0"}
    diff = diff_schemas(old, new)
    assert len(diff.changed) == 1
    assert diff.changed[0].key == "spacing.line_spacing_body"
    assert diff.changed[0].old_value == "1.5"
    assert diff.changed[0].new_value == "2.0"


def test_diff_schemas_new_field():
    old = {}
    new = {"new_rule.watermark_required": True}
    diff = diff_schemas(old, new)
    assert len(diff.new_fields) == 1
    assert diff.new_fields[0].key == "new_rule.watermark_required"
    assert diff.new_fields[0].new_value is True
    assert diff.new_fields[0].old_value is None


def test_diff_schemas_removed():
    old = {"numbering.chapter_numbering_format": "BAB I"}
    new = {}
    diff = diff_schemas(old, new)
    assert len(diff.removed) == 1
    assert diff.removed[0].key == "numbering.chapter_numbering_format"
    assert diff.removed[0].old_value == "BAB I"
    assert diff.removed[0].new_value is None


def test_diff_schemas_null_vs_value_is_changed():
    old = {"typography.font_family": None}
    new = {"typography.font_family": "Arial"}
    diff = diff_schemas(old, new)
    assert len(diff.changed) == 1


def test_diff_schemas_both_null_is_matched():
    old = {"typography.orientation": None}
    new = {"typography.orientation": None}
    diff = diff_schemas(old, new)
    assert "typography.orientation" in diff.matched


def test_diff_schemas_mixed():
    old = {
        "typography.font_family": "Times New Roman",
        "spacing.line_spacing_body": "1.5",
        "numbering.chapter_numbering_format": "BAB I",
    }
    new = {
        "typography.font_family": "Times New Roman",
        "spacing.line_spacing_body": "2.0",
        "new_rule.watermark": "required",
    }
    diff = diff_schemas(old, new)
    assert "typography.font_family" in diff.matched
    assert any(fc.key == "spacing.line_spacing_body" for fc in diff.changed)
    assert any(fc.key == "new_rule.watermark" for fc in diff.new_fields)
    assert any(fc.key == "numbering.chapter_numbering_format" for fc in diff.removed)


# --- flatten_schema() ---

def test_flatten_schema_basic():
    data = {"typography": {"font_family": "TNR", "font_size_body_pt": 12}}
    result = flatten_schema(data)
    assert result["typography.font_family"] == "TNR"
    assert result["typography.font_size_body_pt"] == 12


def test_flatten_schema_skips_sources():
    data = {
        "typography": {
            "font_family": "TNR",
            "sources": [{"chunk_index": 1}],
        }
    }
    result = flatten_schema(data)
    assert "typography.font_family" in result
    assert not any("sources" in k for k in result)


def test_flatten_schema_skips_top_level_metadata():
    data = {
        "document_type": "proposal",
        "source_document": "panduan.pdf",
        "typography": {"font_family": "TNR"},
    }
    result = flatten_schema(data)
    assert "document_type" not in result
    assert "source_document" not in result
    assert "typography.font_family" in result


def test_flatten_schema_list_serialized_as_json_string():
    data = {
        "document_structure_proposal": {
            "bab_list": [{"bab_number": "I", "title": "Pendahuluan"}]
        }
    }
    result = flatten_schema(data)
    key = "document_structure_proposal.bab_list"
    assert key in result
    parsed = json.loads(result[key])
    assert parsed[0]["title"] == "Pendahuluan"


def test_flatten_schema_bool_and_none_values_preserved():
    data = {"figures_and_tables": {"source_required_if_not_own": True, "max_width_constraint": None}}
    result = flatten_schema(data)
    assert result["figures_and_tables.source_required_if_not_own"] is True
    assert result["figures_and_tables.max_width_constraint"] is None


# --- generate_report() ---

def test_generate_report_contains_all_section_headers():
    diff = SchemaDiff(
        matched=["typography.font_family"],
        changed=[FieldChange(key="spacing.line_spacing_body", old_value="1.5", new_value="2.0")],
        new_fields=[FieldChange(key="new_rule.watermark", old_value=None, new_value=True)],
        removed=[FieldChange(key="old_rule.signatories", old_value="3", new_value=None)],
    )
    report = generate_report(diff)
    assert "Matched" in report
    assert "Changed" in report
    assert "New" in report
    assert "Removed" in report


def test_generate_report_summary_counts():
    diff = SchemaDiff(
        matched=["a", "b"],
        changed=[FieldChange("c", "x", "y")],
        new_fields=[FieldChange("d", None, "z")],
        removed=[],
    )
    report = generate_report(diff)
    assert "Matched (sama): 2" in report
    assert "Changed (berubah): 1" in report
    assert "New (baru, belum ada di schema): 1" in report
    assert "Removed (hilang dari dokumen baru): 0" in report


def test_generate_report_lists_all_keys():
    diff = SchemaDiff(
        matched=["typography.font_family"],
        changed=[FieldChange(key="spacing.line_spacing_body", old_value="1.5", new_value="2.0")],
        new_fields=[FieldChange(key="new_rule.watermark", old_value=None, new_value=True)],
        removed=[FieldChange(key="old_rule.signatories", old_value="3", new_value=None)],
    )
    report = generate_report(diff)
    assert "typography.font_family" in report
    assert "spacing.line_spacing_body" in report
    assert "new_rule.watermark" in report
    assert "old_rule.signatories" in report


# --- free_extract_all_rules() JSON parsing ---

@patch("model_ai.extractor.schema_differ.ChatGroq")
@patch("model_ai.extractor.schema_differ.render_prompt")
@patch("model_ai.extractor.schema_differ.get_config")
def test_free_extract_parses_plain_json(mock_config, mock_render, mock_llm_class):
    """LLM mengembalikan JSON polos tanpa code fence."""
    fake_response = MagicMock()
    fake_response.content = '{"typography.font_family": "TNR", "page_layout.paper_size": "A4"}'

    mock_llm_instance = MagicMock()
    mock_llm_instance.invoke.return_value = fake_response
    mock_llm_class.return_value = mock_llm_instance

    mock_config_instance = MagicMock()
    mock_config_instance.model_name = "test-model"
    mock_config_instance.groq_api_key.get_secret_value.return_value = "test-key"
    mock_config.return_value = mock_config_instance

    mock_render.return_value = "dummy prompt"

    with patch("model_ai.extractor.prompts.FREE_EXTRACTION", MagicMock(template="dummy")):
        from model_ai.extractor.schema_differ import free_extract_all_rules
        result = free_extract_all_rules([{"content": "dummy chunk"}])

    assert result["typography.font_family"] == "TNR"
    assert result["page_layout.paper_size"] == "A4"


@patch("model_ai.extractor.schema_differ.ChatGroq")
@patch("model_ai.extractor.schema_differ.render_prompt")
@patch("model_ai.extractor.schema_differ.get_config")
def test_free_extract_parses_json_code_fence(mock_config, mock_render, mock_llm_class):
    """LLM mengembalikan JSON di dalam code fence markdown."""
    fake_response = MagicMock()
    fake_response.content = '```json\n{"typography.font_size_body_pt": 12}\n```'

    mock_llm_instance = MagicMock()
    mock_llm_instance.invoke.return_value = fake_response
    mock_llm_class.return_value = mock_llm_instance

    mock_config_instance = MagicMock()
    mock_config_instance.model_name = "test-model"
    mock_config_instance.groq_api_key.get_secret_value.return_value = "test-key"
    mock_config.return_value = mock_config_instance

    mock_render.return_value = "dummy prompt"

    with patch("model_ai.extractor.prompts.FREE_EXTRACTION", MagicMock(template="dummy")):
        from model_ai.extractor.schema_differ import free_extract_all_rules
        result = free_extract_all_rules([{"content": "dummy chunk"}])

    assert result["typography.font_size_body_pt"] == 12


@patch("model_ai.extractor.schema_differ.ChatGroq")
@patch("model_ai.extractor.schema_differ.render_prompt")
@patch("model_ai.extractor.schema_differ.get_config")
def test_free_extract_returns_empty_dict_on_invalid_json(mock_config, mock_render, mock_llm_class):
    """LLM mengembalikan respons yang tidak bisa di-parse → return {}."""
    fake_response = MagicMock()
    fake_response.content = "Maaf, saya tidak dapat mengekstrak aturan dari konteks ini."

    mock_llm_instance = MagicMock()
    mock_llm_instance.invoke.return_value = fake_response
    mock_llm_class.return_value = mock_llm_instance

    mock_config_instance = MagicMock()
    mock_config_instance.model_name = "test-model"
    mock_config_instance.groq_api_key.get_secret_value.return_value = "test-key"
    mock_config.return_value = mock_config_instance

    mock_render.return_value = "dummy prompt"

    with patch("model_ai.extractor.prompts.FREE_EXTRACTION", MagicMock(template="dummy")):
        from model_ai.extractor.schema_differ import free_extract_all_rules
        result = free_extract_all_rules([{"content": "dummy chunk"}])

    assert result == {}


def test_free_extract_returns_empty_dict_for_empty_chunks():
    """Jika tidak ada chunks, tidak perlu memanggil LLM."""
    from model_ai.extractor.schema_differ import free_extract_all_rules
    result = free_extract_all_rules([])
    assert result == {}
