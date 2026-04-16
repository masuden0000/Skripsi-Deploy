# RAGAS Evaluation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Tambahkan dua command (`generate_testset` dan `eval`) ke `manage.py` yang menggunakan RAGAS + OpenAI gpt-4o sebagai LLM judge untuk mengevaluasi kualitas RAG pipeline secara kuantitatif.

**Architecture:** Hybrid approach — testset synthetic di-generate sekali dari `output_chunks.json` menggunakan RAGAS `TestsetGenerator`, disimpan ke `eval_testset.json`, lalu command `eval` me-load testset tersebut, menjalankan RAG pipeline, dan mengevaluasi hasilnya. RAG pipeline (`rag_service.py`) dipakai as-is tanpa modifikasi.

**Tech Stack:** Python 3.11+, ragas>=0.2.0, langchain-openai>=0.1.0, openai>=1.0.0, existing langchain-core, existing Supabase RAG pipeline.

---

## File Structure

| File | Status | Tanggung Jawab |
|---|---|---|
| `experiments/pymupdf4llm/model_ai/eval/__init__.py` | Create | Package marker |
| `experiments/pymupdf4llm/model_ai/eval/testset_generator.py` | Create | Load chunks, generate synthetic Q&A via RAGAS, simpan `eval_testset.json` |
| `experiments/pymupdf4llm/model_ai/eval/ragas_evaluator.py` | Create | Load testset, run RAG pipeline per pertanyaan, evaluate dengan RAGAS metrics, simpan `eval_results.json` |
| `experiments/pymupdf4llm/manage.py` | Modify | Tambah subcommand `generate_testset` dan `eval` |
| `experiments/pymupdf4llm/requirements.txt` | Modify | Tambah ragas, langchain-openai, openai |
| `experiments/pymupdf4llm/.env.example` | Modify | Tambah OPENAI_API_KEY dan RAGAS_TESTSET_SIZE |

---

## Task 1: Tambah Dependencies

**Files:**
- Modify: `experiments/pymupdf4llm/requirements.txt`
- Modify: `experiments/pymupdf4llm/.env.example`

- [ ] **Step 1: Tambah packages ke requirements.txt**

Edit `experiments/pymupdf4llm/requirements.txt` — tambahkan tiga baris di akhir file:

```
pymupdf4llm
langchain-text-splitters>=0.3,<0.4
langchain-core>=0.3,<0.4
langchain-google-genai>=2.1,<3
python-dotenv>=1.0,<2
pydantic>=2.10,<3
supabase>=2.9,<3
ragas>=0.2.0
langchain-openai>=0.1.0
openai>=1.0.0
```

- [ ] **Step 2: Tambah env vars ke .env.example**

Edit `experiments/pymupdf4llm/.env.example` — tambahkan section baru di akhir file:

```
# Evaluation Configuration (required for generate_testset and eval commands)
OPENAI_API_KEY=your_openai_api_key_here
RAGAS_TESTSET_SIZE=20
```

- [ ] **Step 3: Install dependencies**

```bash
cd experiments/pymupdf4llm
pip install ragas>=0.2.0 langchain-openai>=0.1.0 openai>=1.0.0
```

Expected output: Successfully installed ragas-... langchain-openai-... openai-...

- [ ] **Step 4: Verifikasi import**

```bash
python -c "from ragas import evaluate, EvaluationDataset, SingleTurnSample; from ragas.testset import TestsetGenerator; from langchain_openai import ChatOpenAI, OpenAIEmbeddings; print('OK')"
```

Expected output: `OK`

- [ ] **Step 5: Commit**

```bash
git add experiments/pymupdf4llm/requirements.txt experiments/pymupdf4llm/.env.example
git commit -m "chore: add ragas + langchain-openai + openai to dependencies"
```

---

## Task 2: Buat eval package dan testset_generator.py

**Files:**
- Create: `experiments/pymupdf4llm/model_ai/eval/__init__.py`
- Create: `experiments/pymupdf4llm/model_ai/eval/testset_generator.py`

- [ ] **Step 1: Buat `__init__.py`**

Buat file kosong:
```python
```
(file kosong, hanya sebagai package marker)

- [ ] **Step 2: Buat `testset_generator.py`**

Buat file `experiments/pymupdf4llm/model_ai/eval/testset_generator.py` dengan isi:

```python
import json
import os
from pathlib import Path

from dotenv import load_dotenv
from langchain_core.documents import Document
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from ragas.embeddings import LangchainEmbeddingsWrapper
from ragas.llms import LangchainLLMWrapper
from ragas.testset import TestsetGenerator

APP_DIR = Path(__file__).resolve().parents[2]
ENV_FILE = APP_DIR / ".env"
CHUNKS_FILE = APP_DIR / "data" / "output_chunks.json"
TESTSET_FILE = APP_DIR / "data" / "eval_testset.json"

load_dotenv(dotenv_path=ENV_FILE)


def _get_required_env(name: str) -> str:
    value = os.getenv(name, "").strip()
    if not value:
        raise SystemExit(f"[eval] {name} belum di-set di file .env.")
    return value


def _load_chunks_as_documents() -> list[Document]:
    if not CHUNKS_FILE.exists():
        raise SystemExit(
            f"[eval] File chunks tidak ditemukan: {CHUNKS_FILE}\n"
            "Jalankan `python manage.py setup --skip-ingest` terlebih dahulu."
        )
    with CHUNKS_FILE.open(encoding="utf-8") as f:
        chunks = json.load(f)

    docs = []
    for chunk in chunks:
        content = chunk.get("content", "").strip()
        if not content:
            continue
        docs.append(
            Document(
                page_content=content,
                metadata={
                    "source": chunk.get("chunk_parent", "unknown"),
                    "page_start": chunk.get("page_start", 0),
                    "page_end": chunk.get("page_end", 0),
                },
            )
        )
    return docs


def _build_generator() -> TestsetGenerator:
    api_key = _get_required_env("OPENAI_API_KEY")
    testset_size = int(os.getenv("RAGAS_TESTSET_SIZE", "20"))

    generator_llm = LangchainLLMWrapper(
        ChatOpenAI(model="gpt-4o", openai_api_key=api_key)
    )
    generator_embeddings = LangchainEmbeddingsWrapper(
        OpenAIEmbeddings(openai_api_key=api_key)
    )
    return TestsetGenerator(
        llm=generator_llm,
        embedding_model=generator_embeddings,
    )


def generate_testset() -> Path:
    _get_required_env("OPENAI_API_KEY")
    testset_size = int(os.getenv("RAGAS_TESTSET_SIZE", "20"))

    print(f"[eval] Memuat chunks dari {CHUNKS_FILE}...")
    docs = _load_chunks_as_documents()
    print(f"[eval] {len(docs)} dokumen siap untuk testset generation.")

    print(f"[eval] Generating {testset_size} synthetic Q&A pairs via gpt-4o...")
    generator = _build_generator()
    testset = generator.generate_with_langchain_docs(docs, testset_size=testset_size)

    rows = testset.to_pandas().to_dict("records")
    TESTSET_FILE.parent.mkdir(parents=True, exist_ok=True)
    with TESTSET_FILE.open("w", encoding="utf-8") as f:
        json.dump(rows, f, ensure_ascii=False, indent=2)

    print(f"[eval] Testset disimpan ke {TESTSET_FILE} ({len(rows)} samples).")
    return TESTSET_FILE
```

- [ ] **Step 3: Verifikasi import bersih**

```bash
cd experiments/pymupdf4llm
python -c "from model_ai.eval.testset_generator import generate_testset; print('import OK')"
```

Expected output: `import OK`

- [ ] **Step 4: Commit**

```bash
git add experiments/pymupdf4llm/model_ai/eval/
git commit -m "feat: add eval package with testset_generator module"
```

---

## Task 3: Buat ragas_evaluator.py

**Files:**
- Create: `experiments/pymupdf4llm/model_ai/eval/ragas_evaluator.py`

- [ ] **Step 1: Buat `ragas_evaluator.py`**

Buat file `experiments/pymupdf4llm/model_ai/eval/ragas_evaluator.py`:

```python
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
```

- [ ] **Step 2: Verifikasi import bersih**

```bash
cd experiments/pymupdf4llm
python -c "from model_ai.eval.ragas_evaluator import run_evaluation; print('import OK')"
```

Expected output: `import OK`

- [ ] **Step 3: Commit**

```bash
git add experiments/pymupdf4llm/model_ai/eval/ragas_evaluator.py
git commit -m "feat: add ragas_evaluator with 5-metric evaluation pipeline"
```

---

## Task 4: Tambah Commands ke manage.py

**Files:**
- Modify: `experiments/pymupdf4llm/manage.py`

- [ ] **Step 1: Tambah fungsi `run_generate_testset` dan `run_eval`**

Edit `experiments/pymupdf4llm/manage.py` — tambahkan dua fungsi baru setelah fungsi `run_setup`:

```python
def run_generate_testset() -> None:
    from model_ai.eval.testset_generator import generate_testset

    generate_testset()


def run_eval() -> None:
    from model_ai.eval.ragas_evaluator import run_evaluation

    run_evaluation()
```

- [ ] **Step 2: Daftarkan subcommands di `main()`**

Edit bagian `subparsers` di dalam fungsi `main()` — tambahkan dua subparser baru setelah blok `ui`:

```python
    subparsers.add_parser(
        "generate_testset",
        help="Generate synthetic Q&A testset dari output_chunks.json menggunakan RAGAS + gpt-4o.",
    )

    subparsers.add_parser(
        "eval",
        help="Evaluasi RAG pipeline menggunakan RAGAS metrics (Faithfulness, AnswerRelevancy, dll).",
    )
```

- [ ] **Step 3: Tambah handler di bagian bawah `main()`**

Edit blok `if args.command` di akhir fungsi `main()` — tambahkan dua kondisi baru:

```python
    if args.command == "generate_testset":
        run_generate_testset()
        return

    if args.command == "eval":
        run_eval()
```

- [ ] **Step 4: Verifikasi `--help` menampilkan command baru**

```bash
cd experiments/pymupdf4llm
python manage.py --help
```

Expected output (sebagian):
```
  {setup,ui,generate_testset,eval}
    generate_testset    Generate synthetic Q&A testset dari output_chunks.json...
    eval                Evaluasi RAG pipeline menggunakan RAGAS metrics...
```

- [ ] **Step 5: Commit**

```bash
git add experiments/pymupdf4llm/manage.py
git commit -m "feat: add generate_testset and eval commands to manage.py"
```

---

## Task 5: Smoke Test End-to-End (dry run)

- [ ] **Step 1: Cek OPENAI_API_KEY sudah ada di .env**

Buka `experiments/pymupdf4llm/.env` dan pastikan `OPENAI_API_KEY` sudah diisi dengan nilai yang valid (bukan placeholder).

- [ ] **Step 2: Jalankan generate_testset**

```bash
cd experiments/pymupdf4llm
python manage.py generate_testset
```

Expected output (sebagian):
```
[eval] Memuat chunks dari .../data/output_chunks.json...
[eval] 90 dokumen siap untuk testset generation.
[eval] Generating 20 synthetic Q&A pairs via gpt-4o...
[eval] Testset disimpan ke .../data/eval_testset.json (20 samples).
```

- [ ] **Step 3: Verifikasi eval_testset.json terbentuk**

```bash
python -c "
import json
with open('experiments/pymupdf4llm/data/eval_testset.json') as f:
    data = json.load(f)
print(f'Samples: {len(data)}')
print('Keys sample[0]:', list(data[0].keys()))
"
```

Expected output:
```
Samples: 20
Keys sample[0]: ['user_input', 'reference', ...]
```

- [ ] **Step 4: Jalankan eval**

```bash
cd experiments/pymupdf4llm
python manage.py eval
```

Expected output (sebagian):
```
[eval] Memuat testset...
[eval] 20 pertanyaan ditemukan.
[eval] Menjalankan RAG pipeline untuk setiap pertanyaan...
...
Evaluation Results:
┌──────────────────────┬─────────┐
│ Metric               │ Score   │
├──────────────────────┼─────────┤
│ faithfulness         │ 0.XXXX  │
...
Results saved to .../data/eval_results.json
```

- [ ] **Step 5: Tambahkan data/eval_testset.json dan data/eval_results.json ke .gitignore**

Buka `.gitignore` di root project dan pastikan ada entri berikut (tambahkan jika belum):

```
experiments/pymupdf4llm/data/eval_testset.json
experiments/pymupdf4llm/data/eval_results.json
```

- [ ] **Step 6: Commit final**

```bash
git add .gitignore
git commit -m "chore: ignore eval_testset.json and eval_results.json from git"
```
