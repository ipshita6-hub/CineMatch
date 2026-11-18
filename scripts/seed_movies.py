"""Seed the `movies` table from the preprocessing artifacts.

Idempotent: re-running updates existing rows rather than duplicating them.
Usage:  python scripts/seed_movies.py
"""

from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
from sqlalchemy import text

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "backend"))

from app.db.session import SessionLocal, engine  # noqa: E402
from ml import config as C  # noqa: E402


def main() -> None:
    df = pd.read_csv(C.MOVIES_FEATURES_CSV)
    rows = []
    for r in df.itertuples(index=False):
        rows.append({
            "movie_id": int(r.movieId),
            "movie_idx": None if pd.isna(r.movie_idx) else int(r.movie_idx),
            "title": str(r.title)[:512],
            "genres": str(r.genres)[:512],
            "release_year": None if pd.isna(r.release_year) else int(r.release_year),
            "train_rating_count": int(r.train_rating_count or 0),
            "train_avg_rating": None if pd.isna(r.train_avg_rating) else float(r.train_avg_rating),
            "tmdb_id": None if pd.isna(getattr(r, "tmdbId", None)) else int(r.tmdbId),
            "imdb_id": None if pd.isna(getattr(r, "imdbId", None)) else int(r.imdbId),
        })

    stmt = text("""
        INSERT INTO movies (movie_id, movie_idx, title, genres, release_year,
                            train_rating_count, train_avg_rating, tmdb_id, imdb_id)
        VALUES (:movie_id, :movie_idx, :title, :genres, :release_year,
                :train_rating_count, :train_avg_rating, :tmdb_id, :imdb_id)
        ON CONFLICT (movie_id) DO UPDATE SET
            movie_idx = EXCLUDED.movie_idx,
            title = EXCLUDED.title,
            genres = EXCLUDED.genres,
            release_year = EXCLUDED.release_year,
            train_rating_count = EXCLUDED.train_rating_count,
            train_avg_rating = EXCLUDED.train_avg_rating,
            tmdb_id = EXCLUDED.tmdb_id,
            imdb_id = EXCLUDED.imdb_id
    """)
    with engine.begin() as conn:
        for i in range(0, len(rows), 2000):
            conn.execute(stmt, rows[i:i + 2000])

    with SessionLocal() as db:
        total = db.execute(text("SELECT count(*) FROM movies")).scalar()
        in_model = db.execute(
            text("SELECT count(*) FROM movies WHERE movie_idx IS NOT NULL")).scalar()
        with_tmdb = db.execute(
            text("SELECT count(*) FROM movies WHERE tmdb_id IS NOT NULL")).scalar()
    print(f"Seeded {total} movies ({in_model} in the model index, {with_tmdb} with a TMDB id)")


if __name__ == "__main__":
    main()
