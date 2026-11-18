"""FastAPI application entrypoint.

Model weights are loaded exactly once, during startup, so request handling
never pays model-construction cost.
"""

from __future__ import annotations

import logging
import sys
import time
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

# Make the repository root importable so `ml.*` resolves without installation.
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from app.api import auth, metrics, movies, recommendations, system  # noqa: E402
from app.core.config import settings  # noqa: E402
from app.api import users  # noqa: E402
from app.services.latency import latency_tracker  # noqa: E402
from app.services.tmdb import tmdb_service  # noqa: E402

logging.basicConfig(
    level=getattr(logging, settings.log_level.upper(), logging.INFO),
    format="%(asctime)s %(levelname)-8s %(name)s | %(message)s",
)
logger = logging.getLogger("movierec")


@asynccontextmanager
async def lifespan(app: FastAPI):
    t0 = time.perf_counter()
    try:
        from ml.inference.recommender import get_service
        svc = get_service()
        logger.info(
            "models loaded in %.2fs | users=%s movies=%s available=%s",
            time.perf_counter() - t0, svc.num_users, svc.num_movies, svc.available_models,
        )
    except Exception:
        logger.exception("model artifacts could not be loaded; "
                         "API will serve fallbacks and report degraded health")
    yield
    tmdb_service.close()


app = FastAPI(
    title=settings.app_name,
    version=settings.api_version,
    description=(
        "Neural Collaborative Filtering (NeuMF) movie recommender trained on MovieLens 20M. "
        "Serves personalised top-N recommendations, calibrated rating predictions and the "
        "evaluation metrics behind the analytics dashboard."
    ),
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def timing_middleware(request: Request, call_next):
    start = time.perf_counter()
    response = await call_next(request)
    elapsed_ms = (time.perf_counter() - start) * 1000
    route = request.scope.get("route")
    name = getattr(route, "path", request.url.path)
    latency_tracker.record(f"{request.method} {name}", elapsed_ms)
    response.headers["X-Response-Time-ms"] = f"{elapsed_ms:.2f}"
    return response


@app.exception_handler(RequestValidationError)
async def validation_handler(request: Request, exc: RequestValidationError):
    # Pydantic puts the original exception object in `ctx`, which json cannot
    # encode; keep only the serialisable fields.
    detail = [
        {"loc": [str(p) for p in err.get("loc", [])],
         "msg": str(err.get("msg", "")),
         "type": str(err.get("type", ""))}
        for err in exc.errors()
    ]
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={"error": "validation_error", "detail": detail},
    )


@app.exception_handler(Exception)
async def unhandled_handler(request: Request, exc: Exception):
    logger.exception("unhandled error on %s %s", request.method, request.url.path)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"error": "internal_error",
                 "detail": "An unexpected error occurred. The incident has been logged."},
    )


app.include_router(system.router)
app.include_router(auth.router)
app.include_router(movies.router)
app.include_router(recommendations.router)
app.include_router(users.router)
app.include_router(metrics.router)


@app.get("/", tags=["system"])
def root() -> dict:
    return {"name": settings.app_name, "version": settings.api_version, "docs": "/docs"}
