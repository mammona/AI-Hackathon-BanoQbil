# V13 Retrieve -> Rerank Symptom RAG

## Why V13

V12 used the embedding Top-1 score as the final classifier. Real Punjabi testing showed that the correct symptom was often present in Top-3/Top-5 but not ranked first. Example:

- farmer: `پتے مڑ وی رہے نیں`
- embedding Top-1: `LEAF_YELLOWING`
- Top-2: `LEAF_DRYING`
- Top-3: `LEAF_CURLING` (correct)

V13 separates retrieval from final classification.

## Runtime flow

1. Qwen3 1.7B preserves/splits Q1 symptom spans.
2. Python validates explicit affected part from raw Q1.
3. Crop + affected part hard-filter the controlled concept set.
4. Qwen3-Embedding 0.6B retrieves Top-5 concepts in the selected language.
5. Clear retrievals are accepted directly only when both score and margin are strong.
6. Ambiguous retrievals are sent to a constrained Qwen3 1.7B reranker.
7. The reranker may choose only one retrieved code or `OTHERS_MAP`.
8. If reranking fails, the system fails safe to `OTHERS_MAP`.

No runtime translation is used.

## Local models

```powershell
ollama pull qwen3:1.7b
ollama pull qwen3-embedding:0.6b
```

## Swagger test API

Start backend:

```powershell
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

Open:

`http://127.0.0.1:8000/docs`

### Test one symptom

`POST /api/v1/rag/test`

Example:

```json
{
  "symptom": "پتے مڑ وی رہے نیں",
  "crop": "cotton",
  "language": "punjabi",
  "affected_part": "leaves",
  "use_reranker": true,
  "top_k": 5
}
```

The response shows Top-5 embedding candidates, whether the reranker was used, and the final code.

### Run all 10 Punjabi reports

`POST /api/v1/rag/test-suite/punjabi?use_reranker=true`

For a retrieval-only baseline:

`POST /api/v1/rag/test-suite/punjabi?use_reranker=false`

Compare Top-1 / Top-3 / Top-5 recall with final accuracy.

## Command-line tests

Retrieval only:

```powershell
python -m scripts.evaluate_punjabi_rag_reports --mode both
```

Retrieve + rerank:

```powershell
python -m scripts.evaluate_punjabi_retrieve_rerank
```
