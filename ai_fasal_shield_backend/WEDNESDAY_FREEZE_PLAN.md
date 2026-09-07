# Wednesday Freeze Plan

Do not redesign symptom RAG again unless the dedicated reranker fails the benchmark badly.

## Gate 1 - V17 symptom layer

1. `python -m scripts.prepare_qwen_reranker`
2. `ollama list` and confirm `qwen3-embedding:0.6b` + `qwen3:1.7b`
3. `python -m scripts.evaluate_punjabi_dedicated_reranker`
4. Freeze V17 if final accuracy is at least 90% with no pipeline crashes and the unknown case is rejected.
5. If accuracy is below 90%, inspect reranker probabilities first. Tune only `SYMPTOM_RERANKER_MIN_SCORE` from evidence. Do not return to generative/pairwise reranking.

## Gate 2 - End-to-end demo

Verify mobile report -> backend -> structured report -> database -> GPS/time fields.

## Gate 3 - Outbreak story

Demonstrate multiple nearby reports of the same crop + compatible symptom code becoming a cluster/risk signal, then expert verification and a nearby farmer warning.

## Gate 4 - Demo reliability

Pre-download all models, warm them once, use fixed demo images/audio as backups, and keep one known-good report flow ready.
