"""Pydantic request/response schemas."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

ModelName = Literal["neumf", "mf", "popularity", "hybrid"]


# ----------------------------------------------------------------- auth
class RegisterRequest(BaseModel):
    username: str = Field(min_length=3, max_length=64, pattern=r"^[A-Za-z0-9_.-]+$")
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)


class LoginRequest(BaseModel):
    username: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_at: datetime
    user: "UserResponse"


class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    username: str
    email: EmailStr
    onboarded: bool
    movielens_user_id: int | None = None
    created_at: datetime


# ---------------------------------------------------------------- movies
class MovieResponse(BaseModel):
    movie_id: int
    title: str
    genres: list[str]
    release_year: int | None = None
    dataset_rating_count: int = 0
    dataset_avg_rating: float | None = None
    poster_url: str | None = None
    backdrop_url: str | None = None
    overview: str | None = None
    tmdb_rating: float | None = None
    poster_source: Literal["tmdb", "placeholder"] = "placeholder"
    user_rating: float | None = None


class MovieListResponse(BaseModel):
    items: list[MovieResponse]
    total: int
    page: int
    page_size: int
    pages: int


class MovieDetailResponse(MovieResponse):
    predicted_rating: float | None = None
    predicted_rating_scale: list[float] | None = None
    predicted_rating_status: str = "unavailable"
    similar_movies: list[MovieResponse] = []


# ------------------------------------------------------- recommendations
class RecommendationItem(MovieResponse):
    rank: int
    score: float
    model: str
    explanation: str


class RecommendationResponse(BaseModel):
    user_id: int | None = None
    movielens_user_id: int | None = None
    model_requested: str
    model_used: str
    fallback_used: bool
    fallback_reason: str | None = None
    personalised: bool
    count: int
    generated_in_ms: float
    cached: bool = False
    items: list[RecommendationItem]


# ------------------------------------------------------------- prediction
class PredictRequest(BaseModel):
    user_id: int | None = Field(default=None, description="MovieLens user id (dataset profile)")
    movie_id: int

    @field_validator("movie_id")
    @classmethod
    def positive(cls, v: int) -> int:
        if v <= 0:
            raise ValueError("movie_id must be positive")
        return v


class PredictResponse(BaseModel):
    movie_id: int
    title: str | None = None
    predicted_rating: float | None = None
    rating_scale: list[float] | None = None
    model: str
    source: str
    status: str
    detail: str | None = None


# ------------------------------------------------------------ preferences
class PreferenceRequest(BaseModel):
    preferred_genres: list[str] = []
    default_model: ModelName = "neumf"


class PreferenceResponse(BaseModel):
    preferred_genres: list[str]
    default_model: str
    updated_at: datetime | None = None


class RatingRequest(BaseModel):
    movie_id: int
    rating: float = Field(ge=0.5, le=5.0)

    @field_validator("rating")
    @classmethod
    def half_star(cls, v: float) -> float:
        if round(v * 2) != v * 2:
            raise ValueError("rating must be on the MovieLens half-star scale")
        return v


class RatingResponse(BaseModel):
    movie_id: int
    title: str | None = None
    rating: float
    created_at: datetime
    updated_at: datetime


class OnboardingRequest(BaseModel):
    preferred_genres: list[str] = []
    ratings: list[RatingRequest] = []


class OnboardingResponse(BaseModel):
    onboarded: bool
    ratings_recorded: int
    embedding_fitted: bool
    embedding_detail: str
    personalisation_available: bool


# ---------------------------------------------------------------- system
class HealthResponse(BaseModel):
    status: str
    api_version: str
    database: str
    models_loaded: dict[str, bool]
    active_model_version: str | None
    dataset: str


class MetricsResponse(BaseModel):
    status: str
    evaluation: dict[str, Any] | None = None
    dataset: dict[str, Any] | None = None
    detail: str | None = None
