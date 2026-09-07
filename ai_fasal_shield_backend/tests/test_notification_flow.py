from datetime import datetime, timezone

from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker

from app.api.alerts import verify_alert
from app.database import Base
from app.models.database_models import Alert, Notification
from app.models.schemas import AlertLevel, AlertVerificationRequest
from app.repositories.device_repository import DeviceRepository


def session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine, expire_on_commit=False)()


def amber(db, alert_id="ALT-NOTIFY-001"):
    row = Alert(
        alert_id=alert_id,
        crop="cotton",
        primary_disease="curl_virus",
        primary_symptom_codes=["LEAF_CURLING", "LEAF_YELLOWING"],
        center_latitude=31.5204,
        center_longitude=74.3587,
        radius_km=5.0,
        report_count=3,
        alert_level="AMBER",
        status="pending_verification",
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )
    db.add(row); db.commit(); db.refresh(row); return row


def add_devices(db):
    repo = DeviceRepository()
    repo.upsert(db, device_id="COTTON-NEAR", crops=["cotton"], preferred_language="punjabi", latitude=31.521, longitude=74.359, push_token=None, notifications_enabled=True)
    repo.upsert(db, device_id="RICE-NEAR", crops=["rice"], preferred_language="urdu", latitude=31.521, longitude=74.359, push_token=None, notifications_enabled=True)
    repo.upsert(db, device_id="COTTON-FAR", crops=["cotton"], preferred_language="english", latitude=31.62, longitude=74.45, push_token=None, notifications_enabled=True)
    repo.upsert(db, device_id="COTTON-DISABLED", crops=["cotton"], preferred_language="english", latitude=31.521, longitude=74.359, push_token=None, notifications_enabled=False)


def test_confirmed_amber_creates_notifications_only_for_eligible_devices():
    db = session(); amber(db); add_devices(db)
    result = verify_alert(
        "ALT-NOTIFY-001",
        AlertVerificationRequest(decision="confirmed", expert_name="Agriculture Officer", note="Field confirmed"),
        db,
    )
    assert result.alert_level == AlertLevel.RED
    assert result.status == "confirmed"
    assert result.eligible_device_count == 1
    assert result.notification_count == 1
    rows = list(db.scalars(select(Notification)).all())
    assert len(rows) == 1
    assert rows[0].device_id == "COTTON-NEAR"
    assert rows[0].status == "unread"
    assert rows[0].language == "punjabi"
    assert rows[0].title == "فصل دی بیماری دا تصدیق شدہ الرٹ"
    assert "کپاس" in rows[0].message
    assert "پتے مڑنا" in rows[0].message
    assert rows[0].message == rows[0].message_local
    # Expert verification notes are internal and must never be copied to farmers.
    assert "Field confirmed" not in rows[0].message


def test_reconfirm_is_idempotent_and_does_not_duplicate_notification():
    db = session(); amber(db); add_devices(db)
    req = AlertVerificationRequest(decision="confirmed", expert_name="Officer", note=None)
    first = verify_alert("ALT-NOTIFY-001", req, db)
    second = verify_alert("ALT-NOTIFY-001", req, db)
    assert first.notification_count == 1
    assert second.notification_count == 1
    assert len(list(db.scalars(select(Notification)).all())) == 1


def test_rejected_amber_does_not_send_notifications():
    db = session(); amber(db, "ALT-REJECT-001"); add_devices(db)
    result = verify_alert(
        "ALT-REJECT-001",
        AlertVerificationRequest(decision="rejected", expert_name="Officer", note="Not confirmed"),
        db,
    )
    assert result.status == "rejected"
    assert result.notification_count == 0
    assert list(db.scalars(select(Notification)).all()) == []


def test_farmer_notification_is_punjabi_even_if_device_preference_is_english():
    db = session()
    amber(db, "ALT-PUNJABI-001")
    repo = DeviceRepository()
    repo.upsert(
        db,
        device_id="COTTON-ENGLISH-PREF",
        crops=["cotton"],
        preferred_language="english",
        latitude=31.521,
        longitude=74.359,
        push_token=None,
        notifications_enabled=True,
    )
    private_note = "Internal lab note: do not send this sentence to farmers."
    result = verify_alert(
        "ALT-PUNJABI-001",
        AlertVerificationRequest(
            decision="confirmed",
            expert_name="Agriculture Officer",
            note=private_note,
        ),
        db,
    )
    assert result.alert_level == AlertLevel.RED
    rows = list(db.scalars(select(Notification)).all())
    assert len(rows) == 1
    notification = rows[0]
    assert notification.language == "punjabi"
    assert notification.title == "فصل دی بیماری دا تصدیق شدہ الرٹ"
    assert notification.message == notification.message_local
    assert "کپاس" in notification.message
    assert "پتیاں دے مڑن والی وائرس بیماری" in notification.message
    assert "پتے مڑنا" in notification.message
    assert private_note not in notification.message
    assert result.verification_note == private_note


def test_reviewer_farmer_instruction_is_sent_but_private_note_is_not():
    db = session(); amber(db, "ALT-INSTRUCTION-001"); add_devices(db)
    private_note = "Internal verification detail - never send"
    farmer_instruction = "اگلے تین دن اپنی کپاس دی فصل روزانہ چیک کرو تے پتے مڑن تے فوراً رپورٹ کرو۔"
    result = verify_alert(
        "ALT-INSTRUCTION-001",
        AlertVerificationRequest(
            decision="confirmed",
            expert_name="Agriculture Officer",
            note=private_note,
            farmer_instruction=farmer_instruction,
        ),
        db,
    )
    assert result.farmer_instruction == farmer_instruction
    notification = db.scalar(select(Notification).where(Notification.alert_id == "ALT-INSTRUCTION-001"))
    assert notification is not None
    assert "زرعی ماہر دی ہدایت:" in notification.message
    assert farmer_instruction in notification.message
    assert private_note not in notification.message


def test_reconfirm_updates_existing_notification_when_instruction_changes():
    db = session(); amber(db, "ALT-INSTRUCTION-UPDATE"); add_devices(db)
    first_instruction = "اپنی فصل دا معائنہ کرو۔"
    second_instruction = "متاثرہ پودیاں دی تصویر بنا کے نئی رپورٹ جمع کرو۔"

    verify_alert(
        "ALT-INSTRUCTION-UPDATE",
        AlertVerificationRequest(
            decision="confirmed",
            expert_name="Officer",
            note="private one",
            farmer_instruction=first_instruction,
        ),
        db,
    )
    notification = db.scalar(select(Notification).where(Notification.alert_id == "ALT-INSTRUCTION-UPDATE"))
    assert notification is not None
    notification.status = "read"
    db.add(notification); db.commit()

    result = verify_alert(
        "ALT-INSTRUCTION-UPDATE",
        AlertVerificationRequest(
            decision="confirmed",
            expert_name="Officer",
            note="private two",
            farmer_instruction=second_instruction,
        ),
        db,
    )
    rows = list(db.scalars(select(Notification).where(Notification.alert_id == "ALT-INSTRUCTION-UPDATE")).all())
    assert result.notification_count == 1
    assert len(rows) == 1
    assert second_instruction in rows[0].message
    assert first_instruction not in rows[0].message
    assert rows[0].status == "unread"
