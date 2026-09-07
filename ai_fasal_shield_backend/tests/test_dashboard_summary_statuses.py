from datetime import datetime, timezone

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database import Base
from app.models.database_models import Report
from app.repositories.report_repository import ReportRepository


def session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine, expire_on_commit=False)()


def report(report_id: str, status: str):
    return Report(
        report_id=report_id, selected_crop="cotton", language="punjabi",
        image_status="not_submitted", image_submitted=False,
        question_1_raw="x", question_2_raw="", question_3_raw="", question_4_raw="",
        symptoms=[], symptom_codes=[], symptom_mapping=[],
        evidence_mode="CONTEXT_ONLY", evidence_strength="LOW",
        image_evidence_available=False, symptom_evidence_available=False,
        canonical_symptom_evidence_available=False, usable_for_outbreak=False,
        summary="test", recommended_next_step="test", requires_expert_review=False,
        expert_review_status="NOT_REQUIRED", latitude=0.0, longitude=0.0,
        location_available=False, processing_status=status, reported_at=datetime.now(timezone.utc),
    )


def test_completed_reports_includes_successful_no_image_and_unverified_states():
    db=session()
    db.add_all([
        report("D1", "completed"),
        report("D2", "completed_without_image"),
        report("D3", "completed_with_unverified_image"),
        report("D4", "disease_low_confidence"),
        report("D5", "processing_failed"),
    ])
    db.commit()
    summary=ReportRepository().dashboard_summary(db)
    assert summary["total_reports"] == 5
    assert summary["completed_reports"] == 4
    assert summary["failed_reports"] == 1
