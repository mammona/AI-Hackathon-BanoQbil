# V17 Outbreak-Ready Changelog

## Kept intact
- `qwen3:1.7b` for focused Q1-Q4 farmer-answer extraction through Ollama.
- `qwen3-embedding:0.6b` for multilingual symptom candidate retrieval through Ollama.
- `Qwen/Qwen3-Reranker-0.6B` as the dedicated symptom reranker through Transformers.
- API-selected crop routing to the cotton/rice EfficientNet disease checkpoints.
- Existing report fields and report endpoints.

## Fixed
- Removed the `matched_specific_over_parent` early-accept path. Ambiguous embedding results now reach the dedicated reranker unless they pass the strong direct-accept gate (`>=0.65` score and `>=0.08` margin by default).
- Punjabi Q1 fallback splitting now recognizes `تے` in addition to Urdu `اور` and English `and`.
- Symptom logs now expose whether the dedicated reranker was used and its selected score.

## Added
- Deterministic report evidence modes: `MULTIMODAL`, `IMAGE_ONLY`, `SYMPTOM_ONLY`, `CONTEXT_ONLY`.
- SQLite persistence fields for evidence quality and outbreak usability.
- Optional GPS. Missing GPS reports are stored but not automatically geo-clustered.
- Optional timestamp. Missing timestamp uses server UTC time.
- `alerts` and `alert_reports` tables.
- Deterministic Haversine + 7-day outbreak engine.
- `NO_ALERT -> MONITORING -> AMBER`; RED only after expert confirmation.
- `GET /api/v1/alerts`
- `GET /api/v1/alerts/active`
- `GET /api/v1/alerts/{alert_id}`
- `POST /api/v1/alerts/{alert_id}/verify`
- Expanded `GET /api/v1/dashboard/summary`.
- Additive SQLite compatibility migration on startup.
- `scripts/reset_prototype_db.py` for a clean demo reset.

## Safety / prototype rules
- `OTHERS_MAP` alone never makes reports related.
- Cotton `healthy` is stored but never used as disease outbreak evidence.
- Low-confidence image predictions do not count as reliable outbreak image evidence.
- Reports remain stored even if outbreak evaluation fails.
- No SigLIP in the current prototype. The API-selected crop is trusted for disease-model routing.

## V17 Admin Dashboard update

- Clarified in OpenAPI/Swagger that image is OPTIONAL.
- Added regression tests proving symptom-only reports reach `/reports/process` without a file upload.
- Added `/admin` local admin/expert dashboard.
- Dashboard reviews farmer reports from SQLite and active outbreak alerts.
- Dashboard supports Amber confirmation -> Red and alert rejection using the existing expert verification API.
