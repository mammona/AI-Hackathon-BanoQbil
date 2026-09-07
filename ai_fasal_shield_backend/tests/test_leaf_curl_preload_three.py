import json
from pathlib import Path


def test_leaf_curl_preload_contains_exactly_three_reports():
    root = Path(__file__).resolve().parents[1]
    data = json.loads((root / "data" / "leaf_curl_2km_demo_reports.json").read_text(encoding="utf-8"))
    reports = data["reports"]
    assert len(reports) == 3
    assert [r["expected_alert_level"] for r in reports] == ["NO_ALERT", "MONITORING", "MONITORING"]
    assert all(r["symptom_codes"] == ["LEAF_CURLING"] for r in reports)
