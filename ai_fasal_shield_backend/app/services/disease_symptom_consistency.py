from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class ConsistencyStatus(str, Enum):
    CONSISTENT = "CONSISTENT"
    INCONSISTENT = "INCONSISTENT"
    NOT_APPLICABLE = "NOT_APPLICABLE"


@dataclass(frozen=True)
class ConsistencyResult:
    status: ConsistencyStatus
    reason: str
    matched_symptom_codes: tuple[str, ...] = ()


# Conservative disease -> symptom support profiles used for two purposes:
# 1) multimodal report safety: image disease vs farmer symptom consistency
# 2) outbreak linking across image-supported and symptom-only reports
#
# These rules are intentionally deterministic and auditable. They do not ask an
# LLM to decide whether a disease and symptom are compatible.
DISEASE_SYMPTOM_PROFILES: dict[tuple[str, str], frozenset[str]] = {
    # Cotton
    ("cotton", "bacterial_blight"): frozenset({
        "LEAF_WATER_SOAKED_LESIONS",
        "LEAF_BROWN_SPOTS",
        "LEAF_BLACK_SPOTS",
        "LEAF_LESIONS",
        "LEAF_STREAKS",
        "LEAF_YELLOWING",
        "BOLL_SPOTS",
        "BOLL_ROTTING",
        "STEM_LESIONS",
    }),
    ("cotton", "curl_virus"): frozenset({
        "LEAF_CURLING",
        "LEAF_YELLOWING",
        "LEAF_DISCOLORATION",
        "STUNTED_GROWTH",
        "POOR_GROWTH",
    }),
    ("cotton", "fusarium_wilt"): frozenset({
        "LEAF_WILTING",
        "PLANT_WILTING",
        "LEAF_YELLOWING",
        "PLANT_YELLOWING",
        "STEM_DARKENING",
        "ROOT_DARKENING",
        "ROOT_ROTTING",
        "PLANT_DRYING",
        "PLANT_DEATH",
    }),
    # Rice
    ("rice", "bacterial_blight"): frozenset({
        "LEAF_WATER_SOAKED_LESIONS",
        "LEAF_STREAKS",
        "LEAF_YELLOWING",
        "LEAF_TIP_DRYING",
        "LEAF_EDGE_DRYING",
        "LEAF_DRYING",
    }),
    ("rice", "blast"): frozenset({
        "LEAF_SPINDLE_LESIONS",
        "LEAF_LESIONS",
        "LEAF_BROWN_SPOTS",
        "STEM_LESIONS",
        "PANICLE_DISCOLORATION",
        "PANICLE_DRYING",
        "GRAIN_DAMAGE",
    }),
    ("rice", "brown_spot"): frozenset({
        "LEAF_BROWN_SPOTS",
        "LEAF_LESIONS",
        "LEAF_YELLOWING",
        "GRAIN_DISCOLORATION",
        "GRAIN_DAMAGE",
    }),
}


class DiseaseSymptomConsistencyService:
    @staticmethod
    def _canonical_codes(symptom_codes: list[str] | tuple[str, ...] | set[str]) -> set[str]:
        return {
            str(code)
            for code in symptom_codes
            if str(code) and str(code) != "OTHERS_MAP"
        }

    def supported_symptoms(self, crop: str, disease: str | None) -> frozenset[str]:
        if not disease:
            return frozenset()
        return DISEASE_SYMPTOM_PROFILES.get(
            (crop.strip().lower(), disease.strip().lower()),
            frozenset(),
        )

    def disease_supports_symptoms(
        self,
        *,
        crop: str,
        disease: str | None,
        symptom_codes: set[str] | list[str] | tuple[str, ...],
    ) -> bool:
        codes = self._canonical_codes(symptom_codes)
        if not codes or not disease or disease.strip().lower() == "healthy":
            return False
        supported = self.supported_symptoms(crop, disease)
        return bool(codes & supported)

    def assess(
        self,
        *,
        crop: str,
        disease: str | None,
        symptom_codes: list[str] | tuple[str, ...] | set[str],
        image_evidence_available: bool,
    ) -> ConsistencyResult:
        codes = self._canonical_codes(symptom_codes)
        disease_name = (disease or "").strip().lower()

        # Consistency is meaningful only when both reliable image disease evidence
        # and canonical symptom evidence are present.
        if not image_evidence_available or not disease_name or disease_name == "healthy" or not codes:
            return ConsistencyResult(
                ConsistencyStatus.NOT_APPLICABLE,
                "Disease-symptom consistency requires both reliable disease image evidence and canonical symptom evidence.",
            )

        supported = self.supported_symptoms(crop, disease_name)
        if not supported:
            return ConsistencyResult(
                ConsistencyStatus.INCONSISTENT,
                f"No approved symptom compatibility profile is available for {crop}/{disease_name}; expert review is required.",
            )

        matched = tuple(sorted(codes & supported))
        if matched:
            return ConsistencyResult(
                ConsistencyStatus.CONSISTENT,
                f"Image disease {disease_name} is compatible with farmer symptom evidence: {', '.join(matched)}.",
                matched,
            )

        return ConsistencyResult(
            ConsistencyStatus.INCONSISTENT,
            f"Image disease {disease_name} is not supported by the reported canonical symptoms: {', '.join(sorted(codes))}.",
        )
