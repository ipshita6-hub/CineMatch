"""Optional TMDB metadata enrichment.

Design rules:
  * The application is fully functional with no API key: posters fall back to
    deterministic genre-based placeholders generated in the frontend.
  * MovieLens ships links.csv with real tmdbId values, so lookups are by ID -
    no fuzzy title matching, no risk of attaching the wrong film's artwork.
  * Results (including failures) are cached in PostgreSQL.
  * A TMDB outage must never break a request: every call is wrapped and the
    response degrades to placeholder artwork.
"""

from __future__ import annotations

import logging
from concurrent.futures import ThreadPoolExecutor

import httpx
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.entities import Movie, MovieMetadataCache

logger = logging.getLogger(__name__)


class TMDBService:
    # Cold lookups are fetched concurrently and capped per request so a long
    # result page cannot turn into a long serial chain of HTTP calls.
    MAX_INLINE_LOOKUPS = 24
    POOL_SIZE = 8

    def __init__(self) -> None:
        self.enabled = settings.tmdb_enabled
        self._client: httpx.Client | None = None
        self.failures = 0
        self.lookups = 0
        self.skipped_over_budget = 0
        self.last_status: int | str | None = None

    @property
    def client(self) -> httpx.Client:
        if self._client is None:
            self._client = httpx.Client(
                timeout=settings.tmdb_timeout_seconds,
                limits=httpx.Limits(max_connections=self.POOL_SIZE,
                                    max_keepalive_connections=self.POOL_SIZE),
            )
        return self._client

    def close(self) -> None:
        if self._client is not None:
            self._client.close()
            self._client = None

    def _fetch(self, tmdb_id: int) -> dict | None:
        self.lookups += 1
        try:
            r = self.client.get(
                f"{settings.tmdb_base_url}/movie/{tmdb_id}",
                params={"api_key": settings.tmdb_api_key},
            )
            if r.status_code != 200:
                # A non-200 is a failure too. Counting only exceptions meant a
                # rejected API key (401) reported zero failures, which made a
                # misconfigured key look like a clean run.
                self.failures += 1
                self.last_status = r.status_code
                logger.warning("tmdb lookup %s returned %s", tmdb_id, r.status_code)
                return None
            self.last_status = 200
            return r.json()
        except Exception as exc:                      # network, timeout, parse
            self.failures += 1
            self.last_status = "exception"
            logger.warning("tmdb lookup failed for %s: %s", tmdb_id, exc)
            return None

    def enrich(self, db: Session, movies: list[Movie]) -> dict[int, MovieMetadataCache]:
        """Return cached metadata for the given movies, fetching what is missing."""
        if not movies:
            return {}
        ids = [m.movie_id for m in movies]
        cached = {
            c.movie_id: c
            for c in db.query(MovieMetadataCache).filter(MovieMetadataCache.movie_id.in_(ids)).all()
        }
        if not self.enabled:
            return cached

        missing = [m for m in movies if m.movie_id not in cached and m.tmdb_id]
        if len(missing) > self.MAX_INLINE_LOOKUPS:
            self.skipped_over_budget += len(missing) - self.MAX_INLINE_LOOKUPS
            missing = missing[:self.MAX_INLINE_LOOKUPS]

        if missing:
            with ThreadPoolExecutor(max_workers=self.POOL_SIZE) as pool:
                fetched = list(pool.map(lambda m: self._fetch(int(m.tmdb_id)), missing))
        else:
            fetched = []

        for movie, data in zip(missing, fetched):
            if data is None:
                entry = MovieMetadataCache(movie_id=movie.movie_id, lookup_failed=True,
                                           source="tmdb")
            else:
                poster = data.get("poster_path")
                backdrop = data.get("backdrop_path")
                entry = MovieMetadataCache(
                    movie_id=movie.movie_id,
                    poster_url=f"{settings.tmdb_image_base}{poster}" if poster else None,
                    backdrop_url=(f"https://image.tmdb.org/t/p/w1280{backdrop}"
                                  if backdrop else None),
                    overview=(data.get("overview") or None),
                    tmdb_rating=data.get("vote_average"),
                    runtime=data.get("runtime"),
                    lookup_failed=False, source="tmdb",
                )
            db.merge(entry)
            cached[movie.movie_id] = entry
        if missing:
            db.commit()
        return cached

    def status(self) -> dict:
        return {"enabled": self.enabled, "lookups": self.lookups,
                "failures": self.failures,
                "last_status": self.last_status,
                "skipped_over_budget": self.skipped_over_budget,
                "max_inline_lookups": self.MAX_INLINE_LOOKUPS}


tmdb_service = TMDBService()
