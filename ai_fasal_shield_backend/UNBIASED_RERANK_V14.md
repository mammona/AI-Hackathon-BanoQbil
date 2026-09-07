# V14 Unbiased Retrieve → Rerank

V14 fixes a reranker-bias bug in V13. The embedding Top-K is still used for candidate retrieval, but the generative Qwen reranker no longer sees embedding scores, canonical codes, English concept names, or embedding-ranked order.

For ambiguous symptoms, candidate meanings are deterministically shuffled and replaced by anonymous labels (`A`, `B`, `C`, ...). Qwen receives only the original farmer symptom and same-language candidate meanings, then returns one anonymous label or `OTHER`. Python maps the label back to the canonical code.

This prevents the wrong embedding Top-1 candidate from biasing the reranker. The Swagger endpoint `POST /api/v1/rag/test` now returns `reranker_mode` and `reranker_candidate_order` for debugging.

Recommended test:

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

Expected final code: `LEAF_CURLING`.
