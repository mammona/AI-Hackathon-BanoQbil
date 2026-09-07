from app.constants.symptoms import SymptomCode
from app.models.schemas import Assessment, DiseasePrediction, ImageAssessment, ImageStatus
from app.services.report_service import ReportService


def disease(name="curl_virus", confidence=0.95, low=False, healthy_supported=True):
    return DiseasePrediction(
        disease=name,
        confidence=confidence,
        confidence_level="high" if not low else "low",
        low_confidence=low,
        healthy_class_supported=healthy_supported,
    )


def test_multimodal_evidence_is_strong_and_usable():
    service = ReportService()
    result = service._evidence(
        disease=disease(),
        assessment=Assessment(symptom_codes=[SymptomCode.LEAF_CURLING]),
        image_assessment=ImageAssessment(status=ImageStatus.validated),
        has_farmer_input=True,
        qwen_error=False,
        mapping_error=False,
    )
    assert result.evidence_mode.value == "MULTIMODAL"
    assert result.evidence_strength.value == "STRONG"
    assert result.usable_for_outbreak is True


def test_image_only_evidence_is_usable():
    service = ReportService()
    result = service._evidence(
        disease=disease(),
        assessment=Assessment(),
        image_assessment=ImageAssessment(status=ImageStatus.validated),
        has_farmer_input=False,
        qwen_error=False,
        mapping_error=False,
    )
    assert result.evidence_mode.value == "IMAGE_ONLY"
    assert result.usable_for_outbreak is True


def test_symptom_only_evidence_is_usable():
    service = ReportService()
    result = service._evidence(
        disease=None,
        assessment=Assessment(symptom_codes=[SymptomCode.LEAF_CURLING]),
        image_assessment=ImageAssessment(status=ImageStatus.not_submitted),
        has_farmer_input=True,
        qwen_error=False,
        mapping_error=False,
    )
    assert result.evidence_mode.value == "SYMPTOM_ONLY"
    assert result.usable_for_outbreak is True


def test_context_only_for_non_symptom_answer():
    service = ReportService()
    result = service._evidence(
        disease=None,
        assessment=Assessment(problem_duration="3 days"),
        image_assessment=ImageAssessment(status=ImageStatus.not_submitted),
        has_farmer_input=True,
        qwen_error=False,
        mapping_error=False,
    )
    assert result.evidence_mode.value == "CONTEXT_ONLY"
    assert result.usable_for_outbreak is False


def test_others_map_only_is_stored_but_not_usable():
    service = ReportService()
    result = service._evidence(
        disease=None,
        assessment=Assessment(
            symptoms=["unknown sticky material"],
            symptom_codes=[SymptomCode.OTHERS_MAP],
        ),
        image_assessment=ImageAssessment(status=ImageStatus.not_submitted),
        has_farmer_input=True,
        qwen_error=False,
        mapping_error=False,
    )
    assert result.evidence_mode.value == "CONTEXT_ONLY"
    assert result.usable_for_outbreak is False
    assert result.needs_expert_review is True


def test_healthy_image_is_not_outbreak_evidence():
    service = ReportService()
    result = service._evidence(
        disease=disease(name="healthy"),
        assessment=Assessment(),
        image_assessment=ImageAssessment(status=ImageStatus.validated),
        has_farmer_input=False,
        qwen_error=False,
        mapping_error=False,
    )
    assert result.image_evidence_available is False
    assert result.evidence_mode.value == "CONTEXT_ONLY"
    assert result.usable_for_outbreak is False
