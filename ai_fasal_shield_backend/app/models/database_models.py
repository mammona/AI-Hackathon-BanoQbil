from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.types import JSON

from app.database import Base

json_type = JSON().with_variant(JSONB, "postgresql")


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Report(Base):
    __tablename__ = "reports"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    report_id: Mapped[str] = mapped_column(String(100), unique=True, index=True, nullable=False)
    device_id: Mapped[str | None] = mapped_column(String(160), index=True)

    selected_crop: Mapped[str] = mapped_column(String(32), index=True, nullable=False)
    language: Mapped[str] = mapped_column(String(20), index=True, nullable=False, default="urdu")

    # Backward-compatible image fields. Crop identity is not inferred in this MVP.
    detected_crop: Mapped[str | None] = mapped_column(String(32), index=True)
    image_status: Mapped[str] = mapped_column(String(40), index=True, nullable=False)
    crop_match: Mapped[bool | None] = mapped_column(Boolean)
    crop_validation_confidence: Mapped[float | None] = mapped_column(Float)
    image_submitted: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, index=True)

    disease: Mapped[str | None] = mapped_column(String(100), index=True)
    disease_confidence: Mapped[float | None] = mapped_column(Float)
    disease_confidence_level: Mapped[str | None] = mapped_column(String(20))
    healthy_class_supported: Mapped[bool | None] = mapped_column(Boolean)

    question_1_raw: Mapped[str] = mapped_column(Text, nullable=False, default="")
    question_2_raw: Mapped[str] = mapped_column(Text, nullable=False, default="")
    question_3_raw: Mapped[str] = mapped_column(Text, nullable=False, default="")
    question_4_raw: Mapped[str] = mapped_column(Text, nullable=False, default="")

    symptoms: Mapped[list] = mapped_column(json_type, default=list, nullable=False)
    symptom_codes: Mapped[list] = mapped_column(json_type, default=list, nullable=False)
    symptom_mapping: Mapped[list] = mapped_column(json_type, default=list, nullable=False)
    symptom_dictionary_version: Mapped[str | None] = mapped_column(String(20))
    affected_part: Mapped[str | None] = mapped_column(String(100))
    problem_duration: Mapped[str | None] = mapped_column(String(100))
    affected_area: Mapped[str | None] = mapped_column(String(100))
    spread_status: Mapped[str | None] = mapped_column(String(100), index=True)

    # Deterministic evidence metadata used by the outbreak engine.
    evidence_mode: Mapped[str] = mapped_column(String(32), nullable=False, default="CONTEXT_ONLY", index=True)
    evidence_strength: Mapped[str] = mapped_column(String(16), nullable=False, default="LOW", index=True)
    image_evidence_available: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, index=True)
    symptom_evidence_available: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    canonical_symptom_evidence_available: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, index=True)
    usable_for_outbreak: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, index=True)

    summary: Mapped[str] = mapped_column(Text, nullable=False)
    recommended_next_step: Mapped[str] = mapped_column(Text, nullable=False)
    requires_expert_review: Mapped[bool] = mapped_column(Boolean, default=True, index=True, nullable=False)

    # Human review workflow. A report that needs review can be held out of
    # automatic outbreak clustering until an expert marks it VALID.
    expert_review_status: Mapped[str] = mapped_column(String(24), nullable=False, default="PENDING", index=True)
    reviewed_by: Mapped[str | None] = mapped_column(String(200))
    review_note: Mapped[str | None] = mapped_column(Text)
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    # Keep latitude/longitude non-null for compatibility with existing SQLite DBs.
    # location_available=False means the stored 0/0 placeholders MUST NOT be used.
    latitude: Mapped[float] = mapped_column(Float, nullable=False, index=True, default=0.0)
    longitude: Mapped[float] = mapped_column(Float, nullable=False, index=True, default=0.0)
    location_available: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, index=True)
    image_path: Mapped[str | None] = mapped_column(Text)

    processing_status: Mapped[str] = mapped_column(String(60), index=True, nullable=False)
    reported_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow, nullable=False)


class Alert(Base):
    __tablename__ = "alerts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    alert_id: Mapped[str] = mapped_column(String(100), unique=True, index=True, nullable=False)
    crop: Mapped[str] = mapped_column(String(32), index=True, nullable=False)

    primary_disease: Mapped[str | None] = mapped_column(String(100), index=True)
    primary_symptom_codes: Mapped[list] = mapped_column("primary_symptom_codes_json", json_type, default=list, nullable=False)

    center_latitude: Mapped[float] = mapped_column(Float, nullable=False)
    center_longitude: Mapped[float] = mapped_column(Float, nullable=False)
    radius_km: Mapped[float] = mapped_column(Float, nullable=False, default=5.0)
    report_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    alert_level: Mapped[str] = mapped_column(String(24), nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False, index=True, default="active")

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow, nullable=False)

    verified_by: Mapped[str | None] = mapped_column(String(200))
    verification_note: Mapped[str | None] = mapped_column(Text)
    # Explicit farmer-facing instruction supplied by the confirming reviewer.
    # This is intentionally separate from the private verification note.
    farmer_instruction: Mapped[str | None] = mapped_column(Text)
    verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class AlertReport(Base):
    __tablename__ = "alert_reports"
    __table_args__ = (UniqueConstraint("alert_id", "report_id", name="uq_alert_report"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    alert_id: Mapped[str] = mapped_column(
        String(100), ForeignKey("alerts.alert_id", ondelete="CASCADE"), index=True, nullable=False
    )
    report_id: Mapped[str] = mapped_column(
        String(100), ForeignKey("reports.report_id", ondelete="CASCADE"), index=True, nullable=False
    )


class RegisteredDevice(Base):
    __tablename__ = "registered_devices"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    device_id: Mapped[str] = mapped_column(String(160), unique=True, index=True, nullable=False)
    push_token: Mapped[str | None] = mapped_column(Text)
    crops: Mapped[list] = mapped_column("crops_json", json_type, default=list, nullable=False)
    preferred_language: Mapped[str] = mapped_column(String(20), nullable=False, default="punjabi", index=True)
    latitude: Mapped[float | None] = mapped_column(Float, index=True)
    longitude: Mapped[float | None] = mapped_column(Float, index=True)
    location_available: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, index=True)
    notifications_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, index=True)
    last_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow, nullable=False)


class Notification(Base):
    __tablename__ = "notifications"
    __table_args__ = (UniqueConstraint("alert_id", "device_id", name="uq_alert_device_notification"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    notification_id: Mapped[str] = mapped_column(String(100), unique=True, index=True, nullable=False)
    alert_id: Mapped[str] = mapped_column(
        String(100), ForeignKey("alerts.alert_id", ondelete="CASCADE"), index=True, nullable=False
    )
    device_id: Mapped[str] = mapped_column(
        String(160), ForeignKey("registered_devices.device_id", ondelete="CASCADE"), index=True, nullable=False
    )
    crop: Mapped[str] = mapped_column(String(32), index=True, nullable=False)
    title: Mapped[str] = mapped_column(String(240), nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    message_local: Mapped[str] = mapped_column(Text, nullable=False)
    language: Mapped[str] = mapped_column(String(20), nullable=False, default="punjabi")
    distance_km: Mapped[float] = mapped_column(Float, nullable=False)
    status: Mapped[str] = mapped_column(String(24), nullable=False, default="unread", index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False, index=True)
    read_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
