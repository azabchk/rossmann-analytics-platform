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
