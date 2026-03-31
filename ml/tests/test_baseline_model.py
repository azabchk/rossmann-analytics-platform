"""Tests for baseline forecasting model."""

import pytest
import pandas as pd
import numpy as np
from datetime import date, timedelta


class TestBaselineForecaster:
    """Tests for BaselineForecaster class."""

    def test_initialization(self):
        """Test forecaster initialization."""
        from ml.src.training.train_baseline import BaselineForecaster

        forecaster = BaselineForecaster(window_days=28)
        assert forecaster.window_days == 28
        assert forecaster.fitted is False

    def test_fit(self):
        """Test model fitting."""
        from ml.src.training.train_baseline import BaselineForecaster

        df = pd.DataFrame({
            "sales_date": pd.date_range("2023-01-01", periods=100),
            "sales": np.random.randint(100, 1000, size=100),
        })

        forecaster = BaselineForecaster(window_days=28)
        forecaster.fit(df)

        assert forecaster.fitted is True

    def test_predict(self):
        """Test prediction generation."""
        from ml.src.training.train_baseline import BaselineForecaster

        df = pd.DataFrame({
            "sales_date": pd.date_range("2023-01-01", periods=100),
            "sales": np.random.randint(100, 1000, size=100),
        })

        forecaster = BaselineForecaster(window_days=28)
        forecaster.fit(df)

        forecasts = forecaster.predict(horizon_days=14, include_ci=True)

        assert len(forecasts) == 14
        assert "forecast_date" in forecasts.columns
        assert "predicted_sales" in forecasts.columns
        assert "lower_bound" in forecasts.columns
        assert "upper_bound" in forecasts.columns
        assert all(forecasts["predicted_sales"] >= 0)

    def test_predict_without_fitting_raises_error(self):
        """Test that prediction without fitting raises error."""
        from ml.src.training.train_baseline import BaselineForecaster

        forecaster = BaselineForecaster()

        with pytest.raises(ValueError, match="must be fitted"):
            forecaster.predict(horizon_days=7)

    def test_evaluate(self):
        """Test model evaluation."""
        from ml.src.training.train_baseline import BaselineForecaster

        # Training data
        train_df = pd.DataFrame({
            "sales_date": pd.date_range("2023-01-01", periods=90),
            "sales": np.random.randint(100, 1000, size=90),
        })

        # Test data
        test_df = pd.DataFrame({
            "sales_date": pd.date_range("2023-04-01", periods=14),
            "sales": np.random.randint(100, 1000, size=14),
        })

        forecaster = BaselineForecaster(window_days=28)
        forecaster.fit(train_df)

        metrics = forecaster.evaluate(test_df)

        assert "mape" in metrics
        assert "rmse" in metrics
        assert "mae" in metrics
        assert metrics["mape"] >= 0
        assert metrics["rmse"] >= 0
        assert metrics["mae"] >= 0


class TestTrainBaselineModel:
    """Tests for train_baseline_model function."""

    def test_train_with_sufficient_data(self):
        """Test training with sufficient data."""
        from ml.src.training.train_baseline import train_baseline_model

        df = pd.DataFrame({
            "store_id": [1] * 100,
            "sales_date": pd.date_range("2023-01-01", periods=100),
            "sales": np.random.randint(100, 1000, size=100),
        })

        forecaster = train_baseline_model(df, store_id=1, min_history_days=30)

        assert forecaster is not None
        assert forecaster.fitted is True

    def test_train_with_insufficient_data(self):
        """Test training with insufficient data returns None."""
        from ml.src.training.train_baseline import train_baseline_model

        df = pd.DataFrame({
            "store_id": [1] * 20,
            "sales_date": pd.date_range("2023-01-01", periods=20),
            "sales": np.random.randint(100, 1000, size=20),
        })

        forecaster = train_baseline_model(df, store_id=1, min_history_days=30)

        assert forecaster is None


class TestGenerateBaselineForecasts:
    """Tests for generate_baseline_forecasts function."""

    def test_generate_forecasts_for_multiple_stores(self):
        """Test generating forecasts for multiple stores."""
        from ml.src.training.train_baseline import generate_baseline_forecasts

        df = pd.DataFrame({
            "store_id": [1] * 100 + [2] * 100,
            "sales_date": list(pd.date_range("2023-01-01", periods=100)) * 2,
            "sales": np.random.randint(100, 1000, size=200),
        })

        results = generate_baseline_forecasts(
            df=df,
            store_ids=[1, 2],
            horizon_weeks=4,
            min_history_days=30,
        )

        assert 1 in results
        assert 2 in results

        forecast_1, warning_1 = results[1]
        forecast_2, warning_2 = results[2]

        assert forecast_1 is not None
        assert forecast_2 is not None
        assert warning_1 is None
        assert warning_2 is None
        assert len(forecast_1) == 28  # 4 weeks * 7 days
        assert len(forecast_2) == 28

    def test_generate_forecasts_with_insufficient_data(self):
        """Test generating forecasts with insufficient data."""
        from ml.src.training.train_baseline import generate_baseline_forecasts

        df = pd.DataFrame({
            "store_id": [1] * 20,
            "sales_date": pd.date_range("2023-01-01", periods=20),
            "sales": np.random.randint(100, 1000, size=20),
        })

        results = generate_baseline_forecasts(
            df=df,
            store_ids=[1],
            horizon_weeks=4,
            min_history_days=30,
        )

        forecast, warning = results[1]

        assert forecast is None
        assert warning is not None
        assert "insufficient" in warning.lower()
