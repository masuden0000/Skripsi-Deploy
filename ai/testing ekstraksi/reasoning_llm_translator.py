from __future__ import annotations

import json
import re
from typing import Any

from reasoning_schema import ReasoningCandidate, RetrievedChunk


def _safe_json(value: Any, *, limit: int = 2500) -> str:
    text = json.dumps(value, ensure_ascii=False)
    if len(text) <= limit:
        return text
    return text[:limit] + "...[truncated]"


def _extract_json_object(text: str) -> dict[str, Any]:
    text = text.strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?", "", text, flags=re.IGNORECASE).strip()
        text = re.sub(r"```$", "", text).strip()
    match = re.search(r"\{.*\}", text, flags=re.DOTALL)
    if not match:
        raise ValueError("LLM tidak mengembalikan JSON object.")
    payload = json.loads(match.group(0))
    if not isinstance(payload, dict):
        raise ValueError("Output LLM harus JSON object.")
    return payload


class LLMReasoningTranslator:
    def __init__(self, *, groq_api_key: str, model_name: str, temperature: float) -> None:
        from langchain_groq import ChatGroq

        self.llm = ChatGroq(
            model=model_name,
            temperature=temperature,
            api_key=groq_api_key,
        )

    def translate(
        self,
        *,
        source_field: str,
        source_value: Any,
        source_fact: str,
        input_kind: str,
        retrieved_chunks: list[RetrievedChunk],
    ) -> ReasoningCandidate:
        allowed_paths = [chunk.path for chunk in retrieved_chunks if chunk.path]
        catalog_context = "\n\n---\n\n".join(chunk.text for chunk in retrieved_chunks)

        prompt = f"""
Kamu menerjemahkan fakta formatting ke properti python-docx.

Balas hanya JSON object dengan shape ini:
{{
  "source_field": "...",
  "source_fact": "...",
  "status": "mapped | unmapped | needs_review",
  "decision_steps": ["..."],
  "target_path": "path dari allowed_target_paths atau null",
  "normalized_value": 12,
  "python_docx_expression": "contoh Pt(12), True, atau null",
  "confidence": 0.0,
  "reason": "alasan singkat"
}}

Aturan wajib:
- Gunakan hanya source_fact, source_value, dan dictionary_context di bawah ini.
- Jangan memakai pengetahuan bebas di luar konteks dictionary.
- Input yang diterjemahkan adalah document_metadata.payload, bukan output_chunks.json.
- target_path harus persis salah satu dari allowed_target_paths.
- Jika tidak ada padanan jelas, status harus "unmapped" dan target_path harus null.
- Jika ada padanan tetapi masih meragukan, status harus "needs_review".
- decision_steps berisi 2 sampai 5 langkah pendek.
- python_docx_expression hanya teks audit, bukan kode yang akan dieksekusi.
- normalized_value harus mempertahankan tipe JSON dari source_value jika cocok.
- Angka harus JSON number, contoh 12 atau 1.15, bukan string "12" atau "1.15".
- Boolean harus JSON boolean, contoh true atau false, bukan string "True".
- Enum boleh string, contoh "JUSTIFY".
- Guard mapping formatting:
  - typography.font_size_* hanya boleh dipetakan ke font.size.
  - typography.heading_bold hanya boleh dipetakan ke font.bold atau run.bold.
  - spacing.line_spacing hanya boleh dipetakan ke paragraph_format.line_spacing.
  - spacing.paragraph_alignment hanya boleh dipetakan ke alignment paragraph.
  - page_count_limits.* bukan instruksi formatting langsung; gunakan needs_review atau unmapped jika target tidak jelas.
- source_field dan source_fact harus sama persis dengan input.

source_field:
{source_field}

source_fact:
{source_fact}

source_value:
{_safe_json(source_value)}

input_kind:
{input_kind}

allowed_target_paths:
{json.dumps(allowed_paths, ensure_ascii=False, indent=2)}

dictionary_context:
{catalog_context}
""".strip()

        response = self.llm.invoke(prompt)
        content = response.content if hasattr(response, "content") else str(response)
        payload = _extract_json_object(str(content))
        return ReasoningCandidate(
            source_field=str(payload.get("source_field", source_field)),
            source_fact=str(payload.get("source_fact", source_fact)),
            status=payload.get("status", "needs_review"),
            decision_steps=[str(item) for item in payload.get("decision_steps", [])],
            target_path=payload.get("target_path"),
            normalized_value=payload.get("normalized_value"),
            python_docx_expression=payload.get("python_docx_expression"),
            confidence=float(payload.get("confidence", 0.0) or 0.0),
            reason=str(payload.get("reason", "")),
            decision_source="llm",
        )
