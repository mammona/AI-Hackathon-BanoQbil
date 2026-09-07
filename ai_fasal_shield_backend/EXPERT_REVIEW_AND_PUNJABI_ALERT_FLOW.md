# Expert review + Punjabi farmer alert flow

1. Farmer report is stored immediately.
2. Reports flagged by the AI as needing expert review are held out of automatic clustering until reviewed.
3. Admin opens the report and chooses **Mark Valid**, **Mark Invalid**, or **Needs Follow-up**.
4. `VALID` makes usable structured evidence eligible for outbreak detection and immediately rechecks nearby reports within the configured 5 km / 7 day rules.
5. If the cluster becomes `MONITORING` or `AMBER`, the dashboard opens that outbreak alert.
6. An expert can confirm only `AMBER`. Confirmation promotes it to `RED`.
7. The backend finds registered same-crop devices inside the alert radius and creates Punjabi Shahmukhi notifications.
8. Report review notes and alert verification notes are internal and are never copied into farmer notifications.

## API

`POST /api/v1/reports/{report_id}/review`

```json
{
  "decision": "valid",
  "expert_name": "Agriculture Officer",
  "note": "Field evidence looks valid."
}
```

Decisions: `valid`, `invalid`, `follow_up`.

Alert confirmation remains:

`POST /api/v1/alerts/{alert_id}/verify`

```json
{
  "decision": "confirmed",
  "expert_name": "Agriculture Officer",
  "note": "Internal verification note."
}
```

New RED notifications are Punjabi and contain crop, problem, common symptoms, approximate distance, and a safe action message.
