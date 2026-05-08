from __future__ import annotations

from typing import Any

from reasoning_schema import CatalogEntry, ReasoningCandidate, ReasoningValidationResult, RetrievedChunk, SourceFact


_FIELD_TARGET_GUARDS: dict[str, set[str]] = {
    "typography.font_family": {"font.name"},
    "typography.heading_bold": {"font.bold", "run.bold"},
    "typography.heading_all_caps": {"font.all_caps"},
    "page_layout.margin_top_cm": {"section.top_margin"},
    "page_layout.margin_bottom_cm": {"section.bottom_margin"},
    "page_layout.margin_left_cm": {"section.left_margin"},
    "page_layout.margin_right_cm": {"section.right_margin"},
    "page_layout.orientation": {"section.orientation"},
    "spacing.line_spacing": {"paragraph_format.line_spacing"},
    "spacing.line_spacing_rule": {"paragraph_format.line_spacing_rule"},
    "spacing.paragraph_alignment": {"paragraph_format.alignment", "paragraph.alignment"},
}

_NON_DIRECT_FORMATTING_PREFIXES = (
    "document_structure_proposal.",
    "page_count_limits.",
)

_NON_DIRECT_FORMATTING_FIELDS = {
    "document_type",
    "source_document",
}


def _coerce_enum_value(value: Any) -> str:
    if isinstance(value, str):
        return value.strip().upper()
    return str(value).strip().upper()


def _parse_bool_text(value: str) -> bool | None:
    normalized = value.strip().lower()
    if normalized in {"true", "yes", "ya", "1"}:
        return True
    if normalized in {"false", "no", "tidak", "0"}:
        return False
    return None


def _parse_number_text(value: str) -> int | float | None:
    normalized = value.strip().replace(",", ".")
    if not normalized:
        return None
    try:
        number = float(normalized)
    except ValueError:
        return None
    if number.is_integer() and "." not in normalized:
        return int(number)
    return number


def _declared_type_text(declared_type: str | None) -> str:
    return (declared_type or "").lower()


def _allowed_targets_for_field(source_field: str) -> set[str] | None:
    if source_field.startswith("typography.font_size_"):
        return {"font.size"}
    return _FIELD_TARGET_GUARDS.get(source_field)


def _is_non_direct_formatting_field(source_field: str) -> bool:
    if source_field in _NON_DIRECT_FORMATTING_FIELDS:
        return True
    return any(source_field.startswith(prefix) for prefix in _NON_DIRECT_FORMATTING_PREFIXES)


def _normalize_value_for_declared_type(
    *,
    source_value: Any,
    candidate_value: Any,
    declared_type: str | None,
    enum_members: list[str],
) -> Any:
    type_text = _declared_type_text(declared_type)
    value = source_value if source_value is not None else candidate_value

    if value is None:
        return candidate_value

    if enum_members:
        return _coerce_enum_value(candidate_value if candidate_value is not None else value)

    if "bool" in type_text or "boolean" in type_text:
        if isinstance(value, bool):
            return value
        if isinstance(candidate_value, bool):
            return candidate_value
        if isinstance(value, str):
            parsed = _parse_bool_text(value)
            if parsed is not None:
                return parsed
        if isinstance(candidate_value, str):
            parsed = _parse_bool_text(candidate_value)
            if parsed is not None:
                return parsed
        return candidate_value

    if "int" in type_text and "float" not in type_text:
        if isinstance(value, int) and not isinstance(value, bool):
            return value
        if isinstance(candidate_value, int) and not isinstance(candidate_value, bool):
            return candidate_value
        if isinstance(value, str):
            parsed = _parse_number_text(value)
            if isinstance(parsed, int):
                return parsed
        if isinstance(candidate_value, str):
            parsed = _parse_number_text(candidate_value)
            if isinstance(parsed, int):
                return parsed
        return candidate_value

    if "float" in type_text or "length" in type_text:
        if isinstance(value, (int, float)) and not isinstance(value, bool):
            return value
        if isinstance(candidate_value, (int, float)) and not isinstance(candidate_value, bool):
            return candidate_value
        if isinstance(value, str):
            parsed = _parse_number_text(value)
            if parsed is not None:
                return parsed
        if isinstance(candidate_value, str):
            parsed = _parse_number_text(candidate_value)
            if parsed is not None:
                return parsed
        return candidate_value

    return candidate_value


def _matches_declared_type(value: Any, declared_type: str | None, enum_members: list[str]) -> bool:
    if value is None:
        return declared_type is None or "none" in declared_type.lower()
    if declared_type is None:
        return True

    type_text = _declared_type_text(declared_type)
    if enum_members:
        return _coerce_enum_value(value) in {member.upper() for member in enum_members}
    if "bool" in type_text or "boolean" in type_text:
        return isinstance(value, bool)
    if "int" in type_text and "float" not in type_text:
        return isinstance(value, int) and not isinstance(value, bool)
    if "float" in type_text or "length" in type_text:
        return isinstance(value, (int, float)) and not isinstance(value, bool)
    if "string" in type_text or "str" in type_text:
        return isinstance(value, str)
    return True


def _base_result(
    *,
    fact: SourceFact,
    candidate: ReasoningCandidate,
    retrieved_chunks: list[RetrievedChunk],
    final_status: str,
    validator_reason: str,
    target_kind: str | None = None,
    runtime_action: str = "audit_only",
) -> ReasoningValidationResult:
    return ReasoningValidationResult(
        source_field=fact.source_field,
        source_value=fact.source_value,
        source_fact=fact.source_fact,
        input_kind=fact.input_kind,
        final_status=final_status,  # type: ignore[arg-type]
        target_path=candidate.target_path,
        target_kind=target_kind,
        normalized_value=candidate.normalized_value,
        python_docx_expression=candidate.python_docx_expression,
        confidence=candidate.confidence,
        decision_source=candidate.decision_source,
        decision_steps=candidate.decision_steps,
        llm_status=candidate.status,
        llm_reason=candidate.reason,
        validator_reason=validator_reason,
        runtime_action=runtime_action,  # type: ignore[arg-type]
        retrieved_chunks=retrieved_chunks,
    )


def validate_reasoning_candidate(
    *,
    fact: SourceFact,
    candidate: ReasoningCandidate,
    entries_by_path: dict[str, CatalogEntry],
    retrieved_chunks: list[RetrievedChunk],
    confidence_threshold: float = 0.55,
) -> ReasoningValidationResult:
    if candidate.source_field != fact.source_field:
        return _base_result(
            fact=fact,
            candidate=candidate,
            retrieved_chunks=retrieved_chunks,
            final_status="rejected",
            runtime_action="none",
            validator_reason="source_field dari kandidat tidak sama dengan source_field input.",
        )

    if candidate.status == "unmapped":
        return _base_result(
            fact=fact,
            candidate=candidate,
            retrieved_chunks=retrieved_chunks,
            final_status="unmapped",
            runtime_action="none",
            validator_reason="Tidak ada target python-docx yang cukup jelas untuk fakta ini.",
        )

    if not candidate.target_path:
        return _base_result(
            fact=fact,
            candidate=candidate,
            retrieved_chunks=retrieved_chunks,
            final_status="rejected",
            runtime_action="none",
            validator_reason="target_path kosong.",
        )

    entry = entries_by_path.get(candidate.target_path)
    if entry is None:
        return _base_result(
            fact=fact,
            candidate=candidate,
            retrieved_chunks=retrieved_chunks,
            final_status="rejected",
            runtime_action="none",
            validator_reason="target_path tidak ada di python_docx_full_dictionary.yaml.",
        )

    allowed_targets = _allowed_targets_for_field(fact.source_field)
    if allowed_targets is not None and candidate.target_path not in allowed_targets:
        return _base_result(
            fact=fact,
            candidate=candidate,
            retrieved_chunks=retrieved_chunks,
            final_status="needs_review",
            target_kind=entry.kind,
            runtime_action="none",
            validator_reason=(
                "target_path ada di dictionary, tetapi tidak sesuai guard field formatting: "
                f"{fact.source_field} hanya boleh menuju {sorted(allowed_targets)}."
            ),
        )

    if _is_non_direct_formatting_field(fact.source_field):
        return _base_result(
            fact=fact,
            candidate=candidate,
            retrieved_chunks=retrieved_chunks,
            final_status="needs_review",
            target_kind=entry.kind,
            runtime_action="none",
            validator_reason=(
                "Field ini bukan instruksi formatting langsung dari document_metadata.payload, sehingga mapping "
                "ke properti python-docx perlu review manual."
            ),
        )

    candidate.normalized_value = _normalize_value_for_declared_type(
        source_value=fact.source_value,
        candidate_value=candidate.normalized_value,
        declared_type=entry.value_type,
        enum_members=entry.enum_members,
    )

    if not _matches_declared_type(candidate.normalized_value, entry.value_type, entry.enum_members):
        return _base_result(
            fact=fact,
            candidate=candidate,
            retrieved_chunks=retrieved_chunks,
            final_status="rejected",
            target_kind=entry.kind,
            runtime_action="none",
            validator_reason=f"Tipe nilai tidak cocok dengan tipe dictionary: {entry.value_type}.",
        )

    if candidate.status == "needs_review" or candidate.confidence < confidence_threshold:
        return _base_result(
            fact=fact,
            candidate=candidate,
            retrieved_chunks=retrieved_chunks,
            final_status="needs_review",
            target_kind=entry.kind,
            validator_reason="Target valid, tetapi confidence rendah atau kandidat meminta review.",
        )

    return _base_result(
        fact=fact,
        candidate=candidate,
        retrieved_chunks=retrieved_chunks,
        final_status="accepted",
        target_kind=entry.kind,
        validator_reason=(
            "target_path ada di dictionary dan nilai lolos validasi tipe dasar. "
            "Hasil tetap audit_only karena pipeline ini tidak mengubah docx_renderer."
        ),
    )
