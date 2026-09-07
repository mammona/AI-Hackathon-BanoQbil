"""Preload three leaf-curling reports around 37.4220, -122.0840.

Purpose
-------
Leave the demo in MONITORING with exactly three symptom-only LEAF_CURLING
reports. The next compatible live report from Flutter should join the cluster
and promote it to AMBER. The expert then confirms AMBER -> RED, which dispatches
Punjabi notifications to eligible same-crop registered devices inside the 2 km
notification circle.

The demo intentionally separates:
- outbreak linking radius: OUTBREAK_RADIUS_KM (default 5 km)
- farmer notification radius: NOTIFICATION_RADIUS_KM (default 2 km)
"""
from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from math import pi
from pathlib import Path

from sqlalchemy import delete, select

from app.config import get_settings
from app.database import Base, SessionLocal, engine
from app.models.database_models import Alert, AlertReport, Notification, Report
from app.repositories.alert_repository import AlertRepository
from app.repositories.device_repository import DeviceRepository
from app.services.notification_service import NotificationService
from app.services.outbreak_service import OutbreakService

ROOT = Path(__file__).resolve().parents[1]
REPORT_FILE = ROOT / "data" / "leaf_curl_2km_demo_reports.json"
DEVICE_FILE = ROOT / "data" / "leaf_curl_2km_demo_devices.json"
PREFIX = "LC2KM-"


def _cleanup(db) -> None:
    report_ids = list(
        db.scalars(select(Report.report_id).where(Report.report_id.like(f"{PREFIX}%"))).all()
    )
    alert_ids: list[str] = []
    if report_ids:
        alert_ids = list(
            db.scalars(
                select(AlertReport.alert_id)
                .where(AlertReport.report_id.in_(report_ids))
                .distinct()
            ).all()
        )
    if alert_ids:
        db.execute(delete(Notification).where(Notification.alert_id.in_(alert_ids)))
        db.execute(delete(AlertReport).where(AlertReport.alert_id.in_(alert_ids)))
        db.execute(delete(Alert).where(Alert.alert_id.in_(alert_ids)))
    if report_ids:
        db.execute(delete(AlertReport).where(AlertReport.report_id.in_(report_ids)))
        db.execute(delete(Report).where(Report.report_id.in_(report_ids)))
    db.commit()


def _build_report(item: dict, base_time: datetime) -> Report:
    return Report(
        report_id=item["report_id"],
        device_id=None,
        selected_crop="cotton",
        language=item.get("language", "punjabi"),
        detected_crop=None,
        image_status="not_submitted",
        crop_match=None,
        crop_validation_confidence=None,
        image_submitted=False,
        disease=None,
        disease_confidence=None,
        disease_confidence_level=None,
        healthy_class_supported=None,
        question_1_raw=item.get("question_1_raw", ""),
        question_2_raw=item.get("question_2_raw", ""),
        question_3_raw=item.get("question_3_raw", ""),
        question_4_raw=item.get("question_4_raw", ""),
        symptoms=list(item.get("symptoms") or []),
        symptom_codes=list(item.get("symptom_codes") or ["LEAF_CURLING"]),
        symptom_mapping=[],
        symptom_dictionary_version="leaf-curl-2km-preload",
        affected_part="leaves",
        problem_duration=item.get("question_2_raw") or None,
        affected_area=item.get("question_3_raw") or None,
        spread_status="spreading" if item.get("question_4_raw") else None,
        evidence_mode="SYMPTOM_ONLY",
        evidence_strength="MEDIUM",
        image_evidence_available=False,
        symptom_evidence_available=True,
        canonical_symptom_evidence_available=True,
        usable_for_outbreak=True,
        summary="Synthetic cotton leaf-curling preload report for the 2 km notification demo.",
        recommended_next_step="Wait for an additional compatible field report before AMBER verification.",
        requires_expert_review=False,
        expert_review_status="NOT_REQUIRED",
        latitude=float(item["latitude"]),
        longitude=float(item["longitude"]),
        location_available=True,
        image_path=None,
        processing_status="completed_without_image",
        reported_at=base_time + timedelta(minutes=int(item.get("minutes_offset", 0))),
    )


def main() -> None:
    settings = get_settings()
    Base.metadata.create_all(bind=engine)
    report_payload = json.loads(REPORT_FILE.read_text(encoding="utf-8"))
    device_payload = json.loads(DEVICE_FILE.read_text(encoding="utf-8"))
    anchor = report_payload["anchor"]
    reports = report_payload["reports"]

    if len(reports) != 3:
        raise SystemExit(f"FAIL: preload must contain exactly 3 reports, found {len(reports)}")

    outbreak = OutbreakService()
    notification = NotificationService()
    alert_repo = AlertRepository()
    device_repo = DeviceRepository()
    base_time = datetime.now(timezone.utc).replace(microsecond=0) - timedelta(minutes=10)

    with SessionLocal() as db:
        _cleanup(db)

        for item in device_payload:
            device_repo.upsert(
                db,
                device_id=item["device_id"],
                crops=item["crops"],
                preferred_language=item.get("preferred_language", "punjabi"),
                latitude=item.get("latitude"),
                longitude=item.get("longitude"),
                push_token=item.get("push_token"),
                notifications_enabled=bool(item.get("notifications_enabled", True)),
            )

        print("\nAI Fasal Shield - Leaf Curl 2 km PRELOAD")
        print("=" * 78)
        print(f"Anchor: {anchor['latitude']:.4f}, {anchor['longitude']:.4f}")
        print(f"Outbreak linking radius: {settings.outbreak_radius_km:.2f} km")
        print(f"Notification radius: {settings.notification_radius_km:.2f} km")
        print(f"Notification area: {pi * settings.notification_radius_km ** 2:.3f} km^2")
        print("\nPreloaded report progression")
        print("-" * 78)

        last_result = None
        for item in reports:
            row = _build_report(item, base_time)
            anchor_distance = outbreak.distance_km(
                anchor["latitude"], anchor["longitude"], row.latitude, row.longitude
            )
            if anchor_distance > float(anchor["max_report_distance_km"]) + 1e-6:
                raise SystemExit(
                    f"FAIL: {row.report_id} is {anchor_distance:.3f} km from anchor; expected <= 2 km"
                )
            db.add(row)
            db.commit()
            db.refresh(row)
            result = outbreak.assessment_for_stored_report(db, row)
            last_result = result
            actual_level = result.alert_level.value if result.alert_level else None
            expected_level = item["expected_alert_level"]
            if actual_level != expected_level or result.related_report_count != item["expected_related_count"]:
                raise SystemExit(
                    f"FAIL: {row.report_id}: expected {expected_level}/{item['expected_related_count']}; "
                    f"got {actual_level}/{result.related_report_count}"
                )
            print(
                f"{row.report_id}: anchor_distance={anchor_distance:.3f} km -> "
                f"{actual_level} (related={result.related_report_count})"
            )

        if not last_result or not last_result.alert_id or last_result.alert_level.value != "MONITORING":
            raise SystemExit("FAIL: three symptom-only leaf-curl reports should leave the demo in MONITORING")

        alert = alert_repo.get(db, last_result.alert_id)
        assert alert is not None
        linked = list(
            db.scalars(select(Report).where(Report.report_id.like(f"{PREFIX}%"))).all()
        )
        cluster_spread = max(
            outbreak.distance_km(alert.center_latitude, alert.center_longitude, r.latitude, r.longitude)
            for r in linked
        )
        eligible = notification.eligible_devices(db, alert)

        print("\nCurrent monitoring geometry")
        print("-" * 78)
        print(f"Monitoring center: {alert.center_latitude:.6f}, {alert.center_longitude:.6f}")
        print(f"Observed cluster spread: {cluster_spread:.3f} km")
        print(f"Future RED notification radius: {settings.notification_radius_km:.3f} km")
        print(f"Future RED notification area: {pi * settings.notification_radius_km ** 2:.3f} km^2")
        print(f"Currently eligible same-crop devices: {len(eligible)}")

        target = device_repo.get(db, "d53e3bcf-6dec-4a0d-a80c-c54ca701f300")
        if target is None:
            raise SystemExit("FAIL: target registered device was not seeded")

        print("\nREADY FOR LIVE REPORT")
        print("-" * 78)
        print("Three LEAF_CURLING reports are preloaded and the cluster is MONITORING.")
        print("Submit ONE additional compatible cotton report from Flutter near 37.4220, -122.0840.")
        print("Expected: the live report joins these 3 reports -> AMBER appears in Outbreak Alerts.")
        print("Safety gate remains: expert clicks 'Confirm -> RED & Notify Farmers'.")
        print("Then eligible cotton devices within 2 km of the final alert center receive the Punjabi notification.")
        print("No notification is sent while the alert is only MONITORING or AMBER.")


if __name__ == "__main__":
    main()
