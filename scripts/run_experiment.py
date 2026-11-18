"""Run an additional NeuMF/MF training configuration as a named experiment.

Writes to its own checkpoint so the production checkpoint is untouched, scores
the result on the SHARED test candidate sets, and appends a row to
artifacts/metrics/experiments.json. Only runs that actually execute appear
there — the dashboard never shows a configuration that was not trained.

Example:
  python scripts/run_experiment.py --name neumf-d16 --gmf-dim 16 --mlp-dim 16 \
      --mlp-layers 32,16,8 --negatives 2 --epochs 4 --positives 2000000
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

import numpy as np
import torch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from ml import config as C  # noqa: E402
from ml.evaluation.metrics import ranking_metrics, roc_auc_from_candidates  # noqa: E402
from ml.evaluation.score import score_candidates  # noqa: E402
from ml.models.neumf import NeuMF  # noqa: E402
from ml.training.data import SeenIndex, dataset_shape, load_splits, positive_pairs  # noqa: E402
from ml.training.trainer import train_implicit  # noqa: E402


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--name", required=True)
    ap.add_argument("--gmf-dim", type=int, default=C.NEUMF_GMF_DIM)
    ap.add_argument("--mlp-dim", type=int, default=C.NEUMF_MLP_DIM)
    ap.add_argument("--mlp-layers", default=",".join(map(str, C.NEUMF_MLP_LAYERS)))
    ap.add_argument("--negatives", type=int, default=C.NEUMF_NEGATIVES_PER_POSITIVE)
    ap.add_argument("--epochs", type=int, default=C.NEUMF_EPOCHS)
    ap.add_argument("--lr", type=float, default=C.NEUMF_LEARNING_RATE)
    ap.add_argument("--dropout", type=float, default=C.NEUMF_DROPOUT)
    ap.add_argument("--positives", type=int, default=C.MAX_POSITIVE_TRAIN_ROWS)
    args = ap.parse_args()

    layers = [int(x) for x in args.mlp_layers.split(",")]
    device = C.get_device()
    num_users, num_movies = dataset_shape()
    train, _val, _test = load_splits()
    seen_train = SeenIndex.load(C.MAPPING_DIR / "seen_train.npz", num_users, num_movies)
    users, items, total_pos = positive_pairs(train, args.positives, C.SEED)
    val = np.load(C.VAL_CANDIDATES_NPZ)

    ckpt_path = C.CHECKPOINT_DIR / f"experiment_{args.name}.pt"
    hist_path = C.METRICS_DIR / f"experiment_{args.name}_history.json"

    model = NeuMF(num_users, num_movies, args.gmf_dim, args.mlp_dim, layers, args.dropout)
    train_implicit(
        model, name=f"experiment:{args.name}",
        train_users=users, train_items=items, seen_train=seen_train,
        val_users=val["users"], val_candidates=val["candidates"],
        epochs=args.epochs, batch_size=C.NEUMF_BATCH_SIZE, lr=args.lr,
        weight_decay=C.NEUMF_WEIGHT_DECAY, negatives_per_positive=args.negatives,
        device=device, checkpoint_path=ckpt_path, history_path=hist_path,
        extra_meta={"experiment": args.name, "total_available_positives": total_pos,
                    "positive_subsample_cap": args.positives},
    )

    ckpt = torch.load(ckpt_path, map_location=device, weights_only=False)
    model.load_state_dict(ckpt["model_state_dict"])
    model = model.to(device).eval()

    z = np.load(C.EVAL_CANDIDATES_NPZ)
    scores = score_candidates(model, z["users"], z["candidates"], device=device)
    m = ranking_metrics(scores, C.TOP_K)
    auc = roc_auc_from_candidates(scores)
    print(f"[experiment:{args.name}] test HR@10={m[f'HR@{C.TOP_K}']:.5f} "
          f"NDCG@10={m[f'NDCG@{C.TOP_K}']:.5f} AUC={auc:.5f}")

    reg_path = C.METRICS_DIR / "experiments.json"
    registry = json.loads(reg_path.read_text()) if reg_path.exists() else []
    entry = {
        "experiment_id": f"NeuMF-{args.name}",
        "model": "NeuMF",
        "config": ckpt["config"],
        "training": ckpt["training"],
        "best_epoch": ckpt["epoch"],
        f"test_HR@{C.TOP_K}": m[f"HR@{C.TOP_K}"],
        f"test_NDCG@{C.TOP_K}": m[f"NDCG@{C.TOP_K}"],
        "test_ROC_AUC": auc,
        "evaluated_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
    }
    registry = [e for e in registry if e["experiment_id"] != entry["experiment_id"]]
    registry.append(entry)
    reg_path.write_text(json.dumps(registry, indent=2))
    print(f"Recorded in {reg_path}")


if __name__ == "__main__":
    main()
