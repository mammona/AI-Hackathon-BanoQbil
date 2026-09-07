from __future__ import annotations

from datetime import datetime, timezone

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.models.schemas import (
    ExpertReviewStatus,
    OutbreakAssessment,
    ReportReviewRequest,
    ReportReviewResult,
)
from app.repositories.report_repository import ReportRepository
from app.services.outbreak_service import OutbreakService


class ReportReviewService:
    """Human review gate for individual farmer reports."""

    def __init__(self) -> None:
        self.reports = ReportRepository()
        self.outbreak = OutbreakService()

    @staticmethod
    def _can_be_outbreak_evidence(row) -> bool:
        if getattr(row, "evidence_mode", "CONTEXT_ONLY") == "CONTEXT_ONLY":
            return False
        if getattr(row, "image_evidence_available", False):
            disease = (getattr(row, "disease", None) or "").strip().lower()
            if disease and disease != "healthy":
                return True
        return bool(getattr(row, "canonical_symptom_evidence_available", False))

    def review(
        self,
        db: Session,
        *,
        report_id: str,
        request: ReportReviewRequest,
    ) -> ReportReviewResult:
        row = self.reports.get(db, report_id)
        if row is None:
            raise HTTPException(status_code=404, detail="Report not found")

        existing_alert_ids = self.reports.linked_alert_ids(db, report_id)
        now = datetime.now(timezone.utc)
        row.reviewed_by = request.expert_name.strip()
        row.review_note = request.note
        row.reviewed_at = now

        if request.decision == "valid":
            row.expert_review_status = ExpertReviewStatus.VALID.value
            row.requires_expert_review = False
            row.usable_for_outbreak = self._can_be_outbreak_evidence(row)
            self.reports.update(db, row)
            outbreak = self.outbreak.assessment_after_expert_review(db, row)
        elif request.decision == "invalid":
            row.expert_review_status = ExpertReviewStatus.INVALID.value
            row.requires_expert_review = False
            row.usable_for_outbreak = False
            self.reports.update(db, row)
            for alert_id in existing_alert_ids:
                self.outbreak.recalculate_alert(db, alert_id)
            outbreak = OutbreakAssessment(
                evaluated=False,
                reason="Expert marked this report INVALID; it is stored for audit but excluded from automatic outbreak detection.",
            )
        else:
            row.expert_review_status = ExpertReviewStatus.FOLLOW_UP.value
            row.requires_expert_review = True
            row.usable_for_outbreak = False
            self.reports.update(db, row)
            for alert_id in existing_alert_ids:
                self.outbreak.recalculate_alert(db, alert_id)
            outbreak = OutbreakAssessment(
                evaluated=False,
                reason="Expert requested follow-up; the report is temporarily excluded from automatic outbreak detection.",
            )

        linked_alert_ids = self.reports.linked_alert_ids(db, report_id)
        if outbreak.alert_id and outbreak.alert_id not in linked_alert_ids:
            linked_alert_ids.append(outbreak.alert_id)

        return ReportReviewResult(
            report_id=row.report_id,
            expert_review_status=ExpertReviewStatus(row.expert_review_status),
            requires_expert_review=row.requires_expert_review,
            usable_for_outbreak=row.usable_for_outbreak,
            reviewed_by=row.reviewed_by or request.expert_name.strip(),
            review_note=row.review_note,
            reviewed_at=row.reviewed_at or now,
            outbreak_assessment=outbreak,
            linked_alert_ids=linked_alert_ids,
        )
