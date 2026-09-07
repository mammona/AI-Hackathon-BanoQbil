from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.schemas import DeviceLocationUpdate, DeviceRegistrationRequest, DeviceResponse, NotificationResponse
from app.repositories.device_repository import DeviceRepository
from app.repositories.notification_repository import NotificationRepository

router = APIRouter(); devices = DeviceRepository(); notifications = NotificationRepository()

def _device(row) -> DeviceResponse:
    return DeviceResponse(device_id=row.device_id, crops=row.crops or [], preferred_language=row.preferred_language, latitude=row.latitude, longitude=row.longitude, location_available=row.location_available, notifications_enabled=row.notifications_enabled, has_push_token=bool(row.push_token), last_seen_at=row.last_seen_at, created_at=row.created_at, updated_at=row.updated_at)

def _notification(row) -> NotificationResponse:
    return NotificationResponse(notification_id=row.notification_id, alert_id=row.alert_id, device_id=row.device_id, crop=row.crop, title=row.title, message=row.message, message_local=row.message_local, language=row.language, distance_km=row.distance_km, status=row.status, created_at=row.created_at, read_at=row.read_at)

@router.post("/devices/register", response_model=DeviceResponse)
def register_device(request: DeviceRegistrationRequest, db: Session = Depends(get_db)):
    if (request.latitude is None) != (request.longitude is None):
        raise HTTPException(status_code=422, detail="Provide both latitude and longitude, or omit both.")
    row = devices.upsert(db, device_id=request.device_id.strip(), crops=[c.value for c in request.crops], preferred_language=request.preferred_language.value, latitude=request.latitude, longitude=request.longitude, push_token=request.push_token, notifications_enabled=request.notifications_enabled)
    return _device(row)

@router.get("/devices", response_model=list[DeviceResponse])
def list_devices(limit: int = Query(default=100, ge=1, le=500), offset: int = Query(default=0, ge=0), db: Session = Depends(get_db)):
    return [_device(x) for x in devices.list(db, limit=limit, offset=offset)]

@router.get("/devices/{device_id}", response_model=DeviceResponse)
def get_device(device_id: str, db: Session = Depends(get_db)):
    row = devices.get(db, device_id)
    if not row: raise HTTPException(status_code=404, detail="Device not found")
    return _device(row)

@router.put("/devices/{device_id}/location", response_model=DeviceResponse)
def update_location(device_id: str, request: DeviceLocationUpdate, db: Session = Depends(get_db)):
    row = devices.get(db, device_id)
    if not row: raise HTTPException(status_code=404, detail="Device not found")
    return _device(devices.update_location(db, row, latitude=request.latitude, longitude=request.longitude))

@router.get("/devices/{device_id}/notifications", response_model=list[NotificationResponse])
def device_notifications(device_id: str, unread_only: bool = Query(default=False), limit: int = Query(default=100, ge=1, le=500), db: Session = Depends(get_db)):
    if not devices.get(db, device_id): raise HTTPException(status_code=404, detail="Device not found")
    return [_notification(x) for x in notifications.list_for_device(db, device_id, unread_only=unread_only, limit=limit)]

@router.post("/notifications/{notification_id}/read", response_model=NotificationResponse)
def mark_notification_read(notification_id: str, db: Session = Depends(get_db)):
    row = notifications.get(db, notification_id)
    if not row: raise HTTPException(status_code=404, detail="Notification not found")
    return _notification(notifications.mark_read(db, row))
