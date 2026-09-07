from io import BytesIO
from types import SimpleNamespace

from PIL import Image

from app.models.schemas import CropName, DiseasePrediction, ImageStatus, ReportLanguage
from app.services.report_service import ReportService


def make_image_bytes() -> bytes:
    img = Image.new("RGB", (256, 256), (120, 150, 90))
    buf = BytesIO()
    img.save(buf, format="JPEG")
    return buf.getvalue()


def test_selected_crop_is_disease_router(monkeypatch):
    service = ReportService()
    called = []

    def fake_predict(crop, image):
        called.append(crop)
        return DiseasePrediction(
            disease="healthy" if crop == "cotton" else "blast",
            confidence=0.95,
            confidence_level="high",
            low_confidence=False,
            healthy_class_supported=(crop == "cotton"),
        )

    monkeypatch.setattr(service.disease_service, "predict", fake_predict)
    validation = service.image_validator.validate(make_image_bytes())
    assert validation.ok is True
    assert validation.image is not None

    service.disease_service.predict(CropName.cotton.value, validation.image)
    service.disease_service.predict(CropName.rice.value, validation.image)
    assert called == ["cotton", "rice"]


def test_no_siglip_crop_validator_on_report_service():
    service = ReportService()
    assert not hasattr(service, "crop_validator")


def test_missing_image_status_supported():
    from app.models.schemas import ImageAssessment
    result = ImageAssessment(status=ImageStatus.not_submitted)
    assert result.status == ImageStatus.not_submitted
