from __future__ import annotations

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.models.database_models import Alert, AlertReport


class AlertRepository:
    ACTIVE_STATUSES = {"active", "pending_verification", "confirmed"}

    def get(self, db: Session, alert_id: str) -> Alert | None:
        return db.scalar(select(Alert).where(Alert.alert_id == alert_id))

    def list(self, db: Session, *, active_only: bool = False, limit: int = 100, offset: int = 0) -> list[Alert]:
        stmt = select(Alert).order_by(Alert.updated_at.desc()).limit(limit).offset(offset)
        if active_only:
            stmt = stmt.where(Alert.status.in_(sorted(self.ACTIVE_STATUSES)))
        return list(db.scalars(stmt).all())

    def linked_report_ids(self, db: Session, alert_id: str) -> list[str]:
        stmt = select(AlertReport.report_id).where(AlertReport.alert_id == alert_id)
        return list(db.scalars(stmt).all())

    def find_by_report_overlap(self, db: Session, *, crop: str, report_ids: list[str]) -> Alert | None:
        if not report_ids:
            return None
        stmt = (
            select(Alert)
            .join(AlertReport, AlertReport.alert_id == Alert.alert_id)
            .where(
                Alert.crop == crop,
                Alert.status.in_(sorted(self.ACTIVE_STATUSES)),
                AlertReport.report_id.in_(report_ids),
            )
            .order_by(Alert.updated_at.desc())
            .limit(1)
        )
        return db.scalar(stmt)

    def save(self, db: Session, alert: Alert) -> Alert:
        db.add(alert)
        db.commit()
        db.refresh(alert)
        return alert

    def update(self, db: Session, alert: Alert) -> Alert:
        db.add(alert)
        db.commit()
        db.refresh(alert)
        return alert

    def sync_report_links(self, db: Session, *, alert_id: str, report_ids: list[str], preserve_existing: bool = False) -> None:
        requested = set(report_ids)
        existing = set(self.linked_report_ids(db, alert_id))

        if not preserve_existing:
            stale = existing - requested
            if stale:
                db.execute(
                    delete(AlertReport).where(
                        AlertReport.alert_id == alert_id,
                        AlertReport.report_id.in_(stale),
                    )
                )

        for report_id in sorted(requested - existing):
            db.add(AlertReport(alert_id=alert_id, report_id=report_id))
        db.commit()
