# V17 Notification-Ready Changelog

- Kept V17 Qwen3 extraction, Qwen3 embedding and dedicated Qwen3 reranker architecture intact.
- Kept optional image behavior intact.
- Added optional `device_id` to farmer reports.
- Added `registered_devices` database table.
- Added `notifications` database table with duplicate protection per alert/device.
- Added device registration, device location update and device notification APIs.
- Expert AMBER confirmation now promotes alert to RED and creates in-app notification records for same-crop registered devices within the alert radius.
- Added English, Urdu and Punjabi deterministic warning templates. No pesticide/treatment generation.
- Added notification read endpoint.
- Added dashboard counts for registered devices and unread notifications.
- AMBER review panel now previews eligible farmer device count.
- Dashboard button renamed to **Confirm -> RED & Notify Farmers**.
- Added 15-report deterministic E2E seed data/scripts to this final merged build.
- Added six-device notification demo seed and notification inspection scripts.
- Added notification targeting/idempotency/rejection tests.

- Changed confirmed farmer notifications to Punjabi (Shahmukhi) for the prototype.
- `title`, `message`, and `message_local` are now farmer-facing Punjabi text.
- Added Punjabi mappings for cotton/rice diseases and canonical symptom codes.
- Expert `verification_note` remains stored only on the alert and is never copied into farmer notifications.
- Dashboard now clearly labels the verification note as internal.


## Expert review workflow update
- Added report review database fields: `expert_review_status`, `reviewed_by`, `review_note`, `reviewed_at`.
- Added `POST /api/v1/reports/{report_id}/review`.
- Reports that the AI flags for expert review are held out of automatic clustering until marked `VALID`.
- `VALID` immediately rechecks the geo-temporal outbreak cluster and can create/update MONITORING/AMBER.
- `INVALID` and `FOLLOW_UP` are excluded from automatic outbreak clustering.
- Admin report panel now has Mark Valid, Mark Invalid, and Needs Follow-up actions.
- If a VALID review creates/updates an alert, the admin UI opens the outbreak alert so AMBER can be confirmed to RED.
- Farmer RED notifications remain Punjabi Shahmukhi and never include internal report-review or verification notes.


## Reviewer farmer-instruction update
- Added `alerts.farmer_instruction` as a separate farmer-facing field.
- Kept `verification_note` private/admin-only.
- Punjabi notification now appends reviewer guidance as `زرعی ماہر دی ہدایت: ...`.
- Admin Amber confirmation panel now has separate private note and farmer instruction fields.
- Re-confirming with changed farmer guidance updates the existing notification and marks it unread instead of creating duplicates.
