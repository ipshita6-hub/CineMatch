"""Movie discovery: search, filtering, pagination, detail."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.api.deps import get_optional_user
from app.db.session import get_db
from app.models.entities import Movie, Rating, User
from app.schemas.models import MovieDetailResponse, MovieListResponse
from app.services.catalog import build_responses, split_genres
from app.services.recommender import get_recommendation_service

router = APIRouter(prefix="/movies", tags=["movies"])

SORTS = {
    "popularity": Movie.train_rating_count.desc(),
    "rating": Movie.train_avg_rating.desc().nullslast(),
    "year": Movie.release_year.desc().nullslast(),
    "title": Movie.title.asc(),
}


def _user_ratings(db: Session, user: User | None, movie_ids: list[int]) -> dict[int, float]:
    if user is None or not movie_ids:
        return {}
    rows = db.query(Rating.movie_id, Rating.rating).filter(
        Rating.user_id == user.id, Rating.movie_id.in_(movie_ids)).all()
    return {m: r for m, r in rows}


@router.get("", response_model=MovieListResponse)
def list_movies(
    search: str | None = Query(None, max_length=200),
    genre: str | None = Query(None, max_length=64),
    min_year: int | None = Query(None, ge=1874, le=2100),
    max_year: int | None = Query(None, ge=1874, le=2100),
    min_ratings: int = Query(0, ge=0),
    sort: str = Query("popularity"),
    page: int = Query(1, ge=1),
    page_size: int = Query(24, ge=1, le=100),
    db: Session = Depends(get_db),
    user: User | None = Depends(get_optional_user),
) -> MovieListResponse:
    if sort not in SORTS:
        raise HTTPException(422, f"sort must be one of {sorted(SORTS)}")

    q = db.query(Movie)
    if search:
        q = q.filter(Movie.title.ilike(f"%{search}%"))
    if genre:
        q = q.filter(Movie.genres.ilike(f"%{genre}%"))
    if min_year is not None:
        q = q.filter(Movie.release_year >= min_year)
    if max_year is not None:
        q = q.filter(Movie.release_year <= max_year)
    if min_ratings:
        q = q.filter(Movie.train_rating_count >= min_ratings)

    total = q.with_entities(func.count(Movie.movie_id)).scalar() or 0
    rows = q.order_by(SORTS[sort]).offset((page - 1) * page_size).limit(page_size).all()
    ratings = _user_ratings(db, user, [m.movie_id for m in rows])

    return MovieListResponse(
        items=build_responses(db, rows, ratings), total=int(total), page=page,
        page_size=page_size, pages=max(1, (int(total) + page_size - 1) // page_size),
    )


@router.get("/genres", response_model=list[str])
def genres() -> list[str]:
    return sorted(get_recommendation_service().ml.genre_columns)


@router.get("/{movie_id}", response_model=MovieDetailResponse)
def movie_detail(
    movie_id: int,
    db: Session = Depends(get_db),
    user: User | None = Depends(get_optional_user),
) -> MovieDetailResponse:
    movie = db.get(Movie, movie_id)
    if movie is None:
        raise HTTPException(404, f"Movie {movie_id} not found")

    svc = get_recommendation_service()
    ratings = _user_ratings(db, user, [movie_id])
    base = build_responses(db, [movie], ratings)[0]

    similar: list = []
    if movie.movie_idx is not None:
        sims = svc.ml.similar_by_genre(int(movie.movie_idx), k=8)
        sim_ids = [s["movie_id"] for s in sims]
        sim_rows = db.query(Movie).filter(Movie.movie_id.in_(sim_ids)).all()
        by_id = {m.movie_id: m for m in sim_rows}
        ordered = [by_id[i] for i in sim_ids if i in by_id]
        similar = build_responses(db, ordered, _user_ratings(db, user, sim_ids))

    prediction = {"status": "unavailable"}
    if movie.movie_idx is not None:
        user_idx = None
        vectors = None
        if user is not None:
            if user.movielens_user_id:
                user_idx = svc.ml.userid_to_idx.get(int(user.movielens_user_id))
            else:
                vectors = svc.load_vectors(db, user)
        if user_idx is not None or vectors is not None:
            prediction = svc.ml.predict_rating(int(movie.movie_idx), user_idx, vectors)

    return MovieDetailResponse(
        **base.model_dump(),
        predicted_rating=prediction.get("predicted_rating"),
        predicted_rating_scale=prediction.get("rating_scale"),
        predicted_rating_status=prediction.get("status", "unavailable"),
        similar_movies=similar,
    )
