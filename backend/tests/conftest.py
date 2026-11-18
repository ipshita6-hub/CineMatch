"""Backend test fixtures.

Tests run against a dedicated `movierec_test` database (APP_TESTING=1), so the
development data is never touched. The ML artifacts are shared read-only.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

os.environ["APP_TESTING"] = "1"

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "backend"))

import pandas as pd  # noqa: E402
import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from sqlalchemy import text  # noqa: E402

from app.db.base import Base  # noqa: E402
from app.db.session import SessionLocal, engine  # noqa: E402
from app.main import app  # noqa: E402
from app.models.entities import Movie  # noqa: E402
from app.services.tmdb import tmdb_service  # noqa: E402
from ml import config as C  # noqa: E402

# The suite must not depend on the network or on a TMDB key.
tmdb_service.enabled = False


@pytest.fixture(scope="session", autouse=True)
def database() -> None:
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)

    # Seed the full catalog: anything the model can recommend must resolve to a
    # row, otherwise a result would be silently short.
    df = pd.read_csv(C.MOVIES_FEATURES_CSV)
    with SessionLocal() as db:
        db.bulk_save_objects([
            Movie(
                movie_id=int(r.movieId),
                movie_idx=None if pd.isna(r.movie_idx) else int(r.movie_idx),
                title=str(r.title)[:512], genres=str(r.genres)[:512],
                release_year=None if pd.isna(r.release_year) else int(r.release_year),
                train_rating_count=int(r.train_rating_count or 0),
                train_avg_rating=None if pd.isna(r.train_avg_rating) else float(r.train_avg_rating),
                tmdb_id=None if pd.isna(getattr(r, "tmdbId", None)) else int(r.tmdbId),
            )
            for r in df.itertuples(index=False)
        ])
        db.commit()
    yield
    with engine.begin() as conn:
        conn.execute(text("DROP SCHEMA public CASCADE; CREATE SCHEMA public;"))


@pytest.fixture(scope="session")
def client(database) -> TestClient:
    with TestClient(app) as c:
        yield c


@pytest.fixture
def seeded_movie_ids(client) -> list[int]:
    rows = client.get("/movies", params={"page_size": 12, "sort": "popularity"}).json()
    return [m["movie_id"] for m in rows["items"]]


@pytest.fixture
def auth_client(client) -> TestClient:
    """A registered, signed-in account with a unique username per use."""
    import uuid
    tag = uuid.uuid4().hex[:8]
    r = client.post("/auth/register", json={
        "username": f"tester_{tag}", "email": f"tester_{tag}@example.com",
        "password": "testing-password-1",
    })
    assert r.status_code == 201, r.text
    token = r.json()["access_token"]

    class Authed:
        def __init__(self, inner, token):
            self.inner = inner
            self.headers = {"Authorization": f"Bearer {token}"}
            self.user = r.json()["user"]

        def _call(self, method, url, **kw):
            headers = {**self.headers, **kw.pop("headers", {})}
            return getattr(self.inner, method)(url, headers=headers, **kw)

        def get(self, url, **kw): return self._call("get", url, **kw)
        def post(self, url, **kw): return self._call("post", url, **kw)
        def put(self, url, **kw): return self._call("put", url, **kw)
        def delete(self, url, **kw): return self._call("delete", url, **kw)

    return Authed(client, token)
