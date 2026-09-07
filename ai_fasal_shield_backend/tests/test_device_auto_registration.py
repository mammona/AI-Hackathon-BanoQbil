from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database import Base
from app.repositories.device_repository import DeviceRepository


def session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine, expire_on_commit=False)()


def test_report_device_is_created_when_missing():
    db = session()
    repo = DeviceRepository()
    row = repo.ensure_from_report(
        db,
        device_id="PHONE-UUID-001",
        crop="cotton",
        preferred_language="punjabi",
        latitude=31.5204,
        longitude=74.3587,
    )
    assert row.device_id == "PHONE-UUID-001"
    assert row.crops == ["cotton"]
    assert row.location_available is True
    assert row.notifications_enabled is True


def test_report_device_update_preserves_preferences_and_adds_crop():
    db = session()
    repo = DeviceRepository()
    original = repo.upsert(
        db,
        device_id="PHONE-UUID-002",
        crops=["cotton"],
        preferred_language="urdu",
        latitude=None,
        longitude=None,
        push_token="PUSH-123",
        notifications_enabled=False,
    )
    updated = repo.ensure_from_report(
        db,
        device_id=original.device_id,
        crop="rice",
        preferred_language="punjabi",
        latitude=31.52,
        longitude=74.35,
    )
    assert updated.crops == ["cotton", "rice"]
    assert updated.push_token == "PUSH-123"
    assert updated.notifications_enabled is False
    assert updated.location_available is True
    assert updated.preferred_language == "punjabi"


def test_bundled_demo_device_dataset_seeds_all_devices_including_leafcurl_demo():
    from app.services.demo_device_seed_service import seed_demo_devices
    from app.models.database_models import RegisteredDevice
    from sqlalchemy import func, select

    db = session()
    count = seed_demo_devices(db)
    stored = int(db.scalar(select(func.count(RegisteredDevice.id))) or 0)
    assert count == 11
    assert stored == 11
    assert DeviceRepository().get(db, "d53e3bcf-6dec-4a0d-a80c-c54ca701f300") is not None
