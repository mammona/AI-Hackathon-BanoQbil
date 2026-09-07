from __future__ import annotations

import json
import logging
from pathlib import Path

from sqlalchemy.orm import Session

from app.repositories.device_repository import DeviceRepository

logger = logging.getLogger(__name__)

DEFAULT_DEMO_DEVICE_FILE = Path("data/demo_devices.json")


def seed_demo_devices(db: Session, data_file: Path | str = DEFAULT_DEMO_DEVICE_FILE) -> int:
    """Idempotently seed the bundled demo farmer devices.

    Existing rows are updated rather than duplicated. This is intentionally
    safe to run at every development startup.
    """
    path = Path(data_file)
    if not path.exists():
        logger.warning("Demo device seed file not found: %s", path)
        return 0

    items = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(items, list):
        raise ValueError("Demo device seed data must be a JSON list.")

    repo = DeviceRepository()
    count = 0
    for item in items:
        device_id = str(item.get("device_id") or "").strip()
        if not device_id:
            raise ValueError("Every demo device must have a non-empty device_id.")
        repo.upsert(
            db,
            device_id=device_id,
            crops=list(item.get("crops") or []),
            preferred_language=str(item.get("preferred_language") or "punjabi"),
            latitude=item.get("latitude"),
            longitude=item.get("longitude"),
            push_token=item.get("push_token"),
            notifications_enabled=bool(item.get("notifications_enabled", True)),
        )
        count += 1
    return count
