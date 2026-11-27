"""Inference service shared by the FastAPI backend.

Loads the trained checkpoints once, on CPU, and exposes scoring, top-N
recommendation, calibrated rating prediction, hybrid re-ranking and cold-start
embedding fold-in. It imports nothing from the training entrypoints beyond the
model definitions, so the API never pulls in a training pipeline.
"""

from __future__ import annotations

import json
import os
import threading
import time
from dataclasses import dataclass, field

import numpy as np
import pandas as pd
import torch

from ml import config as C
from ml.models.matrix_factorization import MatrixFactorization
from ml.models.neumf import NeuMF
from ml.models.rating_predictor import RatingPredictor
from ml.training.data import SeenIndex

MODEL_NEUMF = "neumf"
MODEL_MF = "mf"
MODEL_POPULARITY = "popularity"
MODEL_HYBRID = "hybrid"


@dataclass
class UserVectors:
    """Fold-in representation of an application account."""
    gmf: np.ndarray
    mlp: np.ndarray
    rating_gmf: np.ndarray | None = None
    rating_mlp: np.ndarray | None = None
    rating_bias: float = 0.0
    n_ratings: int = 0
    fitted_at: str = field(default_factory=lambda: time.strftime("%Y-%m-%dT%H:%M:%S"))

    def to_json(self) -> str:
        return json.dumps({
            "gmf": self.gmf.tolist(), "mlp": self.mlp.tolist(),
            "rating_gmf": None if self.rating_gmf is None else self.rating_gmf.tolist(),
            "rating_mlp": None if self.rating_mlp is None else self.rating_mlp.tolist(),
            "rating_bias": float(self.rating_bias),
            "n_ratings": int(self.n_ratings), "fitted_at": self.fitted_at,
        })

    @classmethod
    def from_json(cls, raw: str) -> "UserVectors":
        d = json.loads(raw)
        return cls(
            gmf=np.asarray(d["gmf"], dtype=np.float32),
            mlp=np.asarray(d["mlp"], dtype=np.float32),
            rating_gmf=None if d.get("rating_gmf") is None else np.asarray(d["rating_gmf"], dtype=np.float32),
            rating_mlp=None if d.get("rating_mlp") is None else np.asarray(d["rating_mlp"], dtype=np.float32),
            rating_bias=float(d.get("rating_bias", 0.0)),
            n_ratings=int(d.get("n_ratings", 0)),
            fitted_at=d.get("fitted_at", ""),
        )


class RecommenderService:
    def __init__(self, device: str = "cpu"):
        self.device = device
        self.lock = threading.Lock()
        self.loaded_at = time.strftime("%Y-%m-%dT%H:%M:%S")

        self.preprocessing = self._read_json(C.PREPROCESSING_CONFIG_JSON) or {}
        self.evaluation = self._read_json(C.EVALUATION_JSON)
        self.hybrid_evaluation = self._read_json(C.HYBRID_EVALUATION_JSON)
        self.eda = self._read_json(C.EDA_SUMMARY_JSON)
        self.histories = {
            "neumf": self._read_json(C.NEUMF_HISTORY_JSON),
            "mf": self._read_json(C.MF_HISTORY_JSON),
            "rating": self._read_json(C.RATING_HISTORY_JSON),
        }
        self.experiments = self._read_json(C.METRICS_DIR / "experiments.json") or []

        self.user_mapping = pd.read_csv(C.USER_MAPPING_CSV)
        self.movie_mapping = pd.read_csv(C.MOVIE_MAPPING_CSV)
        self.num_users = len(self.user_mapping)
        self.num_movies = len(self.movie_mapping)

        self.userid_to_idx = dict(zip(self.user_mapping["userId"].astype(int),
                                      self.user_mapping["user_idx"].astype(int)))
        self.idx_to_userid = {v: k for k, v in self.userid_to_idx.items()}
        self.movieid_to_idx = dict(zip(self.movie_mapping["movieId"].astype(int),
                                       self.movie_mapping["movie_idx"].astype(int)))
        self.idx_to_movieid = np.zeros(self.num_movies, dtype=np.int64)
        for mid, idx in self.movieid_to_idx.items():
            self.idx_to_movieid[idx] = mid

        self.movies = pd.read_csv(C.MOVIES_FEATURES_CSV)
        self.genre_columns = [
            c for c in self.movies.columns
            if c not in {"movieId", "title", "genres", "release_year", "movie_idx",
                         "train_rating_count", "train_avg_rating", "imdbId", "tmdbId"}
        ]
        self._build_catalog()

        self.popularity = pd.read_csv(C.POPULARITY_CSV).sort_values("movie_idx")
        self.pop_count = np.zeros(self.num_movies, dtype=np.float32)
        self.pop_count[self.popularity["movie_idx"].to_numpy()] = \
            self.popularity["train_rating_count"].to_numpy()
        self.pop_bayes = np.zeros(self.num_movies, dtype=np.float32)
        self.pop_bayes[self.popularity["movie_idx"].to_numpy()] = \
            self.popularity["bayesian_score"].to_numpy()
        self.popularity_order = np.argsort(-self.pop_count, kind="stable")

        self.seen = SeenIndex.load(C.MAPPING_DIR / "seen_all.npz", self.num_users, self.num_movies)

        # LIGHT_INFERENCE=1 serves NeuMF and popularity only, skipping the
        # matrix-factorization and rating-predictor checkpoints (~60 MB of
        # resident memory). Both are already optional everywhere they are used,
        # so this is the same state as their checkpoints being absent. Set it
        # on memory-capped deployments; leave it unset for the full feature set.
        light = os.environ.get("LIGHT_INFERENCE") == "1"
        self.neumf, self.neumf_ckpt = self._load(MODEL_NEUMF)
        if light:
            self.mf, self.mf_ckpt = None, None
            self.rating_model, self.rating_ckpt = None, None
        else:
            self.mf, self.mf_ckpt = self._load(MODEL_MF)
            self.rating_model, self.rating_ckpt = self._load("rating")

        self._all_items = torch.arange(self.num_movies, dtype=torch.long, device=self.device)

    # ------------------------------------------------------------------ load
    @staticmethod
    def _read_json(path):
        try:
            return json.loads(path.read_text())
        except Exception:
            return None

    def _load(self, kind: str):
        path = {MODEL_NEUMF: C.NEUMF_CHECKPOINT, MODEL_MF: C.MF_CHECKPOINT,
                "rating": C.RATING_CHECKPOINT}[kind]
        if not path.exists():
            return None, None
        ckpt = torch.load(path, map_location="cpu", weights_only=False)
        cfg = ckpt["config"]
        if kind == MODEL_MF:
            model = MatrixFactorization(self.num_users, self.num_movies, cfg["embedding_dim"])
        elif kind == MODEL_NEUMF:
            model = NeuMF(self.num_users, self.num_movies, cfg["gmf_embedding_dim"],
                          cfg["mlp_embedding_dim"], cfg["mlp_layers"], cfg["dropout"])
        else:
            model = RatingPredictor(self.num_users, self.num_movies, cfg["gmf_embedding_dim"],
                                    cfg["mlp_embedding_dim"], cfg["mlp_layers"], cfg["dropout"],
                                    cfg["rating_scale"][0], cfg["rating_scale"][1])
        model.load_state_dict(ckpt["model_state_dict"])
        model.eval()
        for p in model.parameters():
            p.requires_grad_(False)
        return model.to(self.device), ckpt

    def _build_catalog(self) -> None:
        m = self.movies.dropna(subset=["movie_idx"]).copy()
        m["movie_idx"] = m["movie_idx"].astype(int)
        self.catalog = m.set_index("movie_idx")
        self.genre_matrix = np.zeros((self.num_movies, len(self.genre_columns)), dtype=np.float32)
        gm = m[self.genre_columns].to_numpy(dtype=np.float32)
        self.genre_matrix[m["movie_idx"].to_numpy()] = gm
        norms = np.linalg.norm(self.genre_matrix, axis=1, keepdims=True)
        self.genre_matrix_norm = self.genre_matrix / np.maximum(norms, 1e-8)
        self.title_by_idx = dict(zip(m["movie_idx"], m["title"]))

    # ------------------------------------------------------------- availability
    @property
    def available_models(self) -> list[str]:
        models = [MODEL_POPULARITY]
        if self.mf is not None:
            models.append(MODEL_MF)
        if self.neumf is not None:
            models.extend([MODEL_NEUMF, MODEL_HYBRID])
        return models

    def has_dataset_user(self, user_idx: int | None) -> bool:
        return user_idx is not None and 0 <= user_idx < self.num_users

    # ------------------------------------------------------------------ scoring
    @torch.no_grad()
    def _model_scores(self, model, user_idx: int) -> np.ndarray:
        users = torch.full_like(self._all_items, int(user_idx))
        return model(users, self._all_items).float().numpy()

    @torch.no_grad()
    def _vector_scores(self, vectors: UserVectors) -> np.ndarray:
        gmf = torch.as_tensor(vectors.gmf, dtype=torch.float32)
        mlp = torch.as_tensor(vectors.mlp, dtype=torch.float32)
        return self.neumf.forward_from_user_vectors(gmf, mlp, self._all_items).float().numpy()

    def raw_scores(self, model: str, user_idx: int | None = None,
                   vectors: UserVectors | None = None) -> tuple[np.ndarray, str]:
        """Returns (scores over every movie_idx, model actually used)."""
        if model in (MODEL_NEUMF, MODEL_HYBRID) and self.neumf is not None:
            if vectors is not None:
                return self._vector_scores(vectors), model
            if self.has_dataset_user(user_idx):
                return self._model_scores(self.neumf, user_idx), model
        if model == MODEL_MF and self.mf is not None and self.has_dataset_user(user_idx):
            return self._model_scores(self.mf, user_idx), MODEL_MF
        return self.pop_count.copy(), MODEL_POPULARITY

    # ------------------------------------------------------------ hybrid blend
    def user_genre_profile(self, liked_idx: np.ndarray) -> np.ndarray | None:
        if liked_idx is None or len(liked_idx) == 0:
            return None
        prof = self.genre_matrix[liked_idx].mean(axis=0)
        n = np.linalg.norm(prof)
        return prof / n if n > 1e-8 else None

    @staticmethod
    def _normalise(x: np.ndarray) -> np.ndarray:
        finite = x[np.isfinite(x)]
        if finite.size == 0:
            return np.zeros_like(x)
        lo, hi = float(finite.min()), float(finite.max())
        if hi - lo < 1e-12:
            return np.zeros_like(x)
        return (x - lo) / (hi - lo)

    def hybrid_scores(self, base: np.ndarray, genre_profile: np.ndarray | None,
                      alpha: float = C.HYBRID_ALPHA, beta: float = C.HYBRID_BETA,
                      gamma: float = C.HYBRID_GAMMA) -> np.ndarray:
        model_n = self._normalise(base)
        pop_n = self._normalise(np.log1p(self.pop_count))
        if genre_profile is None:
            genre_sim = np.zeros(self.num_movies, dtype=np.float32)
        else:
            genre_sim = self.genre_matrix_norm @ genre_profile.astype(np.float32)
        return alpha * model_n + beta * genre_sim + gamma * pop_n

    # -------------------------------------------------------------- top-N API
    def top_n(
        self, *, model: str = MODEL_NEUMF, user_idx: int | None = None,
        vectors: UserVectors | None = None, k: int = 10,
        exclude_idx: np.ndarray | None = None, genre: str | None = None,
        min_year: int | None = None, max_year: int | None = None,
        hybrid_weights: tuple[float, float, float] = (C.HYBRID_ALPHA, C.HYBRID_BETA, C.HYBRID_GAMMA),
    ) -> list[dict]:
        scores, used = self.raw_scores(model, user_idx, vectors)
        base_scores = scores.copy()

        if used == MODEL_HYBRID:
            liked = exclude_idx if exclude_idx is not None else np.array([], dtype=np.int64)
            if self.has_dataset_user(user_idx) and (exclude_idx is None or len(exclude_idx) == 0):
                liked = self.seen.items_for(int(user_idx))
            scores = self.hybrid_scores(base_scores, self.user_genre_profile(liked), *hybrid_weights)

        scores = scores.astype(np.float64)

        # exclusion: dataset history and/or application ratings
        if self.has_dataset_user(user_idx):
            scores[self.seen.items_for(int(user_idx))] = -np.inf
        if exclude_idx is not None and len(exclude_idx):
            scores[np.asarray(exclude_idx, dtype=np.int64)] = -np.inf

        mask = np.ones(self.num_movies, dtype=bool)
        if genre:
            if genre not in self.genre_columns:
                raise ValueError(f"unknown genre '{genre}'")
            mask &= self.genre_matrix[:, self.genre_columns.index(genre)] == 1
        if min_year is not None or max_year is not None:
            years = self.catalog["release_year"].reindex(range(self.num_movies))
            yv = years.to_numpy(dtype="float64")
            if min_year is not None:
                mask &= np.nan_to_num(yv, nan=-1) >= min_year
            if max_year is not None:
                mask &= np.nan_to_num(yv, nan=10**6) <= max_year
        scores[~mask] = -np.inf

        k = max(1, min(int(k), int(np.isfinite(scores).sum())))
        if k == 0:
            return []
        top = np.argpartition(-scores, k - 1)[:k]
        top = top[np.argsort(-scores[top])]

        out = []
        for rank, idx in enumerate(top, start=1):
            if not np.isfinite(scores[idx]):
                continue
            out.append({
                "rank": rank,
                "movie_idx": int(idx),
                "movie_id": int(self.idx_to_movieid[idx]),
                "score": float(scores[idx]),
                "raw_model_score": float(base_scores[idx]),
                "model": used,
            })
        return out

    # ------------------------------------------------------- rating prediction
    @torch.no_grad()
    def predict_rating(self, movie_idx: int, user_idx: int | None = None,
                       vectors: UserVectors | None = None) -> dict:
        if self.rating_model is None:
            return {"status": "unavailable",
                    "detail": "Rating-prediction model has not been trained."}
        item = torch.tensor([int(movie_idx)], dtype=torch.long)
        if vectors is not None and vectors.rating_gmf is not None:
            pred = self.rating_model.forward_from_user_vectors(
                torch.as_tensor(vectors.rating_gmf, dtype=torch.float32),
                torch.as_tensor(vectors.rating_mlp, dtype=torch.float32),
                torch.tensor(float(vectors.rating_bias)), item)
            source = "fold-in user vectors"
        elif self.has_dataset_user(user_idx):
            pred = self.rating_model(torch.tensor([int(user_idx)], dtype=torch.long), item)
            source = "trained dataset user embedding"
        else:
            return {"status": "unavailable",
                    "detail": "No user representation available for rating prediction."}
        return {
            "status": "ok",
            "predicted_rating": round(float(pred.item()), 3),
            "rating_scale": [C.RATING_MIN, C.RATING_MAX],
            "model": "RatingPredictor (NeuMF trunk + calibrated regression head)",
            "source": source,
        }

    # --------------------------------------------------------------- fold-in
    def fit_user_embedding(
        self, rated: list[tuple[int, float]], *, steps: int = 220, lr: float = 0.08,
        negatives: int = 8, seed: int = C.SEED,
    ) -> UserVectors:
        """Fit ONE new user's vectors with every item parameter frozen.

        Positives are the movies the account rated >= the positive threshold;
        negatives are sampled unobserved movies. Runs in well under a second on
        CPU, so a new account gets real NeuMF personalisation without retraining.
        """
        if self.neumf is None:
            raise RuntimeError("NeuMF checkpoint is not available")
        rng = np.random.default_rng(seed)
        rated_idx = np.array([m for m, _ in rated], dtype=np.int64)
        ratings = np.array([r for _, r in rated], dtype=np.float32)
        pos = rated_idx[ratings >= C.POSITIVE_RATING_THRESHOLD]
        if len(pos) == 0:                      # nothing liked yet: use all rated
            pos = rated_idx

        torch.manual_seed(seed)
        gmf_u = torch.zeros(self.neumf.gmf_dim, requires_grad=True)
        mlp_u = torch.zeros(self.neumf.mlp_dim, requires_grad=True)
        with torch.no_grad():
            gmf_u.normal_(0, 0.01)
            mlp_u.normal_(0, 0.01)
        opt = torch.optim.Adam([gmf_u, mlp_u], lr=lr)
        loss_fn = torch.nn.BCEWithLogitsLoss()
        pos_t = torch.as_tensor(pos, dtype=torch.long)
        seen_set = set(rated_idx.tolist())

        for _ in range(steps):
            neg = rng.integers(0, self.num_movies, size=len(pos) * negatives)
            neg = np.array([n for n in neg if n not in seen_set], dtype=np.int64)
            items = torch.cat([pos_t, torch.as_tensor(neg, dtype=torch.long)])
            labels = torch.cat([torch.ones(len(pos)), torch.zeros(len(neg))])
            logits = self.neumf.forward_from_user_vectors(gmf_u, mlp_u, items)
            loss = loss_fn(logits, labels)
            opt.zero_grad(set_to_none=True)
            loss.backward()
            opt.step()

        vectors = UserVectors(gmf=gmf_u.detach().numpy().astype(np.float32),
                              mlp=mlp_u.detach().numpy().astype(np.float32),
                              n_ratings=len(rated))

        # Explicit-rating vectors, fitted on the real star ratings with MSE
        if self.rating_model is not None and len(rated) > 0:
            rg = torch.zeros(self.rating_model.trunk.gmf_dim, requires_grad=True)
            rm = torch.zeros(self.rating_model.trunk.mlp_dim, requires_grad=True)
            rb = torch.zeros(1, requires_grad=True)
            with torch.no_grad():
                rg.normal_(0, 0.01)
                rm.normal_(0, 0.01)
            opt2 = torch.optim.Adam([rg, rm, rb], lr=lr)
            items = torch.as_tensor(rated_idx, dtype=torch.long)
            target = torch.as_tensor(ratings, dtype=torch.float32)
            for _ in range(steps):
                pred = self.rating_model.forward_from_user_vectors(rg, rm, rb.squeeze(), items)
                loss = torch.nn.functional.mse_loss(pred, target)
                opt2.zero_grad(set_to_none=True)
                loss.backward()
                opt2.step()
            vectors.rating_gmf = rg.detach().numpy().astype(np.float32)
            vectors.rating_mlp = rm.detach().numpy().astype(np.float32)
            vectors.rating_bias = float(rb.detach().item())

        return vectors

    # ------------------------------------------------------- catalog helpers
    def similar_by_genre(self, movie_idx: int, k: int = 8) -> list[dict]:
        v = self.genre_matrix_norm[movie_idx]
        sims = self.genre_matrix_norm @ v
        sims[movie_idx] = -np.inf
        # break ties towards movies people have actually rated
        blended = sims + 1e-6 * self._normalise(np.log1p(self.pop_count))
        top = np.argpartition(-blended, k)[:k]
        top = top[np.argsort(-blended[top])]
        return [{"movie_idx": int(i), "movie_id": int(self.idx_to_movieid[i]),
                 "similarity": round(float(sims[i]), 4)} for i in top if np.isfinite(sims[i])]

    def popular(self, k: int = 10, genre: str | None = None,
                exclude_idx: np.ndarray | None = None) -> list[dict]:
        return self.top_n(model=MODEL_POPULARITY, k=k, genre=genre, exclude_idx=exclude_idx)

    def model_info(self) -> dict:
        def ckpt_info(ckpt):
            if ckpt is None:
                return {"status": "not trained"}
            return {"status": "loaded", "config": ckpt["config"], "best_epoch": ckpt["epoch"],
                    "training": ckpt.get("training", {}), "saved_at": ckpt.get("saved_at")}
        return {
            "dataset": C.DATASET_NAME,
            "dataset_version": C.DATASET_VERSION,
            "prd_dataset": C.PRD_DATASET_NAME,
            "dataset_deviation_note": self.preprocessing.get("dataset_deviation_note"),
            "num_users": self.num_users,
            "num_movies": self.num_movies,
            "device": self.device,
            "loaded_at": self.loaded_at,
            "available_models": self.available_models,
            "neumf": ckpt_info(self.neumf_ckpt),
            "matrix_factorization": ckpt_info(self.mf_ckpt),
            "rating_predictor": ckpt_info(self.rating_ckpt),
            "preprocessing": self.preprocessing,
            "training_history": self.histories,
            "experiments": self.experiments,
            "hybrid": {
                "weights": {"alpha": C.HYBRID_ALPHA, "beta": C.HYBRID_BETA,
                            "gamma": C.HYBRID_GAMMA},
                "evaluation": self.hybrid_evaluation or {"status": "Not evaluated"},
            },
        }


_service: RecommenderService | None = None
_service_lock = threading.Lock()


def get_service() -> RecommenderService:
    global _service
    if _service is None:
        with _service_lock:
            if _service is None:
                _service = RecommenderService()
    return _service
