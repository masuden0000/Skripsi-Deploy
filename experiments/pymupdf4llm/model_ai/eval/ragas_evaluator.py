import json
import os
from pathlib import Path

from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from ragas import EvaluationDataset, SingleTurnSample, evaluate
from ragas.llms import LangchainLLMWrapper
from ragas.metrics import (
    AnswerRelevancy,
    ContextPrecision,
    ContextRecall,
    Faithfulness,
    FactualCorrectness,
)

APP_DIR = Path(__file__).resolve().parents[2]
ENV_FILE = APP_DIR / ".env"
TESTSET_FILE = APP_DIR / "data" / "eval_testset.json"
RESULTS_FILE = APP_DIR / "data" / "eval_results.json"

load_dotenv(dotenv_path=ENV_FILE)


def _get_required_env(name: str) -> str:
    value = os.getenv(name, "").strip()
    if not value:
        raise SystemExit(f"[eval] {name} belum di-set di file .env.")
    return value


def _load_testset() -> list[dict]:
    if not TESTSET_FILE.exists():
        raise SystemExit(
            f"[eval] Testset tidak ditemukan: {TESTSET_FILE}\n"
            "Jalankan `python manage.py generate_testset` terlebih dahulu."
        )
    with TESTSET_FILE.open(encoding="utf-8") as f:
        return json.load(f)


def _build_sample(row: dict) -> SingleTurnSample | None:
    """Convert satu row testset + RAG result ke SingleTurnSample."""
    from model_ai.rag.rag_service import ask_rag, retrieve_chunks

    question: str = row.get("user_input", "").strip()
    reference: str = row.get("reference", "").strip()
    if not question:
        return None

    try:
        chunks = retrieve_chunks(question)
        retrieved_contexts = [chunk.content for chunk in chunks]

        rag_response = ask_rag(question)
        response = rag_response.answer
    except Exception as exc:
        print(f"[eval] WARNING: Skip '{question[:60]}...' — {exc}")
        return None

    return SingleTurnSample(
        user_input=question,
        retrieved_contexts=retrieved_contexts,
        response=response,
        reference=reference if reference else None,
    )


def _build_metrics(evaluator_llm: LangchainLLMWrapper) -> list:
    return [
        Faithfulness(llm=evaluator_llm),
        AnswerRelevancy(llm=evaluator_llm),
        ContextPrecision(llm=evaluator_llm),
        ContextRecall(llm=evaluator_llm),
        FactualCorrectness(llm=evaluator_llm),
    ]


def _print_results_table(scores: dict) -> None:
    col_w = 22
    print("\nEvaluation Results:")
    print("┌" + "─" * col_w + "┬─────────┐")
    print(f"│ {'Metric':<{col_w - 2}} │ Score   │")
    print("├" + "─" * col_w + "┼─────────┤")
    for metric, score in scores.items():
        score_str = f"{score:.4f}" if score is not None else "N/A"
        print(f"│ {metric:<{col_w - 2}} │ {score_str:<7} │")
    print("└" + "─" * col_w + "┴─────────┘")


def run_evaluation() -> Path:
    _get_required_env("OPENAI_API_KEY")
    _get_required_env("GOOGLE_API_KEY")  # needed by rag_service internals

    print("[eval] Memuat testset...")
    rows = _load_testset()
    print(f"[eval] {len(rows)} pertanyaan ditemukan.")

    print("[eval] Menjalankan RAG pipeline untuk setiap pertanyaan...")
    samples = []
    for i, row in enumerate(rows, 1):
        print(f"[eval] ({i}/{len(rows)}) {row.get('user_input', '')[:60]}")
        sample = _build_sample(row)
        if sample:
            samples.append(sample)

    if not samples:
        raise SystemExit("[eval] Tidak ada sample yang berhasil diproses. Cek koneksi Supabase dan API keys.")

    print(f"\n[eval] {len(samples)} samples siap dievaluasi.")

    api_key = _get_required_env("OPENAI_API_KEY")
    evaluator_llm = LangchainLLMWrapper(
        ChatOpenAI(model="gpt-4o", openai_api_key=api_key)
    )
    metrics = _build_metrics(evaluator_llm)

    print("[eval] Menjalankan RAGAS evaluation via gpt-4o...")
    dataset = EvaluationDataset(samples=samples)
    result = evaluate(dataset=dataset, metrics=metrics, llm=evaluator_llm)

    scores = {str(k): float(v) for k, v in result.items() if v is not None}
    _print_results_table(scores)

    output = {
        "scores": scores,
        "num_samples": len(samples),
        "model_judge": "gpt-4o",
    }
    RESULTS_FILE.parent.mkdir(parents=True, exist_ok=True)
    with RESULTS_FILE.open("w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    print(f"\nResults saved to {RESULTS_FILE}")
    return RESULTS_FILE
