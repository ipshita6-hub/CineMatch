"""Initialize the production database and run one API worker on Render."""
from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / "backend")]


def main() -> None:
    from app.core.config import settings

    if settings.jwt_secret == "change-me" or len(settings.jwt_secret) < 32:
        raise SystemExit("Set JWT_SECRET to a random value of at least 32 characters")
    if not settings.cors_origin_list or all("localhost" in origin for origin in settings.cors_origin_list):
        raise SystemExit("Set CORS_ORIGINS to the HTTPS origin of the Vercel frontend")

    subprocess.run([sys.executable, "-m", "alembic", "upgrade", "head"], cwd=ROOT / "backend", check=True)
    from sqlalchemy import text
    from app.db.session import engine

    with engine.connect() as connection:
        count = connection.execute(text("SELECT count(*) FROM movies")).scalar_one()
    if count == 0:
        subprocess.run([sys.executable, str(ROOT / "scripts/seed_movies.py")], cwd=ROOT, check=True)
    else:
        print(f"Catalog already contains {count} movies; preserving existing data", flush=True)
    os.execv(sys.executable, [sys.executable, "-m", "uvicorn", "app.main:app", "--app-dir", str(ROOT / "backend"), "--host", "0.0.0.0", "--port", os.environ.get("PORT", "10000"), "--workers", "1"])


if __name__ == "__main__":
    main()
