from datetime import datetime
from enum import Enum
from typing import Literal

from pydantic import BaseModel, Field

from app.constants.symptoms import SymptomCode


class CropName(str, Enum):
    cotton = "cotton"
    rice = "rice"


class ReportLanguage(str, Enum):
    english = "english"
    urdu = "urdu"
    punjabi = "punjabi"

    @classmethod
    def _missing_(cls, value):
        if isinstance(value, str):
            normalized = value.strip().lower()
            if normalized in {"english", "urdu", "punjabi"}:
                return cls(normalized)
            aliases = {
                "en": "english",
                "ur": "urdu",
                "pa": "punjabi",
                "punjabi_shahmukhi": "punjabi",
                "shahmukhi": "punjabi",
            }
            mapped = aliases.get(normalized)
            if mapped:
                return cls(mapped)
        return None


class ImageStatus(str, Enum):
    not_submitted = "not_submitted"
    validated = "validated"
    invalid_image = "invalid_image"
    non_crop = "non_crop"
    wrong_crop = "wrong_crop"
    unsupported_crop = "unsupported_crop"
    not_identified = "not_identified"


class ReportStatus(str, Enum):
    received = "received"
    validating = "validating"
    processing = "processing"
    completed = "completed"
    completed_without_image = "completed_without_image"
    completed_with_unverified_image = "completed_with_unverified_image"
    wrong_crop_image = "wrong_crop_image"
    unsupported_crop_image = "unsupported_crop_image"
    disease_low_confidence = "disease_low_confidence"
    processing_failed = "processing_failed"


class EvidenceMode(str, Enum):
    MULTIMODAL = "MULTIMODAL"
    IMAGE_ONLY = "IMAGE_ONLY"
    SYMPTOM_ONLY = "SYMPTOM_ONLY"
    CONTEXT_ONLY = "CONTEXT_ONLY"
    INSUFFICIENT_EVIDENCE = "INSUFFICIENT_EVIDENCE"


class EvidenceStrength(str, Enum):
    STRONG = "STRONG"
    MEDIUM = "MEDIUM"
    LOW = "LOW"
    NONE = "NONE"


class AlertLevel(str, Enum):
    NO_ALERT = "NO_ALERT"
    MONITORING = "MONITORING"
    AMBER = "AMBER"
    RED = "RED"


class ExpertReviewStatus(str, Enum):
    PENDING = "PENDING"
    VALID = "VALID"
    INVALID = "INVALID"
    FOLLOW_UP = "FOLLOW_UP"
    NOT_REQUIRED = "NOT_REQUIRED"


class ImageAssessment(BaseModel):
    status: ImageStatus
    detected_crop: str | None = None
    matches_selected_crop: bool | None = None
    confidence: float | None = Field(default=None, ge=0, le=1)


class DiseasePrediction(BaseModel):
    disease: str
    confidence: float = Field(ge=0, le=1)
    confidence_level: Literal["low", "medium", "high"]
    verified_by_image: bool = True
    low_confidence: bool = False
    healthy_class_supported: bool = True


class FarmerInput(BaseModel):
    language: ReportLanguage = ReportLanguage.english
    symptoms_raw: str = ""
    onset_raw: str = ""
    affected_extent_raw: str = ""
    spread_raw: str = ""


class FarmerExtraction(BaseModel):
    symptoms: list[str] = Field(default_factory=list)
    affected_part: str | None = None
    problem_duration: str | None = None
    affected_area: str | None = None
    spread_status: str | None = None


class SymptomMappingItem(BaseModel):
    symptom: str
    retrieval_language: ReportLanguage | None = None
    code: SymptomCode
    concept_name: str | None = None
    similarity: float = Field(ge=-1, le=1)
    second_best_similarity: float | None = Field(default=None, ge=-1, le=1)
    margin: float | None = Field(default=None, ge=-2, le=2)
    reranker_score: float | None = Field(default=None, ge=0, le=1)
    reranker_second_score: float | None = Field(default=None, ge=0, le=1)
    reranker_margin: float | None = Field(default=None, ge=-1, le=1)
    reranker_reason: str | None = None
    status: Literal[
        "matched_semantic",
        # Kept so old stored rows can still be read. New V17.1 logic does not emit it.
        "matched_specific_over_parent",
        "ambiguous",
        "embedding_failed",
        "matched_auto",
        "matched_reranked",
        "reranked_other",
        "below_threshold",
        "rerank_failed",
    ]


class Assessment(BaseModel):
    symptoms: list[str] = Field(default_factory=list)
    symptom_codes: list[SymptomCode] = Field(default_factory=list)
    symptom_mapping: list[SymptomMappingItem] = Field(default_factory=list)
    symptom_dictionary_version: str | None = None
    affected_part: str | None = None
    problem_duration: str | None = None
    affected_area: str | None = None
    spread_status: str | None = None


class Location(BaseModel):
    latitude: float | None = Field(default=None, ge=-90, le=90)
    longitude: float | None = Field(default=None, ge=-180, le=180)


class EvidenceAssessment(BaseModel):
    evidence_mode: EvidenceMode
    evidence_strength: EvidenceStrength
    image_evidence_available: bool
    symptom_evidence_available: bool
    canonical_symptom_evidence_available: bool
    usable_for_outbreak: bool
    needs_expert_review: bool
    disease_symptom_consistency: Literal["CONSISTENT", "INCONSISTENT", "NOT_APPLICABLE"] = "NOT_APPLICABLE"
    disease_symptom_consistency_reason: str | None = None
    reason: str


class OutbreakAssessment(BaseModel):
    evaluated: bool
    related_report_count: int = 0
    radius_km: float | None = None
    time_window_days: int | None = None
    alert_level: AlertLevel | None = None
    alert_id: str | None = None
    reason: str | None = None


class StructuredReport(BaseModel):
    report_id: str
    device_id: str | None = None
    crop: CropName
    image_assessment: ImageAssessment
    disease_prediction: DiseasePrediction | None = None
    farmer_input: FarmerInput
    assessment: Assessment
    summary: str
    recommended_next_step: str
    requires_expert_review: bool
    expert_review_status: ExpertReviewStatus = ExpertReviewStatus.PENDING
    reviewed_by: str | None = None
    review_note: str | None = None
    reviewed_at: datetime | None = None
    location: Location
    timestamp: datetime
    status: ReportStatus
    evidence: EvidenceAssessment
    outbreak_assessment: OutbreakAssessment


class ReportListItem(BaseModel):
    report_id: str
    device_id: str | None = None
    selected_crop: str
    language: ReportLanguage
    detected_crop: str | None
    disease: str | None
    disease_confidence: float | None
    symptoms: list[str]
    symptom_codes: list[SymptomCode] = Field(default_factory=list)
    symptom_mapping: list[SymptomMappingItem] = Field(default_factory=list)
    symptom_dictionary_version: str | None = None
    spread_status: str | None
    requires_expert_review: bool
    expert_review_status: ExpertReviewStatus = ExpertReviewStatus.PENDING
    reviewed_by: str | None = None
    reviewed_at: datetime | None = None
    processing_status: str
    latitude: float | None
    longitude: float | None
    reported_at: datetime
    evidence_mode: EvidenceMode
    evidence_strength: EvidenceStrength
    usable_for_outbreak: bool


class AlertSummary(BaseModel):
    alert_id: str
    crop: str
    primary_disease: str | None
    primary_symptom_codes: list[str] = Field(default_factory=list)
    center_latitude: float
    center_longitude: float
    radius_km: float
    report_count: int
    alert_level: AlertLevel
    status: str
    created_at: datetime
    updated_at: datetime
    verified_by: str | None = None
    verification_note: str | None = None
    # Punjabi/Shahmukhi instruction that is safe to send to farmers.
    farmer_instruction: str | None = None
    verified_at: datetime | None = None


class AlertDetail(AlertSummary):
    report_ids: list[str] = Field(default_factory=list)
    # Delivery geometry is distinct from the outbreak-linking radius.
    notification_radius_km: float = 0.0
    notification_area_km2: float = 0.0
    # Maximum distance of any linked report from the calculated alert center.
    cluster_spread_km: float = 0.0
    eligible_device_count: int = 0
    notification_count: int = 0


class AlertVerificationRequest(BaseModel):
    decision: Literal["confirmed", "rejected"]
    expert_name: str = Field(min_length=1, max_length=200)
    # Private/internal verification note. Never sent to farmers.
    note: str | None = Field(default=None, max_length=2000)
    # Optional Punjabi/Shahmukhi instruction that IS included in farmer notifications.
    farmer_instruction: str | None = Field(default=None, max_length=2000)


class ReportReviewRequest(BaseModel):
    decision: Literal["valid", "invalid", "follow_up"]
    expert_name: str = Field(min_length=1, max_length=200)
    note: str | None = Field(default=None, max_length=2000)


class ReportReviewResult(BaseModel):
    report_id: str
    expert_review_status: ExpertReviewStatus
    requires_expert_review: bool
    usable_for_outbreak: bool
    reviewed_by: str
    review_note: str | None = None
    reviewed_at: datetime
    outbreak_assessment: OutbreakAssessment
    linked_alert_ids: list[str] = Field(default_factory=list)


class DashboardSummary(BaseModel):
    # Backward-compatible fields
    total_reports: int
    cotton_reports: int
    rice_reports: int
    expert_review_required: int
    completed_reports: int
    unverified_image_reports: int
    failed_reports: int

    # Outbreak-ready additions
    usable_reports: int
    reports_needing_expert_review: int
    active_monitoring: int
    amber_alerts: int
    red_alerts: int
    registered_devices: int = 0
    unread_notifications: int = 0
    reviewed_valid_reports: int = 0
    reviewed_invalid_reports: int = 0


class DeviceRegistrationRequest(BaseModel):
    device_id: str = Field(min_length=3, max_length=160)
    crops: list[CropName] = Field(min_length=1)
    preferred_language: ReportLanguage = ReportLanguage.punjabi
    latitude: float | None = Field(default=None, ge=-90, le=90)
    longitude: float | None = Field(default=None, ge=-180, le=180)
    push_token: str | None = Field(default=None, max_length=4000)
    notifications_enabled: bool = True


class DeviceLocationUpdate(BaseModel):
    latitude: float = Field(ge=-90, le=90)
    longitude: float = Field(ge=-180, le=180)


class DeviceResponse(BaseModel):
    device_id: str
    crops: list[str] = Field(default_factory=list)
    preferred_language: ReportLanguage
    latitude: float | None = None
    longitude: float | None = None
    location_available: bool
    notifications_enabled: bool
    has_push_token: bool
    last_seen_at: datetime
    created_at: datetime
    updated_at: datetime


class NotificationResponse(BaseModel):
    notification_id: str
    alert_id: str
    device_id: str
    crop: str
    title: str
    message: str
    message_local: str
    language: ReportLanguage
    distance_km: float
    status: str
    created_at: datetime
    read_at: datetime | None = None
