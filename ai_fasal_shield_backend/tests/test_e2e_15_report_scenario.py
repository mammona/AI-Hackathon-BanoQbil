from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import sessionmaker

from app.database import Base
from app.models.database_models import Alert, Report
from app.services.outbreak_service import OutbreakService

ROOT = Path(__file__).resolve().parents[1]
ITEMS = json.loads((ROOT / "data" / "e2e_demo_reports.json").read_text(encoding="utf-8"))


def _session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine, expire_on_commit=False)()


def _row(item: dict, base: datetime) -> Report:
    when = base + timedelta(days=item.get("days_offset", 0), minutes=item.get("minutes_offset", 0))
    codes = list(item.get("symptom_codes") or [])
    symptoms = list(item.get("symptoms") or [])
    image_submitted = bool(item.get("image_submitted", False))
    disease = item.get("disease")
    return Report(
        report_id=item["report_id"],
        selected_crop=item["selected_crop"],
        language=item.get("language", "punjabi"),
        image_status="validated" if image_submitted else "not_submitted",
        image_submitted=image_submitted,
        disease=disease,
        disease_confidence=item.get("disease_confidence"),
        disease_confidence_level="high" if disease else None,
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
        image_evidence_available=bool(item.get("image_evidence_available", False)),
        symptom_evidence_available=bool(symptoms or codes),
        canonical_symptom_evidence_available=any(c != "OTHERS_MAP" for c in codes),
        usable_for_outbreak=bool(item["usable_for_outbreak"]),
        summary="test",
        recommended_next_step="test",
        requires_expert_review=bool(item.get("requires_expert_review", False)),
        latitude=float(item.get("latitude", 0.0)),
        longitude=float(item.get("longitude", 0.0)),
        location_available=bool(item.get("location_available", True)),
        processing_status="completed" if image_submitted else "completed_without_image",
        reported_at=when,
    )


def test_full_15_report_database_and_outbreak_scenario():
    assert len(ITEMS) == 15
    db = _session()
    service = OutbreakService()
    base = datetime(2026, 9, 4, 8, 0, tzinfo=timezone.utc)

    for item in ITEMS:
        row = _row(item, base)
        db.add(row)
        db.commit()
        db.refresh(row)
        result = service.assessment_for_stored_report(db, row)
        actual_level = result.alert_level.value if result.alert_level else None
        assert actual_level == item.get("expected_alert_level"), item["report_id"]
        assert result.related_report_count == item.get("expected_related_count", 0), item["report_id"]

    assert db.scalar(select(func.count(Report.id))) == 15
    alerts = list(db.scalars(select(Alert)).all())
    signatures = sorted((a.crop, a.alert_level, a.report_count) for a in alerts)
    assert signatures == sorted([
        ("cotton", "AMBER", 3),
        ("cotton", "AMBER", 4),
        ("rice", "MONITORING", 2),
    ])


def test_seed_contains_required_edge_cases():
    scenarios = {item["scenario"] for item in ITEMS}
    assert "old_report_excluded" in scenarios
    assert "others_map_not_clustered" in scenarios
    assert "context_only_stored_not_clustered" in scenarios
    assert "outside_5km_not_clustered" in scenarios
    assert "missing_gps_stored_not_evaluated" in scenarios
    assert "healthy_cotton_not_outbreak_evidence" in scenarios
