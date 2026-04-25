import json
import sys
from pathlib import Path

from langchain_google_genai import GoogleGenerativeAIEmbeddings
from langchain_groq import ChatGroq
from supabase import Client, create_client

# Support run langsung via path file tanpa perlu entry dari manage.py.
if __package__:
    from ..config import get_config
    from .models import Source, TypographyExtracted, TypographyInfo
else:
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
    from model_ai.config import get_config
    from model_ai.extractor.models import Source, TypographyExtracted, TypographyInfo

APP_DIR = Path(__file__).resolve().parents[2]
PROJECT_DIR = APP_DIR.parent
PROMPT_PATH = Path(__file__).resolve().parent / "prompts" / "typography.md"
OUTPUT_PATH = APP_DIR / "data" / "output_typography_dummy.json"
EMBEDDING_DIMENSION = 768

CONFIG = get_config()
LLM_MODEL = CONFIG.model_name


def build_sources(chunks: list[dict]) -> list[Source]:
    return [
        Source(
            chunk_index=chunk["chunk_index"],
            page_start=chunk["page_start"],
            page_end=chunk["page_end"],
            header=chunk["chunk_parent"],
            snippet=chunk["content"][:100],
        )
        for chunk in chunks
    ]


def load_prompt(prompt_path: Path) -> tuple[str, str]:
    raw_prompt = prompt_path.read_text(encoding="utf-8")
    return parse_prompt_frontmatter(raw_prompt, prompt_path)


def render_prompt(template: str, chunks: list[dict]) -> str:
    # Gabungkan konteks chunk agar prompt hanya fokus ke bukti yang di-retrieve.
    context = "\n\n---\n\n".join(chunk["content"] for chunk in chunks)
    return template.replace("{context}", context)


def format_vector(values: list[float]) -> str:
    return "[" + ",".join(f"{value:.8f}" for value in values) + "]"


def parse_prompt_frontmatter(raw_prompt: str, prompt_path: Path) -> tuple[str, str]:
    lines = raw_prompt.splitlines()
    if not lines or lines[0].strip() != "---":
        raise ValueError(f"Prompt {prompt_path.name} harus diawali blok frontmatter.")

    metadata_lines: list[str] = []
    body_start_index: int | None = None

    for index, line in enumerate(lines[1:], start=1):
        if line.strip() == "---":
            body_start_index = index + 1
            break
        metadata_lines.append(line)

    if body_start_index is None:
        raise ValueError(
            f"Prompt {prompt_path.name} punya pembuka frontmatter tapi tidak punya penutup."
        )

    metadata: dict[str, str] = {}
    for line in metadata_lines:
        stripped = line.strip()
        if not stripped:
            continue
        if ":" not in stripped:
            raise ValueError(
                f"Baris frontmatter tidak valid di {prompt_path.name}: {line}"
            )

        key, value = stripped.split(":", 1)
        metadata[key.strip()] = value.strip().strip("'\"")

    query = metadata.get("query", "").strip()
    if not query:
        raise ValueError(f"Prompt {prompt_path.name} wajib punya field 'query'.")

    template = "\n".join(lines[body_start_index:]).lstrip()
    return query, template


def build_embedder() -> GoogleGenerativeAIEmbeddings:
    CONFIG.disable_blackhole_proxies()
    return GoogleGenerativeAIEmbeddings(
        model=CONFIG.embedding_model_name,
        google_api_key=CONFIG.require_google_api_key(),
    )


def build_supabase() -> Client:
    return create_client(
        CONFIG.supabase_url,
        CONFIG.supabase_service_role_key.get_secret_value(),
    )


def retrieve_chunks(query: str) -> list[dict]:
    # Embedding query dipakai untuk ambil chunk paling relevan dari Supabase RPC.
    embedder = build_embedder()
    vector = embedder.embed_query(query, output_dimensionality=EMBEDDING_DIMENSION)
    formatted_vector = format_vector(vector)

    client = build_supabase()
    result = client.rpc(
        "match_document_chunks",
        {"query_embedding": formatted_vector, "match_count": CONFIG.rag_top_k},
    ).execute()
    return result.data or []


def extract_typography() -> TypographyInfo:
    query, template = load_prompt(PROMPT_PATH)
    chunks = retrieve_chunks(query)
    prompt = render_prompt(template, chunks)

    # Structured output bikin hasil tetap konsisten ke schema typography.
    CONFIG.disable_blackhole_proxies()
    llm = ChatGroq(
        model=LLM_MODEL,
        api_key=CONFIG.groq_api_key.get_secret_value(),
    )
    chain = llm.with_structured_output(TypographyExtracted)
    extracted = chain.invoke(prompt)

    return TypographyInfo(**extracted.model_dump(), sources=build_sources(chunks))


def build_output_payload(typography: TypographyInfo) -> dict:
    return {
        "source_document": (PROJECT_DIR / "file.pdf").name,
        "extracted_keys": ["typography"],
        "typography": typography.model_dump(),
    }


def save_to_json(payload: dict) -> None:
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_PATH, "w", encoding="utf-8") as file_handle:
        json.dump(payload, file_handle, ensure_ascii=False, indent=4)


def run_typography_dummy_extraction() -> Path:
    print("[extract-dummy] Memproses: typography ...")
    typography = extract_typography()
    payload = build_output_payload(typography)
    save_to_json(payload)
    print(f"[extract-dummy] JSON disimpan: {OUTPUT_PATH}")
    return OUTPUT_PATH


def format_runtime_error(exc: Exception) -> str:
    message = str(exc)

    if "Invalid API Key" in message or "Unauthorized" in message:
        return (
            "Request ke Groq ditolak karena API key tidak valid atau tidak aktif. "
            "Cek nilai GROQ_API_KEY lalu jalankan ulang."
        )

    return message


def main() -> None:
    try:
        run_typography_dummy_extraction()
    except Exception as exc:
        print(f"Error saat menjalankan dummy extraction: {format_runtime_error(exc)}")
        raise SystemExit(1) from exc


if __name__ == "__main__":
    main()
