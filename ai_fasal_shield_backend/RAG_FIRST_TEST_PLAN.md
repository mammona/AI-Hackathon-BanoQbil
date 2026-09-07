# Punjabi RAG-First Test Plan

This package intentionally **does not add a reranker and does not change production RAG logic**.
We first measure whether the current embedding retriever is good enough on 10 realistic Punjabi/Shahmukhi farmer reports.

## What is isolated

The evaluation bypasses Qwen extraction, image validation, disease classification, and the FastAPI report pipeline.
Each report contains manually specified original-language symptom spans and the expected canonical code.
Therefore a failure in this script is a **RAG/retrieval problem**, not a Qwen extraction problem.

## Main command

```powershell
conda activate fasal-backend
python scripts\evaluate_punjabi_rag_reports.py --mode both
```

`--mode both` performs an A/B test without changing production code:

- `current`: current Qwen3-Embedding query instruction ON.
- `plain`: same `qwen3-embedding:0.6b`, same Punjabi concept documents, but no query instruction.

The script reports:

- Top-1 retrieval accuracy
- Top-3 recall
- final threshold/margin decision accuracy
- ambiguous count
- below-threshold count
- exact Top-3 Punjabi concept documents and scores

## Decision rule before implementing a reranker

- If the expected concept is usually **Top-1**, improve threshold/margin only if needed.
- If the expected concept is usually **inside Top-3 but not Top-1**, retrieval is doing its job and a constrained reranker is justified.
- If the expected concept is often **missing from Top-3**, do not add a reranker yet. Improve embeddings/concept descriptions/retrieval first.

## Test one report only

```powershell
python scripts\evaluate_punjabi_rag_reports.py --mode both --case RAG-PB-001
```

## Test data

`evaluation/punjabi_rag_10_reports.json` contains 10 full farmer reports. Q2-Q4 are included so the same reports can later be reused for the end-to-end API test after RAG is accepted.

## Windows direct-script import fix

The evaluator now adds the backend project root to `sys.path`, so this works from the backend root:

```powershell
python scripts\evaluate_punjabi_rag_reports.py --mode both --case RAG-PB-001
```

You can also run it as a module:

```powershell
python -m scripts.evaluate_punjabi_rag_reports --mode both --case RAG-PB-001
```
