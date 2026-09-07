# AI Fasal Shield V17 - Prototype Image Path

## Design frozen for the prototype

The mobile/API field `selected_crop` is the routing authority. There is no SigLIP or crop-recognition step in this version.

- `selected_crop=cotton` -> `cotton_disease_classifier.pt`
- `selected_crop=rice` -> `rice_disease_classifier.pt`

The backend only performs lightweight technical image validation (decodable image, size/basic quality checks) before running the selected disease model.

## Put your trained model files here

From the backend project root:

```text
ai_fasal_shield_backend_qwen3_reranker_v17_api_crop_image/
└── models/
    └── disease/
        ├── cotton_disease_classifier.pt
        ├── rice_disease_classifier.pt
        └── class_mappings.json
```

Only those three files are required for the current PyTorch disease inference path. Your `cotton.onnx`, TensorFlow folder, evaluation JSON, and training metadata can stay elsewhere; this backend does not use them.

Expected mapping:

```json
{
  "rice_disease": {
    "0": "bacterial_blight",
    "1": "blast",
    "2": "brown_spot"
  },
  "cotton_disease": {
    "0": "bacterial_blight",
    "1": "curl_virus",
    "2": "fusarium_wilt",
    "3": "healthy"
  }
}
```

## Verify configuration

```powershell
conda activate fasalshield
cd C:\Users\MammonaQudsia\Documents\ai_fasal_shield_backend_qwen3_reranker_v17_api_crop_image
python -m scripts.check_disease_models
```

## Start

```powershell
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

## Report input rule

The image is optional. Q1-Q4 are individually optional. A request is accepted when it has at least one of:

- an uploaded image, or
- any one of Q1/Q2/Q3/Q4.

A request with neither an image nor any answer is rejected with HTTP 422.
