from __future__ import annotations

from datetime import datetime, timezone
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.database_models import RegisteredDevice


class DeviceRepository:
    def get(self, db: Session, device_id: str) -> RegisteredDevice | None:
        return db.scalar(select(RegisteredDevice).where(RegisteredDevice.device_id == device_id))

    def list(self, db: Session, *, limit: int = 500, offset: int = 0) -> list[RegisteredDevice]:
        stmt = select(RegisteredDevice).order_by(RegisteredDevice.updated_at.desc()).limit(limit).offset(offset)
        return list(db.scalars(stmt).all())

    def active_with_location(self, db: Session) -> list[RegisteredDevice]:
        stmt = select(RegisteredDevice).where(
            RegisteredDevice.notifications_enabled.is_(True),
            RegisteredDevice.location_available.is_(True),
        )
        return list(db.scalars(stmt).all())

    def upsert(self, db: Session, *, device_id: str, crops: list[str], preferred_language: str, latitude: float | None, longitude: float | None, push_token: str | None, notifications_enabled: bool) -> RegisteredDevice:
        row = self.get(db, device_id)
        now = datetime.now(timezone.utc)
        if row is None:
            row = RegisteredDevice(device_id=device_id, created_at=now)
        row.crops = sorted(set(crops))
        row.preferred_language = preferred_language
        row.latitude = latitude
        row.longitude = longitude
        row.location_available = latitude is not None and longitude is not None
        row.push_token = push_token
        row.notifications_enabled = notifications_enabled
        row.last_seen_at = now
        row.updated_at = now
        db.add(row); db.commit(); db.refresh(row)
        return row

    def update_location(self, db: Session, row: RegisteredDevice, *, latitude: float, longitude: float) -> RegisteredDevice:
        now = datetime.now(timezone.utc)
        row.latitude = latitude; row.longitude = longitude; row.location_available = True; row.last_seen_at = now; row.updated_at = now
        db.add(row); db.commit(); db.refresh(row)
        return row
    def ensure_from_report(
        self,
        db: Session,
        *,
        device_id: str,
        crop: str,
        preferred_language: str,
        latitude: float | None,
        longitude: float | None,
    ) -> RegisteredDevice:
        """Create/update a mobile device from a submitted farmer report.

        This closes the old gap where reports stored device_id but the device
        itself was never inserted into registered_devices. Existing push-token
        and notification preferences are preserved.
        """
        row = self.get(db, device_id)
        if row is None:
            return self.upsert(
                db,
                device_id=device_id,
                crops=[crop],
                preferred_language=preferred_language,
                latitude=latitude,
                longitude=longitude,
                push_token=None,
                notifications_enabled=True,
            )

        now = datetime.now(timezone.utc)
        row.crops = sorted(set((row.crops or []) + [crop]))
        row.preferred_language = preferred_language or row.preferred_language
        if latitude is not None and longitude is not None:
            row.latitude = latitude
            row.longitude = longitude
            row.location_available = True
        row.last_seen_at = now
        row.updated_at = now
        db.add(row)
        db.commit()
        db.refresh(row)
        return row

