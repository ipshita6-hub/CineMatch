"""Recommendation service: the bridge between the ML layer and the API.

Responsibilities
  * resolve WHICH user representation to use (dataset profile, fold-in vectors,
    or nothing at all) and fall back gracefully
  * exclude everything the user has already seen - dataset history AND ratings
    submitted inside the application
  * attach catalog metadata and an honest explanation to each item
  * cache results, and invalidate the cache when a user rates something
"""

from __future__ import annotations

import logging
import time

import numpy as np
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.entities import Movie, Rating, RecommendationHistory, User, UserEmbedding
from app.schemas.models import RecommendationItem, RecommendationResponse
from app.services.cache import TTLCache
from app.services.catalog import build_responses, movies_by_ids
from ml.inference.recommender import (
    MODEL_HYBRID, MODEL_MF, MODEL_NEUMF, MODEL_POPULARITY, RecommenderService, UserVectors,
    get_service,
)

logger = logging.getLogger(__name__)
recommendation_cache = TTLCache(ttl_seconds=settings.recommendation_cache_ttl)

MIN_RATINGS_FOR_FOLD_IN = 3

EXPLANATIONS = {
    MODEL_NEUMF: ("NeuMF learned this from patterns in who rates what: users whose rating "
                  "history resembles yours rated this highly. It does not read plots or genres."),
    MODEL_MF: ("Matrix factorization placed this movie close to your taste vector in the "
               "learned latent space."),
    MODEL_POPULARITY: ("A popularity fallback: this is among the most-rated movies in the "
                       "training data, not a personalised result."),
    MODEL_HYBRID: ("Hybrid re-ranking: the NeuMF score blended with genre similarity to the "
                   "movies you rated highly and a popularity signal."),
}


def _cache_key(scope: str, model: str, limit: int, genre: str | None,
               min_year: int | None, max_year: int | None) -> str:
    return f"{scope}|{model}|{limit}|{genre or '-'}|{min_year or '-'}|{max_year or '-'}"


def invalidate_user(user_id: int) -> None:
    recommendation_cache.invalidate_prefix(f"app:{user_id}|")


class RecommendationService:
    def __init__(self) -> None:
        self.ml: RecommenderService = get_service()

    # ------------------------------------------------------------- helpers
    def app_user_excluded_idx(self, db: Session, user: User) -> np.ndarray:
        """movie_idx values the account has already rated inside the app."""
        rows = (db.query(Movie.movie_idx)
                .join(Rating, Rating.movie_id == Movie.movie_id)
                .filter(Rating.user_id == user.id, Movie.movie_idx.isnot(None)).all())
        return np.array([r[0] for r in rows], dtype=np.int64)

    def load_vectors(self, db: Session, user: User) -> UserVectors | None:
        row = db.query(UserEmbedding).filter(UserEmbedding.user_id == user.id).one_or_none()
        if row is None:
            return None
        try:
            return UserVectors.from_json(row.vectors)
        except Exception:
            logger.exception("corrupt embedding row for user %s", user.id)
            return None

    def fit_and_store_vectors(self, db: Session, user: User) -> tuple[bool, str]:
        """Fit fold-in vectors from the account's in-app ratings."""
        if self.ml.neumf is None:
            return False, "NeuMF checkpoint is not loaded; personalisation unavailable."
        rows = (db.query(Movie.movie_idx, Rating.rating)
                .join(Rating, Rating.movie_id == Movie.movie_id)
                .filter(Rating.user_id == user.id, Movie.movie_idx.isnot(None)).all())
        if len(rows) < MIN_RATINGS_FOR_FOLD_IN:
            return False, (f"{len(rows)} rating(s) recorded; at least "
                           f"{MIN_RATINGS_FOR_FOLD_IN} are needed before a user embedding "
                           f"can be fitted. Popularity recommendations are used until then.")
        rated = [(int(idx), float(r)) for idx, r in rows]
        t0 = time.perf_counter()
        vectors = self.ml.fit_user_embedding(rated)
        took = (time.perf_counter() - t0) * 1000

        existing = db.query(UserEmbedding).filter(UserEmbedding.user_id == user.id).one_or_none()
        if existing is None:
            db.add(UserEmbedding(user_id=user.id, vectors=vectors.to_json(),
                                 n_ratings=len(rated), is_stale=False))
        else:
            existing.vectors = vectors.to_json()
            existing.n_ratings = len(rated)
            existing.is_stale = False
        db.commit()
        invalidate_user(user.id)
        return True, (f"Fitted a NeuMF user embedding from {len(rated)} ratings in "
                      f"{took:.0f} ms (item weights frozen).")

    # ------------------------------------------------------- recommendations
    def recommend(
        self, db: Session, *, model: str = MODEL_NEUMF, limit: int = 10,
        user: User | None = None, movielens_user_id: int | None = None,
        genre: str | None = None, min_year: int | None = None, max_year: int | None = None,
        record_history: bool = True,
    ) -> RecommendationResponse:
        t0 = time.perf_counter()

        user_idx: int | None = None
        vectors: UserVectors | None = None
        fallback_reason: str | None = None

        if movielens_user_id is None and user is not None and user.movielens_user_id:
            movielens_user_id = user.movielens_user_id
        if movielens_user_id is not None:
            user_idx = self.ml.userid_to_idx.get(int(movielens_user_id))
            if user_idx is None:
                fallback_reason = (f"MovieLens user {movielens_user_id} is not present in the "
                                   f"trained model; using the popularity fallback.")

        exclude = np.array([], dtype=np.int64)
        scope = "anon"
        if user is not None:
            scope = f"app:{user.id}"
            exclude = self.app_user_excluded_idx(db, user)
            if user_idx is None:
                vectors = self.load_vectors(db, user)
                if vectors is None and model in (MODEL_NEUMF, MODEL_HYBRID, MODEL_MF):
                    fallback_reason = (
                        "This account has no trained MovieLens profile and no fitted user "
                        "embedding yet. Rate a few movies to unlock personalised results.")
        elif movielens_user_id is not None:
            scope = f"ml:{movielens_user_id}"

        key = _cache_key(scope, model, limit, genre, min_year, max_year)
        cached = recommendation_cache.get(key)
        if cached is not None:
            cached = cached.model_copy(update={
                "cached": True,
                "generated_in_ms": round((time.perf_counter() - t0) * 1000, 2)})
            return cached

        requested = model
        if model in (MODEL_NEUMF, MODEL_HYBRID) and self.ml.neumf is None:
            fallback_reason = "NeuMF checkpoint not available."
            model = MODEL_POPULARITY
        if model == MODEL_MF and self.ml.mf is None:
            fallback_reason = "Matrix factorization checkpoint not available."
            model = MODEL_POPULARITY
        if model != MODEL_POPULARITY and user_idx is None and vectors is None:
            model = MODEL_POPULARITY

        try:
            raw = self.ml.top_n(model=model, user_idx=user_idx, vectors=vectors, k=limit,
                                exclude_idx=exclude, genre=genre,
                                min_year=min_year, max_year=max_year)
        except ValueError as exc:
            raise
        except Exception:
            logger.exception("scoring failed; falling back to popularity")
            fallback_reason = "Model scoring failed; served the popularity fallback."
            model = MODEL_POPULARITY
            raw = self.ml.top_n(model=MODEL_POPULARITY, k=limit, exclude_idx=exclude,
                                genre=genre, min_year=min_year, max_year=max_year)

        used = raw[0]["model"] if raw else model
        movie_ids = [r["movie_id"] for r in raw]
        movie_map = movies_by_ids(db, movie_ids)
        ordered = [movie_map[i] for i in movie_ids if i in movie_map]
        responses = {m.movie_id: r for m, r in zip(ordered, build_responses(db, ordered))}

        items: list[RecommendationItem] = []
        for r in raw:
            base = responses.get(r["movie_id"])
            if base is None:
                continue
            items.append(RecommendationItem(**base.model_dump(), rank=r["rank"],
                                            score=round(r["score"], 6), model=used,
                                            explanation=EXPLANATIONS.get(used, "")))

        if record_history and user is not None and items:
            for item in items:
                db.add(RecommendationHistory(user_id=user.id, movie_id=item.movie_id,
                                             recommendation_score=item.score, rank=item.rank,
                                             model_name=used))
            db.commit()

        response = RecommendationResponse(
            user_id=user.id if user else None,
            movielens_user_id=movielens_user_id,
            model_requested=requested,
            model_used=used,
            fallback_used=used != requested,
            fallback_reason=fallback_reason if used != requested else None,
            personalised=used in (MODEL_NEUMF, MODEL_MF, MODEL_HYBRID),
            count=len(items),
            generated_in_ms=round((time.perf_counter() - t0) * 1000, 2),
            cached=False,
            items=items,
        )
        recommendation_cache.set(key, response)
        return response


_service: RecommendationService | None = None


def get_recommendation_service() -> RecommendationService:
    global _service
    if _service is None:
        _service = RecommendationService()
    return _service
