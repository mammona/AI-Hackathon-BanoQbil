from pathlib import Path
import re
from PIL import Image

from app.config import get_settings

_SAFE_ID = re.compile(r"[^A-Za-z0-9_.-]+")


def safe_report_id(report_id: str) -> str:
    value = _SAFE_ID.sub("_", report_id.strip())[:100]
    if not value:
        raise ValueError("Invalid report_id")
    return value


def save_report_image(report_id: str, image: Image.Image) -> str:
    settings = get_settings()
    report_dir = settings.data_dir / safe_report_id(report_id)
    report_dir.mkdir(parents=True, exist_ok=True)
    path = report_dir / "crop.jpg"
    image.convert("RGB").save(path, format="JPEG", quality=90, optimize=True)
    return str(path.as_posix())
