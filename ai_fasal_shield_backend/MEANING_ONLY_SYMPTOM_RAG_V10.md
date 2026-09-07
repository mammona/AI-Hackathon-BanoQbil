# AI Fasal Shield - Meaning-Only Multilingual Symptom RAG V10

## What V10 fixes

V9 repeated crop and plant-part metadata inside both the query vector and every
concept vector. Because Python had already filtered by those fields, the repeated
metadata made unrelated leaf symptoms artificially similar. V10 separates the two
responsibilities.

## Runtime flow

1. Q1 keeps original Urdu/Punjabi/English symptom spans.
2. Python restores a shared explicit plant-part subject after conjunction splitting.
3. Python validates `affected_part` from the raw answer. If Qwen returns `null` but
   the raw answer explicitly contains `پتے`, the final part becomes `leaves`.
4. Python filters the knowledge base by crop and validated plant part.
5. The embedding model sees only the raw symptom meaning.
6. Each canonical concept is represented by one concise meaning-only English document.
7. Cosine similarity ranks only eligible concepts.
8. Low score or small Top1-Top2 margin becomes `OTHERS_MAP`.

## Important

There is still no symptom alias dictionary. Crop/plant-part filtering is deterministic
metadata filtering; symptom normalization remains semantic.

## First live test

```powershell
python scripts/evaluate_meaning_only_rag.py
```

Then run:

```powershell
python scripts/evaluate_yellowing_variants.py
python scripts/evaluate_multilingual_pipeline.py --case 1
```

Do not lower thresholds until the Top-3 rankings from these scripts have been reviewed.

## Hierarchy-aware ambiguity

Some concepts are intentionally parent/child concepts. For example, leaf yellowing
is a specific form of leaf discoloration. If the specific concept ranks first above
its own generic parent, V10 may accept it even when their margin is small, provided
the absolute score still passes the match threshold. The reverse direction remains
ambiguous. This prevents a known ontology relationship from forcing a correct
specific symptom into `OTHERS_MAP`.
