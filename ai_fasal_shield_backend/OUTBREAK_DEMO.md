# Outbreak Demo Sequence

## Model placement
Put the supplied model files here:

```text
models/
└── disease/
    ├── cotton_disease_classifier.pt
    ├── rice_disease_classifier.pt
    └── class_mappings.json
```

## Start

```powershell
conda activate fasalshield
pip install -r requirements.txt
ollama list
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

Open `http://127.0.0.1:8000/docs`.

## Clean database before a judged demo (optional)

```powershell
python -m scripts.reset_prototype_db
```

Restart Uvicorn after reset. The tables are recreated automatically.

## Alert thresholds
- 1 related usable report: `NO_ALERT`
- 2 related usable reports: `MONITORING`
- 3+ related reports with at least one reliable image-supported report: `AMBER`
- Entirely symptom-only cluster: 4+ reports for `AMBER`
- Expert confirms `AMBER`: `RED`

Related means:
- same crop
- within 5 km
- within 7 days
- same reliable disease OR at least one overlapping canonical symptom code

`OTHERS_MAP` is removed before symptom overlap comparison.

## Swagger sequence
Submit reports with unique IDs and nearby coordinates. Use the same canonical symptom (for example leaf curling) or the same image disease.

Suggested coordinates:
- R1: 31.5204, 74.3587
- R2: 31.5214, 74.3597
- R3: 31.5224, 74.3607
- R4: 31.5234, 74.3617

### R1
`POST /api/v1/reports/process`

Expected outbreak result: `NO_ALERT`.

### R2
Submit a related nearby report.

Expected: `MONITORING` and an `alert_id`.

### R3
If at least one of R1-R3 has reliable image-supported disease evidence, expected: `AMBER`.

If the cluster is entirely `SYMPTOM_ONLY`, submit R4 to reach `AMBER`.

### Expert confirmation
Use:

`POST /api/v1/alerts/{alert_id}/verify`

```json
{
  "decision": "confirmed",
  "expert_name": "Agriculture Officer",
  "note": "Field verification confirms the outbreak signal."
}
```

Expected: `RED`, status `confirmed`.

## Useful checks

```text
GET /api/v1/alerts
GET /api/v1/alerts/active
GET /api/v1/alerts/{alert_id}
GET /api/v1/dashboard/summary
GET /api/v1/rag/health
```
