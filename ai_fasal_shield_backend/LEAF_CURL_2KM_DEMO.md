# Leaf Curl 2 km Demo

Current demo mode is a **3-report preload**, not a fully auto-confirmed four-report demo.

Run:

```powershell
python -m scripts.seed_leaf_curl_2km_demo
```

It leaves the system at `MONITORING` with three nearby cotton `LEAF_CURLING` reports. Submit one additional compatible live cotton report from Flutter near `37.4220, -122.0840` to create `AMBER`.

Then open the Outbreak Alerts panel and use **Confirm -> RED & Notify Farmers**. The RED notification is delivered only to eligible same-crop registered devices inside the configured 2 km notification radius from the calculated final alert center.

See `LEAF_CURL_2KM_PRELOAD_AND_CONSISTENCY.md` for the exact disease/symptom correlation rules and full flow.
