"""Stretch goal: does hybrid re-ranking beat pure NeuMF?

Hybrid score = alpha * norm(NeuMF) + beta * genre similarity + gamma * norm(popularity)

Each signal is normalised within the user's candidate list before blending, and
the genre profile is built from the user's TRAINING-split positives only. Pure
NeuMF stays available as its own mode; the result is written to a separate file
so an experimental hybrid number is never mistaken for the main NeuMF result.
"""

from __future__ import annotations

import json
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd
import torch

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from ml import config as C  # noqa: E402
from ml.evaluation.evaluate_all import load_model  # noqa: E402
from ml.evaluation.metrics import ranking_metrics  # noqa: E402
from ml.evaluation.score import score_candidates  # noqa: E402
from ml.training.data import dataset_shape, load_splits  # noqa: E402

WEIGHT_GRID = [
    (1.0, 0.0, 0.0),    # pure NeuMF, for reference inside this file
    (0.9, 0.1, 0.0),
    (0.8, 0.2, 0.0),
    (0.8, 0.1, 0.1),
    (0.7, 0.2, 0.1),
    (0.6, 0.3, 0.1),
]


def row_normalise(x: np.ndarray) -> np.ndarray:
    lo = x.min(axis=1, keepdims=True)
    hi = x.max(axis=1, keepdims=True)
    return (x - lo) / np.maximum(hi - lo, 1e-12)


def main() -> None:
    device = C.get_device()
    num_users, num_movies = dataset_shape()
    train, _val, _test = load_splits()
    neumf, _ = load_model("neumf", num_users, num_movies, device)
    if neumf is None:
        print("NeuMF checkpoint missing; nothing to evaluate.")
        return

    z = np.load(C.EVAL_CANDIDATES_NPZ)
    users, candidates = z["users"], z["candidates"]
    print(f"Hybrid evaluation on {len(users):,} users", flush=True)

    movies = pd.read_csv(C.MOVIES_FEATURES_CSV)
    genre_cols = [c for c in movies.columns
                  if c not in {"movieId", "title", "genres", "release_year", "movie_idx",
                               "train_rating_count", "train_avg_rating", "imdbId", "tmdbId"}]
    gm = np.zeros((num_movies, len(genre_cols)), dtype=np.float32)
    have = movies.dropna(subset=["movie_idx"])
    gm[have["movie_idx"].to_numpy().astype(int)] = have[genre_cols].to_numpy(dtype=np.float32)
    gm_norm = gm / np.maximum(np.linalg.norm(gm, axis=1, keepdims=True), 1e-8)

    # Genre profile per evaluated user, from TRAIN positives only
    pos = train[train["rating"] >= C.POSITIVE_RATING_THRESHOLD][["user_idx", "movie_idx"]]
    pos = pos[pos["user_idx"].isin(set(users.tolist()))]
    profiles = np.zeros((len(users), len(genre_cols)), dtype=np.float32)
    row_of = {int(u): i for i, u in enumerate(users)}
    sums = np.zeros_like(profiles)
    counts = np.zeros(len(users), dtype=np.float32)
    for u, m in zip(pos["user_idx"].to_numpy(), pos["movie_idx"].to_numpy()):
        r = row_of.get(int(u))
        if r is not None:
            sums[r] += gm[int(m)]
            counts[r] += 1
    nz = counts > 0
    profiles[nz] = sums[nz] / counts[nz, None]
    profiles /= np.maximum(np.linalg.norm(profiles, axis=1, keepdims=True), 1e-8)

    model_scores = score_candidates(neumf, users, candidates, device=device)
    model_n = row_normalise(model_scores.astype(np.float64))

    pop = pd.read_csv(C.POPULARITY_CSV).sort_values("movie_idx")
    pop_count = np.zeros(num_movies, dtype=np.float64)
    pop_count[pop["movie_idx"].to_numpy()] = pop["train_rating_count"].to_numpy()
    pop_n = row_normalise(np.log1p(pop_count)[candidates])

    genre_sim = np.einsum('ij,ikj->ik', profiles, gm_norm[candidates]).astype(np.float64)

    results = []
    for alpha, beta, gamma in WEIGHT_GRID:
        blended = alpha * model_n + beta * genre_sim + gamma * pop_n
        m = ranking_metrics(blended, C.TOP_K)
        results.append({"alpha": alpha, "beta": beta, "gamma": gamma,
                        f"HR@{C.TOP_K}": m[f"HR@{C.TOP_K}"],
                        f"NDCG@{C.TOP_K}": m[f"NDCG@{C.TOP_K}"]})
        print(f"  a={alpha} b={beta} g={gamma} -> HR@10={m[f'HR@{C.TOP_K}']:.5f} "
              f"NDCG@10={m[f'NDCG@{C.TOP_K}']:.5f}", flush=True)

    pure = ranking_metrics(model_scores, C.TOP_K)
    best = max(results, key=lambda r: r[f"NDCG@{C.TOP_K}"])
    out = {
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "status": "ok",
        "note": ("Experimental hybrid re-ranking (PRD stretch goal). Normalisation is "
                 "per candidate list; genre profiles use training positives only. "
                 "These are NOT the headline NeuMF results."),
        "pure_neumf": {k: pure[k] for k in (f"HR@{C.TOP_K}", f"NDCG@{C.TOP_K}")},
        "grid": results,
        "best": best,
        "lift_vs_pure_neumf": {
            f"HR@{C.TOP_K}_pct": round((best[f"HR@{C.TOP_K}"] - pure[f"HR@{C.TOP_K}"])
                                       / pure[f"HR@{C.TOP_K}"] * 100, 3),
            f"NDCG@{C.TOP_K}_pct": round((best[f"NDCG@{C.TOP_K}"] - pure[f"NDCG@{C.TOP_K}"])
                                         / pure[f"NDCG@{C.TOP_K}"] * 100, 3),
        },
        "evaluated_users": int(len(users)),
    }
    (C.METRICS_DIR / "hybrid_evaluation.json").write_text(json.dumps(out, indent=2))
    print(f"\nBest: {best}\nLift vs pure NeuMF: {out['lift_vs_pure_neumf']}")


if __name__ == "__main__":
    main()
