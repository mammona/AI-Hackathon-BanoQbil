import json
import logging

from app.constants.plant_parts import validate_affected_part
from app.models.schemas import FarmerInput
from app.services.qwen_report_service import QwenReportService
from app.services.symptom_rag_service import SymptomRAGService


logging.basicConfig(level=logging.WARNING)

farmer = FarmerInput(
    language="urdu",
    symptoms_raw="پتے پیلے ہو رہے ہیں اور مڑ رہے ہیں",
    onset_raw="تین دن پہلے شروع ہوا",
    affected_extent_raw="تقریباً آدھا ایکڑ متاثر ہے",
    spread_raw="ہاں مسئلہ پھیل رہا ہے",
)

assessment = QwenReportService().generate(farmer)
assessment.affected_part = validate_affected_part(
    farmer.symptoms_raw,
    assessment.affected_part,
)
assessment = SymptomRAGService().enrich_assessment(
    assessment,
    crop="cotton",
    language=farmer.language.value,
)

print("\n===== FINAL FARMER ASSESSMENT =====")
print(json.dumps(assessment.model_dump(mode="json"), ensure_ascii=False, indent=2))
