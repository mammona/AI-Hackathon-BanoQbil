# Context-Aware Multilingual Symptom RAG V9

## Problem fixed

V8 correctly stopped translating Q1, but semantic retrieval still saw close scores for specific and broad concepts. It also split shared-subject sentences into fragments such as `مڑ رہے ہیں`, which lose the plant-part context.

## V9 changes

1. **Shared context restoration**: if the complete Q1 contains exactly one explicit plant part, later conjunction fragments inherit the exact original plant-part term. No symptom translation is performed.
2. **Crop + plant-part hard filtering**: irrelevant organs and unsupported crop concepts are removed before similarity scoring.
3. **Structured query**: crop, affected part, and the untouched farmer observation are embedded together.
4. **Concept KB v4.0**: 40 canonical concepts use positive, specificity-focused semantic descriptions rather than phrase aliases.
5. **Hybrid semantic scoring**: each concept has a short identity vector and a full definition vector. Default combined score is 60% identity + 40% definition. Both concept matrices are computed once and cached in RAM.
6. **Conservative decision**: threshold and Top1/Top2 margin remain required. No generative symptom reranker is used.

## Why two concept vectors?

A long definition gives useful meaning but can make closely related concepts similar. A short concept identity emphasizes the actual canonical concept. Combining both remains semantic retrieval while improving separation.

## No alias dictionary

There is no list such as `patta peela -> LEAF_YELLOWING`. Urdu, Punjabi/Shahmukhi, Roman Urdu, and English are embedded directly. The small plant-part vocabulary is retained only as an explicit evidence guardrail.

## Evaluation

Run:

```powershell
python scripts\evaluate_yellowing_variants.py
python scripts\evaluate_multilingual_retrieval.py
python scripts\evaluate_multilingual_pipeline.py
```

Do not lower `SYMPTOM_MATCH_THRESHOLD` or `SYMPTOM_MIN_MARGIN` until the printed Top-3 diagnostics show why a test fails. Tune the concept KB, retrieval model, identity weight, and thresholds from a larger labelled benchmark.
