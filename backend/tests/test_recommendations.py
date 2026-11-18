"""Recommendations, fallbacks, exclusion of seen items and rating prediction."""

import pytest


def test_dataset_user_gets_personalised_recommendations(client):
    r = client.get("/recommendations/1", params={"limit": 5, "model": "neumf"})
    assert r.status_code == 200
    body = r.json()
    assert body["count"] == 5
    assert body["model_used"] in ("neumf", "popularity")
    if body["model_used"] == "neumf":
        assert body["personalised"] is True
        assert body["fallback_used"] is False
    ranks = [i["rank"] for i in body["items"]]
    assert ranks == sorted(ranks) == list(range(1, 6))
    scores = [i["score"] for i in body["items"]]
    assert scores == sorted(scores, reverse=True)


@pytest.mark.parametrize("model", ["neumf", "mf", "popularity", "hybrid"])
def test_every_model_can_serve(client, model):
    r = client.get("/recommendations/7", params={"limit": 3, "model": model})
    assert r.status_code == 200
    assert len(r.json()["items"]) == 3


def test_unknown_dataset_user_falls_back_rather_than_failing(client):
    r = client.get("/recommendations/99999999", params={"limit": 3, "model": "neumf"})
    assert r.status_code == 200
    body = r.json()
    assert body["model_used"] == "popularity"
    assert body["fallback_used"] is True
    assert "not present in the trained model" in body["fallback_reason"]
    assert body["personalised"] is False
    assert len(body["items"]) == 3


def test_invalid_model_is_rejected(client):
    assert client.get("/recommendations/1", params={"model": "magic"}).status_code == 422


def test_limit_bounds_are_enforced(client):
    assert client.get("/recommendations/1", params={"limit": 0}).status_code == 422
    assert client.get("/recommendations/1", params={"limit": 500}).status_code == 422


def test_genre_filter_only_returns_that_genre(client):
    body = client.get("/recommendations/1", params={"limit": 8, "genre": "Horror"}).json()
    assert body["count"] > 0
    for item in body["items"]:
        assert "Horror" in item["genres"]


def test_unknown_genre_is_a_validation_error(client):
    r = client.get("/recommendations/1", params={"genre": "Telenovela"})
    assert r.status_code == 422


def test_new_account_falls_back_until_it_has_ratings(auth_client):
    body = auth_client.get("/recommendations/me", params={"limit": 5, "model": "neumf"}).json()
    assert body["model_used"] == "popularity"
    assert body["fallback_used"] is True
    assert "rate a few movies" in body["fallback_reason"].lower()


def test_rated_movies_are_excluded_from_recommendations(auth_client, seeded_movie_ids):
    first = auth_client.get("/recommendations/me", params={"limit": 10}).json()
    target = first["items"][0]["movie_id"]

    assert auth_client.post("/users/me/ratings",
                            json={"movie_id": target, "rating": 5.0}).status_code == 201

    after = auth_client.get("/recommendations/me", params={"limit": 10}).json()
    assert target not in [i["movie_id"] for i in after["items"]]


def test_fold_in_makes_an_account_personalised(auth_client, seeded_movie_ids):
    payload = {"preferred_genres": ["Action"],
               "ratings": [{"movie_id": m, "rating": 5.0} for m in seeded_movie_ids[:5]]}
    r = auth_client.post("/users/me/onboarding", json=payload)
    assert r.status_code == 200
    assert r.json()["embedding_fitted"] is True

    body = auth_client.get("/recommendations/me", params={"limit": 5, "model": "neumf"}).json()
    assert body["model_used"] == "neumf"
    assert body["personalised"] is True
    rated = set(seeded_movie_ids[:5])
    assert not rated & {i["movie_id"] for i in body["items"]}


def test_predict_returns_a_calibrated_rating(client):
    r = client.post("/predict", json={"user_id": 1, "movie_id": 2571})
    assert r.status_code == 200
    body = r.json()
    if body["status"] == "ok":
        assert body["rating_scale"] == [0.5, 5.0]
        assert 0.5 <= body["predicted_rating"] <= 5.0
        assert "RatingPredictor" in body["model"]


def test_predict_rejects_an_unknown_movie(client):
    assert client.post("/predict", json={"user_id": 1, "movie_id": 99999999}).status_code == 404


def test_predict_explains_itself_for_an_unknown_user(client):
    body = client.post("/predict", json={"user_id": 99999999, "movie_id": 2571}).json()
    assert body["status"] == "unavailable"
    assert "not part of the trained model" in body["detail"]


def test_predict_validates_its_payload(client):
    assert client.post("/predict", json={"movie_id": -1}).status_code == 422
    assert client.post("/predict", json={}).status_code == 422
