"""Prophet model training for time-series forecasting.

This module provides Prophet-based forecasting using the Facebook Prophet
library for time-series prediction with seasonality and holiday effects.
"""

from datetime import date, timedelta
from typing import Dict, List, Optional, Tuple

import numpy as np
import pandas as pd


class ProphetForecaster:
    """Prophet-based time-series forecaster."""

    def __init__(
        self,
        yearly_seasonality: bool = True,
        weekly_seasonality: bool = True,
        daily_seasonality: bool = False,
        seasonality_mode: str = "multiplicative",
        uncertainty_samples: int = 1000,
    ):
        """Initialize the Prophet forecaster.

        Args:
            yearly_seasonality: Include yearly seasonality
            weekly_seasonality: Include weekly seasonality
            daily_seasonality: Include daily seasonality
            seasonality_mode: Seasonality mode ('additive' or 'multiplicative')
            uncertainty_samples: Number of uncertainty samples for CI calculation
        """
        try:
            from prophet import Prophet
        except ImportError:
            raise ImportError("Prophet library is required. Install with: pip install prophet")

        self.yearly_seasonality = yearly_seasonality
        self.weekly_seasonality = weekly_seasonality
        self.daily_seasonality = daily_seasonality
        self.seasonality_mode = seasonality_mode
        self.uncertainty_samples = uncertainty_samples
        self.fitted: bool = False
        self.model: Optional["Prophet"] = None

    def _create_model(self) -> "Prophet":
        """Create a Prophet model with configured parameters."""
        from prophet import Prophet

        model = Prophet(
            yearly_seasonality=self.yearly_seasonality,
            weekly_seasonality=self.weekly_seasonality,
            daily_seasonality=self.daily_seasonality,
            seasonality_mode=self.seasonality_mode,
            interval_width=0.95,
            uncertainty_samples=self.uncertainty_samples,
            changepoint_prior_scale=0.05,
            seasonality_prior_scale=10.0,
            holidays_prior_scale=10.0,
        )
        return model

    def fit(self, df: pd.DataFrame) -> None:
        """Fit the Prophet model to historical data.

        Args:
            df: DataFrame with columns 'ds' (date), 'y' (value), and optional regressors
        """
        if "ds" not in df.columns or "y" not in df.columns:
            raise ValueError("DataFrame must contain 'ds' and 'y' columns")

        train_df = df[["ds", "y"]].copy()

        # Add extra regressors if present
        regressors = [col for col in df.columns if col not in ["ds", "y", "store_id"]]
        self.regressors = regressors

        self.model = self._create_model()

        # Add regressors to model
        for regressor in regressors:
            if regressor in df.columns:
                self.model.add_regressor(regressor, mode="multiplicative")
                train_df[regressor] = df[regressor].values

        self.model.fit(train_df)
        self.fitted = True

    def predict(self, horizon_days: int, future_df: Optional[pd.DataFrame] = None) -> pd.DataFrame:
        """Generate forecasts for the specified horizon.

        Args:
            horizon_days: Number of days to forecast
            future_df: Optional DataFrame with future regressor values

        Returns:
            DataFrame with forecast_date, predicted_sales, lower_bound, upper_bound
        """
        if not self.fitted:
            raise ValueError("Model must be fitted before prediction")

        # Create future dataframe
        future = self.model.make_future_dataframe(periods=horizon_days)

        # Add future regressor values if provided
        if future_df is not None and len(self.regressors) > 0:
            for regressor in self.regressors:
                if regressor in future_df.columns:
                    future[regressor] = future_df[regressor].values

        # Generate predictions
        forecast = self.model.predict(future)

        # Extract only the forecast period
        last_history_date = self.model.history_dates.max()
        forecast_period = forecast[forecast["ds"] > last_history_date]

        result = pd.DataFrame({
            "forecast_date": forecast_period["ds"].dt.date,
            "predicted_sales": forecast_period["yhat"].values,
            "lower_bound": forecast_period["yhat_lower"].values,
            "upper_bound": forecast_period["yhat_upper"].values,
        })

        # Ensure non-negative values
        result["predicted_sales"] = result["predicted_sales"].clip(lower=0)
        result["lower_bound"] = result["lower_bound"].clip(lower=0)
        result["upper_bound"] = result["upper_bound"].clip(lower=0)

        return result

    def evaluate(self, test_df: pd.DataFrame) -> Dict[str, float]:
        """Evaluate the Prophet model on test data.

        Args:
            test_df: DataFrame with 'ds' and 'y' columns for testing

        Returns:
            Dictionary with MAPE, RMSE, and MAE metrics
        """
        horizon = len(test_df)
        predictions = self.predict(horizon_days=horizon)

        merged = test_df.merge(
            predictions,
            left_on="ds",
            right_on="forecast_date",
            how="inner",
        )

        if len(merged) == 0:
            return {"mape": np.nan, "rmse": np.nan, "mae": np.nan}

        actual = merged["y"].values
        predicted = merged["predicted_sales"].values

        mape = np.mean(np.abs((actual - predicted) / np.maximum(actual, 1))) * 100
        rmse = np.sqrt(np.mean((actual - predicted) ** 2))
        mae = np.mean(np.abs(actual - predicted))

        return {"mape": float(mape), "rmse": float(rmse), "mae": float(mae)}


def train_prophet_model(
    df: pd.DataFrame,
    store_id: int,
    min_history_days: int = 90,
) -> Optional[ProphetForecaster]:
    """Train a Prophet model for a single store.

    Args:
        df: DataFrame with sales data including store attributes
        store_id: Store identifier
        min_history_days: Minimum days of history required

    Returns:
        Trained ProphetForecaster or None if insufficient data
    """
    store_df = df[df["store_id"] == store_id].copy()

    if len(store_df) < min_history_days:
        return None

    # Prepare Prophet-specific features
    store_df["ds"] = pd.to_datetime(store_df["sales_date"])
    store_df["y"] = store_df["sales"]
    store_df = store_df[store_df["y"] > 0]

    if len(store_df) < min_history_days:
        return None

    try:
        forecaster = ProphetForecaster(
            yearly_seasonality=True,
            weekly_seasonality=True,
            seasonality_mode="multiplicative",
        )
        forecaster.fit(store_df)
        return forecaster
    except Exception:
        return None


def generate_prophet_forecasts(
    df: pd.DataFrame,
    store_ids: List[int],
    horizon_weeks: int = 6,
    min_history_days: int = 90,
) -> Dict[int, Tuple[Optional[pd.DataFrame], Optional[str]]]:
    """Generate Prophet forecasts for multiple stores.

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
            forecaster = train_prophet_model(store_df, store_id, min_history_days=min_history_days)
            if forecaster is not None:
                forecasts = forecaster.predict(horizon_days=horizon_days)
                forecasts["store_id"] = store_id
                results[store_id] = (forecasts, None)
            else:
                results[store_id] = (None, "Model training failed")
        except Exception as e:
            results[store_id] = (None, f"Prediction error: {str(e)}")

    return results
