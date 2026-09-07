"""Verify the expected database state after seed_e2e_demo_reports."""
from __future__ import annotations

from sqlalchemy import func, select

from app.database import SessionLocal
from app.models.database_models import Alert, AlertReport, Report


def main() -> None:
    with SessionLocal() as db:
        report_count = int(
            db.scalar(select(func.count(Report.id)).where(Report.report_id.like("E2E-%"))) or 0
        )
        demo_alerts = list(
            db.scalars(
                select(Alert)
                .join(AlertReport, AlertReport.alert_id == Alert.alert_id)
                .join(Report, Report.report_id == AlertReport.report_id)
                .where(Report.report_id.like("E2E-%"))
                .distinct()
                .order_by(Alert.created_at.asc())
            ).all()
        )

        print(f"Demo reports: {report_count}/15")
        for alert in demo_alerts:
            ids = list(
                db.scalars(
                    select(AlertReport.report_id)
                    .where(AlertReport.alert_id == alert.alert_id)
                    .order_by(AlertReport.report_id)
                ).all()
            )
            print(
                f"{alert.alert_id}: crop={alert.crop}, level={alert.alert_level}, "
                f"report_count={alert.report_count}, reports={ids}"
            )

        levels = sorted((a.crop, a.alert_level, a.report_count) for a in demo_alerts)
        expected = sorted([
            ("cotton", "AMBER", 3),
            ("cotton", "AMBER", 4),
            ("rice", "MONITORING", 2),
        ])

        if report_count != 15:
            raise SystemExit("FAIL: database does not contain exactly 15 E2E reports")
        if levels != expected:
            raise SystemExit(f"FAIL: expected alert signatures {expected}, got {levels}")

        print("PASS: database contains the expected 15 reports and 3 outbreak signals.")


if __name__ == "__main__":
    main()
