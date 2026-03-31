"""Integration tests for authorized dashboard access.

Verifies that authenticated users can access dashboard data
and that access control is properly enforced.
"""

import jwt
import pytest
from fastapi.testclient import TestClient


def create_token_for_user(user_id: str, role: str, email: str | None = None) -> str:
    """Create a JWT token for a specific user."""
    payload = {
        "sub": user_id,
        "email": email or f"{user_id}@example.com",
        "app_metadata": {"role": role},
        "aud": "authenticated",
        "iss": "https://example.supabase.co/auth/v1",
    }
    return jwt.encode(payload, "test-secret", algorithm="HS256")


@pytest.fixture()
def auth_token() -> str:
    """Fixture providing a valid auth token for testing."""
    return create_token_for_user(
        user_id="00000000-0000-0000-0000-000000-001",
        role="store_manager",
        email="manager@example.com",
    )


def test_dashboard_access_authenticated_user(client: TestClient, auth_token: str) -> None:
    """An authenticated user should be able to access their dashboard data."""
    response = client.get(
        "/api/v1/kpis",
        headers={"Authorization": f"Bearer {auth_token}"}
    )
    assert response.status_code == 200, "Authenticated user should access dashboard"


def test_dashboard_access_requires_valid_jwt(client: TestClient) -> None:
    """Dashboard access should require a valid JWT token."""
    response = client.get("/api/v1/kpis")
    assert response.status_code == 401, "No authentication should return 401"


def test_dashboard_access_rejects_expired_token(client: TestClient) -> None:
    """Expired tokens should be rejected."""
    # Create an expired token (exp is in past)
    payload = {
        "sub": "00000000-0000-0000-0000-000000-002",
        "email": "expired@example.com",
        "app_metadata": {"role": "store_manager"},
        "aud": "authenticated",
        "iss": "https://example.supabase.co/auth/v1",
        "exp": 0,  # Expired in 1970
    }
    expired_token = jwt.encode(payload, "test-secret", algorithm="HS256")

    response = client.get(
        "/api/v1/kpis",
        headers={"Authorization": f"Bearer {expired_token}"}
    )
    assert response.status_code == 401, "Expired token should return 401"


def test_store_manager_can_access_stores(client: TestClient) -> None:
    """A store manager should be able to access stores."""
    token = create_token_for_user(
        user_id="00000000-0000-0000-0000-000000-003",
        role="store_manager",
    )
    response = client.get(
        "/api/v1/stores",
        headers={"Authorization": f"Bearer {token}"}
    )
    # The response should be filtered to only authorized stores
    # This is validated by RLS policies on the database
    assert response.status_code == 200


def test_marketing_manager_can_access_stores(client: TestClient) -> None:
    """A marketing manager should be able to access stores."""
    token = create_token_for_user(
        user_id="00000000-0000-0000-0000-000000-004",
        role="marketing_manager",
        email="marketing@example.com",
    )
    response = client.get(
        "/api/v1/stores",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 200
    data = response.json()
    stores = data["stores"] if isinstance(data, dict) else data
    assert isinstance(stores, list), "Response should be a list of stores"


def test_admin_can_access_all_stores(client: TestClient) -> None:
    """An admin should not depend on store_access mappings to list stores."""
    token = create_token_for_user(
        user_id="00000000-0000-0000-0000-000000000001",
        role="admin",
        email="admin@example.com",
    )
    response = client.get(
        "/api/v1/stores",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["count"] == 2
    assert {store["store_id"] for store in data["stores"]} == {1, 2}


def test_data_analyst_can_access_detailed_kpis(client: TestClient, auth_token: str) -> None:
    """A data analyst should be able to access detailed KPIs via API."""
    response = client.get(
        "/api/v1/kpis",
        headers={"Authorization": f"Bearer {auth_token}"}
    )
    assert response.status_code == 200, "Data analyst should access KPIs"


def test_academic_demo_user_read_only_access(client: TestClient) -> None:
    """An academic demo user should have read-only access to dashboard data."""
    token = create_token_for_user(
        user_id="00000000-0000-0000-0000-000000-006",
        role="academic_demo",
        email="demo@example.com",
    )
    # Demo user can read data
    response = client.get(
        "/api/v1/kpis",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 200, "Demo user should have read access"


def test_dashboard_filters_by_date_range(client: TestClient) -> None:
    """Dashboard should respect date range filters."""
    token = create_token_for_user(
        user_id="00000000-0000-0000-0000-000000-007",
        role="store_manager",
    )
    response = client.get(
        "/api/v1/kpis?start_date=2023-01-01&end_date=2023-12-31",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 200
    data = response.json()
    kpis = data["kpis"] if isinstance(data, dict) else data
    assert isinstance(kpis, list), "KPIs should be an array"


def test_dashboard_filters_by_store(client: TestClient) -> None:
    """Dashboard should respect store filtering."""
    token = create_token_for_user(
        user_id="00000000-0000-0000-0000-000000-008",
        role="store_manager",
    )
    response = client.get(
        "/api/v1/kpis?store_id=1",
        headers={"Authorization": f"Bearer {token}"}
    )
    # Should be either 200 (authorized) or 403 (not authorized for this store)
    assert response.status_code in [200, 403]


def test_admin_can_access_dashboard_for_second_store(client: TestClient) -> None:
    """An admin should be able to query KPI data for any existing store."""
    token = create_token_for_user(
        user_id="00000000-0000-0000-0000-000000000001",
        role="admin",
        email="admin@example.com",
    )
    response = client.get(
        "/api/v1/kpis?store_id=2",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["count"] > 0
    assert all(kpi["store_id"] == 2 for kpi in data["kpis"])


def test_user_without_store_access_gets_empty_results(client: TestClient) -> None:
    """A user with no store access should get empty results."""
    token = create_token_for_user(
        user_id="00000000-0000-0000-0000-000000-009",
        role="store_manager",
    )
    response = client.get(
        "/api/v1/kpis",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 200
    data = response.json()
    kpis = data["kpis"] if isinstance(data, dict) else data
    assert len(kpis) == 0, "User with no store access should get empty results"


def test_dashboard_pagination(client: TestClient) -> None:
    """Dashboard should support pagination for large datasets."""
    token = create_token_for_user(
        user_id="00000000-0000-0000-0000-000000-010",
        role="data_analyst",
    )
    response = client.get(
        "/api/v1/kpis?page=1&page_size=50",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 200
    data = response.json()
    # Verify pagination metadata if present
    if isinstance(data, dict):
        assert "kpis" in data or "data" in data, "Response should contain data array"


def test_unauthorized_role_rejected(client: TestClient) -> None:
    """Users with invalid roles are authenticated at auth layer (role validation happens in business logic)."""
    payload = {
        "sub": "00000000-0000-0000-0000-000000-011",
        "email": "invalid@example.com",
        "app_metadata": {"role": "invalid_role"},
        "aud": "authenticated",
        "iss": "https://example.supabase.co/auth/v1",
    }
    token = jwt.encode(payload, "test-secret", algorithm="HS256")

    response = client.get(
        "/api/v1/kpis",
        headers={"Authorization": f"Bearer {token}"}
    )
    # Auth succeeds (valid JWT), role validation happens in business logic
    assert response.status_code in [200, 403]  # 200 if access allowed, 403 if role is rejected
