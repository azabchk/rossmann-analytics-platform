from uuid import uuid4

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


def test_auth_me_accepts_supabase_validated_token_when_local_jwt_decode_fails(client, monkeypatch):
    async def mock_fetch_supabase_user_claims(token, settings):
        assert token == "external-access-token"
        assert settings is not None
        return {
            "sub": "00000000-0000-0000-0000-000000000010",
            "email": "supabase-user@example.com",
            "role": "authenticated",
            "app_metadata": {"role": "authenticated"},
        }

    monkeypatch.setattr(
        "src.security.jwt.fetch_supabase_user_claims",
        mock_fetch_supabase_user_claims,
    )

    response = client.get(
        "/api/v1/auth/me",
        headers={"Authorization": "Bearer external-access-token"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["user_id"] == "00000000-0000-0000-0000-000000000010"
    assert body["email"] == "supabase-user@example.com"
    assert body["role"] == "authenticated"


def test_local_signup_returns_a_valid_access_token(client):
    email = f"codex-signup-{uuid4()}@example.com"

    response = client.post(
        "/api/v1/auth/signup",
        json={
            "email": email,
            "password": "Password12345abc",
        },
    )

    assert response.status_code == 201
    body = response.json()
    assert body["email"] == email
    assert body["role"] == "data_analyst"
    assert body["token_type"] == "bearer"

    me_response = client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {body['access_token']}"},
    )

    assert me_response.status_code == 200
    me_body = me_response.json()
    assert me_body["email"] == email
    assert me_body["role"] == "data_analyst"


def test_local_login_returns_a_valid_access_token_for_existing_account(client):
    email = f"codex-login-{uuid4()}@example.com"
    password = "Password12345abc"

    signup_response = client.post(
        "/api/v1/auth/signup",
        json={
            "email": email,
            "password": password,
        },
    )
    assert signup_response.status_code == 201

    login_response = client.post(
        "/api/v1/auth/login",
        json={
            "email": email,
            "password": password,
        },
    )

    assert login_response.status_code == 200
    body = login_response.json()
    assert body["email"] == email
    assert body["role"] == "data_analyst"

    me_response = client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {body['access_token']}"},
    )

    assert me_response.status_code == 200
    assert me_response.json()["email"] == email


def test_demo_token_endpoint_includes_cors_headers_for_local_frontend(client, monkeypatch):
    monkeypatch.setenv("ENABLE_LOCAL_DEMO_AUTH", "true")
    monkeypatch.setenv(
        "BACKEND_CORS_ORIGINS",
        "http://localhost:3000,http://127.0.0.1:3000",
    )
    get_settings.cache_clear()

    response = client.post(
        "/api/v1/auth/demo-token",
        headers={"Origin": "http://localhost:3000"},
    )

    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == "http://localhost:3000"
