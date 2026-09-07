import json
from pathlib import Path

from app.constants.symptoms import SymptomCode

ROOT = Path(__file__).resolve().parents[1]
DATASET = ROOT / "evaluation" / "punjabi_rag_10_reports.json"


def test_dataset_has_10_unique_reports():
    reports = json.loads(DATASET.read_text(encoding="utf-8"))
    assert len(reports) == 10
    ids = [r["report_id"] for r in reports]
    assert len(ids) == len(set(ids))


def test_dataset_is_punjabi_and_expected_codes_are_valid():
    reports = json.loads(DATASET.read_text(encoding="utf-8"))
    for report in reports:
        assert report["language"] == "punjabi"
        assert report["crop"] in {"cotton", "rice"}
        assert report["affected_part"]
        assert report["rag_symptoms"]
        for item in report["rag_symptoms"]:
            assert item["text"].strip()
            SymptomCode(item["expected_code"])


def test_dataset_contains_unknown_case_and_multiple_parts():
    reports = json.loads(DATASET.read_text(encoding="utf-8"))
    expected = {
        item["expected_code"]
        for report in reports
        for item in report["rag_symptoms"]
    }
    parts = {r["affected_part"] for r in reports}
    assert "OTHERS_MAP" in expected
    assert {"leaves", "stem", "boll", "whole plant", "panicle", "roots"}.issubset(parts)
