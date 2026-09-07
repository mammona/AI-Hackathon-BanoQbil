# V17 - Qwen3 Dedicated Symptom Reranker

V17 starts from the stable V14 retrieval baseline and replaces the generative `qwen3:1.7b` reranking step with the official `Qwen/Qwen3-Reranker-0.6B` text-ranking model.

## Final responsibility split

```text
Qwen3 1.7B (Ollama)
  farmer Q1-Q4 extraction only

Qwen3-Embedding 0.6B (Ollama)
  retrieve candidate symptom concepts

Qwen3-Reranker 0.6B (Hugging Face / local cache)
  score the retrieved candidate meanings

Python
  threshold, OTHERS_MAP, canonical code, logging
```

The reranker uses Qwen's official yes/no logit scoring method. It does not generate A/B/C labels, JSON choices, pairwise votes, or free-form symptom codes.

## Why this replaces V15/V16

The Punjabi benchmark showed the embedding retriever already had 100% Top-3 recall for the 17 known symptoms. The weak component was using the small generative model as a semantic judge. A dedicated reranking model matches the actual task and removes generation/position/pairwise instability.

## Decision rules

1. Retrieval below `SYMPTOM_RETRIEVAL_FLOOR` -> `OTHERS_MAP`.
2. Very strong embedding result -> direct semantic acceptance.
3. Otherwise rerank the Top-3 candidates with `Qwen3-Reranker-0.6B`.
4. Best reranker probability below `SYMPTOM_RERANKER_MIN_SCORE` -> `OTHERS_MAP`.
5. Optional reranker margin gate is controlled by `SYMPTOM_RERANKER_MIN_MARGIN` and defaults to `0.00` so it does not recreate V15's over-rejection problem.

## Important diagnostics

`similarity` remains the selected embedding cosine score.

V17 adds:

- `reranker_score`
- `reranker_second_score`
- `reranker_margin`
- `reranker_reason`

The Swagger test endpoint also shows a `reranker_score` for every candidate actually sent to the dedicated reranker.

## Setup

```powershell
pip install -r requirements.txt
python -m scripts.prepare_qwen_reranker
```

Then:

```powershell
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

## Test endpoints

```text
GET  /api/v1/rag/health
POST /api/v1/rag/reranker/warmup
POST /api/v1/rag/test
GET  /api/v1/rag/test-suite/punjabi/reports
POST /api/v1/rag/test-suite/punjabi/report/{report_id}
POST /api/v1/rag/test-suite/punjabi
```
