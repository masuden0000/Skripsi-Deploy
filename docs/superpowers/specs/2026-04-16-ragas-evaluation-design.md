# RAGAS Evaluation Design
**Date:** 2026-04-16  
**Project:** pymupdf4llm RAG Experiment  
**Status:** Approved

---

## Overview

Tambahkan evaluasi kuantitatif pada RAG pipeline menggunakan framework **RAGAS** dengan **OpenAI gpt-4o** sebagai LLM judge. Implementasi menggunakan pendekatan **Hybrid**: synthetic testset di-generate sekali dan disimpan, lalu digunakan berulang kali untuk evaluasi.

---

## Architecture

### File Structure (baru)
```
experiments/pymupdf4llm/
├── model_ai/
│   └── eval/
│       ├── __init__.py
│       ├── testset_generator.py   ← generate synthetic Q&A dari PDF chunks
│       └── ragas_evaluator.py     ← load testset, run RAG, evaluate
├── data/
│   ├── output_chunks.json         ← sudah ada (sumber untuk testset generation)
│   ├── eval_testset.json          ← baru, hasil generate (di-reuse)
│   └── eval_results.json          ← baru, hasil evaluasi terakhir
└── manage.py                      ← tambah dua command: generate_testset & eval
```

### Commands
| Command | Fungsi |
|---|---|
| `python manage.py generate_testset` | Generate synthetic Q&A dari chunks, simpan ke `data/eval_testset.json` |
| `python manage.py eval` | Load testset, run RAG pipeline, evaluate dengan RAGAS, simpan hasil |

---

## Data Flow

### Step 1: generate_testset
```
data/output_chunks.json
    → load chunks (content + metadata)
    → convert ke RAGAS Document format
    → TestsetGenerator(llm=gpt-4o, embeddings=OpenAIEmbeddings)
    → generate(docs, testset_size=RAGAS_TESTSET_SIZE)
    → simpan ke data/eval_testset.json
       [{ "user_input": "...", "reference": "...", "reference_contexts": [...] }]
```

### Step 2: eval
```
data/eval_testset.json
    → load pertanyaan (user_input, reference, reference_contexts)
    → untuk tiap pertanyaan → rag_service.py (retrieve + generate)
       → retrieved_contexts + response
    → build EvaluationDataset (SingleTurnSample per row)
    → evaluate(dataset, metrics=[...], llm=LangchainLLMWrapper(gpt-4o))
    → print tabel hasil di terminal
    → simpan ke data/eval_results.json (overwrite)
```

**`rag_service.py` digunakan as-is** — tidak ada modifikasi pada pipeline yang sudah ada.

---

## Metrics

| Metric | Butuh Reference | Keterangan |
|---|---|---|
| `Faithfulness` | Tidak | Jawaban sesuai konteks yang di-retrieve |
| `AnswerRelevancy` | Tidak | Jawaban relevan dengan pertanyaan |
| `ContextPrecision` | Ya | Chunk yang di-retrieve relevan |
| `ContextRecall` | Ya | Semua informasi penting ter-cover |
| `FactualCorrectness` | Ya | Fakta dalam jawaban benar |

---

## LLM Judge

```python
from langchain_openai import ChatOpenAI
from ragas.llms import LangchainLLMWrapper

evaluator_llm = LangchainLLMWrapper(ChatOpenAI(model="gpt-4o"))
```

Dipakai oleh semua metrik yang memerlukan LLM judge.

---

## Dependencies

### Tambah ke `requirements.txt`
```
ragas>=0.2.0
langchain-openai>=0.1.0
openai>=1.0.0
```

### Tambah ke `.env` dan `.env.example`
```
OPENAI_API_KEY=sk-...
RAGAS_TESTSET_SIZE=20
```

---

## Error Handling

| Kondisi | Behavior |
|---|---|
| `eval_testset.json` belum ada saat `eval` dijalankan | Print: *"Run `python manage.py generate_testset` first"*, exit |
| `OPENAI_API_KEY` tidak ada | Fail early dengan pesan informatif sebelum API call |
| RAG pipeline gagal untuk satu pertanyaan | Skip sample, log warning, lanjut ke berikutnya |
| `eval_results.json` sudah ada | Overwrite (bukan append) |

---

## Output Terminal (eval)

```
Evaluation Results:
┌─────────────────────┬────────┐
│ Metric              │ Score  │
├─────────────────────┼────────┤
│ faithfulness        │ 0.82   │
│ answer_relevancy    │ 0.91   │
│ context_precision   │ 0.76   │
│ context_recall      │ 0.68   │
│ factual_correctness │ 0.79   │
└─────────────────────┴────────┘
Results saved to data/eval_results.json
```

---

## Out of Scope

- Integrasi evaluasi ke chat server (runtime evaluation)
- Dashboard visualisasi hasil evaluasi
- Evaluasi otomatis saat CI/CD
- Multi-turn conversation evaluation
