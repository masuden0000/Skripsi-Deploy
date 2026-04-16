import os
import sys
from pathlib import Path

from dotenv import load_dotenv
from langchain_core.prompts import ChatPromptTemplate
from langchain_google_genai import ChatGoogleGenerativeAI
from pydantic import BaseModel, Field

APP_DIR = Path(__file__).resolve().parents[2]
ENV_FILE = APP_DIR / ".env"

load_dotenv(dotenv_path=ENV_FILE)


def get_required_env(name: str) -> str:
    """Get required environment variable or raise ValueError."""
    value = os.getenv(name, "").strip()
    if not value:
        raise ValueError(f"{name} belum di-set di file .env.")
    return value


def _validate_env_vars() -> None:
    """Validate required environment variables at module load time."""
    required_vars = ["MODEL_NAME", "TEMPERATURE"]
    for var in required_vars:
        get_required_env(var)


MODEL_NAME = get_required_env("MODEL_NAME")
TEMPERATURE = float(get_required_env("TEMPERATURE"))

_validate_env_vars()


class LLMResponse(BaseModel):
    answer: str = Field(description="Jawaban utama untuk pertanyaan user.")
    keywords: list[str] = Field(description="Kata kunci penting dari jawaban.")
    language: str = Field(description="Bahasa yang dipakai dalam jawaban.")


def get_google_api_key() -> str:
    api_key = os.getenv("GOOGLE_API_KEY", "").strip()
    if not api_key:
        raise ValueError(
            "GOOGLE_API_KEY belum di-set. Tambahkan variabel itu ke file .env di folder pymupdf4llm."
        )
    return api_key


def validate_question(question: str) -> str:
    clean_question = question.strip()
    if not clean_question:
        raise ValueError("Pertanyaan tidak boleh kosong.")
    return clean_question


def build_chain():
    api_key = get_google_api_key()

    prompt = ChatPromptTemplate.from_messages(
        [
            (
                "system",
                (
                    "Kamu adalah asisten AI yang menjawab dalam Bahasa Indonesia "
                    "dengan structured output JSON. "
                    "Isi semua field schema dengan lengkap: "
                    "`answer` berisi jawaban utama yang jelas dan ringkas, "
                    "`keywords` berisi daftar kata kunci penting, "
                    "dan `language` berisi kode bahasa jawaban, misalnya `id`."
                ),
            ),
            ("human", "{question}"),
        ]
    )

    llm = ChatGoogleGenerativeAI(
        model=MODEL_NAME,
        temperature=TEMPERATURE,
        google_api_key=api_key,
    )

    structured_llm = llm.with_structured_output(LLMResponse)
    return prompt | structured_llm


def ask_llm(question: str) -> LLMResponse:
    clean_question = validate_question(question)
    chain = build_chain()
    return chain.invoke({"question": clean_question})


def get_question_from_cli() -> str:
    return " ".join(sys.argv[1:]).strip()


def main() -> None:
    try:
        question = get_question_from_cli()
        answer = ask_llm(question)
        print(answer.model_dump_json(indent=2))
    except ValueError as exc:
        print(f"Error: {exc}")
        raise SystemExit(1) from exc
    except Exception as exc:
        print(f"Error saat memanggil model: {exc}")
        raise SystemExit(1) from exc


if __name__ == "__main__":
    main()
