"""Relational schema.

MovieLens identifiers are anonymised dataset identifiers and are deliberately
kept separate from application accounts: `users.movielens_user_id` is an
OPTIONAL link to a dataset profile, and `users.embedding` holds the fold-in
vectors fitted for accounts that have no dataset profile.
"""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import (
    BigInteger, Boolean, DateTime, Float, ForeignKey, Index, Integer, String, Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    username: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    # Optional association with a MovieLens profile (demo mode).
    movielens_user_id: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)
    onboarded: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)

    preferences: Mapped["UserPreference"] = relationship(
        back_populates="user", uselist=False, cascade="all, delete-orphan")
    ratings: Mapped[list["Rating"]] = relationship(
        back_populates="user", cascade="all, delete-orphan")
    embedding: Mapped["UserEmbedding"] = relationship(
        back_populates="user", uselist=False, cascade="all, delete-orphan")
    sessions: Mapped[list["UserSession"]] = relationship(
        back_populates="user", cascade="all, delete-orphan")


class Movie(Base):
    __tablename__ = "movies"

    movie_id: Mapped[int] = mapped_column(Integer, primary_key=True)   # MovieLens movieId
    movie_idx: Mapped[int | None] = mapped_column(Integer, index=True, nullable=True)
    title: Mapped[str] = mapped_column(String(512), nullable=False, index=True)
    genres: Mapped[str] = mapped_column(String(512), default="(no genres listed)")
    release_year: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)
    train_rating_count: Mapped[int] = mapped_column(Integer, default=0, index=True)
    train_avg_rating: Mapped[float | None] = mapped_column(Float, nullable=True)
    tmdb_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    imdb_id: Mapped[int | None] = mapped_column(Integer, nullable=True)

    metadata_cache: Mapped["MovieMetadataCache"] = relationship(
        back_populates="movie", uselist=False, cascade="all, delete-orphan")


Index("ix_movies_popularity", Movie.train_rating_count.desc())


class Rating(Base):
    """Ratings submitted inside the application (not the dataset's ratings)."""

    __tablename__ = "ratings"
    __table_args__ = (UniqueConstraint("user_id", "movie_id", name="uq_rating_user_movie"),)

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    movie_id: Mapped[int] = mapped_column(ForeignKey("movies.movie_id", ondelete="CASCADE"), index=True)
    rating: Mapped[float] = mapped_column(Float, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow,
                                                 onupdate=_utcnow)

    user: Mapped[User] = relationship(back_populates="ratings")
    movie: Mapped[Movie] = relationship()


class UserPreference(Base):
    __tablename__ = "user_preferences"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"),
                                         unique=True, index=True)
    preferred_genres: Mapped[str] = mapped_column(Text, default="")   # comma separated
    default_model: Mapped[str] = mapped_column(String(32), default="neumf")
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow,
                                                 onupdate=_utcnow)

    user: Mapped[User] = relationship(back_populates="preferences")


class UserEmbedding(Base):
    """Fold-in vectors for an application account (JSON-encoded float arrays)."""

    __tablename__ = "user_embeddings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"),
                                         unique=True, index=True)
    vectors: Mapped[str] = mapped_column(Text, nullable=False)
    n_ratings: Mapped[int] = mapped_column(Integer, default=0)
    model_version: Mapped[str] = mapped_column(String(64), default="neumf")
    is_stale: Mapped[bool] = mapped_column(Boolean, default=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow,
                                                 onupdate=_utcnow)

    user: Mapped[User] = relationship(back_populates="embedding")


class RecommendationHistory(Base):
    __tablename__ = "recommendation_history"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    movie_id: Mapped[int] = mapped_column(Integer, index=True)
    recommendation_score: Mapped[float] = mapped_column(Float)
    rank: Mapped[int] = mapped_column(Integer)
    model_name: Mapped[str] = mapped_column(String(32), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow,
                                                 index=True)


class UserSession(Base):
    __tablename__ = "user_sessions"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    token_id: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    revoked: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))

    user: Mapped[User] = relationship(back_populates="sessions")


class MovieMetadataCache(Base):
    """Cached TMDB enrichment. Absent rows simply mean 'not fetched yet'."""

    __tablename__ = "movie_metadata_cache"

    movie_id: Mapped[int] = mapped_column(ForeignKey("movies.movie_id", ondelete="CASCADE"),
                                          primary_key=True)
    poster_url: Mapped[str | None] = mapped_column(String(512), nullable=True)
    backdrop_url: Mapped[str | None] = mapped_column(String(512), nullable=True)
    overview: Mapped[str | None] = mapped_column(Text, nullable=True)
    tmdb_rating: Mapped[float | None] = mapped_column(Float, nullable=True)
    runtime: Mapped[int | None] = mapped_column(Integer, nullable=True)
    source: Mapped[str] = mapped_column(String(32), default="tmdb")
    fetched_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
    lookup_failed: Mapped[bool] = mapped_column(Boolean, default=False)

    movie: Mapped[Movie] = relationship(back_populates="metadata_cache")
