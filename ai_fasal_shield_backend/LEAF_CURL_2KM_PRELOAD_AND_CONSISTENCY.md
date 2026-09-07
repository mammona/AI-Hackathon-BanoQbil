# Leaf Curl 2 km preload + disease/symptom consistency

## Demo state after seeding

Run:

```powershell
python -m scripts.seed_leaf_curl_2km_demo
```

The script now loads exactly **3** symptom-only cotton reports near **37.4220, -122.0840**:

1. `LC2KM-COT-CURL-001` -> `NO_ALERT`
2. `LC2KM-COT-CURL-002` -> `MONITORING`
3. `LC2KM-COT-CURL-003` -> `MONITORING`

All three use canonical symptom code `LEAF_CURLING`. Their timestamps are deliberately placed several minutes in the past so a new live Flutter report is evaluated against all three.

## What happens when the next live report arrives

A new cotton report near the same location can join the cluster when its structured evidence is related. For example, a strong image prediction of `curl_virus` can connect to the older `LEAF_CURLING` symptom-only reports through the deterministic disease/symptom compatibility profile.

Expected flow:

```text
3 preloaded LEAF_CURLING reports
        ↓
MONITORING
        ↓
1 live compatible cotton report
        ↓
4 related reports
        ↓
AMBER appears in Outbreak Alerts
        ↓
Expert confirms AMBER -> RED
        ↓
Punjabi notification sent to eligible same-crop devices
within 2 km of the final calculated alert center
```

The system intentionally does **not** send farmer notifications at MONITORING or AMBER. RED remains expert-gated.

## Disease ↔ symptom consistency review rule

For multimodal reports, the backend now checks the reliable image disease result against canonical farmer symptom codes.

- `CONSISTENT`: no extra review is required from this check.
- `INCONSISTENT`: `requires_expert_review = true`, report is stored, but held out of automatic outbreak clustering until an expert marks it `VALID`.
- `NOT_APPLICABLE`: there is not enough reliable disease + canonical symptom evidence to perform the comparison; existing safety rules still apply.

Example:

```text
cotton + curl_virus + LEAF_CURLING       -> CONSISTENT
cotton + curl_virus + LEAF_DISCOLORATION -> CONSISTENT
cotton + curl_virus + BOLL_ROTTING        -> INCONSISTENT -> REVIEW
```

The compatibility decision is deterministic. Qwen does not decide this relationship.

## Cross-modal outbreak correlation

The outbreak engine now relates reports using any of these deterministic links:

1. same disease, or
2. overlapping canonical symptom code, or
3. image disease from one report is compatible with the canonical symptoms in the other report.

Crop, 5 km outbreak radius and 7 day time window must still match.

## Notification geometry

- Outbreak linking radius: **5 km**
- Farmer notification radius after RED: **2 km**
- Notification circle area: **12.566 km²**

The final notification eligibility is calculated from the **final alert center**, not from the original anchor point.
