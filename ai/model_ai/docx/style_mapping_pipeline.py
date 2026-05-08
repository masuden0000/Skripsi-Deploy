"""
Fungsi: Pipeline mapping style DOCX berbasis dictionary python-docx + RAG + validasi deterministik.

Digunakan oleh: manage.py

Tujuan: Mengubah hasil ekstraksi bebas menjadi candidate mapping ke properti python-docx
secara fleksibel, namun tetap aman melalui validator + execution plan.
"""
import json
import math
import re
import time
from pathlib import Path
from typing import Any, Literal

import yaml
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from langchain_groq import ChatGroq
from pydantic import BaseModel, Field

from model_ai.config import get_config
from model_ai.extractor.models import DocumentMetadata

# ---------------------------------------------------------------------------
# Digunakan oleh: Dipakai oleh fungsi-fungsi di modul ini dan modul terkait saat import runtime.
# Blok konstanta `APP_DIR` untuk menyimpan konfigurasi/registry yang dipakai berulang.
# ---------------------------------------------------------------------------
APP_DIR = Path(__file__).resolve().parents[2]
# ---------------------------------------------------------------------------
# Digunakan oleh: Dipakai oleh fungsi-fungsi di modul ini dan modul terkait saat import runtime.
# Blok konstanta `DATA_DIR` untuk menyimpan konfigurasi/registry yang dipakai berulang.
# ---------------------------------------------------------------------------
DATA_DIR = APP_DIR / "data"
# ---------------------------------------------------------------------------
# Digunakan oleh: run_docx_style_mapping_pipeline()
# Blok konstanta default path artefak agar command CLI ringkas.
# ---------------------------------------------------------------------------
DEFAULT_DICTIONARY_PATH = DATA_DIR / "python_docx_full_dictionary.yaml"
DEFAULT_CATALOG_PATH = DATA_DIR / "python_docx_property_catalog.json"
DEFAULT_CHUNKS_PATH = DATA_DIR / "python_docx_catalog_chunks.json"
DEFAULT_INDEX_PATH = DATA_DIR / "python_docx_catalog_index.json"
DEFAULT_CANDIDATE_PATH = DATA_DIR / "docx_mapping_candidate.json"
DEFAULT_REPORT_PATH = DATA_DIR / "docx_mapping_report.json"
DEFAULT_APPLY_PLAN_PATH = DATA_DIR / "docx_apply_plan.json"

# ---------------------------------------------------------------------------
# Digunakan oleh: Dipakai oleh fungsi-fungsi di modul ini dan modul terkait saat import runtime.
# Blok konstanta `EMBEDDING_DIMENSION` untuk menyimpan konfigurasi/registry yang dipakai berulang.
# ---------------------------------------------------------------------------
EMBEDDING_DIMENSION = 768
# Google Embedding free tier: 1.500 RPM = 25 req/detik.
# Batching 30 teks per panggilan API → maks ~900 RPM, aman di bawah batas.
_EMBED_BATCH_SIZE = 30
_EMBED_BATCH_DELAY_S = 60

PageNumberPosition = Literal[
    "header_left",
    "header_center",
    "header_right",
    "footer_left",
    "footer_center",
    "footer_right",
]
ParagraphAlignmentOption = Literal["LEFT", "CENTER", "RIGHT", "JUSTIFY"]


# ---------------------------------------------------------------------------
# Digunakan oleh: model_ai/docx/docx_renderer.py; model_ai/docx/generator.py
# Mendefinisikan class `ScopedPropertyMap` untuk kebutuhan modul `style_mapping_pipeline`.
# ---------------------------------------------------------------------------
class ScopedPropertyMap(BaseModel):
    """
    Model utama output pipeline LLM→python-docx.

    Setiap scope adalah dict bebas: LLM menentukan property apa yang diset
    berdasarkan python-docx dictionary. Renderer tahu cara mengeksekusi
    property-property tersebut per scope.

    Scope = fixed (developer). Property dalam scope = dynamic (LLM).
    """
    normal_style: dict[str, Any] = Field(default_factory=dict)
    heading_1_style: dict[str, Any] = Field(default_factory=dict)
    heading_2_style: dict[str, Any] = Field(default_factory=dict)
    page_layout: dict[str, Any] = Field(default_factory=dict)
    page_number_prelim: dict[str, Any] = Field(default_factory=dict)
    page_number_content: dict[str, Any] = Field(default_factory=dict)
    caption_figure: dict[str, Any] = Field(default_factory=dict)
    caption_table: dict[str, Any] = Field(default_factory=dict)


# ---------------------------------------------------------------------------
# Digunakan oleh: model_ai/docx/docx_renderer.py; model_ai/docx/generator.py
# Mendefinisikan class `DocxStyleConfig` untuk kebutuhan modul `style_mapping_pipeline`.
# ---------------------------------------------------------------------------
class DocxStyleConfig(BaseModel):
    heading_bold: bool = False
    heading_all_caps: bool = False
    paragraph_alignment: ParagraphAlignmentOption = "JUSTIFY"
    page_number_prelim_pos: PageNumberPosition = "footer_right"
    page_number_content_pos: PageNumberPosition = "header_right"


# ---------------------------------------------------------------------------
# Digunakan oleh: propose_mappings_with_llm()
# Mendefinisikan class `LLMStyleConfigCandidate` untuk kebutuhan modul `style_mapping_pipeline`.
# ---------------------------------------------------------------------------
class LLMStyleConfigCandidate(BaseModel):
    heading_bold: bool | None = None
    heading_all_caps: bool | None = None
    paragraph_alignment: ParagraphAlignmentOption | None = None
    # Gunakan str bukan PageNumberPosition agar Groq tidak reject nilai uppercase dari LLM
    # Normalisasi ke lowercase dilakukan di propose_mappings_with_llm setelah parsing
    page_number_prelim_pos: str | None = None
    page_number_content_pos: str | None = None


# ---------------------------------------------------------------------------
# Digunakan oleh: build_docx_property_catalog()
# Mendefinisikan class `DocxCatalogEntry` untuk kebutuhan modul `style_mapping_pipeline`.
# ---------------------------------------------------------------------------
class DocxCatalogEntry(BaseModel):
    id: str
    section: str
    kind: str  # property | method | enumeration
    path: str
    value_type: str | None = None
    description: str = ""
    signature: str | None = None
    enum_name: str | None = None
    enum_members: list[str] = []
    chunk_text: str


# ---------------------------------------------------------------------------
# Digunakan oleh: build_catalog_chunks()
# Mendefinisikan class `CatalogChunk` untuk kebutuhan modul `style_mapping_pipeline`.
# ---------------------------------------------------------------------------
class CatalogChunk(BaseModel):
    chunk_id: str
    chunk_type: str  # section | property
    section: str
    path: str | None = None
    text: str


# ---------------------------------------------------------------------------
# Digunakan oleh: propose_mappings_with_llm()
# Mendefinisikan class `ProposedMapping` untuk kebutuhan modul `style_mapping_pipeline`.
# ---------------------------------------------------------------------------
class ProposedMapping(BaseModel):
    source_field: str
    target_path: str
    normalized_value: Any
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    reason: str = ""


# ---------------------------------------------------------------------------
# Digunakan oleh: propose_mappings_with_llm()
# Mendefinisikan class `MappingCandidate` untuk kebutuhan modul `style_mapping_pipeline`.
# ---------------------------------------------------------------------------
class MappingCandidate(BaseModel):
    style_config_candidate: LLMStyleConfigCandidate = Field(default_factory=LLMStyleConfigCandidate)
    mappings: list[ProposedMapping] = []
    new_found: list[dict[str, Any]] = []
    conflicts: list[dict[str, Any]] = []


# ---------------------------------------------------------------------------
# Digunakan oleh: validate_candidate_mappings()
# Mendefinisikan class `ValidatedMapping` untuk kebutuhan modul `style_mapping_pipeline`.
# ---------------------------------------------------------------------------
class ValidatedMapping(BaseModel):
    source_field: str
    target_path: str
    normalized_value: Any
    confidence: float
    reason: str
    status: str  # accepted | rejected
    rejection_reason: str | None = None


# ---------------------------------------------------------------------------
# Digunakan oleh: validate_candidate_mappings()
# Mendefinisikan class `ValidationReport` untuk kebutuhan modul `style_mapping_pipeline`.
# ---------------------------------------------------------------------------
class ValidationReport(BaseModel):
    accepted: list[ValidatedMapping] = []
    rejected: list[ValidatedMapping] = []
    new_found: list[dict[str, Any]] = []
    conflicts: list[dict[str, Any]] = []


# ---------------------------------------------------------------------------
# Digunakan oleh: build_apply_plan()
# Mendefinisikan class `ApplyPlan` untuk kebutuhan modul `style_mapping_pipeline`.
# ---------------------------------------------------------------------------
class ApplyPlan(BaseModel):
    style_config_overrides: dict[str, Any] = {}
    docx_property_overrides: dict[str, Any] = {}
    unmapped_candidates: list[dict[str, Any]] = []


# ---------------------------------------------------------------------------
# Digunakan oleh: Dipakai internal di file ini atau dipanggil dari entrypoint runtime.
# Menjalankan fungsi `_load_dictionary` sebagai bagian alur `style_mapping_pipeline`.
# ---------------------------------------------------------------------------
def _load_dictionary(dictionary_path: Path) -> dict[str, Any]:
    if not dictionary_path.exists():
        raise FileNotFoundError(f"Dictionary python-docx tidak ditemukan: {dictionary_path}")
    raw = dictionary_path.read_text(encoding="utf-8")
    try:
        data = yaml.safe_load(raw)
    except yaml.YAMLError:
        # Beberapa file dictionary membawa jejak sitasi seperti "【...】"
        # atau mojibake "ã€...ã€‘" di luar string YAML valid.
        # Sanitasi ini mempertahankan isi inti dictionary untuk parsing.
        sanitized = re.sub(r"【[^】]*】", "", raw)
        sanitized = re.sub(r"ã€.*?ã€‘", "", sanitized)
        # Beberapa baris punya titik di luar string quote, contoh:
        # description: "....".
        # Itu bukan YAML valid, jadi titik penutup dihapus.
        sanitized_lines: list[str] = []
        for line in sanitized.splitlines():
            # Jika setelah quote penutup ada teks liar, simpan bagian quoted saja.
            line = re.sub(r'^(\s*[^:#\n]+:\s*"(?:[^"\\]|\\.)*")\s+.*$', r"\1", line)
            line = re.sub(r"^(\s*[^:#\n]+:\s*'(?:[^'\\]|\\.)*')\s+.*$", r"\1", line)
            line = re.sub(r'(:\s*".*")\.\s*$', r"\1", line)
            line = re.sub(r"(:\s*'.*')\.\s*$", r"\1", line)
            sanitized_lines.append(line)
        sanitized = "\n".join(sanitized_lines)
        data = yaml.safe_load(sanitized)
    if not isinstance(data, dict):
        raise ValueError("Format dictionary python-docx tidak valid (harus object/dict).")
    return data


# ---------------------------------------------------------------------------
# Digunakan oleh: build_docx_property_catalog()
# Menjalankan fungsi `_extract_enum_members` sebagai bagian alur `style_mapping_pipeline`.
# ---------------------------------------------------------------------------
def _extract_enum_members(data: dict[str, Any]) -> dict[str, list[str]]:
    enum_root = data.get("enumerations", {})
    if not isinstance(enum_root, dict):
        return {}

    members: dict[str, list[str]] = {}
    for enum_name, enum_payload in enum_root.items():
        if not isinstance(enum_payload, dict):
            continue
        raw_members = enum_payload.get("members", [])
        if isinstance(raw_members, list):
            members[enum_name] = [str(item).strip() for item in raw_members if str(item).strip()]
    return members


# ---------------------------------------------------------------------------
# Digunakan oleh: build_docx_property_catalog()
# Menjalankan fungsi `_guess_enum_name` sebagai bagian alur `style_mapping_pipeline`.
# ---------------------------------------------------------------------------
def _guess_enum_name(value_type: str | None, description: str) -> str | None:
    joined = f"{value_type or ''} {description}".upper()
    match = re.search(r"\bWD_[A-Z_]+\b", joined)
    if match:
        return match.group(0)
    return None


# ---------------------------------------------------------------------------
# Digunakan oleh: build_docx_property_catalog()
# Menjalankan fungsi `_entry_text` sebagai bagian alur `style_mapping_pipeline`.
# ---------------------------------------------------------------------------
def _entry_text(
    section: str,
    kind: str,
    path: str,
    value_type: str | None,
    description: str,
    signature: str | None,
    enum_name: str | None,
    enum_members: list[str],
) -> str:
    lines = [
        f"section={section}",
        f"kind={kind}",
        f"path={path}",
    ]
    if value_type:
        lines.append(f"type={value_type}")
    if signature:
        lines.append(f"signature={signature}")
    if enum_name:
        lines.append(f"enum={enum_name}")
    if enum_members:
        lines.append("enum_members=" + ", ".join(enum_members))
    if description:
        lines.append("description=" + description.strip())
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Digunakan oleh: run_docx_style_mapping_pipeline()
# Menjalankan fungsi `build_docx_property_catalog` sebagai bagian alur `style_mapping_pipeline`.
# ---------------------------------------------------------------------------
def build_docx_property_catalog(dictionary_path: Path) -> list[DocxCatalogEntry]:
    data = _load_dictionary(dictionary_path)
    enum_members_map = _extract_enum_members(data)
    entries: list[DocxCatalogEntry] = []

    for section, payload in data.items():
        if section == "enumerations":
            continue
        if not isinstance(payload, dict):
            continue

        properties = payload.get("properties", {})
        if isinstance(properties, dict):
            for prop_name, prop_payload in properties.items():
                if not isinstance(prop_payload, dict):
                    continue
                value_type = str(prop_payload.get("type")) if prop_payload.get("type") is not None else None
                description = str(prop_payload.get("description", "")).strip()
                enum_name = _guess_enum_name(value_type, description)
                enum_members = enum_members_map.get(enum_name, []) if enum_name else []
                path = f"{section}.{prop_name}"
                entry = DocxCatalogEntry(
                    id=f"property::{path}",
                    section=section,
                    kind="property",
                    path=path,
                    value_type=value_type,
                    description=description,
                    enum_name=enum_name,
                    enum_members=enum_members,
                    chunk_text=_entry_text(
                        section=section,
                        kind="property",
                        path=path,
                        value_type=value_type,
                        description=description,
                        signature=None,
                        enum_name=enum_name,
                        enum_members=enum_members,
                    ),
                )
                entries.append(entry)

        methods = payload.get("methods", {})
        if isinstance(methods, dict):
            for method_name, method_payload in methods.items():
                if not isinstance(method_payload, dict):
                    continue
                signature = str(method_payload.get("signature", "")).strip() or None
                description = str(method_payload.get("description", "")).strip()
                path = f"{section}.{method_name}"
                entry = DocxCatalogEntry(
                    id=f"method::{path}",
                    section=section,
                    kind="method",
                    path=path,
                    value_type=None,
                    description=description,
                    signature=signature,
                    chunk_text=_entry_text(
                        section=section,
                        kind="method",
                        path=path,
                        value_type=None,
                        description=description,
                        signature=signature,
                        enum_name=None,
                        enum_members=[],
                    ),
                )
                entries.append(entry)

    for enum_name, members in enum_members_map.items():
        enum_path = f"enumerations.{enum_name}"
        entry = DocxCatalogEntry(
            id=f"enumeration::{enum_name}",
            section="enumerations",
            kind="enumeration",
            path=enum_path,
            value_type="enum",
            description=f"Allowed members for {enum_name}.",
            enum_name=enum_name,
            enum_members=members,
            chunk_text=_entry_text(
                section="enumerations",
                kind="enumeration",
                path=enum_path,
                value_type="enum",
                description=f"Allowed members for {enum_name}.",
                signature=None,
                enum_name=enum_name,
                enum_members=members,
            ),
        )
        entries.append(entry)

    return entries


# ---------------------------------------------------------------------------
# Digunakan oleh: run_docx_style_mapping_pipeline()
# Menjalankan fungsi `build_catalog_chunks` sebagai bagian alur `style_mapping_pipeline`.
# ---------------------------------------------------------------------------
def build_catalog_chunks(entries: list[DocxCatalogEntry]) -> list[CatalogChunk]:
    chunks: list[CatalogChunk] = []

    section_buckets: dict[str, list[DocxCatalogEntry]] = {}
    for entry in entries:
        section_buckets.setdefault(entry.section, []).append(entry)

    # Chunk level 1: per bab/section (mis. table berisi seluruh hal tentang table)
    for section, section_entries in sorted(section_buckets.items(), key=lambda item: item[0]):
        text = "\n\n".join(entry.chunk_text for entry in section_entries)
        chunks.append(
            CatalogChunk(
                chunk_id=f"section::{section}",
                chunk_type="section",
                section=section,
                text=text,
            )
        )

    # Chunk level 2: per properti/metode untuk retrieval presisi
    for entry in entries:
        chunks.append(
            CatalogChunk(
                chunk_id=f"property::{entry.path}",
                chunk_type="property",
                section=entry.section,
                path=entry.path,
                text=entry.chunk_text,
            )
        )

    return chunks


# ---------------------------------------------------------------------------
# Digunakan oleh: run_docx_style_mapping_pipeline()
# Menjalankan fungsi `save_catalog_artifacts` sebagai bagian alur `style_mapping_pipeline`.
# ---------------------------------------------------------------------------
def save_catalog_artifacts(
    entries: list[DocxCatalogEntry],
    chunks: list[CatalogChunk],
    catalog_path: Path,
    chunks_path: Path,
) -> None:
    catalog_path.parent.mkdir(parents=True, exist_ok=True)
    catalog_path.write_text(
        json.dumps([entry.model_dump() for entry in entries], ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    chunks_path.write_text(
        json.dumps([chunk.model_dump() for chunk in chunks], ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


# ---------------------------------------------------------------------------
# Digunakan oleh: build_chunk_index()
# Menjalankan fungsi `_build_embedder` sebagai bagian alur `style_mapping_pipeline`.
# ---------------------------------------------------------------------------
def _build_embedder() -> GoogleGenerativeAIEmbeddings:
    config = get_config()
    config.disable_blackhole_proxies()
    return GoogleGenerativeAIEmbeddings(
        model=config.embedding_model_name,
        google_api_key=config.require_google_api_key(),
    )


# ---------------------------------------------------------------------------
# Digunakan oleh: build_chunk_index()
# Helper untuk embed_documents bertahap agar tidak melebihi batas RPM Google free tier.
# ---------------------------------------------------------------------------
def _embed_documents_throttled(
    embedder: GoogleGenerativeAIEmbeddings,
    texts: list[str],
    batch_size: int = _EMBED_BATCH_SIZE,
    delay_s: float = _EMBED_BATCH_DELAY_S,
) -> list[list[float]]:
    """Kirim embed_documents dalam batch kecil dengan jeda antar batch.

    Google free tier: 1.500 RPM. LangChain memanggil API sekali per teks,
    sehingga 162 teks sekaligus bisa melampaui batas. Dengan batch_size=30
    dan delay_s=2.0, kecepatan efektif ~900 RPM — aman di bawah limit.
    """
    all_vectors: list[list[float]] = []
    total = len(texts)
    for i in range(0, total, batch_size):
        batch = texts[i : i + batch_size]
        batch_vectors = embedder.embed_documents(batch, output_dimensionality=EMBEDDING_DIMENSION)
        all_vectors.extend(batch_vectors)
        remaining = total - (i + batch_size)
        if remaining > 0:
            print(
                f"[embed] Batch {i // batch_size + 1} selesai ({i + len(batch)}/{total} teks). "
                f"Jeda {delay_s}s sebelum batch berikutnya..."
            )
            time.sleep(delay_s)
    return all_vectors


# ---------------------------------------------------------------------------
# Digunakan oleh: retrieve_relevant_chunks()
# Menjalankan fungsi `_tokenize` sebagai bagian alur `style_mapping_pipeline`.
# ---------------------------------------------------------------------------
def _tokenize(text: str) -> set[str]:
    return {token for token in re.findall(r"[a-zA-Z0-9_]+", text.lower()) if token}


# ---------------------------------------------------------------------------
# Digunakan oleh: retrieve_relevant_chunks()
# Menjalankan fungsi `_lexical_score` sebagai bagian alur `style_mapping_pipeline`.
# ---------------------------------------------------------------------------
def _lexical_score(query: str, document_text: str) -> float:
    q = _tokenize(query)
    d = _tokenize(document_text)
    if not q or not d:
        return 0.0
    overlap = len(q & d)
    return overlap / max(len(q), 1)


# ---------------------------------------------------------------------------
# Digunakan oleh: retrieve_relevant_chunks()
# Menjalankan fungsi `_cosine_similarity` sebagai bagian alur `style_mapping_pipeline`.
# ---------------------------------------------------------------------------
def _cosine_similarity(a: list[float], b: list[float]) -> float:
    if not a or not b or len(a) != len(b):
        return 0.0
    dot = sum(x * y for x, y in zip(a, b))
    norm_a = math.sqrt(sum(x * x for x in a))
    norm_b = math.sqrt(sum(y * y for y in b))
    if norm_a == 0.0 or norm_b == 0.0:
        return 0.0
    return dot / (norm_a * norm_b)


# ---------------------------------------------------------------------------
# Digunakan oleh: run_docx_style_mapping_pipeline()
# Menjalankan fungsi `build_chunk_index` sebagai bagian alur `style_mapping_pipeline`.
# ---------------------------------------------------------------------------
def build_chunk_index(
    chunks: list[CatalogChunk],
    index_path: Path,
    with_embeddings: bool = True,
    force_rebuild: bool = False,
) -> list[dict[str, Any]]:
    # Cache hit: kembalikan index dari disk jika sudah ada dan valid.
    if not force_rebuild and index_path.exists():
        try:
            cached = json.loads(index_path.read_text(encoding="utf-8"))
            if cached and (not with_embeddings or cached[0].get("embedding") is not None):
                print(f"[embed] Cache hit: memuat {len(cached)} baris dari {index_path.name}")
                return cached
        except Exception:
            pass  # cache korup → lanjut rebuild

    texts = [chunk.text for chunk in chunks]
    index_rows: list[dict[str, Any]] = []

    vectors: list[list[float] | None]
    if with_embeddings and texts:
        embedder = _build_embedder()
        print(
            f"[embed] Memulai embedding {len(texts)} teks dalam batch {_EMBED_BATCH_SIZE} "
            f"(jeda {_EMBED_BATCH_DELAY_S}s per batch)..."
        )
        embedded = _embed_documents_throttled(embedder, texts)
        vectors = [list(vector) for vector in embedded]
    else:
        vectors = [None for _ in texts]

    for chunk, vector in zip(chunks, vectors):
        index_rows.append(
            {
                "chunk_id": chunk.chunk_id,
                "chunk_type": chunk.chunk_type,
                "section": chunk.section,
                "path": chunk.path,
                "text": chunk.text,
                "embedding": vector,
            }
        )

    index_path.parent.mkdir(parents=True, exist_ok=True)
    index_path.write_text(json.dumps(index_rows, ensure_ascii=False, indent=2), encoding="utf-8")
    return index_rows


# ---------------------------------------------------------------------------
# Digunakan oleh: propose_mappings_with_llm(); propose_mappings_rule_based()
# Menjalankan fungsi `_flatten_json` sebagai bagian alur `style_mapping_pipeline`.
# ---------------------------------------------------------------------------
def _flatten_json(data: Any, prefix: str = "") -> dict[str, Any]:
    if isinstance(data, dict):
        result: dict[str, Any] = {}
        for key, value in data.items():
            next_prefix = f"{prefix}.{key}" if prefix else key
            result.update(_flatten_json(value, prefix=next_prefix))
        return result
    if isinstance(data, list):
        return {prefix: data}
    return {prefix: data}


# ---------------------------------------------------------------------------
# Digunakan oleh: run_docx_style_mapping_pipeline()
# Menjalankan fungsi `coerce_extracted_payload` sebagai bagian alur `style_mapping_pipeline`.
# ---------------------------------------------------------------------------
def coerce_extracted_payload(payload: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(payload, dict):
        raise ValueError(
            "Payload metadata untuk pipeline docx-style-map harus berupa JSON object dari document_metadata.payload."
        )
    return payload


# ---------------------------------------------------------------------------
# Digunakan oleh: translate_docx_style_config()
# Menjalankan fungsi `_coerce_alignment` sebagai bagian alur `style_mapping_pipeline`.
# ---------------------------------------------------------------------------
def _coerce_alignment(raw: str | None) -> ParagraphAlignmentOption:
    val = (raw or "JUSTIFY").strip().upper()
    if val in ("LEFT", "CENTER", "RIGHT", "JUSTIFY"):
        return val  # type: ignore[return-value]
    return "JUSTIFY"


# ---------------------------------------------------------------------------
# Digunakan oleh: translate_docx_style_config()
# Menjalankan fungsi `_build_position` sebagai bagian alur `style_mapping_pipeline`.
# ---------------------------------------------------------------------------
def _build_position(
    location: str | None,
    alignment: str | None,
    default: PageNumberPosition,
) -> PageNumberPosition:
    loc = (location or "").strip().lower()
    aln = (alignment or "RIGHT").strip().lower()
    candidate = f"{loc}_{aln}"
    valid: set[str] = {
        "header_left", "header_center", "header_right",
        "footer_left", "footer_center", "footer_right",
    }
    return candidate if candidate in valid else default  # type: ignore[return-value]


# ---------------------------------------------------------------------------
# Digunakan oleh: translate_docx_style_config()
# Menjalankan fungsi `_coerce_page_number_position` sebagai bagian alur `style_mapping_pipeline`.
# ---------------------------------------------------------------------------
def _coerce_page_number_position(
    value: Any,
    default: PageNumberPosition,
) -> PageNumberPosition:
    raw = str(value or "").strip().lower()
    if "_" in raw:
        loc, aln = raw.split("_", maxsplit=1)
        return _build_position(loc, aln, default=default)
    return default


# ---------------------------------------------------------------------------
# Digunakan oleh: translate_docx_style_config()
# Menjalankan fungsi `build_base_style_config` sebagai bagian alur `style_mapping_pipeline`.
# ---------------------------------------------------------------------------
def build_base_style_config(metadata: DocumentMetadata) -> DocxStyleConfig:
    typ = metadata.typography
    spacing = metadata.spacing
    num = metadata.numbering
    return DocxStyleConfig(
        heading_bold=bool(typ.heading_bold),
        heading_all_caps=bool(typ.heading_all_caps),
        paragraph_alignment=_coerce_alignment(spacing.paragraph_alignment),
        page_number_prelim_pos=_build_position(
            num.preliminary.location if num.preliminary else None,
            num.preliminary.alignment if num.preliminary else None,
            default="footer_right",
        ),
        page_number_content_pos=_build_position(
            num.content.location if num.content else None,
            num.content.alignment if num.content else None,
            default="header_right",
        ),
    )


# ---------------------------------------------------------------------------
# Digunakan oleh: run_docx_style_mapping_pipeline()
# Menjalankan fungsi `retrieve_relevant_chunks` sebagai bagian alur `style_mapping_pipeline`.
# ---------------------------------------------------------------------------
def retrieve_relevant_chunks(
    query: str,
    chunk_index: list[dict[str, Any]],
    top_k: int = 10,
) -> list[dict[str, Any]]:
    if not chunk_index:
        return []

    has_embeddings = bool(chunk_index[0].get("embedding"))
    scored: list[tuple[float, dict[str, Any]]] = []

    if has_embeddings:
        embedder = _build_embedder()
        query_vector = embedder.embed_query(query, output_dimensionality=EMBEDDING_DIMENSION)
        for item in chunk_index:
            embedding = item.get("embedding")
            if isinstance(embedding, list):
                score = _cosine_similarity(query_vector, embedding)
            else:
                score = _lexical_score(query, str(item.get("text", "")))
            scored.append((score, item))
    else:
        for item in chunk_index:
            score = _lexical_score(query, str(item.get("text", "")))
            scored.append((score, item))

    scored.sort(key=lambda item: item[0], reverse=True)
    # Exclude section-level chunks (verbose, 2000-3000 chars each) — pakai property chunks saja
    results = [item for _, item in scored if not item.get("chunk_id", "").startswith("section::")]
    return results[:top_k]


# ---------------------------------------------------------------------------
# Digunakan oleh: propose_mappings_with_llm()
# Menjalankan fungsi `_build_candidate_prompt` sebagai bagian alur `style_mapping_pipeline`.
# ---------------------------------------------------------------------------
def _build_candidate_prompt(
    flattened_payload: dict[str, Any],
    retrieved_chunks: list[dict[str, Any]],
) -> str:
    # Filter: kirim hanya style-relevant scalar fields ke LLM (bukan snippets/konten teks)
    # document_metadata.payload bisa memiliki 800+ keys setelah flatten — mayoritas dari sources[N].snippet
    # dan top-level .sources fields berisi list besar (7000+ chars each)
    style_payload = {
        k: v for k, v in flattened_payload.items()
        if "[" not in k  # skip list-index keys (sources[0], sources[1], dst)
        and not isinstance(v, (list, dict))  # skip list/dict values (sources arrays)
        and not k.endswith(".sources")  # skip citation source fields
    }
    source_lines = []
    for key, value in style_payload.items():
        source_lines.append(f"- {key}: {json.dumps(value, ensure_ascii=False)}")

    catalog_lines = []
    for chunk in retrieved_chunks:
        catalog_lines.append(
            "\n".join(
                [
                    f"[{chunk.get('chunk_id')}]",
                    str(chunk.get("text", "")),
                ]
            )
        )

    return (
        "Kamu bertugas memetakan style extraction ke properti python-docx.\n"
        "Selain mapping properti, isi juga `style_config_candidate` untuk style final DOCX.\n"
        "Gunakan HANYA target_path yang ada di konteks catalog.\n"
        "Jika tidak ada padanan, masukkan ke new_found.\n"
        "Kembalikan JSON sesuai schema terstruktur berikut:\n"
        "- style_config_candidate: {heading_bold, heading_all_caps, paragraph_alignment, page_number_prelim_pos, page_number_content_pos}\n"
        "- mappings: [{source_field, target_path, normalized_value, confidence, reason}]\n"
        "- new_found: [{source_field, value, reason?}]\n"
        "- conflicts: [{source_field, reason}]\n\n"
        "## Source Extracted Fields\n"
        + "\n".join(source_lines)
        + "\n\n## Catalog Context\n"
        + "\n\n---\n\n".join(catalog_lines)
    )


# ---------------------------------------------------------------------------
# Digunakan oleh: run_docx_style_mapping_pipeline()
# Menjalankan fungsi `propose_mappings_with_llm` sebagai bagian alur `style_mapping_pipeline`.
# ---------------------------------------------------------------------------
def propose_mappings_with_llm(
    flattened_payload: dict[str, Any],
    retrieved_chunks: list[dict[str, Any]],
) -> MappingCandidate:
    prompt = _build_candidate_prompt(flattened_payload, retrieved_chunks)
    config = get_config()
    config.disable_blackhole_proxies()

    llm = ChatGroq(
        model=config.model_name,
        temperature=config.temperature,
        api_key=config.groq_api_key.get_secret_value(),
    )
    chain = llm.with_structured_output(MappingCandidate)
    candidate = chain.invoke(prompt)
    # Normalisasi page_number_*_pos ke lowercase (LLM kadang mengembalikan uppercase)
    sc = candidate.style_config_candidate
    if sc.page_number_prelim_pos:
        sc.page_number_prelim_pos = sc.page_number_prelim_pos.lower().replace(" ", "_")
    if sc.page_number_content_pos:
        sc.page_number_content_pos = sc.page_number_content_pos.lower().replace(" ", "_")
    return candidate


# ---------------------------------------------------------------------------
# Digunakan oleh: run_docx_style_mapping_pipeline()
# Menjalankan fungsi `propose_mappings_rule_based` sebagai bagian alur `style_mapping_pipeline`.
# ---------------------------------------------------------------------------
def propose_mappings_rule_based(flattened_payload: dict[str, Any]) -> MappingCandidate:
    mappings: list[ProposedMapping] = []
    new_found: list[dict[str, Any]] = []
    style_candidate = LLMStyleConfigCandidate()

    for key, value in flattened_payload.items():
        key_lower = key.lower()
        if "paragraph_alignment" in key_lower and isinstance(value, str):
            style_candidate.paragraph_alignment = _coerce_alignment(value)
            mappings.append(
                ProposedMapping(
                    source_field=key,
                    target_path="paragraph.alignment",
                    normalized_value=value.strip().upper(),
                    confidence=0.75,
                    reason="Mapping langsung dari field alignment.",
                )
            )
            continue
        if "heading_bold" in key_lower and isinstance(value, bool):
            style_candidate.heading_bold = value
            mappings.append(
                ProposedMapping(
                    source_field=key,
                    target_path="font.bold",
                    normalized_value=value,
                    confidence=0.75,
                    reason="Mapping langsung dari field heading_bold.",
                )
            )
            continue
        if "heading_all_caps" in key_lower and isinstance(value, bool):
            style_candidate.heading_all_caps = value
            mappings.append(
                ProposedMapping(
                    source_field=key,
                    target_path="font.all_caps",
                    normalized_value=value,
                    confidence=0.75,
                    reason="Mapping langsung dari field heading_all_caps.",
                )
            )
            continue
        if "line_spacing" in key_lower and isinstance(value, (int, float)):
            mappings.append(
                ProposedMapping(
                    source_field=key,
                    target_path="paragraph_format.line_spacing",
                    normalized_value=float(value),
                    confidence=0.75,
                    reason="Mapping langsung dari field line spacing.",
                )
            )
            continue
        new_found.append({"source_field": key, "value": value})

    return MappingCandidate(
        style_config_candidate=style_candidate,
        mappings=mappings,
        new_found=new_found,
        conflicts=[],
    )


# ---------------------------------------------------------------------------
# Digunakan oleh: validate_candidate_mappings()
# Menjalankan fungsi `_coerce_enum_value` sebagai bagian alur `style_mapping_pipeline`.
# ---------------------------------------------------------------------------
def _coerce_enum_value(value: Any) -> str:
    if isinstance(value, str):
        return value.strip().upper()
    return str(value).strip().upper()


# ---------------------------------------------------------------------------
# Digunakan oleh: validate_candidate_mappings()
# Menjalankan fungsi `_matches_declared_type` sebagai bagian alur `style_mapping_pipeline`.
# ---------------------------------------------------------------------------
def _matches_declared_type(value: Any, declared_type: str | None, enum_members: list[str]) -> bool:
    if declared_type is None:
        return True

    type_str = declared_type.lower()
    if enum_members:
        coerced = _coerce_enum_value(value)
        return coerced in {member.upper() for member in enum_members}

    if "bool" in type_str or "boolean" in type_str:
        return isinstance(value, bool)
    if "int" in type_str and "float" not in type_str:
        return isinstance(value, int) and not isinstance(value, bool)
    if "float" in type_str:
        return isinstance(value, (int, float)) and not isinstance(value, bool)
    if "length" in type_str:
        return isinstance(value, (int, float))
    if "string" in type_str or "str" in type_str:
        return isinstance(value, str)
    return True


# ---------------------------------------------------------------------------
# Digunakan oleh: run_docx_style_mapping_pipeline()
# Menjalankan fungsi `validate_candidate_mappings` sebagai bagian alur `style_mapping_pipeline`.
# ---------------------------------------------------------------------------
def validate_candidate_mappings(
    candidate: MappingCandidate,
    entries: list[DocxCatalogEntry],
) -> ValidationReport:
    by_path = {entry.path: entry for entry in entries}
    accepted: list[ValidatedMapping] = []
    rejected: list[ValidatedMapping] = []

    for mapping in candidate.mappings:
        entry = by_path.get(mapping.target_path)
        if entry is None:
            rejected.append(
                ValidatedMapping(
                    source_field=mapping.source_field,
                    target_path=mapping.target_path,
                    normalized_value=mapping.normalized_value,
                    confidence=mapping.confidence,
                    reason=mapping.reason,
                    status="rejected",
                    rejection_reason="target_path tidak ada di catalog.",
                )
            )
            continue

        proposed_value = mapping.normalized_value
        if entry.enum_members:
            coerced = _coerce_enum_value(proposed_value)
            if coerced in {member.upper() for member in entry.enum_members}:
                proposed_value = coerced

        if not _matches_declared_type(proposed_value, entry.value_type, entry.enum_members):
            rejected.append(
                ValidatedMapping(
                    source_field=mapping.source_field,
                    target_path=mapping.target_path,
                    normalized_value=mapping.normalized_value,
                    confidence=mapping.confidence,
                    reason=mapping.reason,
                    status="rejected",
                    rejection_reason=(
                        f"Tipe nilai tidak cocok dengan deklarasi catalog: {entry.value_type}."
                    ),
                )
            )
            continue

        accepted.append(
            ValidatedMapping(
                source_field=mapping.source_field,
                target_path=mapping.target_path,
                normalized_value=proposed_value,
                confidence=mapping.confidence,
                reason=mapping.reason,
                status="accepted",
            )
        )

    return ValidationReport(
        accepted=accepted,
        rejected=rejected,
        new_found=candidate.new_found,
        conflicts=candidate.conflicts,
    )


# ---------------------------------------------------------------------------
# Digunakan oleh: build_apply_plan()
# Menjalankan fungsi `_looks_like_heading_scope` sebagai bagian alur `style_mapping_pipeline`.
# ---------------------------------------------------------------------------
def _looks_like_heading_scope(source_field: str) -> bool:
    lowered = source_field.lower()
    return any(token in lowered for token in ("heading", "judul", "bab", "title"))


# ---------------------------------------------------------------------------
# Digunakan oleh: run_docx_style_mapping_pipeline()
# Menjalankan fungsi `build_apply_plan` sebagai bagian alur `style_mapping_pipeline`.
# ---------------------------------------------------------------------------
def build_apply_plan(
    report: ValidationReport,
    candidate: MappingCandidate | None = None,
) -> ApplyPlan:
    style_overrides: dict[str, Any] = {}
    docx_overrides: dict[str, Any] = {}

    if candidate is not None:
        style_candidate = candidate.style_config_candidate
        if style_candidate.heading_bold is not None:
            style_overrides["heading_bold"] = bool(style_candidate.heading_bold)
        if style_candidate.heading_all_caps is not None:
            style_overrides["heading_all_caps"] = bool(style_candidate.heading_all_caps)
        if style_candidate.paragraph_alignment is not None:
            style_overrides["paragraph_alignment"] = _coerce_alignment(style_candidate.paragraph_alignment)
        if style_candidate.page_number_prelim_pos is not None:
            style_overrides["page_number_prelim_pos"] = style_candidate.page_number_prelim_pos
        if style_candidate.page_number_content_pos is not None:
            style_overrides["page_number_content_pos"] = style_candidate.page_number_content_pos

    for item in report.accepted:
        docx_overrides[item.target_path] = item.normalized_value

        if item.target_path == "paragraph.alignment":
            style_overrides["paragraph_alignment"] = _coerce_enum_value(item.normalized_value)
        elif item.target_path == "font.bold" and _looks_like_heading_scope(item.source_field):
            style_overrides["heading_bold"] = bool(item.normalized_value)
        elif item.target_path == "font.all_caps" and _looks_like_heading_scope(item.source_field):
            style_overrides["heading_all_caps"] = bool(item.normalized_value)

    return ApplyPlan(
        style_config_overrides=style_overrides,
        docx_property_overrides=docx_overrides,
        unmapped_candidates=[
            {"source_field": item.source_field, "value": item.normalized_value}
            for item in report.rejected
        ] + report.new_found,
    )


# ---------------------------------------------------------------------------
# Digunakan oleh: run_docx_style_mapping_pipeline()
# Menjalankan fungsi `save_pipeline_outputs` sebagai bagian alur `style_mapping_pipeline`.
# ---------------------------------------------------------------------------
def save_pipeline_outputs(
    candidate: MappingCandidate,
    report: ValidationReport,
    apply_plan: ApplyPlan,
    candidate_path: Path,
    report_path: Path,
    apply_plan_path: Path,
) -> None:
    candidate_path.parent.mkdir(parents=True, exist_ok=True)
    candidate_path.write_text(
        candidate.model_dump_json(indent=2),
        encoding="utf-8",
    )
    report_path.write_text(
        report.model_dump_json(indent=2),
        encoding="utf-8",
    )
    apply_plan_path.write_text(
        apply_plan.model_dump_json(indent=2),
        encoding="utf-8",
    )


# ---------------------------------------------------------------------------
# Digunakan oleh: manage.py
# Menjalankan fungsi `run_docx_style_mapping_pipeline` sebagai bagian alur `style_mapping_pipeline`.
# ---------------------------------------------------------------------------
def run_docx_style_mapping_pipeline(
    dictionary_path: Path = DEFAULT_DICTIONARY_PATH,
    extracted_payload: dict[str, Any] | None = None,
    with_embeddings: bool = True,
    use_llm_mapper: bool = True,
    catalog_path: Path = DEFAULT_CATALOG_PATH,
    chunks_path: Path = DEFAULT_CHUNKS_PATH,
    index_path: Path = DEFAULT_INDEX_PATH,
    candidate_path: Path = DEFAULT_CANDIDATE_PATH,
    report_path: Path = DEFAULT_REPORT_PATH,
    apply_plan_path: Path = DEFAULT_APPLY_PLAN_PATH,
    verbose: bool = True,
) -> tuple[MappingCandidate, ValidationReport, ApplyPlan]:
    payload = coerce_extracted_payload(extracted_payload)

    if verbose:
        print("[docx-map] 1/6 Building flat property catalog dari dictionary python-docx...")
    entries = build_docx_property_catalog(dictionary_path)
    chunks = build_catalog_chunks(entries)
    save_catalog_artifacts(entries, chunks, catalog_path, chunks_path)
    if verbose:
        print(f"[docx-map] Catalog entries: {len(entries)} | Chunks: {len(chunks)}")

    if verbose:
        print("[docx-map] 2/6 Building embedding index untuk catalog chunks...")
    chunk_index = build_chunk_index(chunks, index_path=index_path, with_embeddings=with_embeddings)
    if verbose:
        print(f"[docx-map] Index rows: {len(chunk_index)}")

    if verbose:
        print("[docx-map] 3/6 Running retrieval (RAG) pada dictionary + extracted payload...")
    flattened = _flatten_json(payload)
    query_text = "\n".join(f"{key}: {value}" for key, value in flattened.items())
    retrieved = retrieve_relevant_chunks(query_text, chunk_index=chunk_index, top_k=6)
    if verbose:
        print(f"[docx-map] Retrieved chunks: {len(retrieved)}")

    if verbose:
        print("[docx-map] 4/6 Generating mapping candidate...")
    if use_llm_mapper:
        candidate = propose_mappings_with_llm(flattened_payload=flattened, retrieved_chunks=retrieved)
    else:
        candidate = propose_mappings_rule_based(flattened_payload=flattened)
    if verbose:
        print(f"[docx-map] Candidate mappings: {len(candidate.mappings)} | New found: {len(candidate.new_found)}")

    if verbose:
        print("[docx-map] 5/6 Validating candidate mapping terhadap catalog...")
    report = validate_candidate_mappings(candidate, entries)
    if verbose:
        print(f"[docx-map] Accepted: {len(report.accepted)} | Rejected: {len(report.rejected)}")

    if verbose:
        print("[docx-map] 6/6 Building apply plan + saving audit outputs...")
    apply_plan = build_apply_plan(report, candidate=candidate)
    save_pipeline_outputs(
        candidate=candidate,
        report=report,
        apply_plan=apply_plan,
        candidate_path=candidate_path,
        report_path=report_path,
        apply_plan_path=apply_plan_path,
    )
    if verbose:
        print(f"[docx-map] Candidate:  {candidate_path}")
        print(f"[docx-map] Report:     {report_path}")
        print(f"[docx-map] Apply plan: {apply_plan_path}")
    return candidate, report, apply_plan


# ---------------------------------------------------------------------------
# Digunakan oleh: model_ai/docx/generator.py
# Menjalankan fungsi `translate_docx_style_config` sebagai bagian alur `style_mapping_pipeline`.
# ---------------------------------------------------------------------------
def translate_docx_style_config(
    metadata: DocumentMetadata,
    extracted_payload: dict[str, Any],
    dictionary_path: Path = DEFAULT_DICTIONARY_PATH,
    use_llm_mapper: bool = True,
    with_embeddings: bool = True,
) -> DocxStyleConfig:
    base = build_base_style_config(metadata)
    try:
        _, _, apply_plan = run_docx_style_mapping_pipeline(
            dictionary_path=dictionary_path,
            extracted_payload=extracted_payload,
            with_embeddings=with_embeddings,
            use_llm_mapper=use_llm_mapper,
            verbose=False,
        )
    except Exception as exc:
        if not use_llm_mapper:
            raise

        # Fallback aman: tetap pakai pipeline baru, tapi tanpa embedding + tanpa LLM.
        print(
            "[docx-map] Warning: mode LLM gagal, fallback ke mode deterministik "
            f"(no-embeddings, no-llm-mapper). Detail: {exc}"
        )
        _, _, apply_plan = run_docx_style_mapping_pipeline(
            dictionary_path=dictionary_path,
            extracted_payload=extracted_payload,
            with_embeddings=False,
            use_llm_mapper=False,
            verbose=False,
        )

    merged = base.model_dump()
    merged.update(apply_plan.style_config_overrides)

    # Jaga agar enum/alignment tetap valid sebelum dipakai renderer.
    if "paragraph_alignment" in merged:
        merged["paragraph_alignment"] = _coerce_alignment(merged["paragraph_alignment"])

    if "page_number_prelim_pos" in merged:
        merged["page_number_prelim_pos"] = _coerce_page_number_position(
            merged["page_number_prelim_pos"],
            default="footer_right",
        )

    if "page_number_content_pos" in merged:
        merged["page_number_content_pos"] = _coerce_page_number_position(
            merged["page_number_content_pos"],
            default="header_right",
        )

    return DocxStyleConfig.model_validate(merged)
