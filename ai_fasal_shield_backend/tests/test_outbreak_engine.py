from datetime import datetime, timedelta, timezone

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.api.alerts import verify_alert
from app.database import Base
from app.models.database_models import Report
from app.models.schemas import AlertLevel, AlertVerificationRequest
from app.services.outbreak_service import OutbreakService


def session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine, expire_on_commit=False)()


def report(
    report_id: str,
    *,
    when: datetime,
    lat: float = 31.5204,
    lon: float = 74.3587,
    crop: str = "cotton",
    disease: str | None = None,
    image_evidence: bool = False,
    codes: list[str] | None = None,
    mode: str = "SYMPTOM_ONLY",
    usable: bool = True,
) -> Report:
    codes = codes or []
    return Report(
        report_id=report_id,
        selected_crop=crop,
        language="punjabi",
        image_status="validated" if image_evidence else "not_submitted",
        image_submitted=image_evidence,
        disease=disease,
        disease_confidence=0.95 if disease else None,
        disease_confidence_level="high" if disease else None,
        healthy_class_supported=True,
        question_1_raw="test",
        question_2_raw="",
        question_3_raw="",
        question_4_raw="",
        symptoms=["test"] if codes else [],
        symptom_codes=codes,
        symptom_mapping=[],
        evidence_mode=mode,
        evidence_strength="STRONG" if mode == "MULTIMODAL" else "MEDIUM",
        image_evidence_available=image_evidence and disease != "healthy",
        symptom_evidence_available=bool(codes),
        canonical_symptom_evidence_available=any(c != "OTHERS_MAP" for c in codes),
        usable_for_outbreak=usable,
        summary="test",
        recommended_next_step="test",
        requires_expert_review=False,
        latitude=lat,
        longitude=lon,
        location_available=True,
        processing_status="completed",
        reported_at=when,
    )


def save(db, row):
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def test_no_alert_to_monitoring_to_amber_to_red():
    db = session()
    service = OutbreakService()
    now = datetime.now(timezone.utc)

    r1 = save(db, report("R1", when=now, disease="curl_virus", image_evidence=True, codes=["LEAF_CURLING"], mode="MULTIMODAL"))
    a1 = service.assessment_for_stored_report(db, r1)
    assert a1.alert_level == AlertLevel.NO_ALERT
    assert a1.related_report_count == 1

    r2 = save(db, report("R2", when=now + timedelta(minutes=1), codes=["LEAF_CURLING"]))
    a2 = service.assessment_for_stored_report(db, r2)
    assert a2.alert_level == AlertLevel.MONITORING
    assert a2.related_report_count == 2
    assert a2.alert_id

    r3 = save(db, report("R3", when=now + timedelta(minutes=2), codes=["LEAF_CURLING"]))
    a3 = service.assessment_for_stored_report(db, r3)
    assert a3.alert_level == AlertLevel.AMBER
    assert a3.related_report_count == 3
    assert a3.alert_id == a2.alert_id

    verified = verify_alert(
        a3.alert_id,
        AlertVerificationRequest(
            decision="confirmed",
            expert_name="Agriculture Officer",
            note="Field confirmed",
        ),
        db,
    )
    assert verified.alert_level == AlertLevel.RED
    assert verified.status == "confirmed"


def test_symptom_only_requires_four_reports_for_amber():
    db = session()
    service = OutbreakService()
    now = datetime.now(timezone.utc)
    last = None
    for i in range(4):
        row = save(db, report(f"S{i}", when=now + timedelta(minutes=i), codes=["LEAF_YELLOWING"]))
        last = service.assessment_for_stored_report(db, row)
        if i == 2:
            assert last.alert_level == AlertLevel.MONITORING
    assert last is not None
    assert last.alert_level == AlertLevel.AMBER
    assert last.related_report_count == 4


def test_others_map_alone_does_not_cluster():
    db = session()
    service = OutbreakService()
    now = datetime.now(timezone.utc)
    for i in range(4):
        row = report(
            f"O{i}",
            when=now + timedelta(minutes=i),
            codes=["OTHERS_MAP"],
            usable=False,
            mode="CONTEXT_ONLY",
        )
        save(db, row)
        result = service.assessment_for_stored_report(db, row)
        assert result.evaluated is False
        assert result.alert_id is None


def test_far_report_does_not_join_cluster():
    db = session()
    service = OutbreakService()
    now = datetime.now(timezone.utc)
    r1 = save(db, report("D1", when=now, codes=["LEAF_CURLING"]))
    service.assessment_for_stored_report(db, r1)
    # Roughly > 10 km away.
    r2 = save(db, report("D2", when=now + timedelta(minutes=1), lat=31.65, lon=74.3587, codes=["LEAF_CURLING"]))
    result = service.assessment_for_stored_report(db, r2)
    assert result.alert_level == AlertLevel.NO_ALERT
    assert result.related_report_count == 1


def test_old_report_does_not_join_cluster():
    db = session()
    service = OutbreakService()
    now = datetime.now(timezone.utc)
    old = save(db, report("T1", when=now - timedelta(days=8), codes=["LEAF_CURLING"]))
    service.assessment_for_stored_report(db, old)
    current = save(db, report("T2", when=now, codes=["LEAF_CURLING"]))
    result = service.assessment_for_stored_report(db, current)
    assert result.alert_level == AlertLevel.NO_ALERT
    assert result.related_report_count == 1


def test_healthy_image_is_not_disease_outbreak_evidence():
    db = session()
    service = OutbreakService()
    now = datetime.now(timezone.utc)
    for i in range(3):
        row = report(
            f"H{i}",
            when=now + timedelta(minutes=i),
            disease="healthy",
            image_evidence=True,
            codes=[],
            mode="CONTEXT_ONLY",
            usable=False,
        )
        row.image_evidence_available = False
        save(db, row)
        result = service.assessment_for_stored_report(db, row)
        assert result.evaluated is False
        assert result.alert_id is None
