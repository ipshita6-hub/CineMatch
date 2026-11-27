"""Shared data utilities: seen-item index, negative sampling, candidate sets."""

from __future__ import annotations

import numpy as np
import pandas as pd

from ml import config as C


class SeenIndex:
    """Observed (user, item) pairs with vectorised membership testing.

    Stored as a sorted array of ``user * num_movies + item`` keys so that
    membership for a whole batch is a single ``np.searchsorted``.

    That key array is built lazily, on the first ``contains`` call. Only the
    training negative sampler needs it; inference uses ``items_for`` alone.
    Building it eagerly costs 152 MB of resident memory plus roughly 457 MB of
    transient peak on the 20M-interaction index, which is enough to exhaust a
    small deployment instance that will never call ``contains``.
    """

    def __init__(self, indptr: np.ndarray, indices: np.ndarray, num_users: int, num_movies: int):
        self.indptr = indptr
        self.indices = indices
        self.num_users = num_users
        self.num_movies = num_movies
        self._keys_cache: np.ndarray | None = None

    @property
    def _keys(self) -> np.ndarray:
        if self._keys_cache is None:
            users = np.repeat(np.arange(self.num_users, dtype=np.int64), np.diff(self.indptr))
            self._keys_cache = np.sort(
                users * np.int64(self.num_movies) + self.indices.astype(np.int64)
            )
        return self._keys_cache

    @classmethod
    def load(cls, path, num_users: int, num_movies: int) -> "SeenIndex":
        z = np.load(path)
        return cls(z["indptr"], z["indices"], num_users, num_movies)

    def contains(self, users: np.ndarray, items: np.ndarray) -> np.ndarray:
        keys = users.astype(np.int64) * np.int64(self.num_movies) + items.astype(np.int64)
        pos = np.searchsorted(self._keys, keys)
        pos = np.clip(pos, 0, len(self._keys) - 1)
        return self._keys[pos] == keys

    def items_for(self, user: int) -> np.ndarray:
        return self.indices[self.indptr[user]:self.indptr[user + 1]]

    def count_for(self, user: int) -> int:
        return int(self.indptr[user + 1] - self.indptr[user])


def sample_negatives(
    users: np.ndarray, n_per_user: int, seen: SeenIndex, rng: np.random.Generator,
    max_rounds: int = 20,
) -> np.ndarray:
    """Draw `n_per_user` unobserved items for each entry of `users`.

    Rejection sampling, resolved in vectorised rounds rather than a Python
    while-loop per sample (the notebook's approach, which is far too slow at
    this scale).
    """
    expanded = np.repeat(users, n_per_user)
    out = rng.integers(0, seen.num_movies, size=expanded.shape[0], dtype=np.int64)
    for _ in range(max_rounds):
        bad = seen.contains(expanded, out)
        if not bad.any():
            break
        out[bad] = rng.integers(0, seen.num_movies, size=int(bad.sum()), dtype=np.int64)
    return out


def build_candidate_sets(
    user_idx: np.ndarray, positive_idx: np.ndarray, n_negatives: int,
    seen: SeenIndex, rng: np.random.Generator,
) -> np.ndarray:
    """(num_users, 1 + n_negatives) matrix; column 0 is the held-out positive.

    Negatives are unobserved anywhere in the user's history and are unique
    within a row, matching the He et al. leave-one-out protocol. Vectorised
    resampling fixes almost every collision; a per-row repair pass then
    guarantees uniqueness rather than letting a duplicate slip through.
    """
    n = len(user_idx)
    negatives = sample_negatives(user_idx, n_negatives, seen, rng).reshape(n, n_negatives)

    def duplicated(neg: np.ndarray) -> np.ndarray:
        rows = np.concatenate([positive_idx.reshape(n, 1), neg], axis=1)
        return (np.diff(np.sort(rows, axis=1), axis=1) == 0).any(axis=1)

    for _ in range(12):
        dup = duplicated(negatives)
        if not dup.any():
            break
        idx = np.where(dup)[0]
        negatives[idx] = sample_negatives(
            user_idx[idx], n_negatives, seen, rng).reshape(len(idx), n_negatives)

    # Deterministic repair for any row the vectorised rounds could not resolve
    # (only reachable when the unobserved pool is very small).
    for i in np.where(duplicated(negatives))[0]:
        user = np.array([user_idx[i]], dtype=np.int64)
        chosen: set[int] = {int(positive_idx[i])}
        picked: list[int] = []
        for _ in range(seen.num_movies * 20):
            if len(picked) == n_negatives:
                break
            movie = int(rng.integers(0, seen.num_movies))
            if movie in chosen or seen.contains(user, np.array([movie]))[0]:
                continue
            chosen.add(movie)
            picked.append(movie)
        if len(picked) < n_negatives:
            raise ValueError(
                f"user {int(user_idx[i])} has too few unobserved movies to draw "
                f"{n_negatives} distinct negatives")
        negatives[i] = picked

    return np.concatenate([positive_idx.reshape(n, 1), negatives], axis=1).astype(np.int64)


def load_splits():
    train = pd.read_parquet(C.TRAIN_PARQUET)
    val = pd.read_parquet(C.VAL_PARQUET)
    test = pd.read_parquet(C.TEST_PARQUET)
    return train, val, test


def dataset_shape() -> tuple[int, int]:
    users = pd.read_csv(C.USER_MAPPING_CSV)
    movies = pd.read_csv(C.MOVIE_MAPPING_CSV)
    return len(users), len(movies)


def positive_pairs(df: pd.DataFrame, max_rows: int | None, seed: int):
    """Deduplicated positive (user_idx, movie_idx) pairs, optionally subsampled."""
    pos = df[df["rating"] >= C.POSITIVE_RATING_THRESHOLD][["user_idx", "movie_idx"]]
    pos = pos.drop_duplicates()
    total = len(pos)
    if max_rows is not None and total > max_rows:
        pos = pos.sample(n=max_rows, random_state=seed)
    return (pos["user_idx"].to_numpy().astype(np.int64),
            pos["movie_idx"].to_numpy().astype(np.int64),
            total)
