"""Train the implicit Matrix Factorization baseline (notebook architecture)."""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from ml import config as C  # noqa: E402
from ml.models.matrix_factorization import MatrixFactorization  # noqa: E402
from ml.training.data import SeenIndex, dataset_shape, load_splits, positive_pairs  # noqa: E402
from ml.training.trainer import train_implicit  # noqa: E402


def main() -> None:
    num_users, num_movies = dataset_shape()
    train, _val, _test = load_splits()
    seen_train = SeenIndex.load(C.MAPPING_DIR / "seen_train.npz", num_users, num_movies)

    users, items, total_pos = positive_pairs(train, C.MAX_POSITIVE_TRAIN_ROWS, C.SEED)
    z = np.load(C.VAL_CANDIDATES_NPZ)

    model = MatrixFactorization(num_users, num_movies, C.MF_EMBEDDING_DIM)
    train_implicit(
        model, name="MatrixFactorization",
        train_users=users, train_items=items, seen_train=seen_train,
        val_users=z["users"], val_candidates=z["candidates"],
        epochs=C.MF_EPOCHS, batch_size=C.MF_BATCH_SIZE, lr=C.MF_LEARNING_RATE,
        weight_decay=C.MF_WEIGHT_DECAY,
        negatives_per_positive=C.MF_NEGATIVES_PER_POSITIVE,
        device=C.get_device(), checkpoint_path=C.MF_CHECKPOINT,
        history_path=C.MF_HISTORY_JSON,
        extra_meta={"total_available_positives": total_pos,
                    "positive_subsample_cap": C.MAX_POSITIVE_TRAIN_ROWS},
    )


if __name__ == "__main__":
    main()
