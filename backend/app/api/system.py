"""Health and model-information endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.session import get_db
from app.schemas.models import HealthResponse
from ml import config as C
from ml.inference.recommender import get_service

router = APIRouter(tags=["system"])


@router.get("/health", response_model=HealthResponse)
def health(db: Session = Depends(get_db)) -> HealthResponse:
    try:
        db.execute(text("SELECT 1"))
        database = "connected"
    except Exception as exc:
        database = f"error: {type(exc).__name__}"

    try:
        ml = get_service()
        loaded = {
            "neumf": ml.neumf is not None,
            "matrix_factorization": ml.mf is not None,
            "rating_predictor": ml.rating_model is not None,
            "popularity": True,
        }
        version = (ml.neumf_ckpt or {}).get("saved_at") if ml.neumf_ckpt else None
        dataset = C.DATASET_NAME
    except Exception as exc:
        loaded = {"neumf": False, "matrix_factorization": False,
                  "rating_predictor": False, "popularity": False}
        version = None
        dataset = f"unavailable: {type(exc).__name__}"

    healthy = database == "connected" and any(loaded.values())
    return HealthResponse(
        status="ok" if healthy else "degraded",
        api_version=settings.api_version,
        database=database,
        models_loaded=loaded,
        active_model_version=version,
        dataset=dataset,
    )


@router.get("/model/info")
def model_info() -> dict:
    return get_service().model_info()
