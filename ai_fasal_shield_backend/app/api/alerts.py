from datetime import datetime, timezone
from math import pi

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.schemas import (
    AlertDetail,
    AlertLevel,
    AlertSummary,
    AlertVerificationRequest,
)
from app.repositories.alert_repository import AlertRepository
from app.repositories.notification_repository import NotificationRepository
from app.repositories.report_repository import ReportRepository
from app.services.notification_service import NotificationService
from app.services.outbreak_service import OutbreakService

router = APIRouter()
repo = AlertRepository()
notification_repo = NotificationRepository()
notification_service = NotificationService()
report_repo = ReportRepository()


def _summary(row) -> AlertSummary:
    return AlertSummary(
        alert_id=row.alert_id,
        crop=row.crop,
        primary_disease=row.primary_disease,
        primary_symptom_codes=row.primary_symptom_codes or [],
        center_latitude=row.center_latitude,
        center_longitude=row.center_longitude,
        radius_km=row.radius_km,
        report_count=row.report_count,
        alert_level=AlertLevel(row.alert_level),
        status=row.status,
        created_at=row.created_at,
        updated_at=row.updated_at,
        verified_by=row.verified_by,
        verification_note=row.verification_note,
        farmer_instruction=row.farmer_instruction,
        verified_at=row.verified_at,
    )


def _detail(db: Session, row) -> AlertDetail:
    payload = _summary(row).model_dump()
    report_ids = repo.linked_report_ids(db, row.alert_id)
    payload["report_ids"] = report_ids

    notification_radius = float(notification_service.settings.notification_radius_km)
    payload["notification_radius_km"] = notification_radius
    payload["notification_area_km2"] = round(pi * notification_radius * notification_radius, 3)

    linked_reports = [
        r for r in report_repo.get_many(db, report_ids)
        if r.location_available
    ]
    payload["cluster_spread_km"] = round(
        max(
            (
                OutbreakService.distance_km(
                    row.center_latitude, row.center_longitude, r.latitude, r.longitude
                )
            )
            for r in linked_reports
        ),
        3,
    ) if linked_reports else 0.0

    payload["eligible_device_count"] = len(notification_service.eligible_devices(db, row))
    payload["notification_count"] = notification_repo.count_for_alert(db, row.alert_id)
    return AlertDetail(**payload)


@router.get("/alerts", response_model=list[AlertSummary])
def list_alerts(
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
):
    return [_summary(row) for row in repo.list(db, limit=limit, offset=offset)]


@router.get("/alerts/active", response_model=list[AlertSummary])
def active_alerts(
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
):
    return [
        _summary(row)
        for row in repo.list(db, active_only=True, limit=limit, offset=offset)
    ]


@router.get("/alerts/{alert_id}", response_model=AlertDetail)
def get_alert(alert_id: str, db: Session = Depends(get_db)):
    row = repo.get(db, alert_id)
    if not row:
        raise HTTPException(status_code=404, detail="Alert not found")
    return _detail(db, row)


@router.post("/alerts/{alert_id}/verify", response_model=AlertDetail)
def verify_alert(
    alert_id: str,
    request: AlertVerificationRequest,
    db: Session = Depends(get_db),
):
    row = repo.get(db, alert_id)
    if not row:
        raise HTTPException(status_code=404, detail="Alert not found")

    if request.decision == "confirmed":
        if row.alert_level not in {AlertLevel.AMBER.value, AlertLevel.RED.value}:
            raise HTTPException(
                status_code=409,
                detail="Only an AMBER alert can be promoted to RED by expert confirmation.",
            )
        row.alert_level = AlertLevel.RED.value
        row.status = "confirmed"
    else:
        row.status = "rejected"

    row.verified_by = request.expert_name.strip()
    row.verification_note = request.note
    # Store farmer-facing guidance separately from the internal verification note.
    row.farmer_instruction = (request.farmer_instruction or "").strip() or None
    row.verified_at = datetime.now(timezone.utc)
    repo.update(db, row)
    if request.decision == "confirmed":
        notification_service.dispatch_confirmed_alert(db, row)
    return _detail(db, row)
