"""Registration, login, token handling and the protected-route guard."""

import uuid


def _creds():
    tag = uuid.uuid4().hex[:8]
    return {"username": f"user_{tag}", "email": f"user_{tag}@example.com",
            "password": "a-strong-password"}


def test_register_returns_a_token_and_user(client):
    r = client.post("/auth/register", json=_creds())
    assert r.status_code == 201
    body = r.json()
    assert body["token_type"] == "bearer"
    assert body["user"]["onboarded"] is False
    assert "password" not in body["user"]
    assert "hashed_password" not in body["user"]


def test_duplicate_username_is_rejected(client):
    creds = _creds()
    assert client.post("/auth/register", json=creds).status_code == 201
    r = client.post("/auth/register", json={**creds, "email": "other@example.com"})
    assert r.status_code == 409


def test_weak_password_is_rejected(client):
    r = client.post("/auth/register", json={**_creds(), "password": "short"})
    assert r.status_code == 422


def test_login_with_correct_and_incorrect_password(client):
    creds = _creds()
    client.post("/auth/register", json=creds)
    ok = client.post("/auth/login", json={"username": creds["username"],
                                          "password": creds["password"]})
    assert ok.status_code == 200
    bad = client.post("/auth/login", json={"username": creds["username"],
                                           "password": "wrong-password"})
    assert bad.status_code == 401


def test_me_requires_a_token(client):
    assert client.get("/auth/me").status_code == 401
    assert client.get("/auth/me", headers={"Authorization": "Bearer nonsense"}).status_code == 401


def test_me_returns_the_signed_in_account(auth_client):
    body = auth_client.get("/auth/me").json()
    assert body["username"] == auth_client.user["username"]


def test_logout_revokes_sessions(auth_client):
    r = auth_client.post("/auth/logout")
    assert r.status_code == 200
    assert r.json()["sessions_revoked"] >= 1
