"""Train NeuMF (GMF + MLP), the project's primary model."""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from ml import config as C  # noqa: E402
from ml.models.neumf import NeuMF  # noqa: E402
from ml.training.data import SeenIndex, dataset_shape, load_splits, positive_pairs  # noqa: E402
from ml.training.trainer import train_implicit  # noqa: E402


def main() -> None:
    num_users, num_movies = dataset_shape()
    train, _val, _test = load_splits()
    seen_train = SeenIndex.load(C.MAPPING_DIR / "seen_train.npz", num_users, num_movies)

    users, items, total_pos = positive_pairs(train, C.MAX_POSITIVE_TRAIN_ROWS, C.SEED)
    z = np.load(C.VAL_CANDIDATES_NPZ)

    model = NeuMF(
        num_users, num_movies,
        gmf_dim=C.NEUMF_GMF_DIM, mlp_dim=C.NEUMF_MLP_DIM,
        mlp_layers=C.NEUMF_MLP_LAYERS, dropout=C.NEUMF_DROPOUT,
    )
    train_implicit(
        model, name="NeuMF",
        train_users=users, train_items=items, seen_train=seen_train,
        val_users=z["users"], val_candidates=z["candidates"],
        epochs=C.NEUMF_EPOCHS, batch_size=C.NEUMF_BATCH_SIZE, lr=C.NEUMF_LEARNING_RATE,
        weight_decay=C.NEUMF_WEIGHT_DECAY,
        negatives_per_positive=C.NEUMF_NEGATIVES_PER_POSITIVE,
        device=C.get_device(), checkpoint_path=C.NEUMF_CHECKPOINT,
        history_path=C.NEUMF_HISTORY_JSON,
        extra_meta={"total_available_positives": total_pos,
                    "positive_subsample_cap": C.MAX_POSITIVE_TRAIN_ROWS},
    )


if __name__ == "__main__":
    main()
