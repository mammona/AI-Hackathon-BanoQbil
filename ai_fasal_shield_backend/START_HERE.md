# Start Here - V17 Dedicated Qwen3 Reranker

## 1. Activate backend

```powershell
conda activate fasal-backend
pip install -r requirements.txt
```

## 2. Verify the two Ollama models

```powershell
ollama list
```

Required in Ollama:

```text
qwen3:1.7b
qwen3-embedding:0.6b
```

If missing:

```powershell
ollama pull qwen3:1.7b
ollama pull qwen3-embedding:0.6b
```

`qwen3:1.7b` is only for farmer-answer extraction. It is no longer the symptom reranker.

## 3. Download the dedicated reranker once

```powershell
python -m scripts.prepare_qwen_reranker
```

This downloads/caches:

```text
Qwen/Qwen3-Reranker-0.6B
```

The model is about 1.2 GB. Do this before the demo so the reranker is available from local cache.

## 4. Start FastAPI

```powershell
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

Open:

```text
http://127.0.0.1:8000/docs
```

## 5. Verify RAG health

Use:

```text
GET /api/v1/rag/health
```

Expected reranker cache:

```text
cached
```

Then warm the model once:

```text
POST /api/v1/rag/reranker/warmup
```

## 6. Test the known curling failure first

Use:

```text
POST /api/v1/rag/test
```

Body:

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

Expected final code:

```text
LEAF_CURLING
```

The response shows both `score` (embedding cosine similarity) and `reranker_score` (dedicated reranker probability). They are different metrics.

## 7. Run the complete Punjabi benchmark

Swagger:

```text
POST /api/v1/rag/test-suite/punjabi?use_reranker=true
```

or terminal:

```powershell
python -m scripts.evaluate_punjabi_dedicated_reranker
```

Freeze this module if the dedicated reranker reaches the agreed quality target. Do not resume qwen3:1.7b prompt experiments.
