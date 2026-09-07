from datetime import datetime

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.schemas import CropName, DashboardSummary, ReportLanguage, ReportListItem, ReportReviewRequest, ReportReviewResult, StructuredReport
from app.repositories.report_repository import ReportRepository
from app.services.report_service import ReportService
from app.services.report_review_service import ReportReviewService

router = APIRouter()
service = ReportService()
repo = ReportRepository()
review_service = ReportReviewService()


@router.post(
    "/reports/process",
    response_model=StructuredReport,
    summary="Process an optional-image farmer report",
    description=(
        "Image is OPTIONAL. Q1-Q4 are individually OPTIONAL. "
        "The report is accepted when an image OR at least one farmer answer is provided. "
        "Only a completely empty report is rejected."
    ),
)
def process_report(
    report_id: str = Form(..., min_length=1, max_length=100),
    device_id: str | None = Form(default=None, description="OPTIONAL mobile installation/device id"),
    selected_crop: CropName = Form(...),
    language: ReportLanguage = Form(...),
    answer_1: str = Form(default="", description="OPTIONAL Q1: symptoms / visible crop problem"),
    answer_2: str = Form(default="", description="OPTIONAL Q2: when the problem started"),
    answer_3: str = Form(default="", description="OPTIONAL Q3: affected area / plants"),
    answer_4: str = Form(default="", description="OPTIONAL Q4: spread / worsening status"),
    latitude: float | None = Form(default=None, ge=-90, le=90),
    longitude: float | None = Form(default=None, ge=-180, le=180),
    timestamp: datetime | None = Form(default=None),
    image: UploadFile | None = File(
        default=None,
        description="OPTIONAL crop image. Leave empty when one or more farmer answers are provided.",
    ),
    db: Session = Depends(get_db),
):
    # Image and Q1-Q4 are independently optional, but the report cannot be empty.
    # Some multipart clients/Swagger versions can send an empty file control as an
    # UploadFile with an empty filename. Treat that exactly like "no image".
    has_any_answer = any((value or "").strip() for value in (answer_1, answer_2, answer_3, answer_4))
    has_image = image is not None and bool((image.filename or "").strip())

    if not has_image and not has_any_answer:
        raise HTTPException(
            status_code=422,
            detail="Provide at least one input source: an image or at least one farmer answer.",
        )

    # Geographic outbreak logic needs a complete coordinate pair. A report without
    # GPS is still accepted and stored, but cannot auto-cluster geographically.
    if (latitude is None) != (longitude is None):
        raise HTTPException(
            status_code=422,
            detail="Provide both latitude and longitude, or omit both.",
        )

    try:
        image_bytes = image.file.read() if has_image else None
        # A zero-byte upload is the same as no image when farmer answers exist.
        # This prevents an empty browser file field from entering image validation.
        if image_bytes == b"":
            image_bytes = None
        return service.process(
            db,
            report_id=report_id,
            device_id=(device_id or "").strip() or None,
            selected_crop=selected_crop,
            language=language,
            answer_1=answer_1,
            answer_2=answer_2,
            answer_3=answer_3,
            answer_4=answer_4,
            latitude=latitude,
            longitude=longitude,
            timestamp=timestamp,
            image_bytes=image_bytes,
        )
    except HTTPException:
        raise
    except Exception as exc:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Report processing failed: {exc}") from exc


@router.get("/reports", response_model=list[ReportListItem])
def list_reports(
    crop: str | None = Query(default=None),
    status: str | None = Query(default=None),
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
):
    rows = repo.list(db, crop=crop, status=status, limit=limit, offset=offset)
    return [
        ReportListItem(
            report_id=r.report_id,
            device_id=getattr(r, "device_id", None),
            selected_crop=r.selected_crop,
            language=ReportLanguage(r.language or "urdu"),
            detected_crop=r.detected_crop,
            disease=r.disease,
            disease_confidence=r.disease_confidence,
            symptoms=r.symptoms or [],
            symptom_codes=r.symptom_codes or [],
            symptom_mapping=r.symptom_mapping or [],
            symptom_dictionary_version=r.symptom_dictionary_version,
            spread_status=r.spread_status,
            requires_expert_review=r.requires_expert_review,
            expert_review_status=getattr(r, "expert_review_status", "PENDING"),
            reviewed_by=getattr(r, "reviewed_by", None),
            reviewed_at=getattr(r, "reviewed_at", None),
            processing_status=r.processing_status,
            latitude=r.latitude if getattr(r, "location_available", True) else None,
            longitude=r.longitude if getattr(r, "location_available", True) else None,
            reported_at=r.reported_at,
            evidence_mode=getattr(r, "evidence_mode", "CONTEXT_ONLY"),
            evidence_strength=getattr(r, "evidence_strength", "LOW"),
            usable_for_outbreak=bool(getattr(r, "usable_for_outbreak", False)),
        )
        for r in rows
    ]


@router.get("/reports/{report_id}", response_model=StructuredReport)
def get_report(report_id: str, db: Session = Depends(get_db)):
    row = repo.get(db, report_id)
    if not row:
        raise HTTPException(status_code=404, detail="Report not found")
    return service._db_to_structured(row)


@router.post("/reports/{report_id}/review", response_model=ReportReviewResult)
def review_report(
    report_id: str,
    request: ReportReviewRequest,
    db: Session = Depends(get_db),
):
    """Save expert review and re-evaluate the report's outbreak contribution.

    VALID can create/update MONITORING or AMBER. INVALID and FOLLOW_UP are
    retained for audit but excluded from automatic clustering.
    """
    return review_service.review(db, report_id=report_id, request=request)


@router.get("/dashboard/summary", response_model=DashboardSummary)
def dashboard_summary(db: Session = Depends(get_db)):
    return repo.dashboard_summary(db)
