"""Top-N recommendations and explicit rating prediction."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_optional_user
from app.db.session import get_db
from app.models.entities import Movie, User
from app.schemas.models import (
    ModelName, PredictRequest, PredictResponse, RecommendationResponse,
)
from app.services.recommender import get_recommendation_service

router = APIRouter(tags=["recommendations"])


@router.get("/recommendations/me", response_model=RecommendationResponse)
def my_recommendations(
    limit: int = Query(10, ge=1, le=100),
    model: ModelName = Query("neumf"),
    genre: str | None = Query(None),
    min_year: int | None = Query(None, ge=1874, le=2100),
    max_year: int | None = Query(None, ge=1874, le=2100),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> RecommendationResponse:
    """Recommendations for the signed-in application account."""
    svc = get_recommendation_service()
    try:
        return svc.recommend(db, model=model, limit=limit, user=user,
                             genre=genre, min_year=min_year, max_year=max_year)
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc


@router.get("/recommendations/{user_id}", response_model=RecommendationResponse)
def recommendations_for_dataset_user(
    user_id: int,
    limit: int = Query(10, ge=1, le=100),
    model: ModelName = Query("neumf"),
    genre: str | None = Query(None),
    min_year: int | None = Query(None, ge=1874, le=2100),
    max_year: int | None = Query(None, ge=1874, le=2100),
    db: Session = Depends(get_db),
    user: User | None = Depends(get_optional_user),
) -> RecommendationResponse:
    """Recommendations for a MovieLens dataset user id (PRD contract).

    An unknown id is not an error: the popularity fallback is served and the
    response says so explicitly.
    """
    svc = get_recommendation_service()
    try:
        return svc.recommend(db, model=model, limit=limit, user=None,
                             movielens_user_id=user_id, genre=genre,
                             min_year=min_year, max_year=max_year, record_history=False)
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc


@router.post("/predict", response_model=PredictResponse)
def predict(
    payload: PredictRequest,
    db: Session = Depends(get_db),
    user: User | None = Depends(get_optional_user),
) -> PredictResponse:
    """Predict a calibrated 0.5-5.0 rating.

    This uses the dedicated rating-prediction model, never a NeuMF ranking
    logit.
    """
    svc = get_recommendation_service()
    movie = db.get(Movie, payload.movie_id)
    if movie is None:
        raise HTTPException(404, f"Movie {payload.movie_id} not found")
    if movie.movie_idx is None:
        return PredictResponse(
            movie_id=movie.movie_id, title=movie.title, model="RatingPredictor",
            source="none", status="unavailable",
            detail=("This movie was filtered out of the modelling set (fewer than the "
                    "minimum number of ratings), so no prediction can be made."))

    user_idx = None
    vectors = None
    if payload.user_id is not None:
        user_idx = svc.ml.userid_to_idx.get(int(payload.user_id))
        if user_idx is None:
            return PredictResponse(
                movie_id=movie.movie_id, title=movie.title, model="RatingPredictor",
                source="none", status="unavailable",
                detail=f"MovieLens user {payload.user_id} is not part of the trained model.")
    elif user is not None:
        if user.movielens_user_id:
            user_idx = svc.ml.userid_to_idx.get(int(user.movielens_user_id))
        else:
            vectors = svc.load_vectors(db, user)
    if user_idx is None and vectors is None:
        return PredictResponse(
            movie_id=movie.movie_id, title=movie.title, model="RatingPredictor",
            source="none", status="unavailable",
            detail=("No user representation available. Pass a MovieLens user_id, or sign in "
                    "and rate a few movies so a user embedding can be fitted."))

    result = svc.ml.predict_rating(int(movie.movie_idx), user_idx, vectors)
    return PredictResponse(
        movie_id=movie.movie_id, title=movie.title,
        predicted_rating=result.get("predicted_rating"),
        rating_scale=result.get("rating_scale"),
        model=result.get("model", "RatingPredictor"),
        source=result.get("source", "none"),
        status=result.get("status", "unavailable"),
        detail=result.get("detail"),
    )
