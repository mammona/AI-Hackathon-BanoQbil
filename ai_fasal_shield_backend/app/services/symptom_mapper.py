"""Backward-compatible entry points for semantic symptom mapping.

The old alias mapper has been removed. These helpers now delegate to the
RAG-style semantic retriever in `symptom_rag_service.py`.
"""

from app.constants.symptoms import SymptomCode
from app.services.symptom_rag_service import SymptomRAGService


_service: SymptomRAGService | None = None


def _get_service() -> SymptomRAGService:
    global _service
    if _service is None:
        _service = SymptomRAGService()
    return _service


def map_symptom_code(
    symptom: str,
    *,
    crop: str = "cotton",
    affected_part: str | None = None,
    language: str = "english",
) -> SymptomCode:
    code, _, _ = _get_service().map_one(
        symptom,
        crop=crop,
        affected_part=affected_part,
        language=language,
    )
    return code


def map_symptom_codes(
    symptoms: list[str],
    *,
    crop: str = "cotton",
    affected_part: str | None = None,
    language: str = "english",
) -> list[SymptomCode]:
    return [
        map_symptom_code(
            symptom,
            crop=crop,
            affected_part=affected_part,
            language=language,
        )
        for symptom in symptoms
    ]
