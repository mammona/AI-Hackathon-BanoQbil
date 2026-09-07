from datetime import datetime, timedelta, timezone

from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker

from app.api.alerts import verify_alert
from app.database import Base
from app.models.database_models import Notification, Report
from app.models.schemas import AlertLevel, AlertVerificationRequest
from app.repositories.device_repository import DeviceRepository
from app.services.outbreak_service import OutbreakService


def session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine, expire_on_commit=False)()


def make_report(report_id, when, lat, lon, *, disease=None, codes=None, image=False):
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
        symptoms=["test"],
        symptom_codes=codes,
        symptom_mapping=[],
        evidence_mode="MULTIMODAL" if image else "SYMPTOM_ONLY",
        evidence_strength="STRONG" if image else "MEDIUM",
        image_evidence_available=bool(image and disease),
        symptom_evidence_available=True,
        canonical_symptom_evidence_available=True,
        usable_for_outbreak=True,
        summary="test",
        recommended_next_step="test",
        requires_expert_review=False,
        expert_review_status="NOT_REQUIRED",
        latitude=lat,
        longitude=lon,
        location_available=True,
        processing_status="completed",
        reported_at=when,
    )


def test_three_leaf_curl_preloads_plus_live_curl_virus_report_create_amber_then_red_notification():
    db = session()
    outbreak = OutbreakService()
    now = datetime.now(timezone.utc)

    preload = [
        make_report("PRE1", now - timedelta(minutes=10), 37.42335, -122.0840, codes=["LEAF_CURLING"]),
        make_report("PRE2", now - timedelta(minutes=9), 37.42351, -122.07689, codes=["LEAF_CURLING"]),
        make_report("PRE3", now - timedelta(minutes=8), 37.41244, -122.08078, codes=["LEAF_CURLING"]),
    ]
    for row in preload:
        db.add(row); db.commit(); db.refresh(row)
        last = outbreak.assessment_for_stored_report(db, row)
    assert last.alert_level == AlertLevel.MONITORING
    assert last.related_report_count == 3

    live = make_report(
        "LIVE4", now, 37.4220, -122.0840,
        disease="curl_virus",
        codes=["LEAF_DISCOLORATION"],
        image=True,
    )
    db.add(live); db.commit(); db.refresh(live)
    triggered = outbreak.assessment_for_stored_report(db, live)
    assert triggered.alert_level == AlertLevel.AMBER
    assert triggered.related_report_count == 4

    DeviceRepository().upsert(
        db,
        device_id="d53e3bcf-6dec-4a0d-a80c-c54ca701f300",
        crops=["cotton"],
        preferred_language="punjabi",
        latitude=37.4220,
        longitude=-122.0840,
        push_token=None,
        notifications_enabled=True,
    )
    verified = verify_alert(
        triggered.alert_id,
        AlertVerificationRequest(
            decision="confirmed",
            expert_name="Officer",
            note="confirmed",
            farmer_instruction="اپنی فصل چیک کرو۔",
        ),
        db,
    )
    assert verified.alert_level == AlertLevel.RED
    notification = db.scalar(
        select(Notification).where(Notification.device_id == "d53e3bcf-6dec-4a0d-a80c-c54ca701f300")
    )
    assert notification is not None
    assert notification.distance_km <= 2.0
