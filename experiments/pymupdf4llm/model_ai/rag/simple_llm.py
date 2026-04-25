import sys
from pathlib import Path

from langchain_core.prompts import ChatPromptTemplate
from langchain_groq import ChatGroq
from pydantic import BaseModel, Field

if __package__:
    from ..config import get_config
else:
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
    from model_ai.config import get_config

CONFIG = get_config()
MODEL_NAME = CONFIG.model_name
TEMPERATURE = CONFIG.temperature


class LLMResponse(BaseModel):
    answer: str = Field(description="Jawaban utama untuk pertanyaan user.")
    keywords: list[str] = Field(description="Kata kunci penting dari jawaban.")
    language: str = Field(description="Bahasa yang dipakai dalam jawaban.")


def validate_question(question: str) -> str:
    clean_question = question.strip()
    if not clean_question:
        raise ValueError("Pertanyaan tidak boleh kosong.")
    return clean_question


def build_chain():
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

    CONFIG.disable_blackhole_proxies()
    llm = ChatGroq(
        model=MODEL_NAME,
        temperature=TEMPERATURE,
        api_key=CONFIG.groq_api_key.get_secret_value(),
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
