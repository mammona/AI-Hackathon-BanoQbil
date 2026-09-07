from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.constants.symptoms import SYMPTOM_DICTIONARY_VERSION, SymptomCode
from app.database import Base
from app.models.schemas import Assessment, CropName, ReportLanguage
from app.services.report_service import ReportService


def session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine, expire_on_commit=False)()


def test_completed_without_image_retry_is_idempotent_and_registers_device():
    db = session()
    service = ReportService()
    calls = {"qwen": 0, "rag": 0}

    def fake_generate(_farmer):
        calls["qwen"] += 1
        return Assessment(symptoms=["پتے مڑ رہے نیں"], affected_part="leaves")

    def fake_enrich(assessment, *, crop, language):
        calls["rag"] += 1
        assessment.symptom_codes = [SymptomCode.LEAF_CURLING]
        assessment.symptom_mapping = []
        assessment.symptom_dictionary_version = SYMPTOM_DICTIONARY_VERSION
        return assessment

    service.qwen.generate = fake_generate
    service.symptom_rag.enrich_assessment = fake_enrich

    kwargs = dict(
        report_id="IDEM-NO-IMAGE-001",
        device_id="PHONE-IDEM-001",
        selected_crop=CropName.cotton,
        language=ReportLanguage.punjabi,
        answer_1="پتے مڑ رہے نیں",
        answer_2="",
        answer_3="",
        answer_4="",
        latitude=31.5204,
        longitude=74.3587,
        timestamp=None,
        image_bytes=None,
    )

    first = service.process(db, **kwargs)
    second = service.process(db, **kwargs)

    assert first.status.value == "completed_without_image"
    assert second.status.value == "completed_without_image"
    assert calls == {"qwen": 1, "rag": 1}
    device = service.devices.get(db, "PHONE-IDEM-001")
    assert device is not None
    assert device.crops == ["cotton"]
