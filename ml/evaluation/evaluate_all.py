"""Evaluate Popularity, Matrix Factorization and NeuMF on IDENTICAL candidate
sets, plus explicit rating prediction, and write the artifacts the dashboard
reads.

Outputs
  artifacts/metrics/evaluation.json
  artifacts/metrics/model_comparison.csv
  artifacts/metrics/experiments.json   (append-only registry of executed runs)
"""

from __future__ import annotations

import json
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd
import torch

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from ml import config as C  # noqa: E402
from ml.evaluation.metrics import ranking_metrics, rating_metrics, roc_auc_from_candidates  # noqa: E402
from ml.evaluation.score import score_candidates, score_candidates_popularity  # noqa: E402
from ml.models.matrix_factorization import MatrixFactorization  # noqa: E402
from ml.models.neumf import NeuMF  # noqa: E402
from ml.models.rating_predictor import RatingPredictor  # noqa: E402
from ml.training.data import SeenIndex, dataset_shape, load_splits  # noqa: E402


def load_model(kind: str, num_users: int, num_movies: int, device: str):
    """Returns (model, checkpoint) or (None, None) when not yet trained."""
    path = {"mf": C.MF_CHECKPOINT, "neumf": C.NEUMF_CHECKPOINT, "rating": C.RATING_CHECKPOINT}[kind]
    if not path.exists():
        return None, None
    ckpt = torch.load(path, map_location=device, weights_only=False)
    cfg = ckpt["config"]
    if kind == "mf":
        model = MatrixFactorization(num_users, num_movies, cfg["embedding_dim"])
    elif kind == "neumf":
        model = NeuMF(num_users, num_movies, cfg["gmf_embedding_dim"],
                      cfg["mlp_embedding_dim"], cfg["mlp_layers"], cfg["dropout"])
    else:
        model = RatingPredictor(num_users, num_movies, cfg["gmf_embedding_dim"],
                                cfg["mlp_embedding_dim"], cfg["mlp_layers"], cfg["dropout"],
                                cfg["rating_scale"][0], cfg["rating_scale"][1])
    model.load_state_dict(ckpt["model_state_dict"])
    return model.to(device).eval(), ckpt


def recommendation_analytics(scores_fn, users, seen_all, popularity, movies_features,
                             num_movies, k=10, sample=2000, seed=C.SEED):
    """Diversity / coverage / long-tail analysis of actual top-k output."""
    rng = np.random.default_rng(seed)
    sel = rng.choice(users, size=min(sample, len(users)), replace=False)

    head_cut = popularity.sort_values("train_rating_count", ascending=False)
    head_set = set(head_cut.head(int(num_movies * 0.2))["movie_idx"].astype(int))

    genre_cols = [c for c in movies_features.columns
                  if movies_features[c].dropna().isin([0, 1]).all()
                  and c not in {"movie_idx", "movieId", "train_rating_count"}]
    gidx = movies_features.dropna(subset=["movie_idx"]).set_index(
        movies_features.dropna(subset=["movie_idx"])["movie_idx"].astype(int))

    recommended, all_scores, genre_counter, head_hits, total = [], [], {}, 0, 0
    for u in sel:
        s = scores_fn(int(u))
        s = s.copy()
        s[seen_all.items_for(int(u))] = -np.inf
        top = np.argpartition(-s, k)[:k]
        top = top[np.argsort(-s[top])]
        recommended.extend(top.tolist())
        all_scores.extend(s[top].tolist())
        for m in top:
            total += 1
            if int(m) in head_set:
                head_hits += 1
            if int(m) in gidx.index:
                row = gidx.loc[int(m)]
                for g in genre_cols:
                    if float(row.get(g, 0)) == 1.0:
                        genre_counter[g] = genre_counter.get(g, 0) + 1

    uniq = len(set(recommended))
    hist, edges = np.histogram(np.array(all_scores, dtype=float), bins=20)
    return {
        "users_sampled": int(len(sel)),
        "top_k": k,
        "catalog_coverage_pct": round(uniq / num_movies * 100, 4),
        "unique_movies_recommended": int(uniq),
        "head_share_pct": round(head_hits / max(total, 1) * 100, 2),
        "long_tail_share_pct": round(100 - head_hits / max(total, 1) * 100, 2),
        "genre_distribution": [
            {"genre": g, "count": int(c)}
            for g, c in sorted(genre_counter.items(), key=lambda x: -x[1])
        ],
        "score_distribution": [
            {"bin_start": round(float(edges[i]), 4), "bin_end": round(float(edges[i + 1]), 4),
             "count": int(hist[i])} for i in range(len(hist))
        ],
    }


def main() -> None:
    device = C.get_device()
    num_users, num_movies = dataset_shape()
    train, val, test = load_splits()
    seen_all = SeenIndex.load(C.MAPPING_DIR / "seen_all.npz", num_users, num_movies)
    popularity = pd.read_csv(C.POPULARITY_CSV)
    movies_features = pd.read_csv(C.MOVIES_FEATURES_CSV)

    z = np.load(C.EVAL_CANDIDATES_NPZ)
    users, candidates = z["users"], z["candidates"]
    print(f"Evaluating on {len(users):,} held-out users x {candidates.shape[1]} candidates", flush=True)

    results: dict[str, dict] = {}

    # ---------------- Popularity baseline ----------------
    pop_score = np.zeros(num_movies, dtype=np.float32)
    pop_score[popularity["movie_idx"].to_numpy()] = popularity["train_rating_count"].to_numpy()
    s = score_candidates_popularity(pop_score, candidates)
    results["Popularity"] = {**ranking_metrics(s, C.TOP_K),
                             "ROC_AUC": roc_auc_from_candidates(s),
                             "personalised": False,
                             "description": "Ranks by training-set rating count (non-personalised)."}
    print("Popularity:", results["Popularity"], flush=True)

    # ---------------- Matrix Factorization ----------------
    mf, mf_ckpt = load_model("mf", num_users, num_movies, device)
    if mf is not None:
        s = score_candidates(mf, users, candidates, device=device)
        results["MatrixFactorization"] = {
            **ranking_metrics(s, C.TOP_K), "ROC_AUC": roc_auc_from_candidates(s),
            "personalised": True, "description": "Implicit MF: dot product + biases.",
            "trained_epoch": mf_ckpt["epoch"],
        }
        print("MF:", results["MatrixFactorization"], flush=True)

    # ---------------- NeuMF ----------------
    neumf, neumf_ckpt = load_model("neumf", num_users, num_movies, device)
    if neumf is not None:
        s = score_candidates(neumf, users, candidates, device=device)
        results["NeuMF"] = {
            **ranking_metrics(s, C.TOP_K), "ROC_AUC": roc_auc_from_candidates(s),
            "personalised": True, "description": "NeuMF: GMF + MLP fusion (He et al. 2017).",
            "trained_epoch": neumf_ckpt["epoch"],
        }
        print("NeuMF:", results["NeuMF"], flush=True)

    # ---------------- Explicit rating prediction ----------------
    rating_block = {"status": "Not evaluated"}
    rp, rp_ckpt = load_model("rating", num_users, num_movies, device)
    if rp is not None:
        from ml.training.train_rating import predict_all
        tu = test["user_idx"].to_numpy().astype(np.int64)
        ti = test["movie_idx"].to_numpy().astype(np.int64)
        ty = test["rating"].to_numpy().astype(np.float32)
        pred = predict_all(rp, tu, ti, device)
        rating_block = {
            "model": "RatingPredictor (NeuMF trunk + calibrated regression head)",
            **rating_metrics(ty, pred),
            "rating_scale": [C.RATING_MIN, C.RATING_MAX],
            "prediction_min": round(float(pred.min()), 4),
            "prediction_max": round(float(pred.max()), 4),
            "trained_epoch": rp_ckpt["epoch"],
            "baselines": {},
        }
        gm = float(train["rating"].mean())
        rating_block["baselines"]["global_mean"] = rating_metrics(ty, np.full_like(ty, gm))
        item_mean = train.groupby("movie_idx")["rating"].mean()
        im = test["movie_idx"].map(item_mean).fillna(gm).to_numpy().astype(np.float32)
        rating_block["baselines"]["item_mean"] = rating_metrics(ty, im)
        print("Rating:", {k: v for k, v in rating_block.items() if k != "baselines"}, flush=True)

    # ---------------- Recommendation analytics (actual top-10 output) ----
    analytics = {}
    if neumf is not None:
        all_items = torch.arange(num_movies, dtype=torch.long, device=device)

        @torch.no_grad()
        def neumf_scores(u: int) -> np.ndarray:
            uu = torch.full_like(all_items, u)
            return neumf(uu, all_items).float().cpu().numpy()

        analytics["NeuMF"] = recommendation_analytics(
            neumf_scores, users, seen_all, popularity, movies_features, num_movies)
        analytics["Popularity"] = recommendation_analytics(
            lambda u: pop_score.copy(), users, seen_all, popularity, movies_features, num_movies)

    # ---------------- Improvements (only where valid) ----------------
    improvements = {}
    if "NeuMF" in results:
        for base in ("Popularity", "MatrixFactorization"):
            if base in results:
                for metric in (f"HR@{C.TOP_K}", f"NDCG@{C.TOP_K}"):
                    b = results[base][metric]
                    if b > 0:
                        improvements[f"NeuMF_vs_{base}_{metric}_pct"] = round(
                            (results["NeuMF"][metric] - b) / b * 100, 2)

    out = {
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "dataset": C.DATASET_NAME,
        "dataset_note": (f"The PRD specifies {C.PRD_DATASET_NAME}; all experiments use "
                         f"{C.DATASET_NAME}, the dataset actually supplied."),
        "protocol": {
            "split": "chronological leave-one-out",
            "relevance": f"held-out interaction counts as relevant only when rating >= {C.POSITIVE_RATING_THRESHOLD}",
            "candidates_per_user": int(candidates.shape[1]),
            "negatives_per_user": C.N_EVAL_NEGATIVES,
            "k": C.TOP_K,
            "identical_candidate_sets": True,
            "tie_breaking": "pessimistic for the positive item",
            "precision_recall_note": (
                "Exactly one relevant item exists per user, so Precision@10 = HR@10/10 "
                "and Recall@10 = HR@10 by construction."),
        },
        "dataset_shape": {"num_users": num_users, "num_movies": num_movies,
                          "interactions": int(len(train) + len(val) + len(test)),
                          "train_rows": int(len(train)), "validation_rows": int(len(val)),
                          "test_rows": int(len(test))},
        "models": results,
        "rating_prediction": rating_block,
        "recommendation_analytics": analytics,
        "improvements": improvements,
    }
    C.EVALUATION_JSON.write_text(json.dumps(out, indent=2))

    rows = []
    for name, m in results.items():
        rows.append({"model": name, **{k: v for k, v in m.items()
                                       if isinstance(v, (int, float))}})
    pd.DataFrame(rows).to_csv(C.MODEL_COMPARISON_CSV, index=False)

    # Append-only experiment registry (only runs that actually executed)
    reg_path = C.METRICS_DIR / "experiments.json"
    registry = json.loads(reg_path.read_text()) if reg_path.exists() else []
    for name, ckpt in (("MatrixFactorization", mf_ckpt), ("NeuMF", neumf_ckpt)):
        if ckpt is None:
            continue
        entry = {
            "experiment_id": f"{name}-{ckpt['saved_at']}",
            "model": name,
            "config": ckpt["config"],
            "training": ckpt["training"],
            "best_epoch": ckpt["epoch"],
            f"test_HR@{C.TOP_K}": results[name][f"HR@{C.TOP_K}"],
            f"test_NDCG@{C.TOP_K}": results[name][f"NDCG@{C.TOP_K}"],
            "evaluated_at": out["generated_at"],
        }
        if not any(e["experiment_id"] == entry["experiment_id"] for e in registry):
            registry.append(entry)
    reg_path.write_text(json.dumps(registry, indent=2))

    print(f"\nWrote {C.EVALUATION_JSON}", flush=True)


if __name__ == "__main__":
    main()
