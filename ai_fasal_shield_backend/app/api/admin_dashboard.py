from pathlib import Path

from fastapi import APIRouter
from fastapi.responses import HTMLResponse

router = APIRouter()

_ADMIN_HTML = Path(__file__).resolve().parents[1] / "static" / "admin.html"


@router.get("/admin", response_class=HTMLResponse, include_in_schema=False)
def admin_dashboard() -> HTMLResponse:
    """Offline-friendly admin/expert dashboard for the hackathon prototype."""
    return HTMLResponse(_ADMIN_HTML.read_text(encoding="utf-8"))
