"""Shared training loop for the implicit-feedback ranking models.

Used by both the Matrix Factorization baseline and NeuMF so that the two are
trained under an identical protocol and the comparison is fair:

  * positives  = training-split interactions with rating >= 4.0
  * negatives  = items the user has not interacted with IN THE TRAINING SPLIT,
                 resampled fresh every epoch
  * loss       = BCEWithLogits
  * monitoring = HR@10 / NDCG@10 on the VALIDATION leave-one-out interaction
  * stopping   = early stopping on validation HR@10, best checkpoint kept

Validation and test interactions are never used as training examples.
"""

from __future__ import annotations

import json
import time

import numpy as np
import torch
from torch import nn

from ml import config as C
from ml.evaluation.metrics import ranking_metrics
from ml.evaluation.score import score_candidates
from ml.training.data import SeenIndex, sample_negatives


def _validation_loss(scores: np.ndarray) -> float:
    """BCE on the validation candidate matrix (col 0 positive, rest negative)."""
    s = torch.as_tensor(scores, dtype=torch.float32)
    labels = torch.zeros_like(s)
    labels[:, 0] = 1.0
    return float(nn.functional.binary_cross_entropy_with_logits(s, labels).item())


def train_implicit(
    model: nn.Module,
    *,
    name: str,
    train_users: np.ndarray,
    train_items: np.ndarray,
    seen_train: SeenIndex,
    val_users: np.ndarray,
    val_candidates: np.ndarray,
    epochs: int,
    batch_size: int,
    lr: float,
    weight_decay: float,
    negatives_per_positive: int,
    device: str,
    checkpoint_path,
    history_path,
    patience: int = C.EARLY_STOPPING_PATIENCE,
    seed: int = C.SEED,
    extra_meta: dict | None = None,
) -> dict:
    torch.manual_seed(seed)
    rng = np.random.default_rng(seed)

    model = model.to(device)
    optimizer = torch.optim.Adam(model.parameters(), lr=lr, weight_decay=weight_decay)
    loss_fn = nn.BCEWithLogitsLoss()

    n_pos = len(train_users)
    history: list[dict] = []
    best_hr = -1.0
    best_epoch = -1
    epochs_without_improvement = 0
    t_start = time.time()

    print(f"[{name}] positives={n_pos:,}  negatives/positive={negatives_per_positive}  "
          f"samples/epoch={n_pos * (1 + negatives_per_positive):,}  device={device}", flush=True)

    for epoch in range(1, epochs + 1):
        t0 = time.time()
        model.train()

        neg_items = sample_negatives(train_users, negatives_per_positive, seen_train, rng)
        neg_users = np.repeat(train_users, negatives_per_positive)

        users = np.concatenate([train_users, neg_users])
        items = np.concatenate([train_items, neg_items])
        labels = np.concatenate([np.ones(n_pos, dtype=np.float32),
                                 np.zeros(len(neg_items), dtype=np.float32)])
        order = rng.permutation(len(users))
        users, items, labels = users[order], items[order], labels[order]

        u_t = torch.from_numpy(users)
        i_t = torch.from_numpy(items)
        l_t = torch.from_numpy(labels)

        total_loss, n_batches = 0.0, 0
        for start in range(0, len(users), batch_size):
            end = start + batch_size
            bu = u_t[start:end].to(device, non_blocking=True)
            bi = i_t[start:end].to(device, non_blocking=True)
            bl = l_t[start:end].to(device, non_blocking=True)

            logits = model(bu, bi)
            loss = loss_fn(logits, bl)

            optimizer.zero_grad(set_to_none=True)
            loss.backward()
            optimizer.step()

            total_loss += float(loss.item())
            n_batches += 1

        train_loss = total_loss / max(n_batches, 1)

        val_scores = score_candidates(model, val_users, val_candidates, device=device)
        val_rank = ranking_metrics(val_scores, C.TOP_K)
        val_loss = _validation_loss(val_scores)

        entry = {
            "epoch": epoch,
            "train_loss": round(train_loss, 5),
            "val_loss": round(val_loss, 5),
            f"val_HR@{C.TOP_K}": round(val_rank[f"HR@{C.TOP_K}"], 5),
            f"val_NDCG@{C.TOP_K}": round(val_rank[f"NDCG@{C.TOP_K}"], 5),
            "seconds": round(time.time() - t0, 1),
        }
        history.append(entry)
        print(f"[{name}] {entry}", flush=True)

        hr = val_rank[f"HR@{C.TOP_K}"]
        if hr > best_hr:
            best_hr, best_epoch = hr, epoch
            epochs_without_improvement = 0
            torch.save({
                "model_state_dict": model.state_dict(),
                "config": model.config(),
                "epoch": epoch,
                f"val_HR@{C.TOP_K}": hr,
                f"val_NDCG@{C.TOP_K}": val_rank[f"NDCG@{C.TOP_K}"],
                "training": {
                    "positives": int(n_pos),
                    "negatives_per_positive": negatives_per_positive,
                    "batch_size": batch_size,
                    "learning_rate": lr,
                    "weight_decay": weight_decay,
                    "optimizer": "Adam",
                    "loss": "BCEWithLogitsLoss",
                    "seed": seed,
                    "device": device,
                    **(extra_meta or {}),
                },
                "dataset": C.DATASET_NAME,
                "saved_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
            }, checkpoint_path)
        else:
            epochs_without_improvement += 1
            if epochs_without_improvement >= patience:
                print(f"[{name}] early stopping at epoch {epoch} "
                      f"(best epoch {best_epoch}, HR@{C.TOP_K}={best_hr:.5f})", flush=True)
                break

    summary = {
        "model": name,
        "history": history,
        "best_epoch": best_epoch,
        f"best_val_HR@{C.TOP_K}": round(best_hr, 5),
        "early_stopped": best_epoch != history[-1]["epoch"],
        "epochs_run": len(history),
        "total_seconds": round(time.time() - t_start, 1),
        "checkpoint": str(checkpoint_path),
    }
    history_path.write_text(json.dumps(summary, indent=2))
    print(f"[{name}] done in {summary['total_seconds']}s; best epoch {best_epoch}", flush=True)
    return summary
