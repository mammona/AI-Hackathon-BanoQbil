from datetime import datetime, timezone

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database import Base
from app.models.database_models import Report
from app.models.schemas import Assessment, CropName, DiseasePrediction, ImageAssessment, ImageStatus, SymptomCode
from app.services.disease_symptom_consistency import ConsistencyStatus, DiseaseSymptomConsistencyService
from app.services.outbreak_service import OutbreakService
from app.services.report_service import ReportService


def session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine, expire_on_commit=False)()


def test_cotton_curl_virus_and_leaf_curling_are_consistent():
    result = DiseaseSymptomConsistencyService().assess(
        crop="cotton",
        disease="curl_virus",
        symptom_codes=["LEAF_CURLING"],
        image_evidence_available=True,
    )
    assert result.status == ConsistencyStatus.CONSISTENT
    assert "LEAF_CURLING" in result.matched_symptom_codes


def test_cotton_curl_virus_and_unrelated_boll_rot_requires_review():
    service = ReportService()
    evidence = service._evidence(
        crop=CropName.cotton,
        disease=DiseasePrediction(
            disease="curl_virus",
            confidence=0.99,
            confidence_level="high",
            verified_by_image=True,
            low_confidence=False,
            healthy_class_supported=True,
        ),
        assessment=Assessment(
            symptoms=["boll is rotting"],
            symptom_codes=[SymptomCode.BOLL_ROTTING],
        ),
        image_assessment=ImageAssessment(
            status=ImageStatus.validated,
            detected_crop="cotton",
            matches_selected_crop=True,
            confidence=1.0,
        ),
        has_farmer_input=True,
        qwen_error=False,
        mapping_error=False,
    )
    assert evidence.disease_symptom_consistency == "INCONSISTENT"
    assert evidence.needs_expert_review is True


def _report(report_id: str, *, disease=None, image=False, codes=None) -> Report:
    codes = list(codes or [])
    return Report(
        report_id=report_id,
        selected_crop="cotton",
        language="punjabi",
        image_status="validated" if image else "not_submitted",
        image_submitted=image,
        disease=disease,
        disease_confidence=0.99 if disease else None,
        disease_confidence_level="high" if disease else None,
        healthy_class_supported=True if disease else None,
        question_1_raw="test",
        question_2_raw="",
        question_3_raw="",
        question_4_raw="",
        symptoms=["test"] if codes else [],
        symptom_codes=codes,
        symptom_mapping=[],
        evidence_mode="MULTIMODAL" if image and codes else "SYMPTOM_ONLY",
        evidence_strength="STRONG" if image and codes else "MEDIUM",
        image_evidence_available=bool(image and disease),
        symptom_evidence_available=bool(codes),
        canonical_symptom_evidence_available=bool(codes),
        usable_for_outbreak=True,
        summary="test",
        recommended_next_step="test",
        requires_expert_review=False,
        expert_review_status="NOT_REQUIRED",
        latitude=37.4220,
        longitude=-122.0840,
        location_available=True,
        processing_status="completed",
        reported_at=datetime.now(timezone.utc),
    )


def test_curl_virus_image_report_links_to_leaf_curling_symptom_only_report():
    db = session()
    outbreak = OutbreakService()

    symptom_only = _report("SYMPTOM-1", codes=["LEAF_CURLING"])
    live_image = _report("IMAGE-1", disease="curl_virus", image=True, codes=["LEAF_DISCOLORATION"])
    db.add_all([symptom_only, live_image])
    db.commit()

    # No exact symptom overlap is required here: curl_virus is deterministically
    # compatible with the old report's LEAF_CURLING code.
    assert outbreak._evidence_related(symptom_only, live_image) is True
