
## Prototype image path (V17 API-crop routing)

This build intentionally does **not** use SigLIP. `selected_crop` from the API directly routes the valid uploaded image to the corresponding cotton/rice disease model. See `IMAGE_MODEL_SETUP.md` for exact model placement and commands.

# AI Fasal Shield Backend - V17 Dedicated Qwen3 Reranker

The current symptom pipeline keeps the successful multilingual retrieval layer and replaces generative reranking with `Qwen/Qwen3-Reranker-0.6B`. Start with `START_HERE.md` and `QWEN3_DEDICATED_RERANKER_V17.md`.

```text
qwen3:1.7b                  -> farmer extraction
qwen3-embedding:0.6b        -> candidate retrieval
Qwen/Qwen3-Reranker-0.6B    -> candidate reranking
```

No paid API is required. Download the reranker before the demo with:

```powershell
python -m scripts.prepare_qwen_reranker
```

---

# AI Fasal Shield Backend - V11 Language-Selected Multilingual Symptom RAG

V11 removes runtime symptom translation from the RAG path.

The mobile/API request now contains a required `language` form parameter:

- `english`
- `urdu`
- `punjabi` = Pakistani Punjabi in Shahmukhi script

The selected language controls **which canonical symptom concept embeddings are used**.

```text
Farmer Q1
   ↓
Qwen3 1.7B copies original symptom spans + proposes affected_part
   ↓
Python validates explicit plant-part evidence
   ↓
crop + plant part hard filter
   ↓
language parameter
   ├─ english  → English concept descriptions only
   ├─ urdu     → Urdu concept descriptions only
   └─ punjabi  → Punjabi/Shahmukhi concept descriptions only
   ↓
qwen3-embedding:0.6b
   ↓
Top-3 cosine similarity
   ↓
threshold + margin
   ↓
canonical symptom code OR OTHERS_MAP
```

There is no symptom alias table and no Punjabi/Urdu-to-English translation call before RAG.

## Knowledge base v6.0

`app/constants/symptoms.py` contains 40 rice/cotton canonical concepts. Every concept has:

- canonical English code/name
- English semantic definition
- Urdu semantic definition
- Punjabi/Shahmukhi semantic definition
- crop metadata
- plant-part metadata

Crop and plant-part metadata are **filters**, not embedding text.

## API change

`POST /api/v1/reports/process` now requires:

```text
language = english | urdu | punjabi
```

Example for the user's current test:

```text
selected_crop = cotton
language = urdu
answer_1 = پتے پیلے ہو رہے ہیں اور مڑ رہے ہیں
```

The response preserves the report language and each mapping includes `retrieval_language`.

## Local models

```text
qwen3:1.7b
qwen3-embedding:0.6b
```

No paid API is required.

## Recommended validation

```powershell
python -m pytest -q tests\test_language_selected_rag.py tests\test_symptom_rag.py tests\test_plant_part_validator.py tests\test_qwen_focused_questions.py tests\test_embedding_backend.py

python scripts\evaluate_language_selected_rag.py --language urdu
python scripts\evaluate_language_selected_rag.py --language punjabi
python scripts\evaluate_language_selected_rag.py --language english

python scripts\evaluate_multilingual_pipeline.py --case 1
```

Read `LANGUAGE_SELECTED_SYMPTOM_RAG_V11.md` for the design details.

## V12 clean language-selected RAG

The current symptom retriever uses the report `language` parameter and embeds short, positive concept descriptions only. Detailed exclusion-heavy definitions are retained for documentation but are not used as embedding documents. Start evaluation with:

```powershell
python scripts\evaluate_clean_language_rag.py --language punjabi
python scripts\evaluate_clean_language_rag.py --language urdu
```

See `CLEAN_LANGUAGE_SYMPTOM_RAG_V12.md`.


## V13 retrieve -> rerank symptom RAG

The current symptom pipeline uses Qwen3-Embedding for Top-5 candidate retrieval and constrained local Qwen3 1.7B reranking only for ambiguous cases. Test it in Swagger with `POST /api/v1/rag/test` or run the bundled 10-report benchmark with `POST /api/v1/rag/test-suite/punjabi`. See `RETRIEVE_RERANK_RAG_V13.md`.

## V17 outbreak-ready update

The current prototype keeps the V17 Qwen extraction + embedding + dedicated reranker pipeline and adds deterministic SQL-backed outbreak detection. See `CHANGELOG_V17_OUTBREAK.md` and `OUTBREAK_DEMO.md`.

Main additions:
- optional image and independently optional Q1-Q4 answers (at least one input required)
- `MULTIMODAL`, `IMAGE_ONLY`, `SYMPTOM_ONLY`, and `CONTEXT_ONLY` evidence modes
- SQLite `alerts` + `alert_reports`
- 5 km / 7 day deterministic clustering
- `NO_ALERT -> MONITORING -> AMBER -> expert-confirmed RED`

If upgrading an old SQLite DB, startup adds the new columns/tables without deleting old reports. Old rows are preserved conservatively; for the cleanest judged demo, reset the prototype DB and submit the demo reports again:

```powershell
python -m scripts.reset_prototype_db
```

## Admin / Expert Dashboard

After starting Uvicorn, open:

```text
http://127.0.0.1:8000/admin
```

The dashboard reads the existing SQLite/API data and lets the admin or agricultural expert inspect farmer reports and review outbreak alerts. Amber alerts can be confirmed to Red or rejected directly from the dashboard.

### Important input rule

The crop image is **optional**. Q1-Q4 are also individually optional. `/api/v1/reports/process` accepts the report when an image OR at least one farmer answer is present. Only an entirely empty evidence submission is rejected.


## Punjabi confirmed farmer notifications

When an agricultural expert confirms an AMBER alert, the backend promotes it to RED and creates farmer-facing notification records in Punjabi (Shahmukhi). Internal canonical crop/disease/symptom codes remain unchanged for outbreak logic.

The expert verification note is stored separately on the alert and is **not** used as the farmer notification message.

## Expert report review + Punjabi farmer alerts

The admin dashboard now supports `VALID`, `INVALID`, and `FOLLOW_UP` review decisions for individual farmer reports. Reports that the AI flags for expert review are held out of automatic outbreak clustering until marked `VALID`. A valid review immediately rechecks the 5 km / 7 day outbreak rules; if it produces an AMBER alert, the dashboard opens that alert for expert confirmation. Confirming AMBER promotes it to RED and creates Punjabi Shahmukhi notifications for eligible registered farmer devices. Internal report-review and alert-verification notes are never sent to farmers.

API: `POST /api/v1/reports/{report_id}/review`


## Reviewer instructions in farmer notifications

Alert confirmation separates the private verification note from the Punjabi farmer instruction. Only `farmer_instruction` is appended to farmer notifications. The private verification note remains admin-only.

## V17.1 device registration fix

The backend now automatically registers/updates any mobile `device_id` received with a farmer report. Bundled demo devices are also seeded idempotently at startup from `data/demo_devices.json` when `AUTO_SEED_DEMO_DEVICES=true`. See `DEVICE_REGISTRATION_FIX.md`.
