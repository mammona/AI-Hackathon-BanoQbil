from datetime import datetime, timezone

from fastapi.testclient import TestClient

from app.api import reports as reports_api
from app.main import app
from app.models.schemas import (
    Assessment,
    CropName,
    EvidenceAssessment,
    EvidenceMode,
    EvidenceStrength,
    FarmerInput,
    ImageAssessment,
    ImageStatus,
    Location,
    OutbreakAssessment,
    ReportLanguage,
    ReportStatus,
    StructuredReport,
)


def _stub_report(report_id: str, crop: CropName, language: ReportLanguage) -> StructuredReport:
    return StructuredReport(
        report_id=report_id,
        crop=crop,
        image_assessment=ImageAssessment(status=ImageStatus.not_submitted),
        disease_prediction=None,
        farmer_input=FarmerInput(language=language, symptoms_raw="پتے مڑ رہے نیں"),
        assessment=Assessment(symptoms=["پتے مڑ رہے نیں"]),
        summary="stub",
        recommended_next_step="stub",
        requires_expert_review=False,
        location=Location(latitude=31.52, longitude=74.35),
        timestamp=datetime.now(timezone.utc),
        status=ReportStatus.completed_without_image,
        evidence=EvidenceAssessment(
            evidence_mode=EvidenceMode.SYMPTOM_ONLY,
            evidence_strength=EvidenceStrength.MEDIUM,
            image_evidence_available=False,
            symptom_evidence_available=True,
            canonical_symptom_evidence_available=True,
            usable_for_outbreak=True,
            needs_expert_review=False,
            reason="stub",
        ),
        outbreak_assessment=OutbreakAssessment(evaluated=True, related_report_count=1),
    )


def test_openapi_does_not_require_image():
    schema = app.openapi()
    op = schema["paths"]["/api/v1/reports/process"]["post"]
    body_schema = op["requestBody"]["content"]["multipart/form-data"]["schema"]
    ref = body_schema.get("$ref")
    if ref:
        name = ref.rsplit("/", 1)[-1]
        body_schema = schema["components"]["schemas"][name]
    assert "image" not in body_schema.get("required", [])


def test_symptom_only_request_reaches_service_without_image(monkeypatch):
    def fake_process(db, **kwargs):
        assert kwargs["image_bytes"] is None
        assert kwargs["answer_1"] == "پتے مڑ رہے نیں"
        return _stub_report(kwargs["report_id"], kwargs["selected_crop"], kwargs["language"])

    monkeypatch.setattr(reports_api.service, "process", fake_process)
    client = TestClient(app)
    response = client.post(
        "/api/v1/reports/process",
        data={
            "report_id": "NO-IMAGE-001",
            "selected_crop": "cotton",
            "language": "punjabi",
            "answer_1": "پتے مڑ رہے نیں",
            "answer_2": "",
            "answer_3": "",
            "answer_4": "",
            "latitude": "31.52",
            "longitude": "74.35",
        },
    )
    assert response.status_code == 200, response.text
    assert response.json()["image_assessment"]["status"] == "not_submitted"


def test_completely_empty_evidence_is_rejected_without_image():
    client = TestClient(app)
    response = client.post(
        "/api/v1/reports/process",
        data={
            "report_id": "EMPTY-001",
            "selected_crop": "cotton",
            "language": "punjabi",
            "answer_1": "",
            "answer_2": "",
            "answer_3": "",
            "answer_4": "",
        },
    )
    assert response.status_code == 422
    assert "image or at least one farmer answer" in response.json()["detail"]


def test_empty_file_control_is_treated_as_no_image(monkeypatch):
    def fake_process(db, **kwargs):
        assert kwargs["image_bytes"] is None
        assert kwargs["answer_1"] == "پتے مڑ رہے نیں"
        return _stub_report(kwargs["report_id"], kwargs["selected_crop"], kwargs["language"])

    monkeypatch.setattr(reports_api.service, "process", fake_process)
    client = TestClient(app)
    response = client.post(
        "/api/v1/reports/process",
        data={
            "report_id": "EMPTY-FILE-CONTROL-001",
            "selected_crop": "cotton",
            "language": "punjabi",
            "answer_1": "پتے مڑ رہے نیں",
            "answer_2": "",
            "answer_3": "",
            "answer_4": "",
            "latitude": "31.52",
            "longitude": "74.35",
        },
        files={"image": ("", b"", "application/octet-stream")},
    )
    assert response.status_code == 200, response.text
    assert response.json()["image_assessment"]["status"] == "not_submitted"
