"""Baseline forecasting model using historical averaging.

This module provides a simple but robust baseline model that can be used
as a fallback for stores with insufficient data or when advanced models fail.
"""

from datetime import date, timedelta
from typing import Dict, List, Optional, Tuple

import numpy as np
import pandas as pd


class BaselineForecaster:
    """Simple baseline forecaster using historical sales averages."""

    def __init__(self, window_days: int = 28):
        """Initialize the baseline forecaster.

        Args:
            window_days: Number of days to use for calculating averages
        """
        self.window_days = window_days
        self.fitted: bool = False

    def fit(self, df: pd.DataFrame, date_col: str = "sales_date", sales_col: str = "sales") -> None:
        """Fit the baseline model to historical data.

        Args:
            df: DataFrame with historical sales data
            date_col: Name of the date column
            sales_col: Name of the sales column
        """
        self._fit_data = df.sort_values(date_col).copy()
        self.fitted = True

    def predict(
        self,
        horizon_days: int,
        include_ci: bool = True,
        confidence_level: float = 0.95,
    ) -> pd.DataFrame:
        """Generate forecasts for the specified horizon.

        Args:
            horizon_days: Number of days to forecast
            include_ci: Whether to include confidence intervals
            confidence_level: Confidence level for intervals (0-1)

        Returns:
            DataFrame with forecast_date, predicted_sales, lower_bound, upper_bound
        """
        if not self.fitted:
            raise ValueError("Model must be fitted before prediction")

        if len(self._fit_data) == 0:
            raise ValueError("No training data available")

        last_date = self._fit_data["sales_date"].max()
        forecast_dates = [last_date + timedelta(days=d) for d in range(1, horizon_days + 1)]

        # Calculate various statistics from historical data
        recent_sales = self._fit_data[self._fit_data["sales"] > 0]["sales"]
        mean_sales = recent_sales.mean()
        std_sales = recent_sales.std()
        median_sales = recent_sales.median()

        # Calculate day-of-week effects
        self._fit_data["day_of_week"] = self._fit_data["sales_date"].dt.dayofweek
        dow_means = self._fit_data.groupby("day_of_week")["sales"].mean()

        # Generate forecasts with day-of-week adjustments
        forecasts = []
        for forecast_date in forecast_dates:
            dow = forecast_date.weekday()
            dow_effect = dow_means.get(dow, mean_sales) / mean_sales if mean_sales > 0 else 1.0

            # Combine overall mean with day-of-week effect
            predicted = mean_sales * dow_effect
            predicted = max(predicted, 0)

            # Calculate confidence intervals based on historical variability
            if include_ci:
                z_score = 1.96 if confidence_level >= 0.95 else 1.65
                margin = std_sales * z_score / np.sqrt(len(recent_sales))
                lower_bound = max(predicted - margin, 0)
                upper_bound = predicted + margin
            else:
                lower_bound = None
                upper_bound = None

            forecasts.append({
                "forecast_date": forecast_date,
                "predicted_sales": predicted,
                "lower_bound": lower_bound,
                "upper_bound": upper_bound,
            })

        return pd.DataFrame(forecasts)

    def evaluate(
        self,
        test_df: pd.DataFrame,
        date_col: str = "sales_date",
        sales_col: str = "sales",
    ) -> Dict[str, float]:
        """Evaluate the baseline model on test data.

        Args:
            test_df: DataFrame with test data
            date_col: Name of the date column
            sales_col: Name of the sales column

        Returns:
            Dictionary with MAPE, RMSE, and MAE metrics
        """
        horizon = len(test_df)
        predictions = self.predict(horizon_days=horizon, include_ci=False)

        merged = test_df.merge(
            predictions[["forecast_date", "predicted_sales"]],
            left_on=date_col,
            right_on="forecast_date",
            how="inner",
        )

        if len(merged) == 0:
            return {"mape": np.nan, "rmse": np.nan, "mae": np.nan}

        actual = merged[sales_col].values
        predicted = merged["predicted_sales"].values

        # Calculate metrics
        mape = np.mean(np.abs((actual - predicted) / np.maximum(actual, 1))) * 100
        rmse = np.sqrt(np.mean((actual - predicted) ** 2))
        mae = np.mean(np.abs(actual - predicted))

        return {"mape": float(mape), "rmse": float(rmse), "mae": float(mae)}


def train_baseline_model(
    df: pd.DataFrame,
    store_id: int,
    window_days: int = 28,
    min_history_days: int = 30,
) -> Optional[BaselineForecaster]:
    """Train a baseline forecasting model for a single store.

    Args:
        df: DataFrame with sales data for a single store
        store_id: Store identifier
        window_days: Window for moving average calculation
        min_history_days: Minimum days of history required

    Returns:
        Trained BaselineForecaster or None if insufficient data
    """
    store_df = df[df["store_id"] == store_id].copy()

    if len(store_df) < min_history_days:
        return None

    forecaster = BaselineForecaster(window_days=window_days)
    forecaster.fit(store_df)

    return forecaster


def generate_baseline_forecasts(
    df: pd.DataFrame,
    store_ids: List[int],
    horizon_weeks: int = 6,
    min_history_days: int = 30,
) -> Dict[int, Tuple[Optional[pd.DataFrame], Optional[str]]]:
    """Generate baseline forecasts for multiple stores.

    Args:
        df: DataFrame with sales data for all stores
        store_ids: List of store IDs to generate forecasts for
        horizon_weeks: Number of weeks to forecast
        min_history_days: Minimum days of history required

    Returns:
        Dictionary mapping store_id to (forecast_df, warning_message)
    """
    results = {}
    horizon_days = horizon_weeks * 7

    for store_id in store_ids:
        store_df = df[df["store_id"] == store_id].copy()

        if len(store_df) < min_history_days:
            results[store_id] = (
                None,
                f"Insufficient history: {len(store_df)} days (minimum {min_history_days} required)"
            )
            continue

        try:
            forecaster = train_baseline_model(store_df, store_id, min_history_days=min_history_days)
            if forecaster is not None:
                forecasts = forecaster.predict(horizon_days=horizon_days, include_ci=True)
                forecasts["store_id"] = store_id
                results[store_id] = (forecasts, None)
            else:
                results[store_id] = (None, "Model training failed")
        except Exception as e:
            results[store_id] = (None, f"Prediction error: {str(e)}")

    return results
