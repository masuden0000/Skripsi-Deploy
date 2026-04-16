import os
import sys
from pathlib import Path
from typing import Literal

from dotenv import load_dotenv
from langchain_core.prompts import ChatPromptTemplate
from langchain_google_genai import (ChatGoogleGenerativeAI,
                                    GoogleGenerativeAIEmbeddings)
from pydantic import BaseModel, Field
from supabase import Client, create_client

APP_DIR = Path(__file__).resolve().parents[2]
ENV_FILE = APP_DIR / ".env"

load_dotenv(dotenv_path=ENV_FILE)


def get_required_env(name: str) -> str:
    value = os.getenv(name, "").strip()
    if not value:
        raise ValueError(f"{name} belum di-set di file .env.")
    return value


def _validate_env_vars() -> None:
    """Validate required environment variables at module load time."""
    required_vars = ["MODEL_NAME", "TEMPERATURE", "EMBEDDING_MODEL_NAME"]
    for var in required_vars:
        get_required_env(var)


MODEL_NAME = get_required_env("MODEL_NAME")
TEMPERATURE = float(get_required_env("TEMPERATURE"))
EMBEDDING_MODEL_NAME = get_required_env("EMBEDDING_MODEL_NAME")
EMBEDDING_DIMENSION = 768
RAG_TOP_K = int(get_required_env("RAG_TOP_K"))
MIN_CONTEXT_SIMILARITY = float(get_required_env("RAG_MIN_CONTEXT_SIMILARITY"))

_validate_env_vars()


class Citation(BaseModel):
    chunk_index: int = Field(description="Nomor chunk yang dipakai sebagai referensi.")
    chunk_parent: str = Field(description="Judul section atau parent dari chunk.")
    page_start: int = Field(description="Halaman awal chunk.")
    page_end: int = Field(description="Halaman akhir chunk.")


class RAGResponse(BaseModel):
    answer_type: Literal["summary", "format_guidance", "procedure", "not_in_source"] = Field(
        description="Jenis jawaban final berdasarkan intent pertanyaan user."
    )
    scope_status: Literal["grounded", "insufficient_context", "out_of_scope"] = Field(
        description="Status apakah jawaban benar-benar didukung context, kurang context, atau di luar cakupan."
    )
    answer: str = Field(description="Jawaban utama untuk pertanyaan user.")
    bullet_points: list[str] = Field(
        description="Daftar poin penting yang merangkum isi jawaban."
    )
    steps: list[str] = Field(
        description="Langkah-langkah terurut untuk pertanyaan prosedural atau format penulisan."
    )
    keywords: list[str] = Field(description="Kata kunci penting dari jawaban.")
    language: str = Field(description="Bahasa yang dipakai dalam jawaban.")
    citations: list[Citation] = Field(description="Daftar sitasi chunk yang dipakai.")


class RetrievedChunk(BaseModel):
    chunk_index: int
    content: str
    chunk_parent: str
    page_start: int
    page_end: int
    similarity: float | None = None


def validate_question(question: str) -> str:
    clean_question = question.strip()
    if not clean_question:
        raise ValueError("Pertanyaan tidak boleh kosong.")
    return clean_question


def get_question_from_cli() -> str:
    return " ".join(sys.argv[1:]).strip()


def build_supabase_client() -> Client:
    return create_client(
        get_required_env("SUPABASE_URL"),
        get_required_env("SUPABASE_SERVICE_ROLE_KEY"),
    )


def build_embedder() -> GoogleGenerativeAIEmbeddings:
    return GoogleGenerativeAIEmbeddings(
        model=EMBEDDING_MODEL_NAME,
        google_api_key=get_required_env("GOOGLE_API_KEY"),  # type: ignore
    )


def format_vector(values: list[float]) -> str:
    return "[" + ",".join(f"{value:.8f}" for value in values) + "]"


def retrieve_chunks(question: str) -> list[RetrievedChunk]:
    embedder = build_embedder()
    query_embedding = embedder.embed_query(
        question,
        output_dimensionality=EMBEDDING_DIMENSION,
    )
    client = build_supabase_client()

    response = client.rpc(
        "match_document_chunks",
        {
            "query_embedding": format_vector(query_embedding),
            "match_count": RAG_TOP_K,
        },
    ).execute()

    records = response.data or []
    return [RetrievedChunk.model_validate(item) for item in records]  # type: ignore


def build_context(chunks: list[RetrievedChunk]) -> str:
    blocks = []
    for chunk in chunks:
        blocks.append(
            "\n".join(
                [
                    f"Chunk #{chunk.chunk_index}",
                    f"Bagian: {chunk.chunk_parent}",
                    f"Halaman: {chunk.page_start}-{chunk.page_end}",
                    f"Konten: {chunk.content}",
                ]
            )
        )
    return "\n\n---\n\n".join(blocks)


def context_is_weak(chunks: list[RetrievedChunk]) -> bool:
    if not chunks:
        return True

    strongest_score = max(
        (chunk.similarity for chunk in chunks if chunk.similarity is not None),
        default=0.0,
    )
    return strongest_score < MIN_CONTEXT_SIMILARITY


def build_chain():
    prompt = ChatPromptTemplate.from_messages(
        [
            (
                "system",
                (
                    "Kamu adalah asisten RAG khusus dokumen PKM. "
                    "Tugasmu hanya menjawab berdasarkan context yang diberikan dari basis pengetahuan PKM. "
                    "Jangan gunakan pengetahuan umum, asumsi pribadi, atau informasi di luar context. "
                    "Lakukan penalaran secara internal untuk: mengenali intent pertanyaan, "
                    "menilai apakah context cukup, lalu memilih format jawaban yang paling sesuai. "
                    "Jangan tampilkan proses berpikir internal itu ke user. "
                    "Jika context tidak cukup, isi `scope_status` dengan `insufficient_context`. "
                    "Jika pertanyaan berada di luar cakupan sumber PKM yang tersedia, isi `scope_status` "
                    "dengan `out_of_scope` dan `answer_type` dengan `not_in_source`. "
                    "Jika pertanyaan membahas format penulisan, sistematika proposal, prosedur pengusulan, "
                    "atau langkah pengerjaan, prioritaskan jawaban terstruktur dalam bentuk ringkasan, "
                    "poin-poin, dan langkah-langkah. "
                    "Isi semua field schema. `bullet_points` wajib selalu ada, `steps` diisi saat relevan. "
                    "Gunakan sitasi hanya dari chunk yang benar-benar diberikan. "
                    "Jawab seluruhnya dalam Bahasa Indonesia."
                ),
            ),
            (
                "human",
                (
                    "Pertanyaan user:\n{question}\n\n"
                    "Context yang boleh dipakai:\n{context}\n\n"
                    "Aturan tambahan:\n"
                    "- Jika informasi tidak cukup, katakan secara eksplisit bahwa sumber PKM saat ini belum cukup.\n"
                    "- Jika pertanyaan di luar PKM atau tidak didukung sumber, tolak dengan sopan tanpa menambah informasi umum.\n"
                    "- Jika pertanyaan meminta format atau sistematika proposal, tampilkan jawaban dengan poin-poin dan langkah bila ada.\n\n"
                    "Kembalikan jawaban terstruktur sesuai schema."
                ),
            ),
        ]
    )

    llm = ChatGoogleGenerativeAI(
        model=get_required_env("MODEL_NAME"),
        temperature=TEMPERATURE,
        google_api_key=get_required_env("GOOGLE_API_KEY"),
    )

    structured_llm = llm.with_structured_output(RAGResponse)
    return prompt | structured_llm


def build_empty_response() -> RAGResponse:
    return RAGResponse(
        answer_type="not_in_source",
        scope_status="out_of_scope",
        answer="Informasi yang relevan tidak ditemukan dalam basis pengetahuan yang tersedia.",
        bullet_points=[],
        steps=[],
        keywords=[],
        language="id",
        citations=[],
    )


def build_insufficient_context_response(chunks: list[RetrievedChunk]) -> RAGResponse:
    return RAGResponse(
        answer_type="summary",
        scope_status="insufficient_context",
        answer=(
            "Saya belum bisa memberikan jawaban yang kuat karena potongan sumber PKM yang "
            "ditemukan belum cukup spesifik untuk menjawab pertanyaan ini."
        ),
        bullet_points=[
            "Pertanyaan Anda masih berkaitan dengan basis pengetahuan PKM, tetapi bukti yang ditemukan belum cukup kuat.",
            "Saya hanya boleh menjawab berdasarkan chunk yang tersedia saat ini.",
            "Coba gunakan pertanyaan yang lebih spesifik, misalnya nama bagian, format proposal, atau jenis PKM tertentu.",
        ],
        steps=[],
        keywords=["PKM", "konteks terbatas"],
        language="id",
        citations=[
            Citation(
                chunk_index=chunk.chunk_index,
                chunk_parent=chunk.chunk_parent,
                page_start=chunk.page_start,
                page_end=chunk.page_end,
            )
            for chunk in chunks
        ],
    )


def normalize_response(
    answer: RAGResponse, retrieved_chunks: list[RetrievedChunk]
) -> RAGResponse:
    if not answer.citations and answer.scope_status != "out_of_scope":
        answer.citations = [
            Citation(
                chunk_index=chunk.chunk_index,
                chunk_parent=chunk.chunk_parent,
                page_start=chunk.page_start,
                page_end=chunk.page_end,
            )
            for chunk in retrieved_chunks
        ]

    if not answer.bullet_points:
        answer.bullet_points = [answer.answer]

    if answer.answer_type in {"format_guidance", "procedure"} and not answer.steps:
        answer.scope_status = "insufficient_context"
        answer.answer = (
            "Saya menemukan topik yang relevan, tetapi detail langkah atau formatnya "
            "belum cukup lengkap untuk dijelaskan secara prosedural dari sumber saat ini."
        )
        answer.bullet_points = [
            "Sumber yang ditemukan menunjukkan topik yang relevan.",
            "Namun, rincian langkah atau format penulisan belum cukup lengkap untuk dijabarkan dengan aman.",
            "Silakan ajukan pertanyaan yang lebih spesifik pada bagian proposal atau lampiran tertentu.",
        ]

    return answer


def ask_rag(question: str) -> RAGResponse:
    clean_question = validate_question(question)
    retrieved_chunks = retrieve_chunks(clean_question)
    if not retrieved_chunks:
        return build_empty_response()

    if context_is_weak(retrieved_chunks):
        return build_insufficient_context_response(retrieved_chunks)

    context = build_context(retrieved_chunks)
    chain = build_chain()
    answer = chain.invoke({"question": clean_question, "context": context})
    return normalize_response(answer, retrieved_chunks)  # type: ignore


def main() -> None:
    try:
        question = get_question_from_cli()
        answer = ask_rag(question)
        print(answer.model_dump_json(indent=2))
    except ValueError as exc:
        print(f"Error: {exc}")
        raise SystemExit(1) from exc
    except Exception as exc:
        print(f"Error saat menjalankan RAG: {exc}")
        raise SystemExit(1) from exc


if __name__ == "__main__":
    main()
