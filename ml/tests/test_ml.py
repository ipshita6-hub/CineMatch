"""ML-layer tests: metrics, mappings, sampling, model shapes, calibration."""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pytest
import torch

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from ml import config as C  # noqa: E402
from ml.evaluation.metrics import ranking_metrics, rating_metrics, roc_auc_from_candidates  # noqa: E402
from ml.models.matrix_factorization import MatrixFactorization  # noqa: E402
from ml.models.neumf import NeuMF  # noqa: E402
from ml.models.rating_predictor import RatingPredictor  # noqa: E402
from ml.training.data import SeenIndex, build_candidate_sets, sample_negatives  # noqa: E402


# --------------------------------------------------------------- metrics
def test_ndcg_matches_a_hand_computation():
    # positive ranked 1st, 3rd, and outside the top-10
    scores = np.full((3, 100), -5.0)
    scores[0, 0], scores[0, 1], scores[0, 2] = 9, 1, 2        # rank 0
    scores[1, 0], scores[1, 1], scores[1, 2] = 5, 9, 7        # rank 2
    scores[2, 0] = 0
    scores[2, 1:20] = 1                                        # rank 19 -> miss
    m = ranking_metrics(scores, k=10)
    expected_ndcg = (1 / np.log2(2) + 1 / np.log2(4) + 0) / 3
    assert m["HR@10"] == pytest.approx(2 / 3)
    assert m["NDCG@10"] == pytest.approx(expected_ndcg, abs=1e-9)
    assert m["MRR"] == pytest.approx((1 / 1 + 1 / 3 + 1 / 20) / 3, abs=1e-9)


def test_precision_and_recall_follow_from_hr_with_one_relevant_item():
    scores = np.random.default_rng(0).normal(size=(500, 100))
    m = ranking_metrics(scores, k=10)
    assert m["Precision@10"] == pytest.approx(m["HR@10"] / 10)
    assert m["Recall@10"] == pytest.approx(m["HR@10"])


def test_a_constant_scorer_cannot_inflate_hit_rate():
    """Ties must be broken against the positive, not in its favour."""
    scores = np.zeros((100, 100))
    assert ranking_metrics(scores, k=10)["HR@10"] == 0.0


def test_perfect_and_worst_rankings():
    best = np.tile(np.concatenate([[10.0], np.zeros(99)]), (50, 1))
    assert ranking_metrics(best, k=10)["HR@10"] == 1.0
    assert ranking_metrics(best, k=10)["NDCG@10"] == 1.0
    worst = np.tile(np.concatenate([[-10.0], np.zeros(99)]), (50, 1))
    assert ranking_metrics(worst, k=10)["HR@10"] == 0.0


def test_roc_auc_bounds():
    best = np.tile(np.concatenate([[10.0], np.full(99, -10.0)]), (20, 1))
    assert roc_auc_from_candidates(best) == pytest.approx(1.0)


def test_rating_metrics():
    y = np.array([4.0, 3.0, 5.0])
    assert rating_metrics(y, y)["RMSE"] == 0.0
    m = rating_metrics(y, y + 1)
    assert m["RMSE"] == pytest.approx(1.0)
    assert m["MAE"] == pytest.approx(1.0)


# ------------------------------------------------------- seen index & sampling
@pytest.fixture(scope="module")
def seen_index() -> SeenIndex:
    # user 0 saw {1,2,3}; user 1 saw {0}; user 2 saw nothing
    indptr = np.array([0, 3, 4, 4], dtype=np.int64)
    indices = np.array([1, 2, 3, 0], dtype=np.int32)
    return SeenIndex(indptr, indices, num_users=3, num_movies=10)


def test_seen_index_membership(seen_index):
    users = np.array([0, 0, 1, 1, 2])
    items = np.array([2, 7, 0, 5, 0])
    assert list(seen_index.contains(users, items)) == [True, False, True, False, False]


def test_sampled_negatives_are_never_observed(seen_index):
    rng = np.random.default_rng(0)
    users = np.array([0, 1, 2] * 50)
    negatives = sample_negatives(users, 4, seen_index, rng)
    assert not seen_index.contains(np.repeat(users, 4), negatives).any()
    assert negatives.min() >= 0 and negatives.max() < seen_index.num_movies


def test_candidate_sets_are_unique_and_unobserved(seen_index):
    rng = np.random.default_rng(1)
    users = np.array([0, 1, 2])
    positives = np.array([5, 6, 7])
    cands = build_candidate_sets(users, positives, 4, seen_index, rng)
    assert cands.shape == (3, 5)
    assert (cands[:, 0] == positives).all()
    for row in cands:
        assert len(set(row.tolist())) == len(row)       # no duplicates in a row
    assert not seen_index.contains(np.repeat(users, 4), cands[:, 1:].ravel()).any()


def test_real_evaluation_candidates_are_sound():
    if not C.EVAL_CANDIDATES_NPZ.exists():
        pytest.skip("evaluation candidates not built")
    z = np.load(C.EVAL_CANDIDATES_NPZ)
    users, cands = z["users"], z["candidates"]
    assert cands.shape[1] == 1 + C.N_EVAL_NEGATIVES
    assert len(np.unique(users)) == len(users)          # one row per user
    for row in cands[:200]:
        assert len(set(row.tolist())) == len(row)


# ---------------------------------------------------------------- mappings
def test_user_and_movie_mappings_round_trip():
    if not C.USER_MAPPING_CSV.exists():
        pytest.skip("preprocessing artifacts not built")
    import pandas as pd
    users = pd.read_csv(C.USER_MAPPING_CSV)
    movies = pd.read_csv(C.MOVIE_MAPPING_CSV)
    for df, col in ((users, "user_idx"), (movies, "movie_idx")):
        idx = df[col].to_numpy()
        assert idx.min() == 0
        assert idx.max() == len(df) - 1
        assert len(np.unique(idx)) == len(df)           # contiguous and unique


def test_splits_are_disjoint_and_chronological():
    if not C.TRAIN_PARQUET.exists():
        pytest.skip("preprocessing artifacts not built")
    import pandas as pd
    val = pd.read_parquet(C.VAL_PARQUET)
    test = pd.read_parquet(C.TEST_PARQUET)
    assert val["user_idx"].is_unique and test["user_idx"].is_unique
    merged = val.merge(test, on=["user_idx", "movie_idx"], how="inner")
    assert len(merged) == 0                              # no leakage val <-> test
    joined = val[["user_idx", "timestamp"]].merge(
        test[["user_idx", "timestamp"]], on="user_idx", suffixes=("_val", "_test"))
    assert (joined["timestamp_test"] >= joined["timestamp_val"]).all()


# ------------------------------------------------------------------ models
def test_neumf_forward_shapes_and_branches():
    model = NeuMF(50, 30, gmf_dim=8, mlp_dim=8, mlp_layers=[16, 8, 4])
    users = torch.randint(0, 50, (7,))
    items = torch.randint(0, 30, (7,))
    assert model(users, items).shape == (7,)
    assert model.interaction_vector(users, items).shape == (7, 8 + 4)
    # GMF and MLP must not share embedding tables
    assert model.gmf_user_emb.weight.data_ptr() != model.mlp_user_emb.weight.data_ptr()


def test_neumf_vector_path_matches_the_embedding_path():
    torch.manual_seed(0)
    model = NeuMF(20, 15, gmf_dim=8, mlp_dim=8, mlp_layers=[16, 8]).eval()
    items = torch.arange(15)
    with torch.no_grad():
        via_table = model(torch.full((15,), 3), items)
        via_vectors = model.forward_from_user_vectors(
            model.gmf_user_emb.weight[3], model.mlp_user_emb.weight[3], items)
    assert torch.allclose(via_table, via_vectors, atol=1e-6)


def test_matrix_factorization_forward():
    model = MatrixFactorization(40, 25, dim=8)
    assert model(torch.randint(0, 40, (5,)), torch.randint(0, 25, (5,))).shape == (5,)


def test_rating_predictions_are_inside_the_movielens_scale():
    torch.manual_seed(0)
    model = RatingPredictor(30, 20, gmf_dim=8, mlp_dim=8, mlp_layers=[16, 8]).eval()
    # push the trunk hard in both directions: the squashing must still hold
    with torch.no_grad():
        for emb in (model.trunk.gmf_user_emb, model.trunk.gmf_item_emb):
            emb.weight.fill_(50.0)
        model.user_bias.weight.fill_(-100.0)
        low = model(torch.arange(30) % 30, torch.arange(30) % 20)
        model.user_bias.weight.fill_(100.0)
        high = model(torch.arange(30) % 30, torch.arange(30) % 20)
    assert low.min() >= C.RATING_MIN and high.max() <= C.RATING_MAX


# ------------------------------------------------- checkpoints and inference
@pytest.mark.skipif(not C.NEUMF_CHECKPOINT.exists(), reason="NeuMF not trained")
def test_checkpoint_loads_and_scores():
    from ml.inference.recommender import MODEL_NEUMF, RecommenderService
    svc = RecommenderService()
    assert svc.neumf is not None
    recs = svc.top_n(model=MODEL_NEUMF, user_idx=0, k=10)
    assert len(recs) == 10
    assert [r["rank"] for r in recs] == list(range(1, 11))
    scores = [r["score"] for r in recs]
    assert scores == sorted(scores, reverse=True)
    # nothing the user already interacted with may be recommended
    seen = set(svc.seen.items_for(0).tolist())
    assert not seen & {r["movie_idx"] for r in recs}


@pytest.mark.skipif(not C.NEUMF_CHECKPOINT.exists(), reason="NeuMF not trained")
def test_fold_in_produces_usable_vectors():
    from ml.inference.recommender import MODEL_NEUMF, RecommenderService
    svc = RecommenderService()
    rated = [(int(i), 5.0) for i in svc.seen.items_for(0)[:6]]
    vectors = svc.fit_user_embedding(rated, steps=40)
    assert vectors.gmf.shape == (svc.neumf.gmf_dim,)
    assert np.isfinite(vectors.gmf).all() and np.isfinite(vectors.mlp).all()
    recs = svc.top_n(model=MODEL_NEUMF, vectors=vectors, k=5,
                     exclude_idx=np.array([m for m, _ in rated]))
    assert len(recs) == 5
    assert not {m for m, _ in rated} & {r["movie_idx"] for r in recs}


@pytest.mark.skipif(not C.NEUMF_CHECKPOINT.exists(), reason="NeuMF not trained")
def test_genre_filter_only_returns_that_genre():
    from ml.inference.recommender import MODEL_NEUMF, RecommenderService
    svc = RecommenderService()
    gi = svc.genre_columns.index("Horror")
    for r in svc.top_n(model=MODEL_NEUMF, user_idx=5, k=10, genre="Horror"):
        assert svc.genre_matrix[r["movie_idx"], gi] == 1
    with pytest.raises(ValueError):
        svc.top_n(model=MODEL_NEUMF, user_idx=5, k=5, genre="Telenovela")
