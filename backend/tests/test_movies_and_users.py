"""Catalog search/filtering and the account-scoped endpoints."""


def test_search_by_title(client):
    body = client.get("/movies", params={"search": "Matrix"}).json()
    assert body["total"] >= 1
    assert any("Matrix" in m["title"] for m in body["items"])


def test_pagination_is_consistent(client):
    p1 = client.get("/movies", params={"page": 1, "page_size": 5}).json()
    p2 = client.get("/movies", params={"page": 2, "page_size": 5}).json()
    assert len(p1["items"]) == 5
    assert p1["total"] == p2["total"]
    assert {m["movie_id"] for m in p1["items"]} & {m["movie_id"] for m in p2["items"]} == set()


def test_year_filtering(client):
    body = client.get("/movies", params={"min_year": 2000, "max_year": 2005}).json()
    for m in body["items"]:
        assert 2000 <= m["release_year"] <= 2005


def test_sorting_by_popularity_is_descending(client):
    body = client.get("/movies", params={"sort": "popularity", "page_size": 10}).json()
    counts = [m["dataset_rating_count"] for m in body["items"]]
    assert counts == sorted(counts, reverse=True)


def test_invalid_sort_is_rejected(client):
    assert client.get("/movies", params={"sort": "vibes"}).status_code == 422


def test_genres_endpoint(client):
    genres = client.get("/movies/genres").json()
    assert "Action" in genres and "Sci-Fi" in genres


def test_movie_detail_includes_similar_titles(client, seeded_movie_ids):
    body = client.get(f"/movies/{seeded_movie_ids[0]}").json()
    assert body["movie_id"] == seeded_movie_ids[0]
    assert len(body["similar_movies"]) > 0
    assert body["predicted_rating_status"] in ("ok", "unavailable")


def test_unknown_movie_returns_404(client):
    assert client.get("/movies/99999999").status_code == 404


def test_preferences_round_trip(auth_client):
    r = auth_client.put("/users/me/preferences",
                        json={"preferred_genres": ["Action", "Drama"], "default_model": "neumf"})
    assert r.status_code == 200
    assert auth_client.get("/users/me/preferences").json()["preferred_genres"] == ["Action", "Drama"]


def test_unknown_genre_preference_rejected(auth_client):
    r = auth_client.put("/users/me/preferences",
                        json={"preferred_genres": ["Telenovela"], "default_model": "neumf"})
    assert r.status_code == 422


def test_rating_validation_and_history(auth_client, seeded_movie_ids):
    movie_id = seeded_movie_ids[0]
    assert auth_client.post("/users/me/ratings",
                            json={"movie_id": movie_id, "rating": 7.0}).status_code == 422
    assert auth_client.post("/users/me/ratings",
                            json={"movie_id": movie_id, "rating": 3.3}).status_code == 422
    assert auth_client.post("/users/me/ratings",
                            json={"movie_id": movie_id, "rating": 3.5}).status_code == 201

    ratings = auth_client.get("/users/me/ratings").json()
    assert ratings["count"] == 1
    assert ratings["items"][0]["user_rating"] == 3.5

    # re-rating updates rather than duplicating
    assert auth_client.post("/users/me/ratings",
                            json={"movie_id": movie_id, "rating": 4.5}).status_code == 201
    assert auth_client.get("/users/me/ratings").json()["count"] == 1

    assert auth_client.delete(f"/users/me/ratings/{movie_id}").status_code == 204
    assert auth_client.get("/users/me/ratings").json()["count"] == 0


def test_rating_an_unknown_movie_404s(auth_client):
    assert auth_client.post("/users/me/ratings",
                            json={"movie_id": 99999999, "rating": 4.0}).status_code == 404


def test_status_reports_the_personalisation_method(auth_client, seeded_movie_ids):
    before = auth_client.get("/users/me/status").json()
    assert before["method"] == "popularity fallback"

    for m in seeded_movie_ids[:4]:
        auth_client.post("/users/me/ratings", json={"movie_id": m, "rating": 4.5})

    after = auth_client.get("/users/me/status").json()
    assert after["embedding_fitted"] is True
    assert after["method"] == "fold-in user embedding"


def test_recommendation_history_is_recorded(auth_client):
    auth_client.get("/recommendations/me", params={"limit": 5})
    body = auth_client.get("/users/me/history").json()
    assert body["count"] > 0
    assert body["items"][0]["model_name"] in ("neumf", "mf", "popularity", "hybrid")


def test_account_endpoints_require_authentication(client):
    for path in ["/users/me/preferences", "/users/me/ratings",
                 "/users/me/history", "/users/me/status", "/recommendations/me"]:
        assert client.get(path).status_code == 401
