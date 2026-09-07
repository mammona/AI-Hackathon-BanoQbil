from datetime import datetime, timedelta, timezone

from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker

from app.database import Base
from app.models.database_models import Notification, Report
from app.models.schemas import AlertLevel, AlertVerificationRequest, ReportReviewRequest
from app.api.alerts import verify_alert
from app.repositories.device_repository import DeviceRepository
from app.services.outbreak_service import OutbreakService
from app.services.report_review_service import ReportReviewService


def session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine, expire_on_commit=False)()


def make_report(report_id, when, *, pending=False, image=False):
    return Report(
        report_id=report_id, selected_crop="cotton", language="punjabi",
        image_status="validated" if image else "not_submitted", image_submitted=image,
        disease="curl_virus" if image else None, disease_confidence=.95 if image else None,
        disease_confidence_level="high" if image else None, healthy_class_supported=True,
        question_1_raw="پتے مڑ رہے نیں", question_2_raw="", question_3_raw="", question_4_raw="",
        symptoms=["پتے مڑ رہے نیں"], symptom_codes=["LEAF_CURLING"], symptom_mapping=[],
        evidence_mode="MULTIMODAL" if image else "SYMPTOM_ONLY", evidence_strength="STRONG" if image else "MEDIUM",
        image_evidence_available=image, symptom_evidence_available=True,
        canonical_symptom_evidence_available=True, usable_for_outbreak=not pending,
        summary="test", recommended_next_step="test", requires_expert_review=pending,
        expert_review_status="PENDING" if pending else "NOT_REQUIRED",
        latitude=31.5204, longitude=74.3587, location_available=True,
        processing_status="completed", reported_at=when,
    )


def save(db, row):
    db.add(row); db.commit(); db.refresh(row); return row


def test_mark_valid_rechecks_cluster_and_can_create_amber():
    db=session(); outbreak=OutbreakService(); review=ReportReviewService(); now=datetime.now(timezone.utc)
    r1=save(db, make_report("RV1", now, image=True)); outbreak.assessment_for_stored_report(db,r1)
    r2=save(db, make_report("RV2", now+timedelta(minutes=1))); a2=outbreak.assessment_for_stored_report(db,r2)
    assert a2.alert_level == AlertLevel.MONITORING
    r3=save(db, make_report("RV3", now+timedelta(minutes=2), pending=True))
    result=review.review(db, report_id=r3.report_id, request=ReportReviewRequest(decision="valid", expert_name="Officer", note="Looks valid"))
    assert result.expert_review_status.value == "VALID"
    assert result.usable_for_outbreak is True
    assert result.outbreak_assessment.alert_level == AlertLevel.AMBER
    assert result.outbreak_assessment.alert_id


def test_invalid_report_is_stored_but_excluded():
    db=session(); review=ReportReviewService(); now=datetime.now(timezone.utc)
    row=save(db, make_report("INV1", now, pending=True))
    result=review.review(db, report_id=row.report_id, request=ReportReviewRequest(decision="invalid", expert_name="Officer", note="Wrong evidence"))
    db.refresh(row)
    assert row.expert_review_status == "INVALID"
    assert row.usable_for_outbreak is False
    assert result.outbreak_assessment.evaluated is False


def test_follow_up_is_held_out_of_clustering():
    db=session(); review=ReportReviewService(); now=datetime.now(timezone.utc)
    row=save(db, make_report("FU1", now, pending=True))
    result=review.review(db, report_id=row.report_id, request=ReportReviewRequest(decision="follow_up", expert_name="Officer", note="Need field photo"))
    assert result.expert_review_status.value == "FOLLOW_UP"
    assert result.requires_expert_review is True
    assert result.usable_for_outbreak is False


def test_report_review_note_is_not_farmer_notification_text():
    db=session(); outbreak=OutbreakService(); review=ReportReviewService(); now=datetime.now(timezone.utc)
    r1=save(db, make_report("PN1",now,image=True)); outbreak.assessment_for_stored_report(db,r1)
    r2=save(db, make_report("PN2",now+timedelta(minutes=1))); outbreak.assessment_for_stored_report(db,r2)
    r3=save(db, make_report("PN3",now+timedelta(minutes=2),pending=True))
    private_note="Internal report note should never reach farmer"
    result=review.review(db, report_id=r3.report_id, request=ReportReviewRequest(decision="valid",expert_name="Officer",note=private_note))
    assert result.outbreak_assessment.alert_level == AlertLevel.AMBER
    DeviceRepository().upsert(db,device_id="FARMER-1",crops=["cotton"],preferred_language="punjabi",latitude=31.521,longitude=74.359,push_token=None,notifications_enabled=True)
    verified=verify_alert(result.outbreak_assessment.alert_id,AlertVerificationRequest(decision="confirmed",expert_name="Officer",note="Internal alert verification note"),db)
    assert verified.alert_level == AlertLevel.RED
    notification=db.scalar(select(Notification))
    assert notification is not None
    assert notification.language == "punjabi"
    assert private_note not in notification.message
    assert "Internal alert verification note" not in notification.message
    assert "کپاس" in notification.message
