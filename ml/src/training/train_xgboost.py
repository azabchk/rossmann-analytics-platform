"""XGBoost model training for sales forecasting.

This module provides XGBoost-based forecasting using gradient boosting
with engineered features including lags, seasonality, and store attributes.
"""

from datetime import date, timedelta
from typing import Dict, List, Optional, Tuple

import numpy as np
import pandas as pd


class XGBoostForecaster:
    """XGBoost-based sales forecaster."""

    def __init__(
        self,
        n_estimators: int = 500,
        max_depth: int = 6,
        learning_rate: float = 0.05,
        subsample: float = 0.8,
        colsample_bytree: float = 0.8,
        random_state: int = 42,
    ):
        """Initialize the XGBoost forecaster.

        Args:
            n_estimators: Number of boosting rounds
            max_depth: Maximum tree depth
            learning_rate: Learning rate (eta)
            subsample: Subsample ratio of training instances
            colsample_bytree: Subsample ratio of columns when constructing tree
            random_state: Random seed for reproducibility
        """
        try:
            import xgboost as xgb
        except ImportError:
            raise ImportError("XGBoost library is required. Install with: pip install xgboost")

        self.n_estimators = n_estimators
        self.max_depth = max_depth
        self.learning_rate = learning_rate
        self.subsample = subsample
        self.colsample_bytree = colsample_bytree
        self.random_state = random_state
        self.fitted: bool = False
        self.model: Optional["xgb.XGBRegressor"] = None
        self.feature_cols: Optional[List[str]] = None
        self.target_col: str = "sales"

    def _create_model(self) -> "xgb.XGBRegressor":
        """Create an XGBoost regressor model."""
        import xgboost as xgb

        model = xgb.XGBRegressor(
            n_estimators=self.n_estimators,
            max_depth=self.max_depth,
            learning_rate=self.learning_rate,
            subsample=self.subsample,
            colsample_bytree=self.colsample_bytree,
            objective="reg:squarederror",
            eval_metric="rmse",
            random_state=self.random_state,
            n_jobs=-1,
        )
        return model

    def fit(
        self,
        df: pd.DataFrame,
        target_col: str = "sales",
        exclude_cols: Optional[List[str]] = None,
    ) -> None:
        """Fit the XGBoost model to historical data.

        Args:
            df: DataFrame with features and target
            target_col: Name of the target column
            exclude_cols: Columns to exclude from features
        """
        if exclude_cols is None:
            exclude_cols = ["store_id", "sales_date", "is_open"]

        # Identify feature columns
        exclude_cols_with_target = exclude_cols + [target_col]
        self.feature_cols = [col for col in df.columns if col not in exclude_cols_with_target]

        if not self.feature_cols:
            raise ValueError("No feature columns available after exclusions")

        # Prepare training data
        X = df[self.feature_cols].fillna(0)
        y = df[target_col].fillna(0)

        # Train model
        self.model = self._create_model()
        self.model.fit(X, y)
        self.fitted = True

    def predict(
        self,
        df: pd.DataFrame,
        include_ci: bool = True,
        confidence_level: float = 0.95,
        n_bootstrap: int = 100,
    ) -> pd.DataFrame:
        """Generate forecasts with optional confidence intervals.

        Args:
            df: DataFrame with features for prediction
            include_ci: Whether to include confidence intervals
            confidence_level: Confidence level for intervals
            n_bootstrap: Number of bootstrap samples for CI estimation

        Returns:
            DataFrame with forecast_date, predicted_sales, lower_bound, upper_bound
        """
        if not self.fitted or self.feature_cols is None:
            raise ValueError("Model must be fitted before prediction")

        X = df[self.feature_cols].fillna(0)

        # Generate point predictions
        predictions = self.model.predict(X)

        # Create result dataframe
        result = pd.DataFrame({
            "forecast_date": df["forecast_date"],
            "predicted_sales": np.maximum(predictions, 0),
        })

        # Estimate confidence intervals via bootstrap if requested
        if include_ci:
            lower_bounds = []
            upper_bounds = []

            for _ in range(n_bootstrap):
                # Sample with replacement from training predictions
                indices = np.random.choice(len(predictions), size=len(predictions), replace=True)
                sample_preds = predictions[indices]

                # Calculate percentiles
                alpha = 1 - confidence_level
                lower = np.percentile(sample_preds, alpha / 2 * 100)
                upper = np.percentile(sample_preds, (1 - alpha / 2) * 100)
                lower_bounds.append(max(lower, 0))
                upper_bounds.append(max(upper, 0))

            result["lower_bound"] = np.mean(lower_bounds, axis=0)
            result["upper_bound"] = np.mean(upper_bounds, axis=0)
        else:
            result["lower_bound"] = None
            result["upper_bound"] = None

        return result

    def evaluate(
        self,
        df: pd.DataFrame,
        target_col: str = "sales",
    ) -> Dict[str, float]:
        """Evaluate the XGBoost model on test data.

        Args:
            df: DataFrame with features and target for testing
            target_col: Name of the target column

        Returns:
            Dictionary with MAPE, RMSE, and MAE metrics
        """
        X = df[self.feature_cols].fillna(0)  # type: ignore
        actual = df[target_col].fillna(0).values

        predictions = self.model.predict(X)
        predictions = np.maximum(predictions, 0)

        mape = np.mean(np.abs((actual - predictions) / np.maximum(actual, 1))) * 100
        rmse = np.sqrt(np.mean((actual - predictions) ** 2))
        mae = np.mean(np.abs(actual - predictions))

        return {"mape": float(mape), "rmse": float(rmse), "mae": float(mae)}


def train_xgboost_model(
    df: pd.DataFrame,
    store_id: int,
    min_history_days: int = 90,
) -> Optional[Tuple[XGBoostForecaster, pd.DataFrame]]:
    """Train an XGBoost model for a single store.

    Args:
        df: DataFrame with sales data including store attributes
        store_id: Store identifier
        min_history_days: Minimum days of history required

    Returns:
        Tuple of (trained forecaster, feature_df) or None if insufficient data
    """
    try:
        from .features.build_forecast_features import build_xgboost_features
    except ImportError:
        # Circular import fallback
        return None

    store_df = df[df["store_id"] == store_id].copy()

    if len(store_df) < min_history_days:
        return None

    try:
        feature_df = build_xgboost_features(store_df, store_id, include_lags=True)

        if len(feature_df) < min_history_days:
            return None

        forecaster = XGBoostForecaster(
            n_estimators=500,
            max_depth=6,
            learning_rate=0.05,
            random_state=42,
        )
        forecaster.fit(feature_df)

        return forecaster, feature_df
    except Exception:
        return None


def generate_xgboost_forecasts(
    df: pd.DataFrame,
    store_ids: List[int],
    horizon_weeks: int = 6,
    min_history_days: int = 90,
) -> Dict[int, Tuple[Optional[pd.DataFrame], Optional[str]]]:
    """Generate XGBoost forecasts for multiple stores.

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
            result = train_xgboost_model(store_df, store_id, min_history_days=min_history_days)
            if result is not None:
                forecaster, feature_df = result

                # Create future feature rows
                last_date = feature_df["sales_date"].max()
                future_dates = [last_date + timedelta(days=d) for d in range(1, horizon_days + 1)]

                future_rows = []
                for forecast_date in future_dates:
                    row = feature_df.iloc[-1].copy()
                    row["forecast_date"] = forecast_date
                    row["sales_date"] = forecast_date
                    # Reset lag features to recent values
                    row["sales_lag_1"] = row["sales"]
                    row["sales_lag_7"] = row["sales_rolling_7d"]
                    row["sales_lag_14"] = row["sales_rolling_28d"]
                    row["sales_lag_28"] = row["sales_rolling_28d"]
                    future_rows.append(row)

                future_df = pd.DataFrame(future_rows)
                forecasts = forecaster.predict(future_df, include_ci=True)
                forecasts["store_id"] = store_id
                results[store_id] = (forecasts, None)
            else:
                results[store_id] = (None, "Model training failed")
        except Exception as e:
            results[store_id] = (None, f"Prediction error: {str(e)}")

    return results
