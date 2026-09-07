from __future__ import annotations

from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.database_models import Alert, AlertReport, Notification, RegisteredDevice, Report


class ReportRepository:
    def get(self, db: Session, report_id: str) -> Report | None:
        return db.scalar(select(Report).where(Report.report_id == report_id))

    def save(self, db: Session, report: Report) -> Report:
        db.add(report)
        db.commit()
        db.refresh(report)
        return report

    def update(self, db: Session, report: Report) -> Report:
        db.add(report)
        db.commit()
        db.refresh(report)
        return report

    def get_many(self, db: Session, report_ids: list[str]) -> list[Report]:
        if not report_ids:
            return []
        stmt = select(Report).where(Report.report_id.in_(report_ids))
        return list(db.scalars(stmt).all())

    def linked_alert_ids(self, db: Session, report_id: str) -> list[str]:
        stmt = select(AlertReport.alert_id).where(AlertReport.report_id == report_id)
        return list(db.scalars(stmt).all())

    def list(self, db: Session, crop: str | None = None, status: str | None = None, limit: int = 100, offset: int = 0) -> list[Report]:
        stmt = select(Report).order_by(Report.reported_at.desc()).limit(limit).offset(offset)
        if crop:
            stmt = stmt.where(Report.selected_crop == crop)
        if status:
            stmt = stmt.where(Report.processing_status == status)
        return list(db.scalars(stmt).all())

    def usable_for_crop_between(
        self,
        db: Session,
        *,
        crop: str,
        start_at: datetime,
        end_at: datetime,
    ) -> list[Report]:
        stmt = (
            select(Report)
            .where(
                Report.selected_crop == crop,
                Report.usable_for_outbreak.is_(True),
                Report.location_available.is_(True),
                Report.reported_at >= start_at,
                Report.reported_at <= end_at,
            )
            .order_by(Report.reported_at.asc())
        )
        return list(db.scalars(stmt).all())

    def dashboard_summary(self, db: Session) -> dict:
        def count_reports(*conditions) -> int:
            stmt = select(func.count(Report.id))
            if conditions:
                stmt = stmt.where(*conditions)
            return int(db.scalar(stmt) or 0)

        def count_alerts(*conditions) -> int:
            stmt = select(func.count(Alert.id))
            if conditions:
                stmt = stmt.where(*conditions)
            return int(db.scalar(stmt) or 0)

        active_statuses = ["active", "pending_verification", "confirmed"]
        return {
            "total_reports": count_reports(),
            "cotton_reports": count_reports(Report.selected_crop == "cotton"),
            "rice_reports": count_reports(Report.selected_crop == "rice"),
            "expert_review_required": count_reports(Report.requires_expert_review.is_(True)),
            # Completed means a terminal successful report, including reports that
            # intentionally had no image or were completed with uncertain image evidence.
            "completed_reports": count_reports(
                Report.processing_status.in_([
                    "completed",
                    "completed_without_image",
                    "completed_with_unverified_image",
                    "disease_low_confidence",
                    "wrong_crop_image",
                    "unsupported_crop_image",
                ])
            ),
            "unverified_image_reports": count_reports(
                Report.processing_status.in_([
                    "completed_with_unverified_image",
                    "completed_without_image",
                ])
            ),
            "failed_reports": count_reports(Report.processing_status == "processing_failed"),
            "usable_reports": count_reports(Report.usable_for_outbreak.is_(True)),
            "reports_needing_expert_review": count_reports(Report.requires_expert_review.is_(True)),
            "reviewed_valid_reports": count_reports(Report.expert_review_status == "VALID"),
            "reviewed_invalid_reports": count_reports(Report.expert_review_status == "INVALID"),
            "active_monitoring": count_alerts(
                Alert.alert_level == "MONITORING",
                Alert.status.in_(active_statuses),
            ),
            "amber_alerts": count_alerts(
                Alert.alert_level == "AMBER",
                Alert.status.in_(active_statuses),
            ),
            "red_alerts": count_alerts(
                Alert.alert_level == "RED",
                Alert.status.in_(active_statuses),
            ),
            "registered_devices": int(db.scalar(select(func.count(RegisteredDevice.id))) or 0),
            "unread_notifications": int(db.scalar(select(func.count(Notification.id)).where(Notification.status == "unread")) or 0),
        }
