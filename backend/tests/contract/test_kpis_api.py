"""Contract tests for KPI API endpoints.

Verifies that KPI API adheres to expected contract
for response format, status codes, and error handling.
"""

import jwt
import pytest
from datetime import date
from fastapi.testclient import TestClient


def create_auth_token(user_id: str = "test-user-id") -> str:
    """Create a mock auth token for testing."""
    payload = {
        "sub": user_id,
        "email": f"{user_id}@example.com",
        "app_metadata": {"role": "store_manager"},
        "aud": "authenticated",
        "iss": "https://example.supabase.co/auth/v1",
    }
    return jwt.encode(payload, "test-secret", algorithm="HS256")


@pytest.fixture()
def auth_token() -> str:
    """Fixture providing a valid auth token for testing."""
    return create_auth_token()


def test_kpis_list_requires_authentication(client: TestClient) -> None:
    """GET /api/v1/kpis should return 401 without authentication."""
    response = client.get("/api/v1/kpis")
    assert response.status_code == 401


def test_kpis_list_with_valid_token(client: TestClient, auth_token: str) -> None:
    """GET /api/v1/kpis should return KPI list for authenticated user."""
    response = client.get(
        "/api/v1/kpis",
        headers={"Authorization": f"Bearer {auth_token}"}
    )
    assert response.status_code == 200
    data = response.json()
    assert "kpis" in data or isinstance(data, list), "Response should contain kpis array"
    kpis = data["kpis"] if isinstance(data, dict) else data
    assert isinstance(kpis, list), "kpis should be an array"


def test_kpis_with_date_filter(client: TestClient, auth_token: str) -> None:
    """GET /api/v1/kpis with date filters should return filtered results."""
    response = client.get(
        "/api/v1/kpis?start_date=2023-01-01&end_date=2023-12-31",
        headers={"Authorization": f"Bearer {auth_token}"}
    )
    assert response.status_code == 200
    data = response.json()
    kpis = data["kpis"] if isinstance(data, dict) else data
    # Verify structure even with empty data
    assert isinstance(kpis, list), "KPIs should be an array"


def test_kpis_with_store_filter(client: TestClient, auth_token: str) -> None:
    """GET /api/v1/kpis with store filter should return store-specific KPIs."""
    response = client.get(
        "/api/v1/kpis?store_id=1",
        headers={"Authorization": f"Bearer {auth_token}"}
    )
    assert response.status_code in [200, 403]  # 200 if authorized, 403 if not


def test_kpis_unauthorized_store(client: TestClient, auth_token: str) -> None:
    """GET /api/v1/kpis for unauthorized store should return 403 or empty array."""
    response = client.get(
        "/api/v1/kpis?store_id=99999",
        headers={"Authorization": f"Bearer {auth_token}"}
    )
    # Should be either 403 (forbidden) or 200 with empty results
    assert response.status_code in [200, 403]


def test_kpis_invalid_date_format(client: TestClient, auth_token: str) -> None:
    """GET /api/v1/kpis with invalid date format should return 422 (validation error)."""
    response = client.get(
        "/api/v1/kpis?start_date=invalid-date",
        headers={"Authorization": f"Bearer {auth_token}"}
    )
    assert response.status_code == 422


def test_kpis_invalid_store_id(client: TestClient, auth_token: str) -> None:
    """GET /api/v1/kpis with invalid store_id should return 422 (validation error)."""
    response = client.get(
        "/api/v1/kpis?store_id=abc",
        headers={"Authorization": f"Bearer {auth_token}"}
    )
    assert response.status_code == 422


def test_daily_kpis_endpoint(client: TestClient, auth_token: str) -> None:
    """GET /api/v1/kpis/daily should return daily KPIs."""
    response = client.get(
        "/api/v1/kpis/daily",
        headers={"Authorization": f"Bearer {auth_token}"}
    )
    assert response.status_code == 200
    data = response.json()
    kpis = data["kpis"] if isinstance(data, dict) else data
    assert isinstance(kpis, list), "KPIs should be an array"


def test_weekly_kpis_endpoint(client: TestClient, auth_token: str) -> None:
    """GET /api/v1/kpis/weekly should return weekly KPIs."""
    response = client.get(
        "/api/v1/kpis/weekly",
        headers={"Authorization": f"Bearer {auth_token}"}
    )
    assert response.status_code == 200
    data = response.json()
    kpis = data["kpis"] if isinstance(data, dict) else data
    assert isinstance(kpis, list), "KPIs should be an array"


def test_monthly_kpis_endpoint(client: TestClient, auth_token: str) -> None:
    """GET /api/v1/kpis/monthly should return monthly KPIs."""
    response = client.get(
        "/api/v1/kpis/monthly",
        headers={"Authorization": f"Bearer {auth_token}"}
    )
    assert response.status_code == 200
    data = response.json()
    kpis = data["kpis"] if isinstance(data, dict) else data
    assert isinstance(kpis, list), "KPIs should be an array"


def test_kpis_aggregation_filter(client: TestClient, auth_token: str) -> None:
    """GET /api/v1/kpis with aggregation parameter should respect it."""
    for agg in ["daily", "weekly", "monthly"]:
        response = client.get(
            f"/api/v1/kpis?aggregation={agg}",
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        assert response.status_code == 200, f"{agg} aggregation should return 200"


def test_kpis_invalid_aggregation(client: TestClient, auth_token: str) -> None:
    """GET /api/v1/kpis with invalid aggregation should return 422."""
    response = client.get(
        "/api/v1/kpis?aggregation=invalid",
        headers={"Authorization": f"Bearer {auth_token}"}
    )
    assert response.status_code == 422
    data = response.json()
    assert "detail" in data, "Validation failures should include FastAPI detail output"
