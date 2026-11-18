"""Movie catalog helpers: DB rows + TMDB cache -> API schema objects."""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.models.entities import Movie, MovieMetadataCache
from app.schemas.models import MovieResponse
from app.services.tmdb import tmdb_service


def split_genres(raw: str | None) -> list[str]:
    if not raw or raw == "(no genres listed)":
        return []
    return [g for g in raw.split("|") if g]


def to_movie_response(
    movie: Movie, meta: MovieMetadataCache | None = None,
    user_rating: float | None = None,
) -> MovieResponse:
    poster = meta.poster_url if meta else None
    return MovieResponse(
        movie_id=movie.movie_id,
        title=movie.title,
        genres=split_genres(movie.genres),
        release_year=movie.release_year,
        dataset_rating_count=movie.train_rating_count or 0,
        dataset_avg_rating=(round(movie.train_avg_rating, 3)
                            if movie.train_avg_rating is not None else None),
        poster_url=poster,
        backdrop_url=meta.backdrop_url if meta else None,
        overview=meta.overview if meta else None,
        tmdb_rating=meta.tmdb_rating if meta else None,
        poster_source="tmdb" if poster else "placeholder",
        user_rating=user_rating,
    )


def build_responses(
    db: Session, movies: list[Movie], user_ratings: dict[int, float] | None = None,
) -> list[MovieResponse]:
    meta = tmdb_service.enrich(db, movies)
    user_ratings = user_ratings or {}
    return [
        to_movie_response(m, meta.get(m.movie_id), user_ratings.get(m.movie_id))
        for m in movies
    ]


def movies_by_ids(db: Session, movie_ids: list[int]) -> dict[int, Movie]:
    if not movie_ids:
        return {}
    rows = db.query(Movie).filter(Movie.movie_id.in_(movie_ids)).all()
    return {m.movie_id: m for m in rows}
