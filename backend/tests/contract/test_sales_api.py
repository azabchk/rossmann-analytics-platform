"""Contract tests for sales API endpoints."""

import jwt
from fastapi.testclient import TestClient


def create_auth_token(user_id: str, role: str, email: str | None = None) -> str:
    payload = {
        "sub": user_id,
        "email": email or f"{user_id}@example.com",
        "app_metadata": {"role": role},
        "aud": "authenticated",
        "iss": "https://example.supabase.co/auth/v1",
    }
    return jwt.encode(payload, "test-secret", algorithm="HS256")


def test_sales_list_requires_authentication(client: TestClient) -> None:
    response = client.get("/api/v1/sales")

    assert response.status_code == 401


def test_admin_can_read_sales_for_unmapped_store(client: TestClient) -> None:
    token = create_auth_token(
        user_id="00000000-0000-0000-0000-000000000001",
        role="admin",
        email="admin@example.com",
    )

    response = client.get(
        "/api/v1/sales?store_id=2",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["count"] == 1
    assert body["data"][0]["store_id"] == 2


def test_sales_summary_returns_expected_shape(client: TestClient) -> None:
    token = create_auth_token(
        user_id="00000000-0000-0000-0000-000000000003",
        role="store_manager",
        email="manager@example.com",
    )

    response = client.get(
        "/api/v1/sales/summary?store_id=1",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    body = response.json()
    assert "total_sales" in body
    assert "total_customers" in body
    assert "total_transactions" in body
    assert "avg_daily_sales" in body
    assert "promo_days" in body


def test_sales_summary_for_unauthorized_store_is_forbidden(client: TestClient) -> None:
    token = create_auth_token(
        user_id="00000000-0000-0000-0000-000000000003",
        role="store_manager",
        email="manager@example.com",
    )

    response = client.get(
        "/api/v1/sales/summary?store_id=2",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 403
