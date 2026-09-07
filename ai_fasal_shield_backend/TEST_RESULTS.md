# Test Results

Updated V17 reviewer-instruction + Punjabi notification + device-registration fix:

```text
pytest -q
81 passed
```

Covered in this build:
- report `device_id` automatically creates/updates `registered_devices`
- existing device push token and notification preference are preserved
- selected crop is added to the reporting device's crop interests
- report GPS becomes the device's latest location when available
- six bundled demo devices seed idempotently from `data/demo_devices.json`
- report VALID / INVALID / FOLLOW_UP workflow
- VALID review can re-evaluate and create AMBER
- AMBER -> expert confirmation -> RED
- private verification note remains internal
- separate Punjabi/Shahmukhi farmer instruction is appended to farmer notification
- notification text remains dynamic by crop, disease/problem, symptoms, and distance
- re-confirming a RED alert with changed farmer instructions updates the existing notification instead of duplicating it
- updated notification is marked unread again so the farmer can see the new guidance
- eligible-device selection by crop + radius
- existing V17 outbreak, optional-image, reranker, admin, and notification tests

The real disease `.pt` weights and Ollama/Hugging Face model runtime still need to be exercised on the user's machine for live inference tests.
