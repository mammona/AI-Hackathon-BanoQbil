from dataclasses import dataclass
import json
from pathlib import Path

import torch
from PIL import Image
from torch import nn
from torchvision import models, transforms

from app.config import get_settings
from app.models.schemas import DiseasePrediction


@dataclass
class LoadedDiseaseModel:
    model: torch.nn.Module
    labels: list[str]
    architecture: str


class DiseaseModelUnavailable(RuntimeError):
    pass


class DiseaseModelService:
    """Load the project's cotton/rice EfficientNet-B0 checkpoints.

    Prototype routing rule:
      selected_crop=cotton -> cotton_disease_classifier.pt
      selected_crop=rice   -> rice_disease_classifier.pt

    There is no SigLIP/crop-recognition routing in this version.

    Expected files:
      models/disease/cotton_disease_classifier.pt
      models/disease/rice_disease_classifier.pt
      models/disease/class_mappings.json

    The loader supports the two most common EfficientNet-B0 state-dict layouts
    used by this project type: timm and torchvision.
    """

    def __init__(self) -> None:
        self.settings = get_settings()
        self._models: dict[str, LoadedDiseaseModel] = {}
        self.transform = transforms.Compose([
            transforms.Resize((224, 224)),
            transforms.ToTensor(),
            transforms.Normalize(
                mean=[0.485, 0.456, 0.406],
                std=[0.229, 0.224, 0.225],
            ),
        ])

    def _model_path(self, crop: str) -> Path:
        if crop == "cotton":
            return self.settings.cotton_model_path
        if crop == "rice":
            return self.settings.rice_model_path
        raise DiseaseModelUnavailable(f"Unsupported crop: {crop}")

    @staticmethod
    def _mapping_key(crop: str) -> str:
        if crop not in {"cotton", "rice"}:
            raise DiseaseModelUnavailable(f"Unsupported crop: {crop}")
        return f"{crop}_disease"

    def _labels(self, crop: str) -> list[str]:
        mapping_path = self.settings.disease_class_mappings_path
        if not mapping_path.exists():
            raise DiseaseModelUnavailable(
                f"Disease class mapping file not found: {mapping_path}"
            )

        try:
            payload = json.loads(mapping_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise DiseaseModelUnavailable(
                f"Could not read disease class mappings: {mapping_path}: {exc}"
            ) from exc

        key = self._mapping_key(crop)
        raw = payload.get(key)
        if not isinstance(raw, dict) or not raw:
            raise DiseaseModelUnavailable(
                f"Missing or empty '{key}' mapping in {mapping_path}"
            )

        try:
            indexed = sorted((int(index), str(label)) for index, label in raw.items())
        except (TypeError, ValueError) as exc:
            raise DiseaseModelUnavailable(
                f"'{key}' mapping must use integer-like class indexes"
            ) from exc

        expected_indexes = list(range(len(indexed)))
        actual_indexes = [index for index, _ in indexed]
        if actual_indexes != expected_indexes:
            raise DiseaseModelUnavailable(
                f"'{key}' indexes must be contiguous from 0; got {actual_indexes}"
            )

        return [label for _, label in indexed]

    @staticmethod
    def _clean_state_dict(state: dict) -> dict:
        cleaned = {}
        for key, value in state.items():
            key = key.removeprefix("module.").removeprefix("model.")
            cleaned[key] = value
        return cleaned

    @staticmethod
    def _extract_state_dict(checkpoint) -> dict:
        if not isinstance(checkpoint, dict):
            raise DiseaseModelUnavailable(
                "Expected a PyTorch state_dict/checkpoint dictionary."
            )

        for key in ("state_dict", "model_state_dict"):
            nested = checkpoint.get(key)
            if isinstance(nested, dict):
                return nested

        # Plain torch.save(model.state_dict(), path) format.
        if checkpoint and all(isinstance(k, str) for k in checkpoint):
            return checkpoint

        raise DiseaseModelUnavailable("No model state_dict found in checkpoint")

    @staticmethod
    def _timm_model(num_classes: int) -> torch.nn.Module:
        try:
            import timm
        except ImportError as exc:
            raise DiseaseModelUnavailable(
                "timm is required to load a timm EfficientNet checkpoint. Run: pip install -r requirements.txt"
            ) from exc
        return timm.create_model(
            "efficientnet_b0",
            pretrained=False,
            num_classes=num_classes,
        )

    @staticmethod
    def _torchvision_model(num_classes: int) -> torch.nn.Module:
        model = models.efficientnet_b0(weights=None)
        in_features = model.classifier[1].in_features
        model.classifier[1] = nn.Linear(in_features, num_classes)
        return model

    def _load_checkpoint(self, model_path: Path):
        try:
            return torch.load(model_path, map_location="cpu", weights_only=True)
        except TypeError:
            return torch.load(model_path, map_location="cpu")
        except Exception as first_exc:
            # Some older checkpoints cannot be read with weights_only=True.
            # These files are local project artifacts, so allow the standard
            # loader as a compatibility fallback.
            try:
                return torch.load(model_path, map_location="cpu", weights_only=False)
            except Exception as second_exc:
                raise DiseaseModelUnavailable(
                    f"Could not load disease checkpoint {model_path}: "
                    f"{first_exc}; fallback also failed: {second_exc}"
                ) from second_exc

    def _load(self, crop: str) -> LoadedDiseaseModel:
        if crop in self._models:
            return self._models[crop]

        model_path = self._model_path(crop)
        labels = self._labels(crop)

        if not model_path.exists():
            raise DiseaseModelUnavailable(f"Disease model file not found: {model_path}")

        checkpoint = self._load_checkpoint(model_path)
        state_dict = self._clean_state_dict(self._extract_state_dict(checkpoint))

        errors: list[str] = []
        candidates = [
            ("timm_efficientnet_b0", self._timm_model),
            ("torchvision_efficientnet_b0", self._torchvision_model),
        ]

        for architecture, factory in candidates:
            model = factory(len(labels))
            try:
                model.load_state_dict(state_dict, strict=True)
            except RuntimeError as exc:
                errors.append(f"{architecture}: {exc}")
                continue

            model.eval()
            loaded = LoadedDiseaseModel(
                model=model,
                labels=labels,
                architecture=architecture,
            )
            self._models[crop] = loaded
            return loaded

        raise DiseaseModelUnavailable(
            f"Checkpoint does not match supported EfficientNet-B0 layouts for {crop}. "
            + " | ".join(errors)
        )

    def labels_for_crop(self, crop: str) -> list[str]:
        return self._labels(crop)

    def has_healthy_class(self, crop: str) -> bool:
        return any(label.strip().lower() == "healthy" for label in self._labels(crop))

    def model_info(self, crop: str) -> dict:
        loaded = self._load(crop)
        return {
            "crop": crop,
            "path": str(self._model_path(crop)),
            "labels": loaded.labels,
            "architecture": loaded.architecture,
            "healthy_class_supported": any(
                label.strip().lower() == "healthy" for label in loaded.labels
            ),
        }

    @torch.inference_mode()
    def predict(self, crop: str, image: Image.Image) -> DiseasePrediction:
        loaded = self._load(crop)
        tensor = self.transform(image).unsqueeze(0)
        logits = loaded.model(tensor)

        if logits.ndim != 2 or logits.shape[0] != 1:
            raise DiseaseModelUnavailable(
                f"Unexpected disease-model output shape: {tuple(logits.shape)}"
            )
        if logits.shape[1] != len(loaded.labels):
            raise DiseaseModelUnavailable(
                f"Model returned {logits.shape[1]} classes but mapping contains "
                f"{len(loaded.labels)} labels for {crop}"
            )

        probs = torch.softmax(logits, dim=1)[0]
        values, indices = torch.topk(probs, k=min(2, len(loaded.labels)))
        top_conf = float(values[0].item())
        second_conf = float(values[1].item()) if len(values) > 1 else 0.0
        margin = top_conf - second_conf
        disease = loaded.labels[int(indices[0].item())]

        low = (
            top_conf < self.settings.disease_threshold
            or margin < self.settings.disease_min_margin
        )

        if top_conf >= 0.85 and not low:
            level = "high"
        elif top_conf >= self.settings.disease_threshold and not low:
            level = "medium"
        else:
            level = "low"

        return DiseasePrediction(
            disease=disease,
            confidence=top_conf,
            confidence_level=level,
            verified_by_image=True,
            low_confidence=low,
            healthy_class_supported=any(
                label.strip().lower() == "healthy" for label in loaded.labels
            ),
        )
