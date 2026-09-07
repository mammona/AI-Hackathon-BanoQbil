from __future__ import annotations

from datetime import datetime, timezone
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.database_models import Notification


class NotificationRepository:
    def get(self, db: Session, notification_id: str) -> Notification | None:
        return db.scalar(select(Notification).where(Notification.notification_id == notification_id))

    def get_for_alert_device(self, db: Session, alert_id: str, device_id: str) -> Notification | None:
        return db.scalar(select(Notification).where(Notification.alert_id == alert_id, Notification.device_id == device_id))

    def save(self, db: Session, row: Notification) -> Notification:
        db.add(row); db.commit(); db.refresh(row); return row

    def list_for_device(self, db: Session, device_id: str, *, unread_only: bool = False, limit: int = 100) -> list[Notification]:
        stmt = select(Notification).where(Notification.device_id == device_id).order_by(Notification.created_at.desc()).limit(limit)
        if unread_only: stmt = stmt.where(Notification.status == "unread")
        return list(db.scalars(stmt).all())

    def count_for_alert(self, db: Session, alert_id: str) -> int:
        return int(db.scalar(select(func.count(Notification.id)).where(Notification.alert_id == alert_id)) or 0)

    def count_unread(self, db: Session) -> int:
        return int(db.scalar(select(func.count(Notification.id)).where(Notification.status == "unread")) or 0)

    def mark_read(self, db: Session, row: Notification) -> Notification:
        if row.status != "read":
            row.status = "read"; row.read_at = datetime.now(timezone.utc); db.add(row); db.commit(); db.refresh(row)
        return row
