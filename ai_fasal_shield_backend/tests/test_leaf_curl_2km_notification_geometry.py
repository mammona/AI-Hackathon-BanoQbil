from math import pi

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database import Base
from app.models.database_models import Alert
from app.repositories.device_repository import DeviceRepository
from app.services.notification_service import NotificationService
from app.services.outbreak_service import OutbreakService


def session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine, expire_on_commit=False)()


def test_notification_radius_is_two_km_and_area_is_correct():
    service = NotificationService()
    assert service.settings.notification_radius_km == 2.0
    assert round(pi * service.settings.notification_radius_km ** 2, 3) == 12.566


def test_leafcurl_demo_device_inside_two_km_is_eligible_and_outside_device_is_not():
    db = session()
    repo = DeviceRepository()
    alert = Alert(
        alert_id="ALT-LC2KM-TEST",
        crop="cotton",
        primary_disease=None,
        primary_symptom_codes=["LEAF_CURLING"],
        center_latitude=37.41930784071978,
        center_longitude=-122.08620178185251,
        radius_km=5.0,
        report_count=4,
        alert_level="RED",
        status="confirmed",
    )
    db.add(alert)
    db.commit()

    repo.upsert(
        db,
        device_id="INSIDE-2KM",
        crops=["cotton"],
        preferred_language="punjabi",
        latitude=37.4220,
        longitude=-122.0840,
        push_token=None,
        notifications_enabled=True,
    )
    repo.upsert(
        db,
        device_id="OUTSIDE-2KM",
        crops=["cotton"],
        preferred_language="punjabi",
        latitude=37.4219960630528,
        longitude=-122.05342556120263,
        push_token=None,
        notifications_enabled=True,
    )
    repo.upsert(
        db,
        device_id="WRONG-CROP",
        crops=["rice"],
        preferred_language="punjabi",
        latitude=37.4220,
        longitude=-122.0840,
        push_token=None,
        notifications_enabled=True,
    )

    service = NotificationService()
    matched = {device.device_id: distance for device, distance in service.eligible_devices(db, alert)}

    assert "INSIDE-2KM" in matched
    assert matched["INSIDE-2KM"] < 2.0
    assert "OUTSIDE-2KM" not in matched
    assert "WRONG-CROP" not in matched

    outside_distance = OutbreakService.distance_km(
        alert.center_latitude,
        alert.center_longitude,
        37.4219960630528,
        -122.05342556120263,
    )
    assert outside_distance > 2.0
