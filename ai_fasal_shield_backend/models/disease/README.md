# Disease image models (V17 image-path integration)

Copy your trained files into this folder with these exact names:

```text
models/disease/
├── cotton_disease_classifier.pt
├── rice_disease_classifier.pt
└── class_mappings.json
```

The backend now reads class order from `class_mappings.json`; separate `labels.txt` files are no longer required.

Current class mapping:

- Cotton: `bacterial_blight`, `curl_virus`, `fusarium_wilt`, `healthy`
- Rice: `bacterial_blight`, `blast`, `brown_spot`

## Important rice limitation

The current rice classifier has **no healthy class**. It is therefore a closed-set 3-disease classifier: even a healthy rice image must be assigned to one of those three classes. For the prototype, do not treat a rice image-only prediction as sufficient evidence for an automatic outbreak alert. Prefer either:

1. cotton for the fully trusted image-only demo path, or
2. rice only when the image result is supported by farmer symptom evidence / expert review.

Add a genuine `healthy` class and retrain the rice model before treating rice image predictions as complete healthy-vs-disease diagnosis.

## Check setup

From the project root:

```powershell
python -m scripts.check_disease_models
```

The script checks model-file presence, mapping order, and whether each crop has a healthy class.
