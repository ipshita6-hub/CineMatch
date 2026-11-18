"""Application settings, loaded from the project-root .env file."""

from __future__ import annotations

from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

PROJECT_ROOT = Path(__file__).resolve().parents[3]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=PROJECT_ROOT / ".env", env_file_encoding="utf-8", extra="ignore"
    )

    app_name: str = "Movie Recommender (NeuMF)"
    api_version: str = "1.0.0"
    log_level: str = "INFO"

    database_url: str = "postgresql+psycopg://localhost:5432/movierec"
    test_database_url: str = "postgresql+psycopg://localhost:5432/movierec_test"

    jwt_secret: str = "change-me"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 10080

    tmdb_api_key: str = ""
    tmdb_base_url: str = "https://api.themoviedb.org/3"
    tmdb_image_base: str = "https://image.tmdb.org/t/p/w500"
    tmdb_timeout_seconds: float = 4.0

    cors_origins: str = "http://localhost:5173,http://127.0.0.1:5173"
    recommendation_cache_ttl: int = 300

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    @property
    def tmdb_enabled(self) -> bool:
        return bool(self.tmdb_api_key.strip())


settings = Settings()
