from __future__ import annotations

from collections import Counter
from datetime import datetime, timedelta, timezone
from math import asin, cos, radians, sin, sqrt
import logging
from uuid import uuid4

from sqlalchemy.orm import Session

from app.config import get_settings
from app.models.database_models import Alert, Report
from app.models.schemas import AlertLevel, OutbreakAssessment
from app.repositories.alert_repository import AlertRepository
from app.repositories.report_repository import ReportRepository
from app.services.disease_symptom_consistency import DiseaseSymptomConsistencyService

logger = logging.getLogger(__name__)


class OutbreakService:
    """Deterministic geo-temporal outbreak signal engine.

    Qwen is deliberately not used here. The engine operates only on structured,
    stored report evidence so the alert decision is explainable and repeatable.
    """

    def __init__(self) -> None:
        self.settings = get_settings()
        self.reports = ReportRepository()
        self.alerts = AlertRepository()
        self.consistency = DiseaseSymptomConsistencyService()

    @staticmethod
    def _aware(value: datetime) -> datetime:
        if value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc)
        return value.astimezone(timezone.utc)

    @staticmethod
    def distance_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        r = 6371.0088
        p1, p2 = radians(lat1), radians(lat2)
        dphi = radians(lat2 - lat1)
        dlambda = radians(lon2 - lon1)
        a = sin(dphi / 2) ** 2 + cos(p1) * cos(p2) * sin(dlambda / 2) ** 2
        return 2 * r * asin(sqrt(min(1.0, a)))

    @staticmethod
    def _canonical_codes(report: Report) -> set[str]:
        return {
            str(code)
            for code in (report.symptom_codes or [])
            if str(code) and str(code) != "OTHERS_MAP"
        }

    @staticmethod
    def _usable_disease(report: Report) -> str | None:
        if not report.image_evidence_available:
            return None
        disease = (report.disease or "").strip().lower()
        if not disease or disease == "healthy":
            return None
        return disease

    def _evidence_related(self, a: Report, b: Report) -> bool:
        disease_a = self._usable_disease(a)
        disease_b = self._usable_disease(b)
        disease_match = bool(disease_a and disease_b and disease_a == disease_b)

        codes_a = self._canonical_codes(a)
        codes_b = self._canonical_codes(b)
        symptom_match = bool(codes_a & codes_b)

        # Cross-modal correlation: an image-supported disease report can link to
        # a symptom-only report when the symptom is deterministically compatible
        # with that disease. This is what lets a live curl_virus report join the
        # pre-seeded LEAF_CURLING cluster without requiring every old report to
        # have an image diagnosis.
        disease_a_supports_b = bool(
            disease_a
            and self.consistency.disease_supports_symptoms(
                crop=a.selected_crop, disease=disease_a, symptom_codes=codes_b
            )
        )
        disease_b_supports_a = bool(
            disease_b
            and self.consistency.disease_supports_symptoms(
                crop=b.selected_crop, disease=disease_b, symptom_codes=codes_a
            )
        )
        return disease_match or symptom_match or disease_a_supports_b or disease_b_supports_a

    def _pair_related(self, a: Report, b: Report) -> bool:
        if a.selected_crop != b.selected_crop:
            return False
        if not (a.location_available and b.location_available):
            return False
        if self.distance_km(a.latitude, a.longitude, b.latitude, b.longitude) > self.settings.outbreak_radius_km:
            return False
        delta = abs((self._aware(a.reported_at) - self._aware(b.reported_at)).total_seconds())
        if delta > self.settings.outbreak_time_window_days * 86400:
            return False
        return self._evidence_related(a, b)

    def _component_from(self, current: Report, candidates: list[Report]) -> list[Report]:
        by_id = {r.report_id: r for r in candidates}
        by_id[current.report_id] = current
        rows = list(by_id.values())

        visited = {current.report_id}
        queue = [current]
        while queue:
            node = queue.pop(0)
            for other in rows:
                if other.report_id in visited:
                    continue
                if self._pair_related(node, other):
                    visited.add(other.report_id)
                    queue.append(other)
        return [by_id[report_id] for report_id in visited]

    @staticmethod
    def _primary_disease(rows: list[Report]) -> str | None:
        values = [
            (r.disease or "").strip().lower()
            for r in rows
            if r.image_evidence_available and (r.disease or "").strip().lower() not in {"", "healthy"}
        ]
        return Counter(values).most_common(1)[0][0] if values else None

    @staticmethod
    def _primary_symptoms(rows: list[Report]) -> list[str]:
        counts: Counter[str] = Counter()
        for row in rows:
            for code in row.symptom_codes or []:
                code = str(code)
                if code and code != "OTHERS_MAP":
                    counts[code] += 1
        return [code for code, _ in counts.most_common()]

    def _level(self, rows: list[Report]) -> AlertLevel:
        count = len(rows)
        if count < self.settings.outbreak_monitoring_min_reports:
            return AlertLevel.NO_ALERT

        image_supported = any(r.image_evidence_available for r in rows)
        symptom_only = all(r.evidence_mode == "SYMPTOM_ONLY" for r in rows)

        if image_supported and count >= self.settings.outbreak_amber_min_reports_with_image:
            return AlertLevel.AMBER
        if symptom_only and count >= self.settings.outbreak_amber_min_symptom_only_reports:
            return AlertLevel.AMBER
        return AlertLevel.MONITORING

    def _upsert_alert(self, db: Session, rows: list[Report], level: AlertLevel) -> Alert:
        report_ids = sorted(r.report_id for r in rows)
        existing = self.alerts.find_by_report_overlap(
            db,
            crop=rows[0].selected_crop,
            report_ids=report_ids,
        )

        latitudes = [r.latitude for r in rows]
        longitudes = [r.longitude for r in rows]
        center_lat = sum(latitudes) / len(latitudes)
        center_lon = sum(longitudes) / len(longitudes)

        if existing is None:
            existing = Alert(
                alert_id=f"ALT-{uuid4().hex[:10].upper()}",
                crop=rows[0].selected_crop,
                primary_disease=self._primary_disease(rows),
                primary_symptom_codes=self._primary_symptoms(rows),
                center_latitude=center_lat,
                center_longitude=center_lon,
                radius_km=self.settings.outbreak_radius_km,
                report_count=len(rows),
                alert_level=level.value,
                status="pending_verification" if level == AlertLevel.AMBER else "active",
            )
            self.alerts.save(db, existing)
        else:
            # A confirmed RED signal must never be automatically downgraded.
            if existing.alert_level != AlertLevel.RED.value:
                existing.alert_level = level.value
                existing.status = "pending_verification" if level == AlertLevel.AMBER else "active"
            existing.primary_disease = self._primary_disease(rows)
            existing.primary_symptom_codes = self._primary_symptoms(rows)
            existing.center_latitude = center_lat
            existing.center_longitude = center_lon
            existing.radius_km = self.settings.outbreak_radius_km
            existing.report_count = len(rows)
            self.alerts.update(db, existing)

        self.alerts.sync_report_links(
            db,
            alert_id=existing.alert_id,
            report_ids=report_ids,
            preserve_existing=existing.alert_level == AlertLevel.RED.value,
        )
        return existing

    def _assessment_for_candidates(
        self,
        db: Session,
        report: Report,
        candidates: list[Report],
    ) -> OutbreakAssessment:
        component = self._component_from(report, candidates)
        level = self._level(component)

        if level == AlertLevel.NO_ALERT:
            return OutbreakAssessment(
                evaluated=True,
                related_report_count=len(component),
                radius_km=self.settings.outbreak_radius_km,
                time_window_days=self.settings.outbreak_time_window_days,
                alert_level=level,
                alert_id=None,
                reason="No local outbreak signal yet.",
            )

        alert = self._upsert_alert(db, component, level)
        return OutbreakAssessment(
            evaluated=True,
            related_report_count=len(component),
            radius_km=self.settings.outbreak_radius_km,
            time_window_days=self.settings.outbreak_time_window_days,
            alert_level=AlertLevel(alert.alert_level),
            alert_id=alert.alert_id,
            reason="Related reports were found using crop, evidence, distance, and time-window rules.",
        )

    def assessment_after_expert_review(self, db: Session, report: Report) -> OutbreakAssessment:
        """Re-evaluate a validated report against both earlier and later nearby reports.

        Normal ingestion only looks backward in time. Expert review can happen later,
        so this method searches the full +/- configured time window around the report.
        """
        if not report.usable_for_outbreak:
            return OutbreakAssessment(
                evaluated=False,
                related_report_count=0,
                radius_km=self.settings.outbreak_radius_km,
                time_window_days=self.settings.outbreak_time_window_days,
                reason="Expert-reviewed report is not usable outbreak evidence.",
            )
        if not report.location_available:
            return OutbreakAssessment(
                evaluated=False,
                related_report_count=0,
                radius_km=self.settings.outbreak_radius_km,
                time_window_days=self.settings.outbreak_time_window_days,
                reason="Location is missing, so geographic outbreak detection was skipped.",
            )

        reported = self._aware(report.reported_at)
        window = timedelta(days=self.settings.outbreak_time_window_days)
        candidates = self.reports.usable_for_crop_between(
            db, crop=report.selected_crop, start_at=reported-window, end_at=reported+window
        )
        return self._assessment_for_candidates(db, report, candidates)

    def recalculate_alert(self, db: Session, alert_id: str) -> Alert | None:
        """Recalculate a non-RED signal after a report is invalidated/followed-up."""
        alert = self.alerts.get(db, alert_id)
        if alert is None or (alert.alert_level == AlertLevel.RED.value and alert.status == "confirmed"):
            return alert

        ids = self.alerts.linked_report_ids(db, alert_id)
        rows = [
            r for r in self.reports.get_many(db, ids)
            if r.usable_for_outbreak and r.location_available and r.expert_review_status != "INVALID"
        ]
        if not rows:
            alert.report_count = 0
            alert.status = "closed"
            self.alerts.update(db, alert)
            self.alerts.sync_report_links(db, alert_id=alert_id, report_ids=[])
            return alert

        # Keep only the connected component around the first remaining report.
        rows = self._component_from(rows[0], rows)
        level = self._level(rows)
        if level == AlertLevel.NO_ALERT:
            alert.report_count = len(rows)
            alert.primary_disease = self._primary_disease(rows)
            alert.primary_symptom_codes = self._primary_symptoms(rows)
            alert.center_latitude = sum(r.latitude for r in rows) / len(rows)
            alert.center_longitude = sum(r.longitude for r in rows) / len(rows)
            alert.status = "closed"
            self.alerts.update(db, alert)
            self.alerts.sync_report_links(db, alert_id=alert_id, report_ids=[r.report_id for r in rows])
            return alert

        return self._upsert_alert(db, rows, level)

    def assessment_for_stored_report(self, db: Session, report: Report) -> OutbreakAssessment:
        if not report.usable_for_outbreak:
            return OutbreakAssessment(
                evaluated=False,
                related_report_count=0,
                radius_km=self.settings.outbreak_radius_km,
                time_window_days=self.settings.outbreak_time_window_days,
                reason="Report is stored but does not contain usable canonical outbreak evidence.",
            )
        if not report.location_available:
            return OutbreakAssessment(
                evaluated=False,
                related_report_count=0,
                radius_km=self.settings.outbreak_radius_km,
                time_window_days=self.settings.outbreak_time_window_days,
                reason="Location is missing, so geographic outbreak detection was skipped.",
            )

        reported = self._aware(report.reported_at)
        start = reported - timedelta(days=self.settings.outbreak_time_window_days)
        candidates = self.reports.usable_for_crop_between(
            db,
            crop=report.selected_crop,
            start_at=start,
            end_at=reported,
        )
        component = self._component_from(report, candidates)
        level = self._level(component)

        if level == AlertLevel.NO_ALERT:
            logger.info(
                "[OUTBREAK] report=%s related=%s level=%s",
                report.report_id,
                len(component),
                level.value,
            )
            return OutbreakAssessment(
                evaluated=True,
                related_report_count=len(component),
                radius_km=self.settings.outbreak_radius_km,
                time_window_days=self.settings.outbreak_time_window_days,
                alert_level=level,
                alert_id=None,
                reason="No local outbreak signal yet.",
            )

        alert = self._upsert_alert(db, component, level)
        final_level = AlertLevel(alert.alert_level)
        logger.info(
            "[OUTBREAK] report=%s related=%s level=%s alert=%s",
            report.report_id,
            len(component),
            final_level.value,
            alert.alert_id,
        )
        return OutbreakAssessment(
            evaluated=True,
            related_report_count=len(component),
            radius_km=self.settings.outbreak_radius_km,
            time_window_days=self.settings.outbreak_time_window_days,
            alert_level=final_level,
            alert_id=alert.alert_id,
            reason="Related reports were found using crop, evidence, distance, and time-window rules.",
        )
