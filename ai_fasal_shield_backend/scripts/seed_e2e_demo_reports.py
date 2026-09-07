"""Seed 15 deterministic demo reports and run the real outbreak engine.

This script intentionally seeds already-structured report evidence. It isolates
SQL + geo/time + outbreak logic from Qwen and the image models, making the
outbreak demo deterministic. For a true live Qwen path, use
scripts/run_live_symptom_e2e.py after starting FastAPI and Ollama.
"""
from __future__ import annotations

import argparse
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

from sqlalchemy import delete, func, select

from app.database import Base, SessionLocal, engine
from app.models.database_models import Alert, AlertReport, Notification, Report
from app.services.outbreak_service import OutbreakService

ROOT = Path(__file__).resolve().parents[1]
DATA_FILE = ROOT / "data" / "e2e_demo_reports.json"


def _clear_all(db) -> None:
    db.execute(delete(Notification))
    db.execute(delete(AlertReport))
    db.execute(delete(Alert))
    db.execute(delete(Report))
    db.commit()


def _clear_demo(db) -> None:
    demo_ids = list(db.scalars(select(Report.report_id).where(Report.report_id.like("E2E-%"))).all())
    if not demo_ids:
        return
    alert_ids = list(
        db.scalars(
            select(AlertReport.alert_id).where(AlertReport.report_id.in_(demo_ids)).distinct()
        ).all()
    )
    db.execute(delete(AlertReport).where(AlertReport.report_id.in_(demo_ids)))
    if alert_ids:
        db.execute(delete(AlertReport).where(AlertReport.alert_id.in_(alert_ids)))
        db.execute(delete(Alert).where(Alert.alert_id.in_(alert_ids)))
    db.execute(delete(Report).where(Report.report_id.in_(demo_ids)))
    db.commit()


def _build_report(item: dict, base_time: datetime) -> Report:
    reported_at = base_time + timedelta(
        days=int(item.get("days_offset", 0)),
        minutes=int(item.get("minutes_offset", 0)),
    )
    disease = item.get("disease")
    image_submitted = bool(item.get("image_submitted", False))
    image_evidence = bool(item.get("image_evidence_available", False))
    location_available = bool(item.get("location_available", True))
    codes = list(item.get("symptom_codes") or [])
    symptoms = list(item.get("symptoms") or [])

    return Report(
        report_id=item["report_id"],
        selected_crop=item["selected_crop"],
        language=item.get("language", "punjabi"),
        detected_crop=None,
        image_status="validated" if image_submitted else "not_submitted",
        crop_match=None,
        crop_validation_confidence=None,
        image_submitted=image_submitted,
        disease=disease,
        disease_confidence=item.get("disease_confidence"),
        disease_confidence_level="high" if disease and item.get("disease_confidence", 0) >= 0.70 else None,
        healthy_class_supported=(item["selected_crop"] == "cotton") if image_submitted else None,
        question_1_raw=item.get("question_1_raw", ""),
        question_2_raw=item.get("question_2_raw", ""),
        question_3_raw=item.get("question_3_raw", ""),
        question_4_raw=item.get("question_4_raw", ""),
        symptoms=symptoms,
        symptom_codes=codes,
        symptom_mapping=[],
        symptom_dictionary_version="demo-seed",
        affected_part="leaves" if symptoms else None,
        problem_duration="3 days" if item.get("question_2_raw") else None,
        affected_area=None,
        spread_status=None,
        evidence_mode=item["evidence_mode"],
        evidence_strength=item["evidence_strength"],
        image_evidence_available=image_evidence,
        symptom_evidence_available=bool(symptoms or codes),
        canonical_symptom_evidence_available=any(code != "OTHERS_MAP" for code in codes),
        usable_for_outbreak=bool(item["usable_for_outbreak"]),
        summary=f"Synthetic E2E demo report: {item['scenario']}",
        recommended_next_step="Use only for prototype end-to-end validation.",
        requires_expert_review=bool(item.get("requires_expert_review", False)),
        latitude=float(item.get("latitude", 0.0)),
        longitude=float(item.get("longitude", 0.0)),
        location_available=location_available,
        image_path=None,
        processing_status="completed" if image_submitted else "completed_without_image",
        reported_at=reported_at,
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--reset-all",
        action="store_true",
        help="Delete ALL reports/alerts before seeding. Recommended for an isolated demo.",
    )
    parser.add_argument(
        "--allow-existing",
        action="store_true",
        help="Allow non-E2E reports to remain. Existing nearby reports may affect expected counts.",
    )
    args = parser.parse_args()

    Base.metadata.create_all(bind=engine)
    items = json.loads(DATA_FILE.read_text(encoding="utf-8"))
    if len(items) != 15:
        raise SystemExit(f"Expected exactly 15 demo reports, found {len(items)}")

    service = OutbreakService()
    base_time = datetime.now(timezone.utc).replace(microsecond=0)

    with SessionLocal() as db:
        if args.reset_all:
            _clear_all(db)
        else:
            non_demo_count = int(
                db.scalar(select(func.count(Report.id)).where(~Report.report_id.like("E2E-%"))) or 0
            )
            if non_demo_count and not args.allow_existing:
                raise SystemExit(
                    f"Database contains {non_demo_count} non-demo reports. "
                    "Run with --reset-all for deterministic results, or --allow-existing if intentional."
                )
            _clear_demo(db)

        print("\nAI Fasal Shield - 15 report deterministic E2E seed")
        print("=" * 72)
        print(f"Base time: {base_time.isoformat()}")
        print("\n#  Report ID                   Scenario                              Actual")
        print("-" * 96)

        failures: list[str] = []
        for idx, item in enumerate(items, start=1):
            row = _build_report(item, base_time)
            db.add(row)
            db.commit()
            db.refresh(row)

            result = service.assessment_for_stored_report(db, row)
            actual_level = result.alert_level.value if result.alert_level else None
            expected_level = item.get("expected_alert_level")
            expected_count = int(item.get("expected_related_count", 0))

            level_ok = actual_level == expected_level
            count_ok = result.related_report_count == expected_count
            ok = level_ok and count_ok
            status = "PASS" if ok else "FAIL"
            print(
                f"{idx:>2}  {row.report_id:<27} {item['scenario']:<36} "
                f"{actual_level or 'SKIPPED':<11} related={result.related_report_count:<2} {status}"
            )
            if not ok:
                failures.append(
                    f"{row.report_id}: expected level={expected_level}, count={expected_count}; "
                    f"actual level={actual_level}, count={result.related_report_count}"
                )

        alerts = list(db.scalars(select(Alert).order_by(Alert.created_at.asc())).all())
        print("\nStored demo reports:", db.scalar(select(func.count(Report.id)).where(Report.report_id.like("E2E-%"))))
        print("Active alerts:", len(alerts))
        for alert in alerts:
            print(
                f"  {alert.alert_id} crop={alert.crop} level={alert.alert_level} "
                f"reports={alert.report_count} disease={alert.primary_disease} "
                f"symptoms={alert.primary_symptom_codes}"
            )

        if failures:
            print("\nFAILURES")
            for failure in failures:
                print(" -", failure)
            raise SystemExit(1)

        print("\nAll 15 deterministic report expectations passed.")
        print("Next: python -m scripts.check_e2e_demo")


if __name__ == "__main__":
    main()
