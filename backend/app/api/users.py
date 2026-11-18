"""Account preferences, ratings, history and onboarding."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.entities import (
    Movie, Rating, RecommendationHistory, User, UserEmbedding, UserPreference,
)
from app.schemas.models import (
    OnboardingRequest, OnboardingResponse, PreferenceRequest, PreferenceResponse,
    RatingRequest, RatingResponse,
)
from app.services.catalog import build_responses
from app.services.recommender import get_recommendation_service, invalidate_user

router = APIRouter(prefix="/users/me", tags=["users"])


def _prefs(db: Session, user: User) -> UserPreference:
    row = db.query(UserPreference).filter(UserPreference.user_id == user.id).one_or_none()
    if row is None:
        row = UserPreference(user_id=user.id, preferred_genres="", default_model="neumf")
        db.add(row)
        db.commit()
        db.refresh(row)
    return row


def _upsert_rating(db: Session, user: User, movie_id: int, value: float) -> Rating:
    movie = db.get(Movie, movie_id)
    if movie is None:
        raise HTTPException(404, f"Movie {movie_id} not found")
    row = db.query(Rating).filter(Rating.user_id == user.id,
                                  Rating.movie_id == movie_id).one_or_none()
    if row is None:
        row = Rating(user_id=user.id, movie_id=movie_id, rating=value)
        db.add(row)
    else:
        row.rating = value
    db.commit()
    db.refresh(row)
    return row


@router.get("/preferences", response_model=PreferenceResponse)
def get_preferences(db: Session = Depends(get_db),
                    user: User = Depends(get_current_user)) -> PreferenceResponse:
    row = _prefs(db, user)
    return PreferenceResponse(
        preferred_genres=[g for g in row.preferred_genres.split(",") if g],
        default_model=row.default_model, updated_at=row.updated_at)


@router.put("/preferences", response_model=PreferenceResponse)
def put_preferences(payload: PreferenceRequest, db: Session = Depends(get_db),
                    user: User = Depends(get_current_user)) -> PreferenceResponse:
    known = set(get_recommendation_service().ml.genre_columns)
    unknown = [g for g in payload.preferred_genres if g not in known]
    if unknown:
        raise HTTPException(422, f"Unknown genres: {unknown}")
    row = _prefs(db, user)
    row.preferred_genres = ",".join(payload.preferred_genres)
    row.default_model = payload.default_model
    db.commit()
    db.refresh(row)
    invalidate_user(user.id)
    return PreferenceResponse(
        preferred_genres=[g for g in row.preferred_genres.split(",") if g],
        default_model=row.default_model, updated_at=row.updated_at)


@router.post("/ratings", response_model=RatingResponse, status_code=201)
def submit_rating(payload: RatingRequest, db: Session = Depends(get_db),
                  user: User = Depends(get_current_user)) -> RatingResponse:
    row = _upsert_rating(db, user, payload.movie_id, payload.rating)
    invalidate_user(user.id)
    # Mark the stored embedding stale and refit immediately: fold-in is cheap.
    svc = get_recommendation_service()
    svc.fit_and_store_vectors(db, user)
    movie = db.get(Movie, payload.movie_id)
    return RatingResponse(movie_id=row.movie_id, title=movie.title if movie else None,
                          rating=row.rating, created_at=row.created_at,
                          updated_at=row.updated_at)


@router.delete("/ratings/{movie_id}", status_code=204)
def delete_rating(movie_id: int, db: Session = Depends(get_db),
                  user: User = Depends(get_current_user)) -> None:
    row = db.query(Rating).filter(Rating.user_id == user.id,
                                  Rating.movie_id == movie_id).one_or_none()
    if row is None:
        raise HTTPException(404, "You have not rated that movie")
    db.delete(row)
    db.commit()
    invalidate_user(user.id)
    get_recommendation_service().fit_and_store_vectors(db, user)


@router.get("/ratings")
def my_ratings(db: Session = Depends(get_db), user: User = Depends(get_current_user),
               limit: int = Query(100, ge=1, le=500)) -> dict:
    rows = (db.query(Rating).filter(Rating.user_id == user.id)
            .order_by(Rating.updated_at.desc()).limit(limit).all())
    movies = {m.movie_id: m for m in db.query(Movie).filter(
        Movie.movie_id.in_([r.movie_id for r in rows])).all()} if rows else {}
    ordered = [movies[r.movie_id] for r in rows if r.movie_id in movies]
    responses = build_responses(db, ordered, {r.movie_id: r.rating for r in rows})
    return {"count": len(responses), "items": [r.model_dump() for r in responses]}


@router.get("/history")
def my_history(db: Session = Depends(get_db), user: User = Depends(get_current_user),
               limit: int = Query(50, ge=1, le=200)) -> dict:
    rows = (db.query(RecommendationHistory)
            .filter(RecommendationHistory.user_id == user.id)
            .order_by(RecommendationHistory.created_at.desc()).limit(limit).all())
    movies = {m.movie_id: m for m in db.query(Movie).filter(
        Movie.movie_id.in_([r.movie_id for r in rows])).all()} if rows else {}
    return {
        "count": len(rows),
        "items": [{
            "movie_id": r.movie_id,
            "title": movies[r.movie_id].title if r.movie_id in movies else None,
            "score": r.recommendation_score, "rank": r.rank,
            "model_name": r.model_name, "created_at": r.created_at,
        } for r in rows],
    }


@router.get("/status")
def personalisation_status(db: Session = Depends(get_db),
                           user: User = Depends(get_current_user)) -> dict:
    emb = db.query(UserEmbedding).filter(UserEmbedding.user_id == user.id).one_or_none()
    n_ratings = db.query(Rating).filter(Rating.user_id == user.id).count()
    return {
        "onboarded": user.onboarded,
        "ratings_submitted": n_ratings,
        "movielens_user_id": user.movielens_user_id,
        "embedding_fitted": emb is not None,
        "embedding_ratings": emb.n_ratings if emb else 0,
        "embedding_updated_at": emb.updated_at if emb else None,
        "personalisation_available": emb is not None or user.movielens_user_id is not None,
        "method": ("dataset profile" if user.movielens_user_id
                   else "fold-in user embedding" if emb else "popularity fallback"),
    }


@router.post("/onboarding", response_model=OnboardingResponse)
def onboarding(payload: OnboardingRequest, db: Session = Depends(get_db),
               user: User = Depends(get_current_user)) -> OnboardingResponse:
    known = set(get_recommendation_service().ml.genre_columns)
    unknown = [g for g in payload.preferred_genres if g not in known]
    if unknown:
        raise HTTPException(422, f"Unknown genres: {unknown}")

    row = _prefs(db, user)
    row.preferred_genres = ",".join(payload.preferred_genres)

    recorded = 0
    for r in payload.ratings:
        _upsert_rating(db, user, r.movie_id, r.rating)
        recorded += 1

    user.onboarded = True
    db.commit()
    invalidate_user(user.id)

    fitted, detail = get_recommendation_service().fit_and_store_vectors(db, user)
    return OnboardingResponse(
        onboarded=True, ratings_recorded=recorded, embedding_fitted=fitted,
        embedding_detail=detail,
        personalisation_available=fitted or user.movielens_user_id is not None)
