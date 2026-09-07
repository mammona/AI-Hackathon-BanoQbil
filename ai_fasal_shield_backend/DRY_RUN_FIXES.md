# V17 Dry-Run Fixes

Version: `0.12.2-v17-dryrun-fixes`

A full dry run found and fixed two issues:

1. **Successful no-image retries were not truly idempotent.** `completed_without_image` reports re-ran Qwen and symptom RAG on every retry because only the exact status `completed` used the early-return path. All successful terminal report states now return the stored result without re-running AI. Device bootstrap is performed before that early return so older V17 reports can repair a missing `registered_devices` row.
2. **`scripts/check_demo_notifications.py` contained literal `\n` characters in Python source**, causing a `SyntaxError`. The helper script is corrected.
3. **Dashboard `completed_reports` under-counted successful no-image reports.** It now counts all successful terminal processing states while `failed_reports` remains separate.

The live E2E script now also sends a persistent `device_id`, supplies `farmer_instruction` at AMBER confirmation, verifies the reporting device exists, and confirms a Punjabi notification is created after RED.
