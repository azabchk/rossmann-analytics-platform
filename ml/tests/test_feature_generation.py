"""Tests for forecast feature generation."""

import pytest
import pandas as pd
import numpy as np
from datetime import date, timedelta


class TestLagFeatures:
    """Tests for lag feature extraction."""

    def test_extract_lag_features_basic(self):
        """Test basic lag feature extraction."""
        from ml.src.features.build_forecast_features import extract_lag_features

        df = pd.DataFrame({
            "sales_date": pd.date_range("2023-01-01", periods=30),
            "sales": np.random.randint(100, 1000, size=30),
        })

        result = extract_lag_features(df, lag_periods=[1, 7, 14])

        assert "sales_lag_1" in result.columns
        assert "sales_lag_7" in result.columns
        assert "sales_lag_14" in result.columns
        assert len(result) == len(df)

    def test_extract_lag_features_null_handling(self):
        """Test that lag features handle nulls correctly."""
        from ml.src.features.build_forecast_features import extract_lag_features

        df = pd.DataFrame({
            "sales_date": pd.date_range("2023-01-01", periods=10),
            "sales": [100, 200, 150, 180, 220, 250, 200, 180, 210, 230],
        })

        result = extract_lag_features(df, lag_periods=[1])

        assert result["sales_lag_1"].iloc[0] != result["sales_lag_1"].iloc[0]  # NaN


class TestSeasonalFeatures:
    """Tests for seasonal feature extraction."""

    def test_extract_seasonal_features_basic(self):
        """Test basic seasonal feature extraction."""
        from ml.src.features.build_forecast_features import extract_seasonal_features

        df = pd.DataFrame({
            "date": pd.date_range("2023-01-01", periods=100),
            "sales": np.random.randint(100, 1000, size=100),
        })

        result = extract_seasonal_features(df, "date")

        assert "year" in result.columns
        assert "month" in result.columns
        assert "day_of_week" in result.columns
        assert "day_of_month" in result.columns
        assert "day_of_year" in result.columns
        assert "week_of_year" in result.columns
        assert "is_weekend" in result.columns
        assert "month_sin" in result.columns
        assert "month_cos" in result.columns

    def test_extract_seasonal_features_weekend_detection(self):
        """Test weekend detection."""
        from ml.src.features.build_forecast_features import extract_seasonal_features

        # Saturday is day 5, Sunday is day 6
        df = pd.DataFrame({
            "date": [pd.Timestamp("2023-01-07"), pd.Timestamp("2023-01-08")],  # Sat, Sun
            "sales": [100, 200],
        })

        result = extract_seasonal_features(df, "date")

        assert all(result["is_weekend"] == 1)


class TestCheckSufficientData:
    """Tests for data sufficiency checking."""

    def test_sufficient_data(self):
        """Test check with sufficient data."""
        from ml.src.features.build_forecast_features import check_sufficient_data

        df = pd.DataFrame({
            "sales_date": pd.date_range("2023-01-01", periods=100),
            "sales": np.random.randint(100, 1000, size=100),
        })

        is_sufficient, warning, days = check_sufficient_data(df, min_days=90)

        assert is_sufficient is True
        assert warning is None
        assert days == 100

    def test_insufficient_data(self):
        """Test check with insufficient data."""
        from ml.src.features.build_forecast_features import check_sufficient_data

        df = pd.DataFrame({
            "sales_date": pd.date_range("2023-01-01", periods=50),
            "sales": np.random.randint(100, 1000, size=50),
        })

        is_sufficient, warning, days = check_sufficient_data(df, min_days=90)

        assert is_sufficient is False
        assert warning is not None
        assert "insufficient" in warning.lower()
        assert days == 50

    def test_sparse_data_warning(self):
        """Test check with sparse data (many zeros)."""
        from ml.src.features.build_forecast_features import check_sufficient_data

        sales = [100] * 50 + [0] * 100
        df = pd.DataFrame({
            "sales_date": pd.date_range("2023-01-01", periods=150),
            "sales": sales,
        })

        is_sufficient, warning, days = check_sufficient_data(df, min_days=90)

        assert is_sufficient is False
        assert warning is not None
        assert "sparse" in warning.lower()


class TestProphetFeatures:
    """Tests for Prophet-specific feature preparation."""

    def test_build_prophet_features(self):
        """Test Prophet feature building."""
        from ml.src.features.build_forecast_features import build_prophet_features

        df = pd.DataFrame({
            "store_id": [1] * 100,
            "sales_date": pd.date_range("2023-01-01", periods=100),
            "sales": np.random.randint(100, 1000, size=100),
            "promo": [True] * 50 + [False] * 50,
            "school_holiday": [False] * 100,
            "state_holiday": [None] * 100,
        })

        result = build_prophet_features(df, store_id=1)

        assert "ds" in result.columns
        assert "y" in result.columns
        assert "store_id" in result.columns
        assert "is_promo" in result.columns
        assert result["y"].min() > 0  # Only positive values


class TestXGBoostFeatures:
    """Tests for XGBoost-specific feature preparation."""

    def test_build_xgboost_features(self):
        """Test XGBoost feature building."""
        from ml.src.features.build_forecast_features import build_xgboost_features

        df = pd.DataFrame({
            "store_id": [1] * 100,
            "sales_date": pd.date_range("2023-01-01", periods=100),
            "sales": np.random.randint(100, 1000, size=100),
            "store_type": ["A"] * 50 + ["B"] * 50,
            "assortment": ["a"] * 60 + ["b"] * 40,
            "competition_distance": np.random.randint(1000, 5000, size=100),
            "promo2": [False] * 100,
            "promo": [True] * 50 + [False] * 50,
            "school_holiday": [False] * 100,
            "state_holiday": [None] * 100,
            "is_open": [True] * 100,
        })

        result = build_xgboost_features(df, store_id=1, include_lags=True)

        assert "year" in result.columns
        assert "month" in result.columns
        assert "store_type_encoded" in result.columns
        assert "is_promo" in result.columns
        assert "sales_rolling_7d" in result.columns
