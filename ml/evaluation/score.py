"""Batched scoring of candidate matrices by a torch model."""

from __future__ import annotations

import numpy as np
import torch


@torch.no_grad()
def score_candidates(model, users: np.ndarray, candidates: np.ndarray,
                     device: str = "cpu", batch_users: int = 2048) -> np.ndarray:
    """Returns a (num_users, num_candidates) float32 score matrix."""
    model.eval()
    n_users, n_cand = candidates.shape
    out = np.empty((n_users, n_cand), dtype=np.float32)
    for start in range(0, n_users, batch_users):
        end = min(start + batch_users, n_users)
        u = torch.as_tensor(users[start:end], dtype=torch.long, device=device)
        c = torch.as_tensor(candidates[start:end], dtype=torch.long, device=device)
        u_rep = u.unsqueeze(1).expand(-1, n_cand).reshape(-1)
        scores = model(u_rep, c.reshape(-1)).reshape(end - start, n_cand)
        out[start:end] = scores.float().cpu().numpy()
    return out


def score_candidates_popularity(popularity_score: np.ndarray, candidates: np.ndarray) -> np.ndarray:
    """Non-personalised: every user gets the same per-item score."""
    return popularity_score[candidates].astype(np.float32)
