"""Build the shared evaluation candidate sets.

One file, one seed, reused by popularity, MF and NeuMF so that the three
models are scored on identical ground. Candidates are only built for users
whose held-out interaction is a POSITIVE one (rating >= threshold), because a
disliked held-out movie is not a relevant item.
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from ml import config as C  # noqa: E402
from ml.training.data import SeenIndex, build_candidate_sets, dataset_shape, load_splits  # noqa: E402


def build(split_df, seen: SeenIndex, n_negatives: int, max_users: int | None,
          seed: int, out_path: Path) -> None:
    pos = split_df[split_df["rating"] >= C.POSITIVE_RATING_THRESHOLD]
    pos = pos[["user_idx", "movie_idx"]].drop_duplicates("user_idx")
    if max_users is not None and len(pos) > max_users:
        pos = pos.sample(n=max_users, random_state=seed)
    pos = pos.sort_values("user_idx")

    users = pos["user_idx"].to_numpy().astype(np.int64)
    positives = pos["movie_idx"].to_numpy().astype(np.int64)
    rng = np.random.default_rng(seed)
    candidates = build_candidate_sets(users, positives, n_negatives, seen, rng)

    # integrity: no negative may be an observed item for that user
    flat_users = np.repeat(users, n_negatives)
    assert not seen.contains(flat_users, candidates[:, 1:].ravel()).any(), \
        "a sampled negative is actually an observed interaction"
    assert (candidates[:, 0] == positives).all()

    np.savez_compressed(out_path, users=users, candidates=candidates)
    print(f"{out_path.name}: {len(users)} users x {candidates.shape[1]} candidates")


def main() -> None:
    num_users, num_movies = dataset_shape()
    train, val, test = load_splits()
    seen_all = SeenIndex.load(C.MAPPING_DIR / "seen_all.npz", num_users, num_movies)

    build(test, seen_all, C.N_EVAL_NEGATIVES, C.MAX_EVAL_USERS, C.SEED, C.EVAL_CANDIDATES_NPZ)
    # validation candidates: capped, used for per-epoch early-stopping only
    build(val, seen_all, C.N_EVAL_NEGATIVES, C.MAX_VAL_USERS, C.SEED + 1, C.VAL_CANDIDATES_NPZ)


if __name__ == "__main__":
    main()
