"""
Fungsi: Membandingkan hasil ekstraksi terstruktur vs ekstraksi bebas untuk analisis selisih schema.

Digunakan oleh: manage.py; tests/extractor/test_schema_differ.py

Tujuan: Membantu evaluasi kualitas schema dengan diff yang bisa ditinjau.
"""
import json
import re
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

from langchain_groq import ChatGroq  # kept for potential direct use
from model_ai.config import get_config
from model_ai.extractor.doc_extractor import render_prompt, _build_llm
from model_ai.metadata_repository import load_document_metadata_payload

# ---------------------------------------------------------------------------
# Digunakan oleh: Dipakai oleh fungsi-fungsi di modul ini dan modul terkait saat import runtime.
# Blok konstanta `APP_DIR` untuk menyimpan konfigurasi/registry yang dipakai berulang.
# ---------------------------------------------------------------------------
APP_DIR = Path(__file__).resolve().parents[2]
# ---------------------------------------------------------------------------
# Digunakan oleh: Dipakai oleh fungsi-fungsi di modul ini dan modul terkait saat import runtime.
# Blok konstanta `DIFF_OUTPUT_DIR` untuk menyimpan konfigurasi/registry yang dipakai berulang.
# ---------------------------------------------------------------------------
DIFF_OUTPUT_DIR = APP_DIR / "data"

# ---------------------------------------------------------------------------
# Digunakan oleh: Dipakai oleh fungsi-fungsi di modul ini dan modul terkait saat import runtime.
# Blok konstanta `_SKIP_KEYS` untuk menyimpan konfigurasi/registry yang dipakai berulang.
# ---------------------------------------------------------------------------
_SKIP_KEYS = {"sources", "document_type", "source_document"}


# ---------------------------------------------------------------------------
# Digunakan oleh: Dipakai internal di file ini atau dipanggil dari entrypoint runtime.
# Mendefinisikan class `FieldChange` untuk kebutuhan modul `schema_differ`.
# ---------------------------------------------------------------------------
@dataclass
class FieldChange:
    key: str
    old_value: Any
    new_value: Any


# ---------------------------------------------------------------------------
# Digunakan oleh: Dipakai internal di file ini atau dipanggil dari entrypoint runtime.
# Mendefinisikan class `SchemaDiff` untuk kebutuhan modul `schema_differ`.
# ---------------------------------------------------------------------------
@dataclass
class SchemaDiff:
    matched: list[str] = field(default_factory=list)
    changed: list[FieldChange] = field(default_factory=list)
    new_fields: list[FieldChange] = field(default_factory=list)
    removed: list[FieldChange] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Digunakan oleh: Dipakai internal di file ini atau dipanggil dari entrypoint runtime.
# Menjalankan fungsi `_normalize` sebagai bagian alur `schema_differ`.
# ---------------------------------------------------------------------------
def _normalize(value: Any) -> str:
    if value is None:
        return ""
    return str(value).strip().lower()


# ---------------------------------------------------------------------------
# Digunakan oleh: Dipakai internal di file ini atau dipanggil dari entrypoint runtime.
# Menjalankan fungsi `flatten_schema` sebagai bagian alur `schema_differ`.
# ---------------------------------------------------------------------------
def flatten_schema(data: dict[str, Any], prefix: str = "") -> dict[str, Any]:
    """Flatten nested dict to dotted key notation, skipping source/metadata keys."""
    result: dict[str, Any] = {}
    for k, v in data.items():
        if k in _SKIP_KEYS:
            continue
        full_key = f"{prefix}.{k}" if prefix else k
        if isinstance(v, dict):
            result.update(flatten_schema(v, prefix=full_key))
        elif isinstance(v, list):
            result[full_key] = json.dumps(v, ensure_ascii=False)
        else:
            result[full_key] = v
    return result


# ---------------------------------------------------------------------------
# Digunakan oleh: Dipakai internal di file ini atau dipanggil dari entrypoint runtime.
# Menjalankan fungsi `diff_schemas` sebagai bagian alur `schema_differ`.
# ---------------------------------------------------------------------------
def diff_schemas(old: dict[str, Any], new: dict[str, Any]) -> SchemaDiff:
    """Compare two flat schema dicts and categorize differences into 4 buckets."""
    diff = SchemaDiff()
    old_keys = set(old.keys())
    new_keys = set(new.keys())

    for key in old_keys & new_keys:
        if _normalize(old[key]) == _normalize(new[key]):
            diff.matched.append(key)
        else:
            diff.changed.append(FieldChange(key=key, old_value=old[key], new_value=new[key]))

    for key in new_keys - old_keys:
        diff.new_fields.append(FieldChange(key=key, old_value=None, new_value=new[key]))

    for key in old_keys - new_keys:
        diff.removed.append(FieldChange(key=key, old_value=old[key], new_value=None))

    return diff


# ---------------------------------------------------------------------------
# Digunakan oleh: Dipakai internal di file ini atau dipanggil dari entrypoint runtime.
# Menjalankan fungsi `load_old_schema` sebagai bagian alur `schema_differ`.
# ---------------------------------------------------------------------------
def load_old_schema(source_doc: str) -> dict[str, Any]:
    """Load and flatten the existing extraction payload from document_metadata."""
    data = load_document_metadata_payload(source_doc)
    return flatten_schema(data)


# ---------------------------------------------------------------------------
# Digunakan oleh: Dipakai internal di file ini atau dipanggil dari entrypoint runtime.
# Menjalankan fungsi `generate_report` sebagai bagian alur `schema_differ`.
# ---------------------------------------------------------------------------
def generate_report(diff: SchemaDiff) -> str:
    """Generate a human-readable markdown diff report."""
    lines = [
        "# Schema Diff Report",
        f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        "",
        "## Ringkasan",
        f"- Matched (sama): {len(diff.matched)}",
        f"- Changed (berubah): {len(diff.changed)}",
        f"- New (baru, belum ada di schema): {len(diff.new_fields)}",
        f"- Removed (hilang dari dokumen baru): {len(diff.removed)}",
        "",
    ]

    if diff.matched:
        lines += ["## Matched — Field & Nilai Sama", ""]
        for key in diff.matched:
            lines.append(f"- `{key}`")
        lines.append("")

    if diff.changed:
        lines += ["## Changed — Nilai Berubah", ""]
        for fc in diff.changed:
            lines += [
                f"- `{fc.key}`",
                f"  - Lama: `{fc.old_value}`",
                f"  - Baru: `{fc.new_value}`",
            ]
        lines.append("")

    if diff.new_fields:
        lines += ["## New — Field Baru (Belum Ada di Schema Eksplisit)", ""]
        for fc in diff.new_fields:
            lines.append(f"- `{fc.key}`: `{fc.new_value}`")
        lines.append("")

    if diff.removed:
        lines += ["## Removed — Field Tidak Ditemukan di Dokumen Baru", ""]
        for fc in diff.removed:
            lines.append(f"- `{fc.key}` (nilai lama: `{fc.old_value}`)")
        lines.append("")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Digunakan oleh: Dipakai internal di file ini atau dipanggil dari entrypoint runtime.
# Menjalankan fungsi `save_diff` sebagai bagian alur `schema_differ`.
# ---------------------------------------------------------------------------
def save_diff(diff: SchemaDiff, report: str) -> None:
    """Save diff results to timestamped JSON and markdown files."""
    DIFF_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")

    json_path = DIFF_OUTPUT_DIR / f"schema_diff_{ts}.json"
    json_path.write_text(
        json.dumps(
            {
                "matched": diff.matched,
                "changed": [
                    {"key": fc.key, "old": fc.old_value, "new": fc.new_value}
                    for fc in diff.changed
                ],
                "new_fields": [
                    {"key": fc.key, "value": fc.new_value} for fc in diff.new_fields
                ],
                "removed": [
                    {"key": fc.key, "old_value": fc.old_value} for fc in diff.removed
                ],
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    md_path = DIFF_OUTPUT_DIR / f"schema_diff_{ts}.md"
    md_path.write_text(report, encoding="utf-8")
    print(f"[schema-diff] Laporan disimpan: {json_path}")
    print(f"[schema-diff] Laporan disimpan: {md_path}")


# ---------------------------------------------------------------------------
# LLM + Supabase functions — imported lazily to avoid circular deps
# ---------------------------------------------------------------------------

def fetch_broad_chunks(source_doc: str) -> list[dict]:
    """Retrieve representative chunks via broad RAG queries for one source document."""
    from model_ai.config import get_config
    from model_ai.extractor.doc_extractor import (
        _build_embedder,
        _build_supabase,
        _expand_to_full_headers,
        _format_vector,
    )
    from model_ai.extractor.prompts import FREE_EXTRACTION

    CONFIG = get_config()
    EMBEDDING_DIMENSION = 768
    _BROAD_QUERIES = [
        "aturan format penulisan dokumen PKM tipografi huruf",
        "ketentuan struktur bab lampiran penomoran halaman",
        "persyaratan teknis layout ukuran kertas margin",
        "ketentuan gambar tabel caption sumber referensi",
        "batas halaman jumlah halaman format nama file",
    ]

    embedder = _build_embedder()
    client = _build_supabase()

    seen: dict[int, dict] = {}
    for query in _BROAD_QUERIES:
        vector = embedder.embed_query(query, output_dimensionality=EMBEDDING_DIMENSION)
        formatted = _format_vector(vector)
        result = client.rpc(
            "match_document_chunks",
            {"query_embedding": formatted, "match_count": FREE_EXTRACTION.top_k or 10},
        ).execute()
        for chunk in (result.data or []):
            if str(chunk.get("source_file") or "") != source_doc:
                continue
            idx = int(chunk["chunk_index"])
            if idx not in seen:
                seen[idx] = chunk

    seed_chunks = sorted(seen.values(), key=lambda c: c["chunk_index"])
    return _expand_to_full_headers(seed_chunks, client)


# ---------------------------------------------------------------------------
# Digunakan oleh: model_ai/extractor/prompts.py
# Menjalankan fungsi `free_extract_all_rules` sebagai bagian alur `schema_differ`.
# ---------------------------------------------------------------------------
def free_extract_all_rules(chunks: list[dict]) -> dict[str, Any]:
    """Ask LLM to freely identify all extractable rules from chunks as flat key-value JSON."""
    if not chunks:
        return {}

    from model_ai.extractor.prompts import FREE_EXTRACTION

    config = get_config()
    prompt = render_prompt(FREE_EXTRACTION.template, chunks)
    config.disable_blackhole_proxies()
    llm = _build_llm()
    result = llm.invoke(prompt)
    raw = str(result.content).strip()

    # Try extracting JSON from markdown code fence first, then plain JSON
    json_match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", raw, re.DOTALL)
    if json_match:
        raw = json_match.group(1)

    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return {}


# ---------------------------------------------------------------------------
# Digunakan oleh: manage.py
# Menjalankan fungsi `run_schema_diff` sebagai bagian alur `schema_differ`.
# ---------------------------------------------------------------------------
def run_schema_diff(source_doc: str) -> SchemaDiff:
    """Orchestrate the full schema diff pipeline."""
    print(
        f"[schema-diff] Memuat schema lama dari document_metadata untuk source_doc={source_doc}..."
    )
    old = load_old_schema(source_doc)
    print(f"[schema-diff] {len(old)} field ditemukan di schema lama.")

    print("[schema-diff] Mengambil chunks dari Supabase...")
    chunks = fetch_broad_chunks(source_doc)
    print(f"[schema-diff] {len(chunks)} chunk ditemukan.")

    print("[schema-diff] Menjalankan free extraction via LLM...")
    new = free_extract_all_rules(chunks)
    print(f"[schema-diff] {len(new)} field diekstrak secara bebas.")

    diff = diff_schemas(old, new)
    report = generate_report(diff)
    save_diff(diff, report)

    print(
        f"[schema-diff] Selesai — "
        f"Matched: {len(diff.matched)}, "
        f"Changed: {len(diff.changed)}, "
        f"New: {len(diff.new_fields)}, "
        f"Removed: {len(diff.removed)}"
    )
    return diff
