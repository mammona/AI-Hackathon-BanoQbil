from datetime import datetime, timezone
import logging

from sqlalchemy.orm import Session

from app.config import get_settings
from app.constants.plant_parts import validate_affected_part
from app.constants.symptoms import SYMPTOM_DICTIONARY_VERSION, SymptomCode
from app.models.database_models import Report
from app.models.schemas import (
    Assessment,
    CropName,
    DiseasePrediction,
    EvidenceAssessment,
    EvidenceMode,
    EvidenceStrength,
    ExpertReviewStatus,
    FarmerInput,
    ImageAssessment,
    ImageStatus,
    Location,
    OutbreakAssessment,
    ReportLanguage,
    ReportStatus,
    StructuredReport,
    SymptomMappingItem,
)
from app.repositories.report_repository import ReportRepository
from app.repositories.device_repository import DeviceRepository
from app.services.disease_model_service import DiseaseModelService, DiseaseModelUnavailable
from app.services.disease_symptom_consistency import DiseaseSymptomConsistencyService, ConsistencyStatus
from app.services.image_validator import ImageValidator
from app.services.outbreak_service import OutbreakService
from app.services.qwen_report_service import QwenReportService, QwenUnavailable
from app.services.symptom_rag_service import SymptomRAGService
from app.utils.files import save_report_image

logger = logging.getLogger(__name__)


class ReportService:
    def __init__(self) -> None:
        self.settings = get_settings()
        self.image_validator = ImageValidator()
        self.disease_service = DiseaseModelService()
        self.disease_symptom_consistency = DiseaseSymptomConsistencyService()
        self.qwen = QwenReportService()
        self.symptom_rag = SymptomRAGService()
        self.outbreak = OutbreakService()
        self.repo = ReportRepository()
        self.devices = DeviceRepository()

    @staticmethod
    def _final_status(
        image: ImageAssessment,
        disease: DiseasePrediction | None,
        disease_error: bool,
        qwen_error: bool,
        *,
        has_farmer_input: bool,
    ) -> ReportStatus:
        if image.status == ImageStatus.not_submitted:
            return ReportStatus.processing_failed if qwen_error else ReportStatus.completed_without_image

        if image.status != ImageStatus.validated:
            if qwen_error and not has_farmer_input:
                return ReportStatus.processing_failed
            return ReportStatus.completed_with_unverified_image

        if disease_error or disease is None:
            if has_farmer_input:
                return ReportStatus.completed_with_unverified_image
            return ReportStatus.processing_failed

        if disease.low_confidence:
            return ReportStatus.disease_low_confidence
        return ReportStatus.completed

    @staticmethod
    def _build_summary(
        crop: CropName,
        assessment: Assessment,
        image: ImageAssessment,
        disease: DiseasePrediction | None,
        qwen_error: bool,
    ) -> str:
        if qwen_error:
            return (
                "Farmer report received, but the farmer answers could not be "
                "normalized automatically. Manual review is required."
            )

        sentences: list[str] = []
        if assessment.symptoms:
            sentences.append(f"The farmer reports {', '.join(assessment.symptoms)} in {crop.value}.")
        if assessment.affected_part:
            sentences.append(f"Affected plant part: {assessment.affected_part}.")
        if assessment.problem_duration:
            duration = assessment.problem_duration.strip()
            sentences.append(
                f"The problem was first noticed {duration}."
                if duration.lower().endswith("ago")
                else f"The problem was first noticed {duration} ago."
            )
        if assessment.affected_area:
            sentences.append(f"Reported affected extent: {assessment.affected_area}.")
        if assessment.spread_status:
            sentences.append(f"Reported spread status: {assessment.spread_status}.")

        if image.status == ImageStatus.not_submitted:
            sentences.append("No crop image was submitted.")
        elif image.status != ImageStatus.validated:
            sentences.append("The submitted image could not pass basic image validation.")
        elif disease is not None:
            sentences.append(
                f"Image model prediction: {disease.disease} ({disease.confidence:.0%} confidence)."
            )
            if not disease.healthy_class_supported:
                sentences.append(
                    "This crop classifier has no healthy class, so the image result is supporting disease evidence rather than a complete healthy-vs-disease diagnosis."
                )

        return " ".join(sentences) if sentences else "Farmer report received; no structured farmer details could be extracted."

    @staticmethod
    def _build_recommendation(
        image: ImageAssessment,
        disease: DiseasePrediction | None,
        qwen_error: bool,
    ) -> str:
        if image.status == ImageStatus.not_submitted:
            if qwen_error:
                return "Store the report for manual review because no image was submitted and farmer-answer normalization failed."
            return "Continue with farmer-reported evidence; image evidence is not available for this report."
        if image.status == ImageStatus.invalid_image:
            return "Keep the farmer report, but request a valid crop image if image-based disease evidence is needed."
        if disease is None:
            return "Keep the farmer report and request expert review because image disease inference was unavailable."
        if disease.low_confidence:
            return "Use the image prediction as uncertain evidence and request expert verification before disease-specific action."
        if disease.disease.strip().lower() == "healthy":
            return "The image model returned healthy; keep the report but do not use the healthy prediction as outbreak evidence."
        if not disease.healthy_class_supported:
            return (
                "Use this rice image prediction as supporting evidence and combine it with farmer symptoms or expert verification because the current rice model has no healthy class."
            )
        return "Use the image-model result together with farmer evidence and field/expert verification before treatment decisions."

    def _evidence(
        self,
        *,
        crop: CropName = CropName.cotton,
        disease: DiseasePrediction | None,
        assessment: Assessment,
        image_assessment: ImageAssessment,
        has_farmer_input: bool,
        qwen_error: bool,
        mapping_error: bool,
    ) -> EvidenceAssessment:
        symptom_codes = [
            code.value if isinstance(code, SymptomCode) else str(code)
            for code in assessment.symptom_codes
        ]
        symptom_evidence_available = bool(assessment.symptoms or symptom_codes)
        canonical_codes = [code for code in symptom_codes if code != SymptomCode.OTHERS_MAP.value]
        canonical_available = bool(canonical_codes)

        image_prediction_reliable = bool(
            image_assessment.status == ImageStatus.validated
            and disease is not None
            and not disease.low_confidence
            and disease.confidence >= self.settings.disease_threshold
        )
        image_is_healthy = bool(
            disease is not None and disease.disease.strip().lower() == "healthy"
        )
        # A confident healthy result is useful report context, but is not disease-outbreak evidence.
        image_evidence_available = image_prediction_reliable and not image_is_healthy

        if image_evidence_available and canonical_available:
            mode = EvidenceMode.MULTIMODAL
            strength = EvidenceStrength.STRONG
            usable = True
            reason = "Reliable image disease evidence and canonical farmer symptom evidence are both available."
        elif image_evidence_available:
            mode = EvidenceMode.IMAGE_ONLY
            strength = EvidenceStrength.MEDIUM
            usable = True
            reason = "Reliable image disease evidence is available; canonical farmer symptom evidence is not available."
        elif canonical_available:
            mode = EvidenceMode.SYMPTOM_ONLY
            strength = EvidenceStrength.MEDIUM
            usable = True
            reason = "Canonical farmer symptom evidence is available; reliable disease image evidence is not available."
        else:
            mode = EvidenceMode.CONTEXT_ONLY
            strength = EvidenceStrength.LOW
            usable = False
            if image_is_healthy and not has_farmer_input:
                reason = "The image model returned healthy, which is stored but is not outbreak evidence."
            elif symptom_codes and set(symptom_codes) == {SymptomCode.OTHERS_MAP.value}:
                reason = "Only OTHERS_MAP symptom evidence is available; it is stored but not used for automatic clustering."
            else:
                reason = "The report is valid but lacks reliable disease or canonical symptom evidence for automatic outbreak matching."

        consistency = self.disease_symptom_consistency.assess(
            crop=crop.value,
            disease=disease.disease if disease else None,
            symptom_codes=symptom_codes,
            image_evidence_available=image_evidence_available,
        )

        # Multimodal safety rule: when both reliable image disease evidence and
        # canonical symptom evidence exist, they must agree with the deterministic
        # disease-symptom profile. A mismatch is stored but held for expert review.
        consistency_requires_review = consistency.status == ConsistencyStatus.INCONSISTENT

        needs_review = bool(
            qwen_error
            or mapping_error
            or any(code == SymptomCode.OTHERS_MAP.value for code in symptom_codes)
            or (image_assessment.status == ImageStatus.invalid_image)
            or (image_assessment.status == ImageStatus.validated and disease is None)
            or (disease is not None and disease.low_confidence)
            or (disease is not None and not disease.healthy_class_supported)
            or (image_is_healthy and canonical_available)
            or (mode == EvidenceMode.CONTEXT_ONLY and not image_is_healthy)
            or consistency_requires_review
        )

        if consistency.status == ConsistencyStatus.CONSISTENT:
            reason = f"{reason} Disease-symptom consistency check passed."
        elif consistency.status == ConsistencyStatus.INCONSISTENT:
            reason = f"{reason} Disease-symptom consistency check failed; expert review is required."

        return EvidenceAssessment(
            evidence_mode=mode,
            evidence_strength=strength,
            image_evidence_available=image_evidence_available,
            symptom_evidence_available=symptom_evidence_available,
            canonical_symptom_evidence_available=canonical_available,
            usable_for_outbreak=usable,
            needs_expert_review=needs_review,
            disease_symptom_consistency=consistency.status.value,
            disease_symptom_consistency_reason=consistency.reason,
            reason=reason,
        )

    def _db_to_structured(
        self,
        row: Report,
        outbreak_assessment: OutbreakAssessment | None = None,
    ) -> StructuredReport:
        disease = None
        if row.disease is not None and row.disease_confidence is not None:
            healthy_supported = row.healthy_class_supported
            if healthy_supported is None:
                try:
                    healthy_supported = self.disease_service.has_healthy_class(row.selected_crop)
                except Exception:
                    healthy_supported = row.selected_crop == "cotton"
            disease = DiseasePrediction(
                disease=row.disease,
                confidence=row.disease_confidence,
                confidence_level=row.disease_confidence_level or "low",
                verified_by_image=row.image_status == "validated",
                low_confidence=row.processing_status == "disease_low_confidence",
                healthy_class_supported=bool(healthy_supported),
            )

        location_available = getattr(row, "location_available", True)
        stored_consistency = self.disease_symptom_consistency.assess(
            crop=row.selected_crop,
            disease=row.disease,
            symptom_codes=list(row.symptom_codes or []),
            image_evidence_available=bool(getattr(row, "image_evidence_available", False)),
        )
        evidence = EvidenceAssessment(
            evidence_mode=EvidenceMode(getattr(row, "evidence_mode", "CONTEXT_ONLY")),
            evidence_strength=EvidenceStrength(getattr(row, "evidence_strength", "LOW")),
            image_evidence_available=bool(getattr(row, "image_evidence_available", False)),
            symptom_evidence_available=bool(getattr(row, "symptom_evidence_available", bool(row.symptoms))),
            canonical_symptom_evidence_available=bool(
                getattr(
                    row,
                    "canonical_symptom_evidence_available",
                    any(code != "OTHERS_MAP" for code in (row.symptom_codes or [])),
                )
            ),
            usable_for_outbreak=bool(getattr(row, "usable_for_outbreak", False)),
            needs_expert_review=row.requires_expert_review,
            disease_symptom_consistency=stored_consistency.status.value,
            disease_symptom_consistency_reason=stored_consistency.reason,
            reason="Stored report evidence metadata.",
        )

        if outbreak_assessment is None:
            outbreak_assessment = OutbreakAssessment(
                evaluated=False,
                related_report_count=0,
                radius_km=self.settings.outbreak_radius_km,
                time_window_days=self.settings.outbreak_time_window_days,
                reason="Outbreak state is evaluated when the report is processed; use /alerts for active cluster state.",
            )

        return StructuredReport(
            report_id=row.report_id,
            device_id=getattr(row, "device_id", None),
            crop=CropName(row.selected_crop),
            image_assessment=ImageAssessment(
                status=ImageStatus(row.image_status),
                detected_crop=row.detected_crop,
                matches_selected_crop=row.crop_match,
                confidence=row.crop_validation_confidence,
            ),
            disease_prediction=disease,
            farmer_input=FarmerInput(
                language=ReportLanguage(row.language or "urdu"),
                symptoms_raw=row.question_1_raw or "",
                onset_raw=row.question_2_raw or "",
                affected_extent_raw=row.question_3_raw or "",
                spread_raw=row.question_4_raw or "",
            ),
            assessment=Assessment(
                symptoms=row.symptoms or [],
                symptom_codes=row.symptom_codes or [],
                symptom_mapping=row.symptom_mapping or [],
                symptom_dictionary_version=row.symptom_dictionary_version,
                affected_part=row.affected_part,
                problem_duration=row.problem_duration,
                affected_area=row.affected_area,
                spread_status=row.spread_status,
            ),
            summary=row.summary,
            recommended_next_step=row.recommended_next_step,
            requires_expert_review=row.requires_expert_review,
            expert_review_status=ExpertReviewStatus(getattr(row, "expert_review_status", "PENDING")),
            reviewed_by=getattr(row, "reviewed_by", None),
            review_note=getattr(row, "review_note", None),
            reviewed_at=getattr(row, "reviewed_at", None),
            location=Location(
                latitude=row.latitude if location_available else None,
                longitude=row.longitude if location_available else None,
            ),
            timestamp=row.reported_at,
            status=ReportStatus(row.processing_status),
            evidence=evidence,
            outbreak_assessment=outbreak_assessment,
        )

    def process(
        self,
        db: Session,
        *,
        report_id: str,
        selected_crop: CropName,
        language: ReportLanguage,
        answer_1: str,
        answer_2: str,
        answer_3: str,
        answer_4: str,
        latitude: float | None,
        longitude: float | None,
        timestamp: datetime | None,
        image_bytes: bytes | None,
        device_id: str | None = None,
    ) -> StructuredReport:
        existing = self.repo.get(db, report_id)

        # Assign server UTC time only when the mobile report omitted timestamp.
        timestamp = timestamp or datetime.now(timezone.utc)
        location_available = latitude is not None and longitude is not None

        # Device registration is independent from AI inference. Bootstrap/update the
        # reporting phone before any idempotent early return so reports created by
        # older V17 builds can repair the missing registered_devices row on retry.
        effective_device_id = device_id or (getattr(existing, "device_id", None) if existing else None)
        if effective_device_id:
            try:
                existing_location_available = bool(getattr(existing, "location_available", False)) if existing else False
                device_latitude = (
                    float(latitude) if latitude is not None
                    else (float(existing.latitude) if existing and existing_location_available else None)
                )
                device_longitude = (
                    float(longitude) if longitude is not None
                    else (float(existing.longitude) if existing and existing_location_available else None)
                )
                self.devices.ensure_from_report(
                    db,
                    device_id=effective_device_id,
                    crop=selected_crop.value if not existing else existing.selected_crop,
                    preferred_language=language.value if not existing else (existing.language or language.value),
                    latitude=device_latitude,
                    longitude=device_longitude,
                )
            except Exception:
                logger.exception("Could not register/update reporting device %s", effective_device_id)
                db.rollback()

        # All successful terminal outcomes are idempotent. The older check only
        # recognized `completed`, so symptom-only reports (`completed_without_image`)
        # re-ran Qwen/RAG on every mobile retry and could change an already stored result.
        terminal_success_statuses = {
            "completed",
            "completed_without_image",
            "completed_with_unverified_image",
            "disease_low_confidence",
            "wrong_crop_image",
            "unsupported_crop_image",
        }
        if existing and existing.processing_status in terminal_success_statuses:
            try:
                outbreak = self.outbreak.assessment_for_stored_report(db, existing)
            except Exception:
                logger.exception("Outbreak re-evaluation failed for idempotent report %s", report_id)
                db.rollback()
                outbreak = OutbreakAssessment(
                    evaluated=False,
                    radius_km=self.settings.outbreak_radius_km,
                    time_window_days=self.settings.outbreak_time_window_days,
                    reason="Report is stored; outbreak evaluation failed independently.",
                )
            return self._db_to_structured(existing, outbreak)

        farmer = FarmerInput(
            language=language,
            symptoms_raw=(answer_1 or "").strip(),
            onset_raw=(answer_2 or "").strip(),
            affected_extent_raw=(answer_3 or "").strip(),
            spread_raw=(answer_4 or "").strip(),
        )
        has_farmer_input = any(
            value.strip() for value in (farmer.symptoms_raw, farmer.onset_raw, farmer.affected_extent_raw, farmer.spread_raw)
        )

        image_path = None
        disease = None
        disease_error = False

        if image_bytes is None:
            image_assessment = ImageAssessment(status=ImageStatus.not_submitted)
        else:
            validation = self.image_validator.validate(image_bytes)
            if not validation.ok or validation.image is None:
                image_assessment = ImageAssessment(status=ImageStatus.invalid_image)
            else:
                image_path = save_report_image(report_id, validation.image)
                image_assessment = ImageAssessment(status=ImageStatus.validated)
                try:
                    disease = self.disease_service.predict(selected_crop.value, validation.image)
                    logger.info(
                        "[IMAGE] crop=%s disease=%s confidence=%.3f low=%s",
                        selected_crop.value,
                        disease.disease,
                        disease.confidence,
                        disease.low_confidence,
                    )
                except DiseaseModelUnavailable:
                    disease_error = True
                    logger.exception("Disease model unavailable for crop %s", selected_crop.value)
                    if not self.settings.allow_missing_disease_model:
                        raise
                except Exception:
                    disease_error = True
                    logger.exception("Disease inference failed for API-selected crop %s", selected_crop.value)

        qwen_error = False
        try:
            assessment = self.qwen.generate(farmer)
        except QwenUnavailable as exc:
            qwen_error = True
            logger.exception("Qwen farmer extraction failed: %s", exc)
            if not self.settings.qwen_allow_fallback:
                raise
            assessment = self.qwen.fallback()

        qwen_affected_part = assessment.affected_part
        assessment.affected_part = validate_affected_part(farmer.symptoms_raw, qwen_affected_part)
        if assessment.affected_part != qwen_affected_part:
            logger.warning(
                "Affected part validated from raw Q1: qwen=%r final=%r",
                qwen_affected_part,
                assessment.affected_part,
            )

        mapping_error = False
        try:
            assessment = self.symptom_rag.enrich_assessment(
                assessment,
                crop=selected_crop.value,
                language=language.value,
            )
        except Exception as exc:
            mapping_error = True
            logger.exception("Symptom semantic mapping failed: %s", exc)
            assessment.symptom_codes = [SymptomCode.OTHERS_MAP for _ in assessment.symptoms]
            assessment.symptom_mapping = [
                SymptomMappingItem(
                    symptom=symptom,
                    retrieval_language=language,
                    code=SymptomCode.OTHERS_MAP,
                    concept_name=None,
                    similarity=0.0,
                    second_best_similarity=None,
                    margin=None,
                    status="embedding_failed",
                )
                for symptom in assessment.symptoms
            ]
            assessment.symptom_dictionary_version = SYMPTOM_DICTIONARY_VERSION

        status = self._final_status(
            image_assessment,
            disease,
            disease_error,
            qwen_error,
            has_farmer_input=has_farmer_input,
        )

        evidence = self._evidence(
            crop=selected_crop,
            disease=disease,
            assessment=assessment,
            image_assessment=image_assessment,
            has_farmer_input=has_farmer_input,
            qwen_error=qwen_error,
            mapping_error=mapping_error,
        )
        requires_review = evidence.needs_expert_review
        # Safety gate: evidence that the system itself flags for expert review is
        # stored immediately but held out of automatic outbreak clustering until
        # an expert marks the report VALID. Clean reports continue automatically.
        if requires_review and evidence.usable_for_outbreak:
            evidence.usable_for_outbreak = False
            evidence.reason = f"{evidence.reason} Held for expert review before automatic outbreak clustering."

        summary = self._build_summary(selected_crop, assessment, image_assessment, disease, qwen_error)
        recommended_next_step = self._build_recommendation(image_assessment, disease, qwen_error)

        row = existing or Report(report_id=report_id)
        row.device_id = device_id
        row.selected_crop = selected_crop.value
        row.language = language.value
        row.detected_crop = image_assessment.detected_crop
        row.image_status = image_assessment.status.value
        row.crop_match = image_assessment.matches_selected_crop
        row.crop_validation_confidence = image_assessment.confidence
        row.image_submitted = image_bytes is not None
        row.disease = disease.disease if disease else None
        row.disease_confidence = disease.confidence if disease else None
        row.disease_confidence_level = disease.confidence_level if disease else None
        row.healthy_class_supported = disease.healthy_class_supported if disease else None
        row.question_1_raw = farmer.symptoms_raw
        row.question_2_raw = farmer.onset_raw
        row.question_3_raw = farmer.affected_extent_raw
        row.question_4_raw = farmer.spread_raw
        row.symptoms = assessment.symptoms
        row.symptom_codes = [code.value for code in assessment.symptom_codes]
        row.symptom_mapping = [item.model_dump(mode="json") for item in assessment.symptom_mapping]
        row.symptom_dictionary_version = assessment.symptom_dictionary_version
        row.affected_part = assessment.affected_part
        row.problem_duration = assessment.problem_duration
        row.affected_area = assessment.affected_area
        row.spread_status = assessment.spread_status
        row.evidence_mode = evidence.evidence_mode.value
        row.evidence_strength = evidence.evidence_strength.value
        row.image_evidence_available = evidence.image_evidence_available
        row.symptom_evidence_available = evidence.symptom_evidence_available
        row.canonical_symptom_evidence_available = evidence.canonical_symptom_evidence_available
        row.usable_for_outbreak = evidence.usable_for_outbreak
        row.summary = summary
        row.recommended_next_step = recommended_next_step
        row.requires_expert_review = requires_review
        # Do not overwrite a completed human review on an idempotent/update path.
        if not existing or getattr(row, "expert_review_status", None) in {None, "PENDING", "NOT_REQUIRED"}:
            row.expert_review_status = "PENDING" if requires_review else "NOT_REQUIRED"
        row.latitude = latitude if latitude is not None else 0.0
        row.longitude = longitude if longitude is not None else 0.0
        row.location_available = location_available
        row.processing_status = status.value
        row.image_path = image_path
        row.reported_at = timestamp

        if existing:
            self.repo.update(db, row)
        else:
            self.repo.save(db, row)

        # The report is already committed. Outbreak failure must never discard it.
        try:
            outbreak_assessment = self.outbreak.assessment_for_stored_report(db, row)
        except Exception:
            logger.exception("Outbreak evaluation failed for stored report %s", report_id)
            db.rollback()
            outbreak_assessment = OutbreakAssessment(
                evaluated=False,
                radius_km=self.settings.outbreak_radius_km,
                time_window_days=self.settings.outbreak_time_window_days,
                reason="Report saved successfully, but outbreak evaluation failed independently.",
            )

        logger.info(
            "[REPORT] id=%s evidence=%s usable_for_outbreak=%s review=%s",
            row.report_id,
            row.evidence_mode,
            row.usable_for_outbreak,
            row.requires_expert_review,
        )

        structured = self._db_to_structured(row, outbreak_assessment)
        # Preserve the richer reason calculated during this processing pass.
        structured.evidence = evidence
        return structured
