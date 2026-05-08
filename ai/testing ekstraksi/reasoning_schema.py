from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Literal


InputKind = Literal["output"]
ReasoningStatus = Literal["mapped", "unmapped", "needs_review"]
DecisionSource = Literal["llm", "rule_based_fallback", "not_run"]
FinalStatus = Literal["accepted", "rejected", "unmapped", "needs_review", "retrieve_failed"]
RuntimeAction = Literal["audit_only", "none"]


@dataclass
class CatalogEntry:
    id: str
    section: str
    kind: str
    path: str
    value_type: str | None = None
    description: str = ""
    enum_members: list[str] = field(default_factory=list)
    chunk_text: str = ""


@dataclass
class RetrievedChunk:
    chunk_id: str
    chunk_parent: str | None = None
    chunk_prev: str | None = None
    chunk_next: str | None = None
    path: str | None = None
    text: str = ""
    score: float = 0.0


@dataclass
class SourceFact:
    source_field: str
    source_fact: str
    input_kind: InputKind
    source_value: Any = None


@dataclass
class ReasoningCandidate:
    source_field: str
    source_fact: str
    status: ReasoningStatus
    decision_steps: list[str] = field(default_factory=list)
    target_path: str | None = None
    normalized_value: Any = None
    python_docx_expression: str | None = None
    confidence: float = 0.0
    reason: str = ""
    decision_source: DecisionSource = "llm"


@dataclass
class ReasoningValidationResult:
    source_field: str
    source_fact: str
    input_kind: InputKind
    final_status: FinalStatus
    source_value: Any = None
    target_path: str | None = None
    target_kind: str | None = None
    normalized_value: Any = None
    python_docx_expression: str | None = None
    confidence: float = 0.0
    decision_source: DecisionSource = "not_run"
    decision_steps: list[str] = field(default_factory=list)
    llm_status: ReasoningStatus | None = None
    llm_reason: str = ""
    validator_reason: str = ""
    runtime_action: RuntimeAction = "audit_only"
    retrieved_chunks: list[RetrievedChunk] = field(default_factory=list)


@dataclass
class ReasoningTranslationReport:
    generated_at: str
    inputs: dict[str, str]
    summary: dict[str, Any]
    results: list[ReasoningValidationResult]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
