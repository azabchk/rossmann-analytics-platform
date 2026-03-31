from src.core.config import get_settings


def test_auth_me_requires_bearer_token(client):
    response = client.get("/api/v1/auth/me")

    assert response.status_code == 401
    assert response.json()["code"] == "authentication_required"


def test_auth_me_returns_request_context_for_valid_token(client, auth_token):
    response = client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {auth_token}"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["user_id"] == "00000000-0000-0000-0000-000000000001"
    assert body["email"] == "admin@example.com"
    assert body["role"] == "admin"


def test_demo_token_endpoint_is_disabled_without_opt_in(client):
    response = client.post("/api/v1/auth/demo-token")

    assert response.status_code == 404
    assert response.json()["code"] == "not_found"


def test_demo_token_endpoint_returns_valid_local_demo_token(client, monkeypatch):
    monkeypatch.setenv("ENABLE_LOCAL_DEMO_AUTH", "true")
    get_settings.cache_clear()

    response = client.post("/api/v1/auth/demo-token")

    assert response.status_code == 200
    body = response.json()
    assert body["email"] == "analyst@example.com"
    assert body["role"] == "data_analyst"
    assert body["token_type"] == "bearer"

    me_response = client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {body['access_token']}"},
    )

    assert me_response.status_code == 200
    me_body = me_response.json()
    assert me_body["user_id"] == "00000000-0000-0000-0000-000000000002"
    assert me_body["email"] == "analyst@example.com"
    assert me_body["role"] == "data_analyst"
