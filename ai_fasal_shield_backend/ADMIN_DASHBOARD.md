# AI Fasal Shield Admin / Expert Dashboard

Start the backend:

```powershell
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

Open:

- Admin dashboard: `http://127.0.0.1:8000/admin`
- Swagger API: `http://127.0.0.1:8000/docs`

## What the dashboard shows

- Total reports, outbreak-usable reports, reports needing expert review
- Monitoring, Amber and Red alert counts
- Farmer report table with crop, disease, canonical symptoms, evidence mode, GPS and status
- Filters for crop, evidence mode and expert-review requirement
- Full report review panel showing raw Q1-Q4 answers, disease evidence, extracted symptoms, location, summary and outbreak assessment
- Alert table showing cluster disease/symptoms, report count, center and status
- Amber alert expert verification: Confirm promotes Amber to Red; Reject marks the alert rejected

The dashboard is implemented with plain HTML/CSS/JavaScript and calls the existing FastAPI endpoints. It has no front-end package dependency and works locally.

## Optional image rule

`POST /api/v1/reports/process` accepts any of these:

- image + all answers
- image + some answers
- image only
- Q1 only
- Q2 only
- Q3 only
- Q4 only
- any combination of Q1-Q4 without an image

Only a report with **no image and no farmer answers at all** is rejected with HTTP 422.
