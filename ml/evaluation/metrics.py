"""Ranking and rating metrics.

All ranking metrics operate on the SAME candidate matrix for every model, so
popularity, MF and NeuMF are directly comparable.
"""

from __future__ import annotations

import numpy as np


def ranking_metrics(scores: np.ndarray, k: int = 10) -> dict:
    """`scores` is (num_users, num_candidates); column 0 is the held-out positive.

    Ties are broken pessimistically for the positive item (it is ranked after
    any candidate with an equal score), so a constant scorer cannot inflate the
    numbers.
    """
    positive_scores = scores[:, :1]
    better = (scores[:, 1:] > positive_scores).sum(axis=1)
    equal = (scores[:, 1:] == positive_scores).sum(axis=1)
    rank = better + equal  # 0-based, pessimistic

    hits = (rank < k).astype(np.float64)
    ndcg = np.where(rank < k, 1.0 / np.log2(rank + 2.0), 0.0)

    n_users = scores.shape[0]
    hr = float(hits.mean())
    return {
        f"HR@{k}": hr,
        f"NDCG@{k}": float(ndcg.mean()),
        # With exactly one relevant item per user these are deterministic
        # functions of HR@k. Reported because the PRD asks for them; the README
        # states the relationship explicitly rather than implying independence.
        f"Precision@{k}": hr / k,
        f"Recall@{k}": hr,
        f"F1@{k}": (2 * (hr / k) * hr / ((hr / k) + hr)) if hr > 0 else 0.0,
        "MRR": float((1.0 / (rank + 1.0)).mean()),
        "evaluated_users": int(n_users),
    }


def roc_auc_from_candidates(scores: np.ndarray) -> float:
    """AUC for the implicit-feedback classification view.

    Label 1 for the held-out positive, 0 for each sampled unobserved item.
    """
    from sklearn.metrics import roc_auc_score

    labels = np.zeros_like(scores, dtype=np.int8)
    labels[:, 0] = 1
    return float(roc_auc_score(labels.ravel(), scores.ravel()))


def rating_metrics(y_true: np.ndarray, y_pred: np.ndarray) -> dict:
    err = y_pred.astype(np.float64) - y_true.astype(np.float64)
    return {
        "RMSE": float(np.sqrt((err ** 2).mean())),
        "MAE": float(np.abs(err).mean()),
        "evaluated_ratings": int(len(y_true)),
    }
