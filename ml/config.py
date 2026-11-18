"""Single source of truth for paths and hyperparameters.

Imported by the preprocessing scripts, the training scripts, the evaluation
suite and the FastAPI backend, so that every component agrees on thresholds,
seeds and artifact locations.

Thresholds marked "NOTEBOOK" are carried over unchanged from the original
Colab notebook (notebooks/movielens20m_with_baselines_simple_3.ipynb) so that
results stay comparable with the work already presented for Viva 1.
"""

from __future__ import annotations

import os
from pathlib import Path

# --------------------------------------------------------------------------
# Paths
# --------------------------------------------------------------------------
PROJECT_ROOT = Path(__file__).resolve().parents[1]

DATA_ROOT = PROJECT_ROOT / "data"
RAW_DIR = DATA_ROOT / "raw"
ML20M_DIR = RAW_DIR / "ml-20m"
PROCESSED_DIR = DATA_ROOT / "processed"

ARTIFACTS_DIR = PROJECT_ROOT / "artifacts"
CHECKPOINT_DIR = ARTIFACTS_DIR / "checkpoints"
MAPPING_DIR = ARTIFACTS_DIR / "mappings"
METRICS_DIR = ARTIFACTS_DIR / "metrics"
METADATA_DIR = ARTIFACTS_DIR / "metadata"

for _d in (RAW_DIR, PROCESSED_DIR, CHECKPOINT_DIR, MAPPING_DIR, METRICS_DIR, METADATA_DIR):
    _d.mkdir(parents=True, exist_ok=True)

# Processed dataset files (Parquet for the large tables, CSV for small ones)
RATINGS_MODEL_PARQUET = PROCESSED_DIR / "ratings_model.parquet"
TRAIN_PARQUET = PROCESSED_DIR / "train.parquet"
VAL_PARQUET = PROCESSED_DIR / "validation.parquet"
TEST_PARQUET = PROCESSED_DIR / "test.parquet"

USER_MAPPING_CSV = MAPPING_DIR / "user_mapping.csv"
MOVIE_MAPPING_CSV = MAPPING_DIR / "movie_mapping.csv"
MOVIES_FEATURES_CSV = METADATA_DIR / "movies_features.csv"
POPULARITY_CSV = METADATA_DIR / "popularity_ranking.csv"

PREPROCESSING_CONFIG_JSON = METRICS_DIR / "preprocessing_config.json"
EDA_SUMMARY_JSON = METRICS_DIR / "eda_summary.json"
EVALUATION_JSON = METRICS_DIR / "evaluation.json"
MODEL_COMPARISON_CSV = METRICS_DIR / "model_comparison.csv"
LATENCY_JSON = METRICS_DIR / "latency.json"
EVAL_CANDIDATES_NPZ = METRICS_DIR / "eval_candidates.npz"
VAL_CANDIDATES_NPZ = METRICS_DIR / "val_candidates.npz"

MF_CHECKPOINT = CHECKPOINT_DIR / "matrix_factorization.pt"
NEUMF_CHECKPOINT = CHECKPOINT_DIR / "neumf.pt"
RATING_CHECKPOINT = CHECKPOINT_DIR / "rating_predictor.pt"

MF_HISTORY_JSON = METRICS_DIR / "mf_history.json"
NEUMF_HISTORY_JSON = METRICS_DIR / "neumf_history.json"
RATING_HISTORY_JSON = METRICS_DIR / "rating_history.json"

ML20M_URL = "https://files.grouplens.org/datasets/movielens/ml-20m.zip"

# --------------------------------------------------------------------------
# Dataset / preprocessing  (NOTEBOOK: unchanged)
# --------------------------------------------------------------------------
SEED = 42
DATASET_NAME = "MovieLens 20M"
DATASET_VERSION = "ml-20m"
# The PRD specifies MovieLens 25M; the dataset actually supplied and used in
# every experiment is MovieLens 20M. This deviation is surfaced in the README,
# the /model/info endpoint and the analytics dashboard.
PRD_DATASET_NAME = "MovieLens 25M"

MIN_USER_RATINGS = 5
MIN_MOVIE_RATINGS = 5
POSITIVE_RATING_THRESHOLD = 4.0
RATING_MIN = 0.5
RATING_MAX = 5.0

# --------------------------------------------------------------------------
# Evaluation protocol  (He et al., WWW 2017 leave-one-out)
# --------------------------------------------------------------------------
TOP_K = 10
N_EVAL_NEGATIVES = 99
# None => evaluate every eligible held-out user. Validation uses a capped
# sample so that per-epoch monitoring stays cheap.
MAX_EVAL_USERS: int | None = None
MAX_VAL_USERS = 10_000
SHRINKAGE_M = 100  # Bayesian prior weight for the popularity score

# --------------------------------------------------------------------------
# Matrix Factorization baseline  (NOTEBOOK architecture, retained)
# --------------------------------------------------------------------------
MF_EMBEDDING_DIM = 32
MF_EPOCHS = 8
MF_BATCH_SIZE = 8192
MF_LEARNING_RATE = 1e-3
MF_WEIGHT_DECAY = 1e-6
MF_NEGATIVES_PER_POSITIVE = 4

# --------------------------------------------------------------------------
# NeuMF  (GMF + MLP fusion)
# --------------------------------------------------------------------------
NEUMF_GMF_DIM = 32
NEUMF_MLP_DIM = 32           # per-tower embedding size; MLP input is 2 * this
NEUMF_MLP_LAYERS = [64, 32, 16]
NEUMF_DROPOUT = 0.1
NEUMF_EPOCHS = 10
NEUMF_BATCH_SIZE = 8192
NEUMF_LEARNING_RATE = 1e-3
NEUMF_WEIGHT_DECAY = 1e-6
NEUMF_NEGATIVES_PER_POSITIVE = 4
EARLY_STOPPING_PATIENCE = 2

# Training-set size cap, agreed explicitly rather than applied silently.
# Preprocessing/EDA/evaluation use the full 20M interactions; the implicit
# ranking models train on a seeded subsample of the positive interactions.
MAX_POSITIVE_TRAIN_ROWS: int | None = 5_000_000

# --------------------------------------------------------------------------
# Hybrid re-ranking (stretch goal)
# --------------------------------------------------------------------------
# Chosen by the weight grid in ml/evaluation/evaluate_hybrid.py, which measured
# every combination on the shared test candidate sets. Recorded here so the
# serving default matches the evaluated configuration.
HYBRID_ALPHA = 0.9   # normalised NeuMF score
HYBRID_BETA = 0.1    # genre similarity to the user's liked movies
HYBRID_GAMMA = 0.0   # popularity
HYBRID_EVALUATION_JSON = METRICS_DIR / "hybrid_evaluation.json"

# --------------------------------------------------------------------------
# Explicit rating prediction (separate model, calibrated to 0.5 - 5.0)
# --------------------------------------------------------------------------
RATING_GMF_DIM = 32
RATING_MLP_DIM = 32
RATING_MLP_LAYERS = [64, 32, 16]
RATING_DROPOUT = 0.1
RATING_EPOCHS = 6
RATING_BATCH_SIZE = 8192
RATING_LEARNING_RATE = 1e-3
RATING_WEIGHT_DECAY = 1e-6
MAX_RATING_TRAIN_ROWS: int | None = 8_000_000


def get_device(prefer_gpu: bool = True) -> str:
    """cuda > mps > cpu. The inference backend forces CPU."""
    if os.environ.get("FORCE_CPU") == "1" or not prefer_gpu:
        return "cpu"
    try:
        import torch
    except ImportError:
        return "cpu"
    if torch.cuda.is_available():
        return "cuda"
    if torch.backends.mps.is_available():
        return "mps"
    return "cpu"


def preprocessing_config() -> dict:
    return {
        "seed": SEED,
        "dataset": DATASET_NAME,
        "dataset_version": DATASET_VERSION,
        "prd_dataset": PRD_DATASET_NAME,
        "dataset_deviation_note": (
            "The PRD specifies MovieLens 25M. Every experiment in this project uses "
            "MovieLens 20M, which is the dataset that was supplied."
        ),
        "min_user_ratings": MIN_USER_RATINGS,
        "min_movie_ratings": MIN_MOVIE_RATINGS,
        "positive_rating_threshold": POSITIVE_RATING_THRESHOLD,
        "rating_scale": [RATING_MIN, RATING_MAX],
        "split": "chronological_leave_one_out",
        "eval_negatives": N_EVAL_NEGATIVES,
        "top_k": TOP_K,
        "notes": "Thresholds carried over unchanged from the original Colab notebook.",
    }
