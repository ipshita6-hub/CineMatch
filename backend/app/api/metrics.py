"""Dashboard metrics.

Every number served here is read from an artifact produced by an actual
evaluation run. Nothing is synthesised: when a metric has not been computed,
the response says "Not evaluated" instead of inventing a value.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.entities import Rating, RecommendationHistory, User
from app.services.cache import TTLCache
from app.services.latency import latency_tracker
from app.services.recommender import recommendation_cache
from app.services.tmdb import tmdb_service
from ml import config as C
from ml.inference.recommender import get_service

router = APIRouter(tags=["metrics"])

NOT_EVALUATED = "Not evaluated"


@router.get("/metrics")
def metrics() -> dict:
    ml = get_service()
    ev = ml.evaluation
    if ev is None:
        return {
            "status": NOT_EVALUATED,
            "detail": ("No evaluation artifact found. Run "
                       "`python -m ml.evaluation.evaluate_all` to produce it."),
            "models": {}, "rating_prediction": {"status": NOT_EVALUATED},
        }

    flat = {}
    for name, m in ev["models"].items():
        flat[name] = {
            "HR@10": m.get(f"HR@{C.TOP_K}", NOT_EVALUATED),
            "NDCG@10": m.get(f"NDCG@{C.TOP_K}", NOT_EVALUATED),
            "Precision@10": m.get(f"Precision@{C.TOP_K}", NOT_EVALUATED),
            "Recall@10": m.get(f"Recall@{C.TOP_K}", NOT_EVALUATED),
            "F1@10": m.get(f"F1@{C.TOP_K}", NOT_EVALUATED),
            "MRR": m.get("MRR", NOT_EVALUATED),
            "ROC_AUC": m.get("ROC_AUC", NOT_EVALUATED),
            "RMSE": NOT_EVALUATED,   # ranking models do not produce star ratings
            "personalised": m.get("personalised", False),
            "description": m.get("description", ""),
            "evaluated_users": m.get("evaluated_users"),
        }
    rating = ev.get("rating_prediction", {"status": NOT_EVALUATED})
    if rating.get("RMSE") is not None and "RatingPredictor" not in flat:
        flat["RatingPredictor"] = {
            **{k: NOT_EVALUATED for k in
               ["HR@10", "NDCG@10", "Precision@10", "Recall@10", "F1@10", "MRR", "ROC_AUC"]},
            "RMSE": rating.get("RMSE"), "MAE": rating.get("MAE"),
            "personalised": True,
            "description": "Explicit rating prediction (separate calibrated model).",
            "evaluated_users": rating.get("evaluated_ratings"),
        }

    return {
        "status": "ok",
        "generated_at": ev.get("generated_at"),
        "dataset": ev.get("dataset"),
        "dataset_note": ev.get("dataset_note"),
        "protocol": ev.get("protocol"),
        "dataset_shape": ev.get("dataset_shape"),
        "models": flat,
        "rating_prediction": rating,
        "improvements": ev.get("improvements", {}),
        "hybrid": ml.hybrid_evaluation or {"status": NOT_EVALUATED},
        "recommendation_analytics": ev.get("recommendation_analytics", {}),
    }


@router.get("/metrics/eda")
def eda_metrics() -> dict:
    eda = get_service().eda
    if eda is None:
        return {"status": NOT_EVALUATED,
                "detail": "Run the preprocessing pipeline to produce eda_summary.json."}
    return {"status": "ok", **eda}


@router.get("/metrics/training")
def training_metrics() -> dict:
    hist = get_service().histories
    out = {}
    for key, value in hist.items():
        out[key] = value if value is not None else {"status": NOT_EVALUATED}
    return {"status": "ok", "histories": out}


@router.get("/metrics/experiments")
def experiments() -> dict:
    """Only experiments that were actually executed appear here."""
    exps = get_service().experiments
    return {"status": "ok" if exps else NOT_EVALUATED, "count": len(exps), "experiments": exps}


@router.get("/metrics/latency")
def latency() -> dict:
    """Measured request latency from this process (no targets, no estimates)."""
    snapshot = latency_tracker.snapshot()
    offline = get_service()._read_json(C.LATENCY_JSON)
    return {
        "status": "ok" if snapshot else "no requests recorded yet",
        "live": snapshot,
        "benchmark": offline or {"status": NOT_EVALUATED,
                                 "detail": "Run scripts/benchmark_latency.py"},
        "target_ms": 200,
        "note": "Values are measured on this machine; they are not a claim about production.",
        "cache": recommendation_cache.stats(),
    }


@router.get("/metrics/app")
def app_metrics(db: Session = Depends(get_db)) -> dict:
    """Live application usage (not model quality)."""
    return {
        "status": "ok",
        "registered_users": db.query(func.count(User.id)).scalar() or 0,
        "app_ratings": db.query(func.count(Rating.id)).scalar() or 0,
        "recommendations_served": db.query(func.count(RecommendationHistory.id)).scalar() or 0,
        "tmdb": tmdb_service.status(),
    }
