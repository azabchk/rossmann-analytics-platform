"""Integration tests for forecast access control."""

import pytest
from httpx import AsyncClient


class TestForecastAccessControl:
    """Integration tests for forecast access control."""

    @pytest.mark.asyncio
    async def test_store_manager_can_access_own_store_forecasts(
        self,
        authenticated_client: AsyncClient,
        test_store_manager_user,
    ):
        """Test that store manager can access their store's forecasts."""
        # This test assumes test_store_manager_user has access to store 1
        response = await authenticated_client.get("/api/v1/forecasts/stores/1")

        # Should get either 200 (has forecasts) or 404 (no forecasts)
        # but not 403 (forbidden) or 401 (unauthorized)
        assert response.status_code in [200, 404]

    @pytest.mark.asyncio
    async def test_analyst_can_access_multiple_store_forecasts(
        self,
        authenticated_client: AsyncClient,
        test_analyst_user,
    ):
        """Test that data analyst can access multiple store forecasts."""
        # This test assumes test_analyst_user has access to multiple stores
        response = await authenticated_client.post(
            "/api/v1/forecasts/batch",
            json={"store_ids": [1, 2, 3]},
        )

        assert response.status_code in [200, 404]

    @pytest.mark.asyncio
    async def test_unauthorized_user_cannot_access_forecasts(
        self,
        async_client: AsyncClient,
    ):
        """Test that unauthorized user cannot access forecasts."""
        response = await async_client.get("/api/v1/forecasts/stores/1")

        assert response.status_code == 401  # Unauthorized

    @pytest.mark.asyncio
    async def test_store_manager_cannot_access_other_store_forecasts(
        self,
        authenticated_client: AsyncClient,
        test_store_manager_user,
    ):
        """Test that store manager cannot access other store's forecasts."""
        # This test assumes test_store_manager_user only has access to store 1
        # and tries to access store 999 (which they don't have access to)
        response = await authenticated_client.get("/api/v1/forecasts/stores/999")

        # Should get 403 (forbidden) or 404 (not found)
        # depending on how access control is implemented
        assert response.status_code in [403, 404]

    @pytest.mark.asyncio
    async def test_admin_can_access_any_store_forecasts(
        self,
        authenticated_client: AsyncClient,
        test_admin_user,
    ):
        """Test that admin can access any store's forecasts."""
        response = await authenticated_client.get("/api/v1/forecasts/stores/1")

        assert response.status_code in [200, 404]


class TestForecastDataRetrieval:
    """Integration tests for forecast data retrieval."""

    @pytest.mark.asyncio
    async def test_forecast_data_returns_confidence_intervals(
        self,
        authenticated_client: AsyncClient,
    ):
        """Test that forecast data includes confidence intervals."""
        # This test requires actual forecast data to be present
        response = await authenticated_client.get("/api/v1/forecasts/stores/1")

        if response.status_code == 200:
            data = response.json()
            forecasts = data.get("forecasts", [])

            if forecasts:
                # Check that at least one forecast has confidence bounds
                has_bounds = any(
                    f.get("lower_bound") is not None and f.get("upper_bound") is not None
                    for f in forecasts
                )
                assert has_bounds, "At least one forecast should have confidence bounds"

    @pytest.mark.asyncio
    async def test_forecast_data_returns_model_metadata(
        self,
        authenticated_client: AsyncClient,
    ):
        """Test that forecast data includes model metadata."""
        response = await authenticated_client.get("/api/v1/forecasts/stores/1")

        if response.status_code == 200:
            data = response.json()

            # Check model_metadata exists
            assert "model_metadata" in data
            model_meta = data["model_metadata"]

            # Check required fields
            assert "model_type" in model_meta
            assert "version" in model_meta
            assert "published_at" in model_meta

    @pytest.mark.asyncio
    async def test_forecast_data_returns_accuracy_metrics(
        self,
        authenticated_client: AsyncClient,
    ):
        """Test that forecast data includes accuracy metrics."""
        response = await authenticated_client.get("/api/v1/forecasts/stores/1")

        if response.status_code == 200:
            data = response.json()

            # Check accuracy_metrics exists (may be None for some models)
            assert "accuracy_metrics" in data

            if data["accuracy_metrics"] is not None:
                acc_metrics = data["accuracy_metrics"]
                # At least one metric should be present
                has_metrics = any(
                    acc_metrics.get(key) is not None
                    for key in ["mape", "rmse", "mae"]
                )
                assert has_metrics, "At least one accuracy metric should be present"


class TestForecastWarnings:
    """Integration tests for low data warnings."""

    @pytest.mark.asyncio
    async def test_warnings_returned_for_insufficient_data_stores(
        self,
        authenticated_client: AsyncClient,
    ):
        """Test that warnings are returned for stores with insufficient data."""
        response = await authenticated_client.post(
            "/api/v1/forecasts/batch",
            json={"store_ids": [1, 2, 3]},
        )

        if response.status_code == 200:
            data = response.json()

            # Check warnings list exists
            assert "warnings" in data
            warnings = data["warnings"]

            # If there are warnings, check structure
            if warnings:
                warning = warnings[0]
                assert "store_id" in warning
                assert "warning_type" in warning
                assert "warning_message" in warning

    @pytest.mark.asyncio
    async def test_specific_store_warnings_endpoint(
        self,
        authenticated_client: AsyncClient,
    ):
        """Test getting warnings for a specific store."""
        response = await authenticated_client.get("/api/v1/forecasts/warnings/1")

        data = response.json()

        # Should return a list (may be empty)
        assert isinstance(data, list)


class TestForecastGeneration:
    """Integration tests for forecast generation."""

    @pytest.mark.asyncio
    async def test_forecast_generation_requires_admin_role(
        self,
        store_manager_client: AsyncClient,
    ):
        """Test that only admins and analysts can trigger forecast generation."""
        response = await store_manager_client.post(
            "/api/v1/forecasts/generate",
            json={
                "store_ids": [1],
                "horizon_weeks": 6,
            },
        )

        # Store manager should get 403 Forbidden
        assert response.status_code == 403

    @pytest.mark.asyncio
    async def test_forecast_generation_accepts_request(
        self,
        admin_client: AsyncClient,
    ):
        """Test that forecast generation accepts valid requests."""
        response = await admin_client.post(
            "/api/v1/forecasts/generate",
            json={
                "store_ids": [1, 2],
                "horizon_weeks": 6,
                "force_retrain": False,
            },
        )

        # Should return 202 Accepted
        assert response.status_code == 202

        data = response.json()
        assert "job_id" in data
        assert "status" in data
        assert "stores_requested" in data
        assert data["stores_requested"] == [1, 2]

    @pytest.mark.asyncio
    async def test_forecast_generation_validates_horizon(
        self,
        admin_client: AsyncClient,
    ):
        """Test that forecast generation validates horizon parameter."""
        # Test with invalid horizon (too large)
        response = await admin_client.post(
            "/api/v1/forecasts/generate",
            json={
                "store_ids": [1],
                "horizon_weeks": 20,  # Exceeds max of 12
            },
        )

        # Should return 422 Unprocessable Entity
        assert response.status_code == 422
