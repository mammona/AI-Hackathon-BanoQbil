"""Seed bundled demo farmer devices for RED-alert notification testing."""
from sqlalchemy import select

from app.database import Base, SessionLocal, engine
from app.models.database_models import RegisteredDevice
from app.services.demo_device_seed_service import seed_demo_devices


def main():
    Base.metadata.create_all(bind=engine)
    with SessionLocal() as db:
        count = seed_demo_devices(db)
        rows = list(db.scalars(select(RegisteredDevice).order_by(RegisteredDevice.device_id)).all())
        for row in rows:
            print(
                f"{row.device_id}: crops={row.crops}, "
                f"location={row.latitude},{row.longitude}, "
                f"language={row.preferred_language}"
            )
    print(f"Seeded/updated {count} bundled demo devices.")


if __name__ == "__main__":
    main()
