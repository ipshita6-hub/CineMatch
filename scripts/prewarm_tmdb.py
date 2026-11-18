"""Warm the TMDB metadata cache for the most-rated movies.

Running this once removes cold-lookup latency from the interactive paths.
Safe to re-run: already-cached movies are skipped.

Usage:  python scripts/prewarm_tmdb.py [limit]
"""

from __future__ import annotations

import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "backend"))

from app.db.session import SessionLocal  # noqa: E402
from app.models.entities import Movie, MovieMetadataCache  # noqa: E402
from app.services.tmdb import tmdb_service  # noqa: E402


def main() -> None:
    limit = int(sys.argv[1]) if len(sys.argv) > 1 else 2000
    if not tmdb_service.enabled:
        print("TMDB_API_KEY is not set; nothing to prewarm. "
              "The application will use genre placeholders.")
        return

    with SessionLocal() as db:
        cached = {c.movie_id for c in db.query(MovieMetadataCache.movie_id).all()}
        movies = (db.query(Movie)
                  .filter(Movie.tmdb_id.isnot(None))
                  .order_by(Movie.train_rating_count.desc())
                  .limit(limit).all())
        todo = [m for m in movies if m.movie_id not in cached]
        print(f"{len(todo)} of the top {limit} movies need a TMDB lookup")

        t0 = time.time()
        done = 0
        batch_size = tmdb_service.MAX_INLINE_LOOKUPS
        for i in range(0, len(todo), batch_size):
            tmdb_service.enrich(db, todo[i:i + batch_size])
            done += len(todo[i:i + batch_size])
            if done % (batch_size * 10) == 0 or done >= len(todo):
                print(f"  {done}/{len(todo)} ({time.time() - t0:.0f}s)", flush=True)

        total = db.query(MovieMetadataCache).count()
        failed = db.query(MovieMetadataCache).filter(
            MovieMetadataCache.lookup_failed.is_(True)).count()
    print(f"Cache now holds {total} entries ({failed} lookups failed) "
          f"in {time.time() - t0:.0f}s")


if __name__ == "__main__":
    main()
