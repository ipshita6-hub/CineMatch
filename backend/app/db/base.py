"""Import side-effect module so Alembic/metadata sees every table."""

from app.db.session import Base  # noqa: F401
from app.models.entities import (  # noqa: F401
    Movie, MovieMetadataCache, Rating, RecommendationHistory, User, UserEmbedding,
    UserPreference, UserSession,
)
