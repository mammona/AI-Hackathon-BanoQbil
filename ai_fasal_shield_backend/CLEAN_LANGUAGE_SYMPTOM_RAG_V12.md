# V12 Clean Language-Selected Symptom RAG

V12 fixes the V11 ranking failure where Punjabi yellowing/curling retrieved brown/white/black spots.

## Root cause fixed

V11 embedded long concept descriptions containing exclusion words such as "not wilting" and "not holes". Embeddings are similarity models, not logical rule engines, so those negative words polluted the concept vector. V11 also used a Punjabi/Urdu task instruction, which added extra language-specific tokens to every short query.

## V12 design

- `language` remains an API parameter: `english`, `urdu`, or `punjabi`.
- Q1 symptom spans stay verbatim in the farmer's original language.
- Qwen still proposes `affected_part`; Python validates explicit raw plant-part evidence.
- Crop and affected part are deterministic filters only.
- RAG uses exactly one selected-language concept catalog.
- Each concept has a short positive retrieval description used only for embeddings.
- Detailed definitions remain in the code for documentation, but they are not embedded.
- All multilingual queries use one short English retrieval-task instruction. The symptom itself is not translated.
- Threshold + margin remain conservative; uncertain cases become `OTHERS_MAP`.

## Test first

```powershell
python scripts\evaluate_clean_language_rag.py --language punjabi
python scripts\evaluate_clean_language_rag.py --language urdu
```

Then test the complete Punjabi report through FastAPI.
