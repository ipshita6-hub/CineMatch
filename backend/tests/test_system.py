"""Health, model info, metrics and database connectivity."""


def test_health_reports_database_and_models(client):
    r = client.get("/health")
    assert r.status_code == 200
    body = r.json()
    assert body["database"] == "connected"
    assert body["status"] == "ok"
    assert body["models_loaded"]["popularity"] is True
    assert body["dataset"] == "MovieLens 20M"


def test_model_info_discloses_dataset_deviation(client):
    body = client.get("/model/info").json()
    assert body["dataset"] == "MovieLens 20M"
    assert body["prd_dataset"] == "MovieLens 25M"
    assert "20M" in body["dataset_deviation_note"]
    assert body["num_users"] > 0 and body["num_movies"] > 0


def test_metrics_are_read_from_the_evaluation_artifact(client):
    body = client.get("/metrics").json()
    if body["status"] == "Not evaluated":
        return                                   # evaluation has not been run
    for name in ("Popularity", "NeuMF"):
        assert name in body["models"]
        assert 0.0 <= body["models"][name]["HR@10"] <= 1.0
    # ranking models must never report a star-rating error
    assert body["models"]["NeuMF"]["RMSE"] == "Not evaluated"
    assert body["protocol"]["identical_candidate_sets"] is True


def test_latency_endpoint_reports_measured_values(client):
    client.get("/health")
    body = client.get("/metrics/latency").json()
    assert body["target_ms"] == 200
    assert any("/health" in route for route in body["live"])


def test_eda_metrics_available(client):
    body = client.get("/metrics/eda").json()
    if body["status"] == "ok":
        assert body["sparsity"]["num_users"] > 0
        assert len(body["rating_distribution"]) == 10
