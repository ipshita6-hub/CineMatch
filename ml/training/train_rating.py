"""Train the explicit rating-prediction model (separate from NeuMF ranking).

Trained on the TRAINING split's real ratings with MSE; evaluated with RMSE on
the validation leave-one-out interaction. Output is squashed into the
MovieLens 0.5-5.0 scale, so a prediction is always a usable star rating.
"""

from __future__ import annotations

import json
import sys
import time
from pathlib import Path

import numpy as np
import torch
from torch import nn

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from ml import config as C  # noqa: E402
from ml.evaluation.metrics import rating_metrics  # noqa: E402
from ml.models.rating_predictor import RatingPredictor  # noqa: E402
from ml.training.data import dataset_shape, load_splits  # noqa: E402


@torch.no_grad()
def predict_all(model, users, items, device, batch=65536):
    model.eval()
    out = np.empty(len(users), dtype=np.float32)
    for s in range(0, len(users), batch):
        e = min(s + batch, len(users))
        u = torch.as_tensor(users[s:e], dtype=torch.long, device=device)
        i = torch.as_tensor(items[s:e], dtype=torch.long, device=device)
        out[s:e] = model(u, i).float().cpu().numpy()
    return out


def main() -> None:
    device = C.get_device()
    num_users, num_movies = dataset_shape()
    train, val, _test = load_splits()

    tr = train[["user_idx", "movie_idx", "rating"]]
    total_rows = len(tr)
    if C.MAX_RATING_TRAIN_ROWS is not None and total_rows > C.MAX_RATING_TRAIN_ROWS:
        tr = tr.sample(n=C.MAX_RATING_TRAIN_ROWS, random_state=C.SEED)

    tu = tr["user_idx"].to_numpy().astype(np.int64)
    ti = tr["movie_idx"].to_numpy().astype(np.int64)
    ty = tr["rating"].to_numpy().astype(np.float32)

    vu = val["user_idx"].to_numpy().astype(np.int64)
    vi = val["movie_idx"].to_numpy().astype(np.int64)
    vy = val["rating"].to_numpy().astype(np.float32)

    torch.manual_seed(C.SEED)
    rng = np.random.default_rng(C.SEED)
    model = RatingPredictor(
        num_users, num_movies, C.RATING_GMF_DIM, C.RATING_MLP_DIM,
        C.RATING_MLP_LAYERS, C.RATING_DROPOUT, C.RATING_MIN, C.RATING_MAX,
    ).to(device)
    opt = torch.optim.Adam(model.parameters(), lr=C.RATING_LEARNING_RATE,
                           weight_decay=C.RATING_WEIGHT_DECAY)
    loss_fn = nn.MSELoss()

    history, best_rmse, best_epoch, bad = [], float("inf"), -1, 0
    t_start = time.time()
    print(f"[RatingPredictor] rows={len(tu):,} (of {total_rows:,}) device={device}", flush=True)

    for epoch in range(1, C.RATING_EPOCHS + 1):
        t0 = time.time()
        model.train()
        order = rng.permutation(len(tu))
        u_t = torch.from_numpy(tu[order])
        i_t = torch.from_numpy(ti[order])
        y_t = torch.from_numpy(ty[order])

        total, nb = 0.0, 0
        for s in range(0, len(order), C.RATING_BATCH_SIZE):
            e = s + C.RATING_BATCH_SIZE
            bu, bi, by = (u_t[s:e].to(device), i_t[s:e].to(device), y_t[s:e].to(device))
            loss = loss_fn(model(bu, bi), by)
            opt.zero_grad(set_to_none=True)
            loss.backward()
            opt.step()
            total += float(loss.item())
            nb += 1

        train_mse = total / max(nb, 1)
        val_pred = predict_all(model, vu, vi, device)
        vm = rating_metrics(vy, val_pred)
        entry = {"epoch": epoch, "train_mse": round(train_mse, 5),
                 "train_rmse": round(train_mse ** 0.5, 5),
                 "val_rmse": round(vm["RMSE"], 5), "val_mae": round(vm["MAE"], 5),
                 "seconds": round(time.time() - t0, 1)}
        history.append(entry)
        print(f"[RatingPredictor] {entry}", flush=True)

        if vm["RMSE"] < best_rmse:
            best_rmse, best_epoch, bad = vm["RMSE"], epoch, 0
            torch.save({
                "model_state_dict": model.state_dict(),
                "config": model.config(),
                "epoch": epoch,
                "val_RMSE": vm["RMSE"],
                "val_MAE": vm["MAE"],
                "training": {
                    "rows": int(len(tu)), "total_available_rows": int(total_rows),
                    "batch_size": C.RATING_BATCH_SIZE, "learning_rate": C.RATING_LEARNING_RATE,
                    "optimizer": "Adam", "loss": "MSELoss", "seed": C.SEED, "device": device,
                },
                "dataset": C.DATASET_NAME,
                "saved_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
            }, C.RATING_CHECKPOINT)
        else:
            bad += 1
            if bad >= C.EARLY_STOPPING_PATIENCE:
                print(f"[RatingPredictor] early stopping at epoch {epoch}", flush=True)
                break

    C.RATING_HISTORY_JSON.write_text(json.dumps({
        "model": "RatingPredictor", "history": history, "best_epoch": best_epoch,
        "best_val_RMSE": round(best_rmse, 5), "epochs_run": len(history),
        "early_stopped": best_epoch != history[-1]["epoch"],
        "total_seconds": round(time.time() - t_start, 1),
        "checkpoint": str(C.RATING_CHECKPOINT),
    }, indent=2))
    print(f"[RatingPredictor] best epoch {best_epoch}, val RMSE {best_rmse:.5f}", flush=True)


if __name__ == "__main__":
    main()
