from __future__ import annotations

import argparse
import json
import math
import os
import re
import sys
from collections import Counter
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

try:
    from dotenv import load_dotenv
except Exception:  # pragma: no cover - fallback untuk environment minimal
    def load_dotenv(*_: Any, **__: Any) -> None:
        return None

from reasoning_llm_translator import LLMReasoningTranslator
from reasoning_schema import (
    CatalogEntry,
    ReasoningCandidate,
    ReasoningTranslationReport,
    RetrievedChunk,
    SourceFact,
)
from reasoning_validator import validate_reasoning_candidate


SCRIPT_DIR = Path(__file__).resolve().parent
APP_DIR = SCRIPT_DIR.parent
if str(APP_DIR) not in sys.path:
    sys.path.insert(0, str(APP_DIR))
DATA_DIR = APP_DIR / "data"
DEFAULT_DICTIONARY = DATA_DIR / "python_docx_full_dictionary.yaml"
DEFAULT_REPORT = SCRIPT_DIR / "reasoning_translation_report.json"
DEFAULT_CATALOG_CHUNKS = SCRIPT_DIR / "python_docx_catalog_chunks.json"
EMBEDDING_DIMENSION = 768


@dataclass
class RetrievalOutcome:
    status: str
    chunks: list[RetrievedChunk]
    error: str | None = None


def _load_json(path: Path) -> Any:
    if not path.exists():
        raise FileNotFoundError(f"Input JSON tidak ditemukan: {path}")
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _detect_input_kind(payload: Any) -> str:
    if isinstance(payload, dict):
        return "output"
    raise ValueError(
        "Pipeline reasoning hanya menerima JSON object metadata dari document_metadata.payload."
    )


def _load_metadata_payload(source_doc: str) -> dict[str, Any]:
    from model_ai.metadata_repository import load_document_metadata_payload

    return load_document_metadata_payload(source_doc)


def _parse_text_line(text: str, prefix: str) -> str | None:
    for line in text.splitlines():
        if line.startswith(prefix):
            return line[len(prefix) :].strip()
    return None


def _load_catalog_entries_and_chunks(chunks_path: Path) -> tuple[list[CatalogEntry], list[RetrievedChunk]]:
    if not chunks_path.exists():
        raise FileNotFoundError(f"File chunk catalog tidak ditemukan: {chunks_path}")

    payload = json.loads(chunks_path.read_text(encoding="utf-8-sig"))
    if not isinstance(payload, list):
        raise ValueError("File chunk catalog harus berisi list JSON.")

    chunks: list[RetrievedChunk] = []
    entries_by_path: dict[str, CatalogEntry] = {}
    for item in payload:
        if not isinstance(item, dict):
            continue

        text = str(item.get("text", ""))
        path = str(item.get("path") or _parse_text_line(text, "path=") or "")
        if not path:
            continue

        section = str(item.get("section") or _parse_text_line(text, "section=") or "")
        kind = str(_parse_text_line(text, "kind=") or "property")
        value_type = _parse_text_line(text, "type=")
        description = _parse_text_line(text, "description=") or ""
        enum_members_raw = _parse_text_line(text, "enum_members=") or ""
        enum_members = [member.strip() for member in enum_members_raw.split(",") if member.strip()]

        chunk = RetrievedChunk(
            chunk_id=str(item.get("chunk_id", "")),
            chunk_parent=item.get("chunk_parent"),
            chunk_prev=item.get("chunk_prev"),
            chunk_next=item.get("chunk_next"),
            path=path,
            text=text,
            score=0.0,
        )
        chunks.append(chunk)

        entries_by_path.setdefault(
            path,
            CatalogEntry(
                id=str(item.get("chunk_parent") or f"{kind}::{path}"),
                section=section,
                kind=kind,
                path=path,
                value_type=value_type,
                description=description,
                enum_members=enum_members,
                chunk_text=text,
            ),
        )

    return list(entries_by_path.values()), chunks


def _tokenize(text: str) -> set[str]:
    return {token for token in re.findall(r"[a-zA-Z0-9_]+", text.lower()) if token}


def _lexical_score(query: str, document_text: str) -> float:
    query_tokens = _tokenize(query)
    document_tokens = _tokenize(document_text)
    if not query_tokens or not document_tokens:
        return 0.0
    return len(query_tokens & document_tokens) / max(len(query_tokens), 1)


def _cosine_similarity(left: list[float], right: list[float]) -> float:
    if not left or not right or len(left) != len(right):
        return 0.0
    dot = sum(a * b for a, b in zip(left, right))
    left_norm = math.sqrt(sum(a * a for a in left))
    right_norm = math.sqrt(sum(b * b for b in right))
    if left_norm == 0.0 or right_norm == 0.0:
        return 0.0
    return dot / (left_norm * right_norm)


class DictionaryRetriever:
    def __init__(
        self,
        chunks: list[RetrievedChunk],
        *,
        mode: str,
        google_api_key: str | None,
        embedding_model_name: str | None,
    ) -> None:
        self.chunks = chunks
        self.mode = mode
        self.google_api_key = google_api_key
        self.embedding_model_name = embedding_model_name
        self.vectors: list[list[float] | None] = [None for _ in chunks]
        self.build_error: str | None = None

        if self.mode == "embedding":
            self._build_embedding_index()

    def _build_embedding_index(self) -> None:
        if not self.google_api_key or not self.embedding_model_name:
            self.build_error = "GOOGLE_API_KEY atau EMBEDDING_MODEL_NAME belum tersedia."
            return

        try:
            from langchain_google_genai import GoogleGenerativeAIEmbeddings

            embedder = GoogleGenerativeAIEmbeddings(
                model=self.embedding_model_name,
                google_api_key=self.google_api_key,
            )
            embedded = embedder.embed_documents(
                [chunk.text for chunk in self.chunks],
                output_dimensionality=EMBEDDING_DIMENSION,
            )
            self.vectors = [list(vector) for vector in embedded]
        except Exception as exc:
            self.build_error = str(exc)

    def retrieve(self, query: str, *, top_k: int) -> RetrievalOutcome:
        if self.mode == "embedding" and self.build_error:
            return RetrievalOutcome(status="retrieve_failed", chunks=[], error=self.build_error)
        if self.mode == "embedding":
            return self._retrieve_embedding(query, top_k=top_k)
        return RetrievalOutcome(status="ok", chunks=self._retrieve_lexical(query, top_k=top_k))

    def _retrieve_embedding(self, query: str, *, top_k: int) -> RetrievalOutcome:
        try:
            from langchain_google_genai import GoogleGenerativeAIEmbeddings

            embedder = GoogleGenerativeAIEmbeddings(
                model=self.embedding_model_name,
                google_api_key=self.google_api_key,
            )
            query_vector = embedder.embed_query(query, output_dimensionality=EMBEDDING_DIMENSION)
        except Exception as exc:
            return RetrievalOutcome(status="retrieve_failed", chunks=[], error=str(exc))

        scored: list[tuple[float, RetrievedChunk]] = []
        for chunk, vector in zip(self.chunks, self.vectors):
            if vector is None:
                continue
            scored.append((_cosine_similarity(query_vector, vector), chunk))

        scored.sort(key=lambda item: item[0], reverse=True)
        return RetrievalOutcome(
            status="ok",
            chunks=[
                RetrievedChunk(**{**chunk.__dict__, "score": score})
                for score, chunk in scored[:top_k]
                if score > 0.0
            ],
        )

    def _retrieve_lexical(self, query: str, *, top_k: int) -> list[RetrievedChunk]:
        scored = [(_lexical_score(query, chunk.text), chunk) for chunk in self.chunks]
        scored.sort(key=lambda item: item[0], reverse=True)
        return [
            RetrievedChunk(**{**chunk.__dict__, "score": score})
            for score, chunk in scored[:top_k]
            if score > 0.0
        ]


def _flatten_output_parameters(data: Any, prefix: str = "") -> dict[str, Any]:
    if isinstance(data, dict):
        result: dict[str, Any] = {}
        for key, value in data.items():
            if key == "sources":
                continue
            next_prefix = f"{prefix}.{key}" if prefix else str(key)
            result.update(_flatten_output_parameters(value, next_prefix))
        return result
    if isinstance(data, list):
        return {prefix: data}
    return {prefix: data}


def _format_value(value: Any) -> str:
    text = json.dumps(value, ensure_ascii=False)
    if len(text) > 500:
        return text[:500] + "...[truncated]"
    return text


def _output_source_fact(field_name: str, value: Any) -> SourceFact:
    key = field_name.lower()
    if "font_size" in key:
        target = "body" if "body" in key else "heading" if "heading" in key else "teks"
        fact = f"Field {field_name} menyatakan ukuran font {target} adalah {value} pt."
    elif "font_family" in key:
        fact = f"Field {field_name} menyatakan jenis font adalah {value}."
    elif "line_spacing" in key:
        fact = f"Field {field_name} menyatakan spasi baris adalah {value}."
    elif "alignment" in key:
        fact = f"Field {field_name} menyatakan alignment paragraf adalah {value}."
    elif "bold" in key:
        fact = f"Field {field_name} menyatakan format bold bernilai {value}."
    elif "all_caps" in key:
        fact = f"Field {field_name} menyatakan format all caps bernilai {value}."
    elif key.startswith("page_layout.margin_"):
        side = key.removeprefix("page_layout.margin_").removesuffix("_cm")
        fact = f"Field {field_name} menyatakan margin {side} adalah {value} cm."
    else:
        fact = f"Field {field_name} memiliki nilai {_format_value(value)}."
    return SourceFact(source_field=field_name, source_value=value, source_fact=fact, input_kind="output")


def _clean_markdown_text(value: str) -> str:
    text = re.sub(r"[*_`#]+", "", value)
    return re.sub(r"\s+", " ", text).strip()


def _build_source_facts(payload: Any, input_kind: str) -> list[SourceFact]:
    if not isinstance(payload, dict):
        raise ValueError(
            "input-kind output membutuhkan JSON object dari document_metadata.payload."
        )
    return [_output_source_fact(field, value) for field, value in _flatten_output_parameters(payload).items()]


def _query_for_fact(fact: SourceFact) -> str:
    return f"{fact.source_field}: {fact.source_fact}\nvalue: {_format_value(fact.source_value)}"


def _env_float(name: str, default: float) -> float:
    raw = os.getenv(name, "").strip()
    if not raw:
        return default
    return float(raw)


def _disable_blackhole_proxies() -> None:
    proxy_keys = ["HTTP_PROXY", "HTTPS_PROXY", "ALL_PROXY", "http_proxy", "https_proxy", "all_proxy"]
    blackhole_targets = {"http://127.0.0.1:9", "https://127.0.0.1:9"}
    for key in proxy_keys:
        if os.getenv(key, "").strip().lower() in blackhole_targets:
            os.environ.pop(key, None)


def _as_number(value: Any) -> int | float | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return value
    if isinstance(value, str):
        match = re.search(r"([0-9]+(?:[,.][0-9]+)?)", value)
        if match:
            number = float(match.group(1).replace(",", "."))
            return int(number) if number.is_integer() else number
    return None


def _first_available_path(entries_by_path: dict[str, Any], *paths: str) -> str | None:
    for path in paths:
        if path in entries_by_path:
            return path
    return None


def _margin_target_path(source_field: str) -> str | None:
    margin_targets = {
        "page_layout.margin_top_cm": "section.top_margin",
        "page_layout.margin_bottom_cm": "section.bottom_margin",
        "page_layout.margin_left_cm": "section.left_margin",
        "page_layout.margin_right_cm": "section.right_margin",
    }
    return margin_targets.get(source_field)


def _fallback_candidate(fact: SourceFact, entries_by_path: dict[str, Any], *, reason: str) -> ReasoningCandidate:
    key = fact.source_field.lower()
    text = f"{fact.source_fact} {_format_value(fact.source_value)}".lower()

    margin_target = _margin_target_path(fact.source_field)
    margin_value = _as_number(fact.source_value)
    if margin_target and margin_value is not None:
        target_path = _first_available_path(entries_by_path, margin_target)
        if target_path:
            side = fact.source_field.removeprefix("page_layout.margin_").removesuffix("_cm")
            return ReasoningCandidate(
                source_field=fact.source_field,
                source_fact=fact.source_fact,
                decision_steps=[
                    f"Fakta diklasifikasikan sebagai margin halaman sisi {side}.",
                    f"Margin {side} di python-docx dikontrol lewat {target_path}.",
                    f"Nilai cm diaudit sebagai Cm({margin_value}).",
                ],
                status="mapped",
                target_path=target_path,
                normalized_value=margin_value,
                python_docx_expression=f"Cm({margin_value})",
                confidence=0.72,
                reason=reason,
                decision_source="rule_based_fallback",
            )

    font_size = _as_number(fact.source_value)
    if font_size is not None and ("font_size" in key or "ukuran font" in text or "ukuran huruf" in text):
        target_path = _first_available_path(entries_by_path, "font.size")
        if target_path:
            return ReasoningCandidate(
                source_field=fact.source_field,
                source_fact=fact.source_fact,
                decision_steps=[
                    "Fakta diklasifikasikan sebagai ukuran font.",
                    "Ukuran font di python-docx dikontrol lewat font.size.",
                    f"Nilai pt diaudit sebagai Pt({font_size}).",
                ],
                status="mapped",
                target_path=target_path,
                normalized_value=font_size,
                python_docx_expression=f"Pt({font_size})",
                confidence=0.72,
                reason=reason,
                decision_source="rule_based_fallback",
            )

    if "font_family" in key or "times new roman" in text or "jenis font" in text:
        target_path = _first_available_path(entries_by_path, "font.name")
        if target_path:
            value = fact.source_value if isinstance(fact.source_value, str) else "Times New Roman"
            return ReasoningCandidate(
                source_field=fact.source_field,
                source_fact=fact.source_fact,
                decision_steps=[
                    "Fakta diklasifikasikan sebagai nama typeface.",
                    "Nama font di python-docx dikontrol lewat font.name.",
                    "Nilai disimpan sebagai string audit.",
                ],
                status="mapped",
                target_path=target_path,
                normalized_value=value,
                python_docx_expression=repr(value),
                confidence=0.72,
                reason=reason,
                decision_source="rule_based_fallback",
            )

    if "line_spacing" in key or "spasi baris" in text:
        spacing = _as_number(fact.source_value)
        target_path = _first_available_path(entries_by_path, "paragraph_format.line_spacing")
        if spacing is not None and target_path:
            return ReasoningCandidate(
                source_field=fact.source_field,
                source_fact=fact.source_fact,
                decision_steps=[
                    "Fakta diklasifikasikan sebagai spasi baris.",
                    "Spasi baris di python-docx dikontrol lewat paragraph_format.line_spacing.",
                    "Nilai numeric disimpan sebagai audit, bukan dieksekusi langsung.",
                ],
                status="mapped",
                target_path=target_path,
                normalized_value=spacing,
                python_docx_expression=str(spacing),
                confidence=0.70,
                reason=reason,
                decision_source="rule_based_fallback",
            )

    if "alignment" in key or "rata kiri kanan" in text or "justify" in text:
        target_path = _first_available_path(entries_by_path, "paragraph_format.alignment")
        if target_path:
            return ReasoningCandidate(
                source_field=fact.source_field,
                source_fact=fact.source_fact,
                decision_steps=[
                    "Fakta diklasifikasikan sebagai alignment paragraf.",
                    "Alignment paragraf di python-docx dikontrol lewat paragraph_format.alignment.",
                    "Nilai JUSTIFY cocok untuk rata kiri kanan.",
                ],
                status="mapped",
                target_path=target_path,
                normalized_value="JUSTIFY",
                python_docx_expression="WD_ALIGN_PARAGRAPH.JUSTIFY",
                confidence=0.70,
                reason=reason,
                decision_source="rule_based_fallback",
            )

    if "bold" in key or "cetak tebal" in text:
        target_path = _first_available_path(entries_by_path, "font.bold", "run.bold")
        if target_path:
            return ReasoningCandidate(
                source_field=fact.source_field,
                source_fact=fact.source_fact,
                decision_steps=[
                    "Fakta diklasifikasikan sebagai teks bold.",
                    "Bold dapat diaudit lewat font.bold atau run.bold.",
                    "Nilai boolean True dipakai karena fakta menunjukkan cetak tebal.",
                ],
                status="mapped",
                target_path=target_path,
                normalized_value=True,
                python_docx_expression="True",
                confidence=0.64,
                reason=reason,
                decision_source="rule_based_fallback",
            )

    if "all_caps" in key or "huruf kapital" in text:
        target_path = _first_available_path(entries_by_path, "font.all_caps")
        if target_path:
            return ReasoningCandidate(
                source_field=fact.source_field,
                source_fact=fact.source_fact,
                decision_steps=[
                    "Fakta diklasifikasikan sebagai kapitalisasi teks.",
                    "All caps di python-docx dikontrol lewat font.all_caps.",
                    "Nilai boolean True dipakai untuk audit.",
                ],
                status="mapped",
                target_path=target_path,
                normalized_value=True,
                python_docx_expression="True",
                confidence=0.64,
                reason=reason,
                decision_source="rule_based_fallback",
            )

    return ReasoningCandidate(
        source_field=fact.source_field,
        source_fact=fact.source_fact,
        decision_steps=[
            "Fakta tidak cocok dengan rule fallback formatting yang aman.",
            "Pipeline tidak membuat mapping agar tidak mengarang properti python-docx.",
        ],
        status="unmapped",
        confidence=0.0,
        reason=reason,
        decision_source="rule_based_fallback",
    )


def _build_translator(args: argparse.Namespace) -> tuple[LLMReasoningTranslator | None, str]:
    if args.no_llm:
        return None, "LLM dimatikan lewat --no-llm."

    groq_api_key = os.getenv("GROQ_API_KEY", "").strip()
    model_name = args.model or os.getenv("MODEL_NAME", "").strip()
    if not groq_api_key:
        return None, "GROQ_API_KEY belum tersedia; memakai fallback rule-based audit."
    if not model_name:
        return None, "MODEL_NAME belum tersedia; memakai fallback rule-based audit."

    try:
        return (
            LLMReasoningTranslator(
                groq_api_key=groq_api_key,
                model_name=model_name,
                temperature=args.temperature if args.temperature is not None else _env_float("TEMPERATURE", 0.0),
            ),
            "LLM aktif.",
        )
    except Exception as exc:
        return None, f"LLM gagal diinisialisasi; memakai fallback rule-based audit. Detail: {_safe_error_detail(exc)}"


def _safe_error_detail(exc: Exception) -> str:
    message = str(exc)
    normalized = message.lower()
    if "rate_limit" in normalized or "rate limit" in normalized or "429" in normalized:
        return "Rate limit LLM tercapai; jalankan ulang nanti atau gunakan --no-llm."
    if len(message) > 220:
        return message[:220] + "...[truncated]"
    return message


def _is_rate_limit_error(exc: Exception) -> bool:
    message = str(exc).lower()
    return "rate_limit" in message or "rate limit" in message or "429" in message


def run_pipeline(args: argparse.Namespace) -> ReasoningTranslationReport:
    load_dotenv(dotenv_path=APP_DIR / ".env")
    _disable_blackhole_proxies()

    dictionary_path = Path(args.dictionary)
    output_path = Path(args.output)
    catalog_chunks_path = Path(args.catalog_chunks)

    if not dictionary_path.exists():
        raise FileNotFoundError(f"Dictionary tidak ditemukan: {dictionary_path}")

    payload = _load_metadata_payload(args.source_doc)
    input_kind = _detect_input_kind(payload)
    source_facts = _build_source_facts(payload, input_kind)
    if args.max_fields:
        source_facts = source_facts[: args.max_fields]

    catalog_entries, catalog_chunks = _load_catalog_entries_and_chunks(catalog_chunks_path)
    entries_by_path = {entry.path: entry for entry in catalog_entries}

    retriever = DictionaryRetriever(
        catalog_chunks,
        mode=args.retrieval_mode,
        google_api_key=os.getenv("GOOGLE_API_KEY", "").strip() or None,
        embedding_model_name=os.getenv("EMBEDDING_MODEL_NAME", "").strip() or None,
    )
    translator, translator_status = _build_translator(args)

    results = []
    for index, fact in enumerate(source_facts, start=1):
        print(f"[reasoning-translate] {index}/{len(source_facts)} {fact.source_field}")
        retrieval = retriever.retrieve(_query_for_fact(fact), top_k=args.top_k)
        retrieved_chunks: list[RetrievedChunk] = retrieval.chunks if retrieval.status == "ok" else []

        if retrieval.status != "ok":
            candidate = _fallback_candidate(
                fact,
                entries_by_path,
                reason=f"Retrieval gagal; fallback audit digunakan. Detail: {retrieval.error or 'tidak ada detail'}",
            )
            result = validate_reasoning_candidate(
                fact=fact,
                candidate=candidate,
                entries_by_path=entries_by_path,
                retrieved_chunks=[],
            )
            if result.final_status == "unmapped":
                result.final_status = "retrieve_failed"
                result.validator_reason = (
                    "Retrieval dictionary gagal dan fallback tidak menemukan mapping aman. "
                    f"Detail: {retrieval.error or 'tidak ada detail'}"
                )
            results.append(result)
            continue

        if translator is None:
            candidate = _fallback_candidate(fact, entries_by_path, reason=translator_status)
        else:
            try:
                candidate = translator.translate(
                    source_field=fact.source_field,
                    source_value=fact.source_value,
                    source_fact=fact.source_fact,
                    input_kind=input_kind,
                    retrieved_chunks=retrieved_chunks,
                )
            except Exception as exc:
                detail = _safe_error_detail(exc)
                if _is_rate_limit_error(exc):
                    translator = None
                    translator_status = f"LLM dinonaktifkan untuk sisa run. Detail: {detail}"
                candidate = _fallback_candidate(
                    fact,
                    entries_by_path,
                    reason=f"LLM gagal menerjemahkan fakta; fallback audit digunakan. Detail: {detail}",
                )

        results.append(
            validate_reasoning_candidate(
                fact=fact,
                candidate=candidate,
                entries_by_path=entries_by_path,
                retrieved_chunks=retrieved_chunks,
            )
        )

    counts = Counter(result.final_status for result in results)
    source_counts = Counter(result.decision_source for result in results)
    summary = {
        "input_kind": input_kind,
        "total_source_facts": len(source_facts),
        "catalog_entries": len(catalog_entries),
        "catalog_chunks": len(catalog_chunks),
        "retrieval_mode": args.retrieval_mode,
        "translator_status": translator_status,
        "accepted": counts.get("accepted", 0),
        "rejected": counts.get("rejected", 0),
        "unmapped": counts.get("unmapped", 0),
        "needs_review": counts.get("needs_review", 0),
        "retrieve_failed": counts.get("retrieve_failed", 0),
        "llm_decisions": source_counts.get("llm", 0),
        "fallback_decisions": source_counts.get("rule_based_fallback", 0),
    }

    report = ReasoningTranslationReport(
        generated_at=datetime.now(timezone.utc).isoformat(),
        inputs={
            "source_doc": args.source_doc,
            "metadata_source": f"document_metadata.payload::{args.source_doc}",
            "input_kind": input_kind,
            "python_docx_dictionary": str(dictionary_path.resolve()),
            "python_docx_catalog_chunks": str(catalog_chunks_path.resolve()),
            "report": str(output_path.resolve()),
        },
        summary=summary,
        results=results,
    )

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(report.to_dict(), ensure_ascii=False, indent=2), encoding="utf-8")
    return report


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Testing ekstraksi: reasoning audit document_metadata.payload ke properti python-docx."
    )
    parser.add_argument(
        "--source-doc",
        required=True,
        help="Nama file PDF sumber yang dipakai sebagai selector document_metadata.",
    )
    parser.add_argument("--dictionary", default=str(DEFAULT_DICTIONARY), help="Path python_docx_full_dictionary.yaml.")
    parser.add_argument("--output", default=str(DEFAULT_REPORT), help="Path laporan JSON.")
    parser.add_argument("--catalog-chunks", default=str(DEFAULT_CATALOG_CHUNKS), help="Path chunk catalog python-docx.")
    parser.add_argument("--top-k", type=int, default=8, help="Jumlah potongan dictionary untuk setiap fakta.")
    parser.add_argument(
        "--retrieval-mode",
        choices=["embedding", "lexical"],
        default="lexical",
        help="Mode RAG. Default lexical agar smoke test tidak tergantung quota embedding.",
    )
    parser.add_argument("--model", default=None, help="Override MODEL_NAME dari ai/.env.")
    parser.add_argument("--temperature", type=float, default=None, help="Override TEMPERATURE dari ai/.env.")
    parser.add_argument("--max-fields", type=int, default=None, help="Batasi jumlah fakta untuk smoke test.")
    parser.add_argument("--no-llm", action="store_true", help="Paksa fallback rule-based audit tanpa memanggil LLM.")
    return parser


def main() -> None:
    parser = build_parser()
    report = run_pipeline(parser.parse_args())
    print("[reasoning-translate] selesai")
    print(json.dumps(report.summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
