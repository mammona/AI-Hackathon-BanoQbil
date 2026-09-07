# V17 Device Registration Fix

This patch fixes a backend gap that caused:

```text
GET /api/v1/devices/<phone-uuid>/notifications -> 404 Device not found
```

even after the phone had submitted reports carrying the same `device_id`.

## Root cause

Older V17 `ReportService` only refreshed GPS for a device if a row already existed in `registered_devices`. It stored `reports.device_id` but never created the corresponding device row.

## Fix

1. Any accepted report with `device_id` now idempotently creates or updates that device in `registered_devices`.
2. The report's selected crop is added to the device crop interests.
3. Report language and GPS update the device when available.
4. Existing push token and notification-enabled preference are preserved.
5. The six bundled demo devices are now loaded from `data/demo_devices.json` and automatically seeded at backend startup when `AUTO_SEED_DEMO_DEVICES=true`.
6. Manual seeding remains available with `python -m scripts.seed_demo_devices`.

After restart, verify:

```text
GET /api/v1/devices
```

The six `DEMO-*` rows should exist. After the Flutter phone submits one report containing its UUID, that UUID should also appear in the same endpoint and its notification endpoint should return `[]` rather than 404 until an eligible RED alert exists.
