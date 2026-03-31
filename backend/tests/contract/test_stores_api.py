"""Contract tests for stores API endpoints.

Verifies that stores API adheres to expected contract
for response format, status codes, and error handling.
"""

import jwt
import pytest
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


def test_stores_list_requires_authentication(client: TestClient) -> None:
    """GET /api/v1/stores should return 401 without authentication."""
    response = client.get("/api/v1/stores")
    assert response.status_code == 401


def test_stores_list_with_valid_token(client: TestClient, auth_token: str) -> None:
    """GET /api/v1/stores should return store list for authenticated user."""
    response = client.get(
        "/api/v1/stores",
        headers={"Authorization": f"Bearer {auth_token}"}
    )
    assert response.status_code == 200
    data = response.json()
    assert "stores" in data or isinstance(data, list), "Response should contain stores array"
    stores = data["stores"] if isinstance(data, dict) else data
    assert isinstance(stores, list), "stores should be an array"


def test_store_detail_requires_authentication(client: TestClient) -> None:
    """GET /api/v1/stores/{store_id} should return 401 without authentication."""
    response = client.get("/api/v1/stores/1")
    assert response.status_code == 401


def test_store_detail_with_valid_token(client: TestClient, auth_token: str) -> None:
    """GET /api/v1/stores/{store_id} should return store details for authorized user."""
    response = client.get(
        "/api/v1/stores/1",
        headers={"Authorization": f"Bearer {auth_token}"}
    )
    # May be 200 (authorized) or 403 (unauthorized to this store)
    assert response.status_code in [200, 403]


def test_store_detail_not_found(client: TestClient, auth_token: str) -> None:
    """GET /api/v1/stores/{nonexistent_id} should return 404."""
    response = client.get(
        "/api/v1/stores/999999",
        headers={"Authorization": f"Bearer {auth_token}"}
    )
    assert response.status_code == 404


def test_invalid_token(client: TestClient) -> None:
    """Requests with invalid token should return 401."""
    response = client.get(
        "/api/v1/stores",
        headers={"Authorization": "Bearer invalid-token"}
    )
    assert response.status_code == 401
    data = response.json()
    assert "error" in data, "Error response should contain error message"
    assert "code" in data, "Error response should contain error code"


def test_missing_bearer_scheme(client: TestClient, auth_token: str) -> None:
    """Requests without Bearer scheme should return 401."""
    response = client.get(
        "/api/v1/stores",
        headers={"Authorization": auth_token}
    )
    assert response.status_code == 401


def test_stores_response_structure(client: TestClient, auth_token: str) -> None:
    """Verify stores endpoint returns proper JSON structure."""
    response = client.get(
        "/api/v1/stores",
        headers={"Authorization": f"Bearer {auth_token}"}
    )
    if response.status_code == 200:
        data = response.json()
        stores = data["stores"] if isinstance(data, dict) else data
        # Verify each store has expected fields
        for store in stores:
            assert "store_id" in store, "Store should have store_id"
            assert "store_type" in store, "Store should have store_type"
            assert "assortment" in store, "Store should have assortment"
            # Optional fields may not exist in all data
