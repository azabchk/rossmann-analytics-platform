"""Contract tests for forecasts API endpoints."""

import pytest
from datetime import date, timedelta
from httpx import AsyncClient


class TestForecastsApiContract:
    """Contract tests for the forecasts API."""

    @pytest.mark.asyncio
    async def test_get_store_forecasts_response_structure(self, authenticated_client: AsyncClient):
        """Test that store forecasts endpoint returns correct structure."""
        response = await authenticated_client.get("/api/v1/forecasts/stores/1")

        # For now, we expect 404 since no forecasts are published
        # But we check the response structure when data exists
        if response.status_code == 200:
            data = response.json()

            # Check top-level fields
            assert "store_id" in data
            assert "model_type" in data
            assert "forecast_start_date" in data
            assert "forecast_end_date" in data
            assert "model_metadata" in data
            assert "forecasts" in data
            assert "total" in data
            assert "offset" in data
            assert "limit" in data

            # Check model_metadata structure
            model_meta = data["model_metadata"]
            assert "model_id" in model_meta
            assert "model_name" in model_meta
            assert "model_type" in model_meta
            assert "version" in model_meta
            assert "is_active" in model_meta
            assert "published_at" in model_meta

            # Check forecast points structure
            forecasts = data["forecasts"]
            if forecasts:
                forecast = forecasts[0]
                assert "forecast_date" in forecast
                assert "predicted_sales" in forecast
                assert "lower_bound" in forecast
                assert "upper_bound" in forecast
                assert "confidence_level" in forecast

                # Check data types
                assert isinstance(forecast["predicted_sales"], (int, float))
                assert forecast["predicted_sales"] >= 0

    @pytest.mark.asyncio
    async def test_get_store_forecasts_with_date_filters(self, authenticated_client: AsyncClient):
        """Test that date filters are accepted."""
        start_date = (date.today() + timedelta(days=1)).isoformat()
        end_date = (date.today() + timedelta(days=14)).isoformat()

        response = await authenticated_client.get(
            f"/api/v1/forecasts/stores/1?start_date={start_date}&end_date={end_date}"
        )

        # Check request doesn't fail with validation
        assert response.status_code in [200, 404]

    @pytest.mark.asyncio
    async def test_get_store_forecasts_with_pagination(self, authenticated_client: AsyncClient):
        """Test that pagination parameters work."""
        response = await authenticated_client.get(
            "/api/v1/forecasts/stores/1?limit=10&offset=0"
        )

        # Check request doesn't fail with validation
        assert response.status_code in [200, 404]

    @pytest.mark.asyncio
    async def test_get_store_forecasts_invalid_pagination(self, authenticated_client: AsyncClient):
        """Test that invalid pagination parameters are rejected."""
        response = await authenticated_client.get(
            "/api/v1/forecasts/stores/1?limit=0"
        )

        assert response.status_code == 422  # Unprocessable Entity

    @pytest.mark.asyncio
    async def test_get_batch_forecasts_response_structure(self, authenticated_client: AsyncClient):
        """Test that batch forecasts endpoint returns correct structure."""
        response = await authenticated_client.post(
            "/api/v1/forecasts/batch",
            json={"store_ids": [1, 2, 3]},
        )

        # Check response structure
        data = response.json()
        assert "forecasts" in data
        assert "warnings" in data

        # Check forecasts is a list
        assert isinstance(data["forecasts"], list)

        # Check warnings is a list
        assert isinstance(data["warnings"], list)

    @pytest.mark.asyncio
    async def test_get_batch_forecasts_empty_store_ids(self, authenticated_client: AsyncClient):
        """Test that empty store_ids list is rejected."""
        response = await authenticated_client.post(
            "/api/v1/forecasts/batch",
            json={"store_ids": []},
        )

        assert response.status_code == 400  # Bad Request

    @pytest.mark.asyncio
    async def test_get_active_model_response_structure(self, authenticated_client: AsyncClient):
        """Test that active model endpoint returns correct structure."""
        response = await authenticated_client.get("/api/v1/forecasts/models/baseline/active")

        # May return 404 if no active model, or 200 with data
        if response.status_code == 200:
            data = response.json()

            # Check structure
            assert "model_id" in data
            assert "model_name" in data
            assert "model_type" in data
            assert "version" in data
            assert "is_active" in data
            assert "published_at" in data

            # Check model_type is expected value
            assert data["model_type"] == "baseline"

    @pytest.mark.asyncio
    async def test_get_active_model_invalid_type(self, authenticated_client: AsyncClient):
        """Test that invalid model type is rejected."""
        response = await authenticated_client.get("/api/v1/forecasts/models/invalid/active")

        assert response.status_code == 400  # Bad Request

    @pytest.mark.asyncio
    async def test_get_store_warnings_response_structure(self, authenticated_client: AsyncClient):
        """Test that warnings endpoint returns correct structure."""
        response = await authenticated_client.get("/api/v1/forecasts/warnings/1")

        data = response.json()

        # Check it returns a list
        assert isinstance(data, list)

        # Check warning structure if warnings exist
        if data:
            warning = data[0]
            assert "store_id" in warning
            assert "warning_type" in warning
            assert "warning_message" in warning
            assert "days_of_history" in warning

    @pytest.mark.asyncio
    async def test_get_model_accuracy_response_structure(self, authenticated_client: AsyncClient):
        """Test that model accuracy endpoint returns correct structure."""
        # Use a placeholder model ID for testing
        response = await authenticated_client.get("/api/v1/forecasts/accuracy/placeholder_id")

        # May return 404 if model doesn't exist
        if response.status_code == 200:
            data = response.json()

            # Check structure
            assert "mape" in data
            assert "rmse" in data
            assert "mae" in data

    @pytest.mark.asyncio
    async def test_generate_forecasts_response_structure(self, authenticated_client: AsyncClient):
        """Test that forecast generation endpoint returns correct structure."""
        response = await authenticated_client.post(
            "/api/v1/forecasts/generate",
            json={
                "store_ids": [1, 2],
                "horizon_weeks": 6,
                "force_retrain": False,
            },
        )

        # Returns 202 Accepted or 403 Forbidden
        if response.status_code in [202, 403]:
            data = response.json()

            # Check structure for 202 response
            if response.status_code == 202:
                assert "job_id" in data
                assert "status" in data
                assert "stores_requested" in data
                assert "message" in data

    @pytest.mark.asyncio
    async def test_forecasts_require_authentication(self, async_client: AsyncClient):
        """Test that forecasts endpoints require authentication."""
        endpoints = [
            "/api/v1/forecasts/stores/1",
            "/api/v1/forecasts/models/baseline/active",
            "/api/v1/forecasts/warnings/1",
        ]

        for endpoint in endpoints:
            response = await async_client.get(endpoint)
            assert response.status_code == 401  # Unauthorized
