"""Single-instance Compose startup: configure DB, migrate, seed, serve."""
import os
import subprocess
import sys
from urllib.parse import quote


def configure_database() -> None:
    if not os.environ.get("DATABASE_URL"):
        username = quote(os.environ["POSTGRES_USER"], safe="")
        password = quote(os.environ["POSTGRES_PASSWORD"], safe="")
        database = quote(os.environ["POSTGRES_DB"], safe="")
        host = os.environ.get("POSTGRES_HOST", "postgres")
        os.environ["DATABASE_URL"] = f"postgresql+psycopg://{username}:{password}@{host}:5432/{database}"


def main() -> None:
    configure_database()
    try:
        subprocess.run([sys.executable, "-m", "alembic", "upgrade", "head"], check=True)
        subprocess.run([sys.executable, "-m", "app.utils.seed_catalog"], check=True)
    except subprocess.CalledProcessError:
        raise SystemExit("Database initialization failed. API was not started.")
    os.execv(sys.executable, [sys.executable, "-m", "uvicorn", "app.main:app",
                            "--host", "0.0.0.0", "--port", "8000", "--no-access-log"])


if __name__ == "__main__":
    main()
