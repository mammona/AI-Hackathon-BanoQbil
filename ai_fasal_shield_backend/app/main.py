from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text

from app.api.alerts import router as alerts_router
from app.api.admin_dashboard import router as admin_dashboard_router
from app.api.devices import router as devices_router
from app.api.rag_debug import router as rag_debug_router
from app.api.reports import router as reports_router
from app.config import get_settings
from app.database import Base, SessionLocal, engine
from app.models import database_models  # noqa: F401
from app.services.demo_device_seed_service import seed_demo_devices

settings = get_settings()


SQLITE_REPORT_ADDITIONS = {
    "device_id": "VARCHAR(160)",
    "symptom_codes": "JSON NOT NULL DEFAULT '[]'",
    "symptom_mapping": "JSON NOT NULL DEFAULT '[]'",
    "symptom_dictionary_version": "VARCHAR(20)",
    "language": "VARCHAR(20) NOT NULL DEFAULT 'urdu'",
    "image_submitted": "BOOLEAN NOT NULL DEFAULT 0",
    "healthy_class_supported": "BOOLEAN",
    "evidence_mode": "VARCHAR(32) NOT NULL DEFAULT 'CONTEXT_ONLY'",
    "evidence_strength": "VARCHAR(16) NOT NULL DEFAULT 'LOW'",
    "image_evidence_available": "BOOLEAN NOT NULL DEFAULT 0",
    "symptom_evidence_available": "BOOLEAN NOT NULL DEFAULT 0",
    "canonical_symptom_evidence_available": "BOOLEAN NOT NULL DEFAULT 0",
    "usable_for_outbreak": "BOOLEAN NOT NULL DEFAULT 0",
    # Existing prototype DBs already had mandatory coordinates, so old rows are real locations.
    "location_available": "BOOLEAN NOT NULL DEFAULT 1",
    "expert_review_status": "VARCHAR(24) NOT NULL DEFAULT 'PENDING'",
    "reviewed_by": "VARCHAR(200)",
    "review_note": "TEXT",
    "reviewed_at": "DATETIME",
}


SQLITE_ALERT_ADDITIONS = {
    # Private verification note already exists in prior builds. This new field is
    # explicitly farmer-facing and can be included in Punjabi notifications.
    "farmer_instruction": "TEXT",
}


def _sqlite_compat_migrate() -> None:
    """Small additive migration for the hackathon SQLite DB.

    It preserves existing report rows. For a clean demo reset, deleting
    fasal_guard.db and restarting is still the simplest option.
    """
    with engine.begin() as conn:
        tables = {row[0] for row in conn.execute(text("SELECT name FROM sqlite_master WHERE type='table'"))}
        if "reports" not in tables:
            return
        columns = {row[1] for row in conn.execute(text("PRAGMA table_info(reports)"))}
        for name, ddl in SQLITE_REPORT_ADDITIONS.items():
            if name not in columns:
                conn.execute(text(f"ALTER TABLE reports ADD COLUMN {name} {ddl}"))

        if "alerts" in tables:
            alert_columns = {row[1] for row in conn.execute(text("PRAGMA table_info(alerts)"))}
            for name, ddl in SQLITE_ALERT_ADDITIONS.items():
                if name not in alert_columns:
                    conn.execute(text(f"ALTER TABLE alerts ADD COLUMN {name} {ddl}"))


@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)
    if settings.database_url.startswith("sqlite"):
        _sqlite_compat_migrate()
    if settings.auto_seed_demo_devices:
        with SessionLocal() as db:
            seed_demo_devices(db, settings.demo_devices_file)
    yield


app = FastAPI(title=settings.app_name, version="0.12.4-v17-leafcurl-preload-consistency", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=settings.cors_origin_list != ["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(admin_dashboard_router)
app.include_router(reports_router, prefix=settings.api_prefix)
app.include_router(alerts_router, prefix=settings.api_prefix)
app.include_router(devices_router, prefix=settings.api_prefix)
app.include_router(rag_debug_router, prefix=settings.api_prefix)


@app.get("/health")
def health():
    db_ok = True
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
    except Exception:
        db_ok = False
    return {
        "status": "ok" if db_ok else "degraded",
        "database": "ok" if db_ok else "unavailable",
        "database_mode": "sqlite" if settings.database_url.startswith("sqlite") else "external",
        "outbreak_engine": "deterministic_geo_temporal",
        "outbreak_radius_km": settings.outbreak_radius_km,
        "notification_radius_km": settings.notification_radius_km,
        "notification_area_km2": round(3.141592653589793 * settings.notification_radius_km ** 2, 3),
        "outbreak_time_window_days": settings.outbreak_time_window_days,
    }
