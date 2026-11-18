"""MovieLens 20M preprocessing pipeline.

A faithful port of sections 0-18 of the original Colab notebook
(notebooks/movielens20m_with_baselines_simple_3.ipynb), with four audited
changes that are documented in the README:

1. Large tables are written as Parquet rather than CSV (20M-row CSVs are
   ~1.5 GB each and slow to re-read).
2. Two "seen" indexes are produced instead of one: negatives for TRAINING are
   drawn against train-only history, negatives for EVALUATION are drawn
   against the full history (He et al., WWW 2017). The notebook used the full
   history for both, which leaks held-out items out of the training negatives.
3. An eda_summary.json is emitted so the analytics dashboard can render
   measured values instead of hardcoded ones.
4. links.csv is joined in so TMDB enrichment can use real tmdbId values.

Every threshold (MIN_USER_RATINGS, MIN_MOVIE_RATINGS,
POSITIVE_RATING_THRESHOLD, SEED) is unchanged from the notebook.

Usage:  python -m ml.preprocessing.run_preprocessing
"""

from __future__ import annotations

import json
import random
import sys
import time
import zipfile
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from ml import config as C  # noqa: E402

random.seed(C.SEED)
np.random.seed(C.SEED)


def log(msg: str) -> None:
    print(f"[{time.strftime('%H:%M:%S')}] {msg}", flush=True)


# ---------------------------------------------------------------------------
# 1. Load
# ---------------------------------------------------------------------------
def ensure_dataset() -> None:
    if (C.ML20M_DIR / "ratings.csv").exists() and (C.ML20M_DIR / "movies.csv").exists():
        log("Dataset already present.")
        return
    zip_path = C.RAW_DIR / "ml-20m.zip"
    if not zip_path.exists():
        import urllib.request
        log("Downloading MovieLens 20M (~190 MB)...")
        urllib.request.urlretrieve(C.ML20M_URL, zip_path)
    log("Extracting...")
    with zipfile.ZipFile(zip_path) as zf:
        zf.extractall(C.RAW_DIR)


def load_raw():
    ratings = pd.read_csv(
        C.ML20M_DIR / "ratings.csv",
        dtype={"userId": "int32", "movieId": "int32",
               "rating": "float32", "timestamp": "int64"},
    )
    movies = pd.read_csv(C.ML20M_DIR / "movies.csv")
    links = None
    if (C.ML20M_DIR / "links.csv").exists():
        links = pd.read_csv(C.ML20M_DIR / "links.csv")
    tags = None
    if (C.ML20M_DIR / "tags.csv").exists():
        tags = pd.read_csv(C.ML20M_DIR / "tags.csv")
    log(f"Ratings: {ratings.shape}  Movies: {movies.shape}")
    return ratings, movies, links, tags


# ---------------------------------------------------------------------------
# Seen-index helper: compact CSR-style structure, far cheaper than dict-of-sets
# ---------------------------------------------------------------------------
def build_seen_index(df: pd.DataFrame, num_users: int):
    users = df["user_idx"].to_numpy()
    movies = df["movie_idx"].to_numpy().astype(np.int32)
    order = np.lexsort((movies, users))
    users_sorted = users[order]
    movies_sorted = movies[order]
    counts = np.bincount(users_sorted, minlength=num_users)
    indptr = np.zeros(num_users + 1, dtype=np.int64)
    np.cumsum(counts, out=indptr[1:])
    return indptr, movies_sorted


def main() -> None:
    t0 = time.time()
    ensure_dataset()
    ratings, movies, links, tags = load_raw()

    report: dict = {}

    # -----------------------------------------------------------------
    # 2/3. Structural EDA, missing values, duplicates
    # -----------------------------------------------------------------
    report["raw"] = {
        "rating_rows": int(len(ratings)),
        "unique_users": int(ratings["userId"].nunique()),
        "unique_movies_in_ratings": int(ratings["movieId"].nunique()),
        "movies_in_movies_csv": int(movies["movieId"].nunique()),
        "rating_min": float(ratings["rating"].min()),
        "rating_max": float(ratings["rating"].max()),
        "timestamp_min": int(ratings["timestamp"].min()),
        "timestamp_max": int(ratings["timestamp"].max()),
        "missing_ratings_cells": int(ratings.isna().sum().sum()),
        "missing_movies_cells": int(movies.isna().sum().sum()),
        "exact_duplicate_rating_rows": int(ratings.duplicated().sum()),
        "repeated_user_movie_pairs": int(ratings.duplicated(["userId", "movieId"]).sum()),
        "orphan_movie_ids": int(len(set(ratings["movieId"]) - set(movies["movieId"]))),
        "tags_rows": int(len(tags)) if tags is not None else 0,
    }
    log(f"Raw EDA: {report['raw']}")

    # -----------------------------------------------------------------
    # 4. Rating distribution
    # -----------------------------------------------------------------
    dist = ratings["rating"].value_counts().sort_index()
    report["rating_distribution"] = [
        {"rating": float(r), "count": int(c), "percentage": round(c / len(ratings) * 100, 4)}
        for r, c in dist.items()
    ]
    report["rating_summary"] = {
        "mean": round(float(ratings["rating"].mean()), 4),
        "median": float(ratings["rating"].median()),
        "std": round(float(ratings["rating"].std()), 4),
    }

    # -----------------------------------------------------------------
    # 7/8. Genres and release year
    # -----------------------------------------------------------------
    movies_clean = movies.copy()
    movies_clean["genres"] = movies_clean["genres"].fillna("(no genres listed)")
    genre_counts = (
        movies_clean["genres"].str.split("|").explode().value_counts().reset_index()
    )
    genre_counts.columns = ["genre", "movie_count"]
    report["genre_distribution"] = [
        {"genre": str(g), "movie_count": int(c)}
        for g, c in zip(genre_counts["genre"], genre_counts["movie_count"])
    ]
    movies_clean["release_year"] = (
        movies_clean["title"].str.extract(r"\((\d{4})\)\s*$", expand=False).astype("Int64")
    )
    report["release_year"] = {
        "with_year": int(movies_clean["release_year"].notna().sum()),
        "without_year": int(movies_clean["release_year"].isna().sum()),
    }
    yr = movies_clean["release_year"].dropna().astype(int)
    report["release_year_distribution"] = [
        {"year": int(y), "movie_count": int(c)}
        for y, c in yr.value_counts().sort_index().items() if y >= 1900
    ]

    # -----------------------------------------------------------------
    # 10. Core cleaning (conservative; identical rules to the notebook)
    # -----------------------------------------------------------------
    rows_before = len(ratings)
    ratings_clean = ratings.dropna(subset=["userId", "movieId", "rating", "timestamp"])
    ratings_clean = ratings_clean[ratings_clean["rating"].between(C.RATING_MIN, C.RATING_MAX)]
    ratings_clean = ratings_clean.drop_duplicates()
    ratings_clean = ratings_clean[
        ratings_clean["movieId"].isin(movies_clean["movieId"])
    ].copy()
    report["cleaning"] = {
        "rows_before": int(rows_before),
        "rows_after": int(len(ratings_clean)),
        "rows_removed": int(rows_before - len(ratings_clean)),
    }
    log(f"Cleaning: {report['cleaning']}")

    # -----------------------------------------------------------------
    # 11. Low-activity filtering (explicit, configured, recorded)
    # -----------------------------------------------------------------
    user_counts = ratings_clean["userId"].value_counts()
    movie_counts = ratings_clean["movieId"].value_counts()
    good_users = user_counts[user_counts >= C.MIN_USER_RATINGS].index
    good_movies = movie_counts[movie_counts >= C.MIN_MOVIE_RATINGS].index
    keep = ratings_clean["userId"].isin(good_users) & ratings_clean["movieId"].isin(good_movies)
    ratings_filtered = ratings_clean[keep].copy()
    report["activity_filtering"] = {
        "min_user_ratings": C.MIN_USER_RATINGS,
        "min_movie_ratings": C.MIN_MOVIE_RATINGS,
        "rows_before": int(len(ratings_clean)),
        "rows_after": int(len(ratings_filtered)),
        "users_retained": int(ratings_filtered["userId"].nunique()),
        "movies_retained": int(ratings_filtered["movieId"].nunique()),
    }
    log(f"Filtering: {report['activity_filtering']}")

    # -----------------------------------------------------------------
    # 5. Activity statistics (computed on the modelling population)
    # -----------------------------------------------------------------
    user_stats = ratings_filtered.groupby("userId")["rating"].agg(["count", "mean"])
    movie_stats = ratings_filtered.groupby("movieId")["rating"].agg(["count", "mean"])

    def describe(s: pd.Series) -> dict:
        d = s.describe()
        return {k: float(d[k]) for k in ["count", "mean", "std", "min", "25%", "50%", "75%", "max"]}

    report["user_activity"] = describe(user_stats["count"])
    report["movie_activity"] = describe(movie_stats["count"])

    def log_histogram(s: pd.Series, n_bins: int = 25) -> list[dict]:
        vals = s.to_numpy()
        edges = np.unique(np.round(np.logspace(0, np.log10(max(vals.max(), 2)), n_bins)).astype(int))
        counts, _ = np.histogram(vals, bins=np.append(edges, edges[-1] + 1))
        return [{"bin_start": int(edges[i]), "count": int(counts[i])} for i in range(len(edges))]

    report["user_activity_histogram"] = log_histogram(user_stats["count"])
    report["movie_popularity_histogram"] = log_histogram(movie_stats["count"])

    # -----------------------------------------------------------------
    # 12. Re-index for embeddings (notebook: sorted-ID category codes)
    # -----------------------------------------------------------------
    ratings_model = ratings_filtered
    ratings_model["user_idx"] = ratings_model["userId"].astype("category").cat.codes.astype("int32")
    ratings_model["movie_idx"] = ratings_model["movieId"].astype("category").cat.codes.astype("int32")

    user_mapping = (ratings_model[["userId", "user_idx"]].drop_duplicates()
                    .sort_values("user_idx").reset_index(drop=True))
    movie_mapping = (ratings_model[["movieId", "movie_idx"]].drop_duplicates()
                     .sort_values("movie_idx").reset_index(drop=True))
    num_users = len(user_mapping)
    num_movies = len(movie_mapping)
    log(f"Users: {num_users}  Movies: {num_movies}")

    # -----------------------------------------------------------------
    # 13. Implicit feedback label
    # -----------------------------------------------------------------
    ratings_model["is_positive"] = (
        ratings_model["rating"] >= C.POSITIVE_RATING_THRESHOLD
    ).astype("int8")
    report["implicit_feedback"] = {
        "positive_rating_threshold": C.POSITIVE_RATING_THRESHOLD,
        "positive_interactions": int(ratings_model["is_positive"].sum()),
        "negative_interactions": int((1 - ratings_model["is_positive"]).sum()),
        "positive_rate_pct": round(float(ratings_model["is_positive"].mean()) * 100, 3),
    }

    # Ratings over time (for the dashboard)
    months = pd.to_datetime(ratings_model["timestamp"], unit="s", utc=True).dt.to_period("M")
    mc = months.value_counts().sort_index()
    report["ratings_over_time"] = [
        {"month": str(p), "count": int(c)} for p, c in mc.items()
    ]

    # -----------------------------------------------------------------
    # 15. Chronological leave-one-out split
    # -----------------------------------------------------------------
    ratings_model = ratings_model.sort_values(["user_idx", "timestamp"], kind="stable")
    pos_from_end = ratings_model.groupby("user_idx", sort=False).cumcount(ascending=False)
    test_df = ratings_model[pos_from_end == 0].copy()
    val_df = ratings_model[pos_from_end == 1].copy()
    train_df = ratings_model[pos_from_end >= 2].copy()
    report["split"] = {
        "protocol": "chronological_leave_one_out",
        "train_rows": int(len(train_df)),
        "validation_rows": int(len(val_df)),
        "test_rows": int(len(test_df)),
        "users_in_train": int(train_df["user_idx"].nunique()),
        "users_in_validation": int(val_df["user_idx"].nunique()),
        "users_in_test": int(test_df["user_idx"].nunique()),
        "test_positive_users": int((test_df["rating"] >= C.POSITIVE_RATING_THRESHOLD).sum()),
        "validation_positive_users": int((val_df["rating"] >= C.POSITIVE_RATING_THRESHOLD).sum()),
    }
    log(f"Split: {report['split']}")

    # -----------------------------------------------------------------
    # 16. Movie feature table + train-only popularity (no leakage)
    # -----------------------------------------------------------------
    genre_dummies = movies_clean["genres"].str.get_dummies(sep="|").astype("int8")
    movies_features = pd.concat(
        [movies_clean[["movieId", "title", "genres", "release_year"]], genre_dummies], axis=1
    )
    train_movie_stats = train_df.groupby("movieId")["rating"].agg(["count", "mean"]).reset_index()
    train_movie_stats.columns = ["movieId", "train_rating_count", "train_avg_rating"]
    movies_features = movies_features.merge(train_movie_stats, on="movieId", how="left")
    movies_features["train_rating_count"] = (
        movies_features["train_rating_count"].fillna(0).astype("int32")
    )
    movies_features = movies_features.merge(movie_mapping, on="movieId", how="left")
    if links is not None:
        movies_features = movies_features.merge(
            links[["movieId", "imdbId", "tmdbId"]], on="movieId", how="left"
        )

    # Popularity table over the model index space (train only)
    global_mean = float(train_df["rating"].mean())
    pop = train_df.groupby("movie_idx")["rating"].agg(["count", "mean"])
    pop.columns = ["train_rating_count", "train_avg_rating"]
    pop = pop.reindex(range(num_movies))
    pop.index.name = "movie_idx"
    pop = pop.reset_index()
    pop["train_rating_count"] = pop["train_rating_count"].fillna(0).astype("int64")
    pop["train_avg_rating"] = pop["train_avg_rating"].fillna(global_mean)
    n, avg = pop["train_rating_count"], pop["train_avg_rating"]
    pop["bayesian_score"] = (n * avg + C.SHRINKAGE_M * global_mean) / (n + C.SHRINKAGE_M)
    popularity_ranked = pop.sort_values(
        ["train_rating_count", "bayesian_score"], ascending=False
    ).reset_index(drop=True)
    popularity_ranked["popularity_rank"] = np.arange(1, len(popularity_ranked) + 1)

    titles = movie_mapping.merge(movies_clean[["movieId", "title"]], on="movieId", how="left")
    report["top_movies"] = [
        {"movie_idx": int(r.movie_idx), "title": str(t), "train_rating_count": int(r.train_rating_count),
         "train_avg_rating": round(float(r.train_avg_rating), 4)}
        for r, t in zip(popularity_ranked.head(20).itertuples(),
                        popularity_ranked.head(20)["movie_idx"].map(
                            dict(zip(titles["movie_idx"], titles["title"]))))
    ]

    report["sparsity"] = {
        "num_users": num_users,
        "num_movies": num_movies,
        "observed_interactions": int(len(ratings_model)),
        "dense_cells": int(num_users) * int(num_movies),
        "density_pct": round(len(ratings_model) / (num_users * num_movies) * 100, 6),
        "sparsity_pct": round(100 - len(ratings_model) / (num_users * num_movies) * 100, 6),
        "global_mean_rating_train": round(global_mean, 4),
    }

    # -----------------------------------------------------------------
    # 17. Assertions
    # -----------------------------------------------------------------
    assert ratings_model["user_idx"].min() >= 0
    assert ratings_model["movie_idx"].min() >= 0
    assert ratings_model["user_idx"].max() < num_users
    assert ratings_model["movie_idx"].max() < num_movies
    assert ratings_model["rating"].between(C.RATING_MIN, C.RATING_MAX).all()
    assert len(train_df) + len(val_df) + len(test_df) == len(ratings_model)
    # leave-one-out integrity: each user's test row is their latest interaction
    assert test_df["user_idx"].nunique() == len(test_df)
    assert val_df["user_idx"].nunique() == len(val_df)
    log("All data-quality assertions passed.")

    # -----------------------------------------------------------------
    # 18. Persist
    # -----------------------------------------------------------------
    keep_cols = ["userId", "movieId", "rating", "timestamp", "user_idx", "movie_idx", "is_positive"]
    ratings_model[keep_cols].to_parquet(C.RATINGS_MODEL_PARQUET, index=False)
    train_df[keep_cols].to_parquet(C.TRAIN_PARQUET, index=False)
    val_df[keep_cols].to_parquet(C.VAL_PARQUET, index=False)
    test_df[keep_cols].to_parquet(C.TEST_PARQUET, index=False)

    user_mapping.to_csv(C.USER_MAPPING_CSV, index=False)
    movie_mapping.to_csv(C.MOVIE_MAPPING_CSV, index=False)
    movies_features.to_csv(C.MOVIES_FEATURES_CSV, index=False)
    popularity_ranked.to_csv(C.POPULARITY_CSV, index=False)

    # Seen indexes: train-only (training negatives) and full (eval negatives)
    tr_ptr, tr_idx = build_seen_index(train_df, num_users)
    np.savez_compressed(C.MAPPING_DIR / "seen_train.npz", indptr=tr_ptr, indices=tr_idx)
    all_ptr, all_idx = build_seen_index(ratings_model, num_users)
    np.savez_compressed(C.MAPPING_DIR / "seen_all.npz", indptr=all_ptr, indices=all_idx)
    log("Seen indexes written (train-only and full history).")

    cfg = C.preprocessing_config()
    cfg.update({
        "num_users": num_users,
        "num_movies": num_movies,
        "train_rows": int(len(train_df)),
        "validation_rows": int(len(val_df)),
        "test_rows": int(len(test_df)),
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
    })
    C.PREPROCESSING_CONFIG_JSON.write_text(json.dumps(cfg, indent=2))
    report["generated_at"] = time.strftime("%Y-%m-%dT%H:%M:%S")
    report["dataset"] = C.DATASET_NAME
    C.EDA_SUMMARY_JSON.write_text(json.dumps(report, indent=2))

    log(f"Done in {time.time() - t0:.1f}s. Artifacts under {C.PROCESSED_DIR} and {C.ARTIFACTS_DIR}")


if __name__ == "__main__":
    main()
