from pathlib import Path

from app.config import get_settings


def main() -> None:
    settings = get_settings()
    prefix = "sqlite:///./"
    if not settings.database_url.startswith(prefix):
        raise SystemExit("Refusing to reset: DATABASE_URL is not the default local SQLite path.")
    path = Path(settings.database_url[len(prefix):])
    if path.exists():
        path.unlink()
        print(f"Deleted {path}. Restart FastAPI to recreate the database and all tables.")
    else:
        print(f"{path} does not exist. Nothing to reset.")


if __name__ == "__main__":
    main()
