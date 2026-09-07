"""Print notification records after an expert confirms a RED alert."""
from sqlalchemy import select
from app.database import SessionLocal
from app.models.database_models import Notification


def main():
    with SessionLocal() as db:
        rows = list(db.scalars(select(Notification).order_by(Notification.created_at.asc())).all())
        print(f"Notifications: {len(rows)}")
        for r in rows:
            print(
                f"{r.notification_id}: alert={r.alert_id}, device={r.device_id}, "
                f"crop={r.crop}, distance={r.distance_km:.2f}km, status={r.status}"
            )
            print(f"  title: {r.title}")
            print(f"  message: {r.message}")


if __name__ == "__main__":
    main()
