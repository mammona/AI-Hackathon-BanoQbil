# V17 image model integration update

The disease image path now uses the project's existing trained `.pt` files directly:

- `models/disease/cotton_disease_classifier.pt`
- `models/disease/rice_disease_classifier.pt`
- `models/disease/class_mappings.json`

Class labels are loaded by numeric index from the mapping JSON. This prevents label-order mismatch between training and inference.

The current rice mapping has no healthy class. Keep rice available, but treat it as supporting evidence only until a healthy class is added and the model is retrained. Cotton already includes `healthy` and is the recommended fully trusted image demo path.

The API disease result now also includes `healthy_class_supported`. Cotton returns `true`; with the current mapping rice returns `false`. Reports from a crop model without a healthy class are automatically marked as requiring expert review, while the predicted class is still preserved for later multimodal fusion.
