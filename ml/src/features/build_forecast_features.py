"""Feature preparation for sales forecasting models.

This module provides functions for building forecasting features from the
cleaned operational data. It supports both Prophet and XGBoost-based models
with appropriate feature extraction.
"""

from datetime import date, timedelta
from typing import Dict, List, Optional, Tuple

import numpy as np
import pandas as pd


def _resolve_date_column(df: pd.DataFrame, preferred: str = "date") -> str:
    """Resolve the date column used by forecasting utilities."""
    if preferred in df.columns:
        return preferred
    if "sales_date" in df.columns:
        return "sales_date"
    if "forecast_date" in df.columns:
        return "forecast_date"
    raise KeyError(preferred)


def extract_lag_features(
    df: pd.DataFrame,
    lag_periods: List[int] = [1, 7, 14, 28],
    sales_col: str = "sales",
) -> pd.DataFrame:
    """Extract lag features from sales data.

    Args:
        df: DataFrame with sales data sorted by date
        lag_periods: List of lag periods in days to create
        sales_col: Name of the sales column

    Returns:
        DataFrame with added lag features
    """
    result = df.copy()
    for lag in lag_periods:
        result[f"sales_lag_{lag}"] = result[sales_col].shift(lag)
    return result


def extract_seasonal_features(df: pd.DataFrame, date_col: str = "date") -> pd.DataFrame:
    """Extract seasonal features from date column.

    Args:
        df: DataFrame with date column
        date_col: Name of the date column

    Returns:
        DataFrame with added seasonal features
    """
    date_col = _resolve_date_column(df, date_col)
    result = df.copy()
    result["year"] = result[date_col].dt.year
    result["month"] = result[date_col].dt.month
    result["day_of_week"] = result[date_col].dt.dayofweek
    result["day_of_month"] = result[date_col].dt.day
    result["day_of_year"] = result[date_col].dt.dayofyear
    result["week_of_year"] = result[date_col].dt.isocalendar().week.astype(int)
    result["is_weekend"] = result["day_of_week"].isin([5, 6]).astype(int)
    result["is_month_start"] = result["day_of_month"] <= 3.0
    result["is_month_end"] = result["day_of_month"] >= 28.0

    # Sin/cos cyclical encoding for month and day
    result["month_sin"] = np.sin(2 * np.pi * result["month"] / 12)
    result["month_cos"] = np.cos(2 * np.pi * result["month"] / 12)
    result["day_of_week_sin"] = np.sin(2 * np.pi * result["day_of_week"] / 7)
    result["day_of_week_cos"] = np.cos(2 * np.pi * result["day_of_week"] / 7)

    return result


def check_sufficient_data(
    df: pd.DataFrame,
    min_days: int = 90,
    date_col: str = "date",
) -> Tuple[bool, Optional[str], int]:
    """Check if a store has sufficient historical data for reliable forecasting.

    Args:
        df: DataFrame with sales data for a single store
        min_days: Minimum number of days of data required
        date_col: Name of the date column

    Returns:
        Tuple of (is_sufficient, warning_message, days_of_history)
    """
    date_col = _resolve_date_column(df, date_col)
    df = df.sort_values(date_col)

    # Count days with non-zero sales
    days_with_sales = df[df["sales"] > 0].shape[0]
    total_days = len(df)

    # Check data sparsity
    if total_days < min_days:
        warning = f"Insufficient history: {total_days} days (minimum {min_days} required)"
        return False, warning, total_days

    # Check if data is too sparse
    sales_ratio = days_with_sales / total_days if total_days > 0 else 0
    if sales_ratio < 0.5:
        warning = f"Sparse data: only {sales_ratio:.1%} of days have sales"
        return False, warning, total_days

    # Check for high variance (potential data quality issues)
    if len(df) > 30:
        sales_std = df["sales"].std()
        sales_mean = df["sales"].mean()
        cv = sales_std / sales_mean if sales_mean > 0 else 0
        if cv > 2.0:
            warning = f"High variance: coefficient of variation {cv:.2f}"
            return False, warning, total_days

    return True, None, total_days


def build_prophet_features(
    df: pd.DataFrame,
    store_id: int,
) -> pd.DataFrame:
    """Build features specifically for Prophet model.

    Prophet requires a specific format with 'ds' (date) and 'y' (value) columns.
    Additional regressors can be included for promotions and holidays.

    Args:
        df: DataFrame with sales data
        store_id: Store identifier for filtering

    Returns:
        DataFrame prepared for Prophet with required columns
    """
    # Filter for specific store
    store_df = df[df["store_id"] == store_id].copy()

    # Prophet expects columns named 'ds' and 'y'
    prophet_df = pd.DataFrame({
        "ds": store_df["sales_date"],
        "y": store_df["sales"],
        "store_id": store_id,
    })

    # Add extra regressors for promotions and holidays
    prophet_df["is_promo"] = store_df["promo"].astype(int)
    prophet_df["is_school_holiday"] = store_df["school_holiday"].astype(int)

    # State holiday as binary
    prophet_df["is_state_holiday"] = (
        store_df["state_holiday"].notna() & (store_df["state_holiday"] != "0")
    ).astype(int)

    # Only include open days
    prophet_df = prophet_df[prophet_df["y"] > 0]

    return prophet_df.sort_values("ds")


def build_xgboost_features(
    df: pd.DataFrame,
    store_id: int,
    include_lags: bool = True,
) -> pd.DataFrame:
    """Build feature matrix for XGBoost model.

    Creates a comprehensive feature set including lag features, seasonal features,
    store attributes, promotion indicators, and holiday effects.

    Args:
        df: DataFrame with sales data
        store_id: Store identifier
        include_lags: Whether to include lag features

    Returns:
        DataFrame with features and target for XGBoost
    """
    # Filter for specific store and merge with store attributes
    store_df = df[df["store_id"] == store_id].copy()

    # Add seasonal features
    store_df = extract_seasonal_features(store_df, "sales_date")

    # Encode categorical variables
    store_df["store_type_encoded"] = store_df["store_type"].map({"A": 0, "B": 1, "C": 2, "D": 3})
    store_df["assortment_encoded"] = store_df["assortment"].map({"a": 0, "b": 1, "c": 2})
    store_df["promo2_encoded"] = store_df["promo2"].astype(int)

    # Normalize competition distance
    max_comp_dist = store_df["competition_distance"].max()
    if max_comp_dist > 0:
        store_df["competition_distance_norm"] = store_df["competition_distance"] / max_comp_dist
    else:
        store_df["competition_distance_norm"] = 0

    # Add promotion and holiday features
    store_df["is_promo"] = store_df["promo"].astype(int)
    store_df["is_school_holiday"] = store_df["school_holiday"].astype(int)
    store_df["is_state_holiday"] = (
        store_df["state_holiday"].notna() & (store_df["state_holiday"] != "0")
    ).astype(int)

    # Combine holiday flags
    store_df["is_holiday"] = (store_df["is_state_holiday"] | store_df["is_school_holiday"]).astype(int)

    # Calculate rolling statistics
    store_df = store_df.sort_values("sales_date")
    store_df["sales_rolling_7d"] = store_df["sales"].rolling(window=7, min_periods=1).mean()
    store_df["sales_rolling_28d"] = store_df["sales"].rolling(window=28, min_periods=1).mean()

    # Add lag features if requested
    if include_lags:
        store_df = extract_lag_features(store_df, [1, 7, 14, 28], "sales")

    # Only include open days for training
    feature_df = store_df[store_df["is_open"] & (store_df["sales"] > 0)].copy()

    return feature_df


def build_forecast_features(
    df: pd.DataFrame,
    store_ids: Optional[List[int]] = None,
    min_days_history: int = 90,
) -> Dict[int, pd.DataFrame]:
    """Build forecast features for multiple stores.

    Args:
        df: DataFrame with sales data including store attributes
        store_ids: List of store IDs to process (None for all stores)
        min_days_history: Minimum days of history required

    Returns:
        Dictionary mapping store_id to DataFrame with features
    """
    results = {}

    if store_ids is None:
        store_ids = df["store_id"].unique().tolist()

    for store_id in store_ids:
        store_df = df[df["store_id"] == store_id].copy()

        # Check data sufficiency
        is_sufficient, warning, days_count = check_sufficient_data(
            store_df, min_days_history, "sales_date"
        )

        if not is_sufficient:
            # Return DataFrame with warning metadata
            results[store_id] = pd.DataFrame({
                "store_id": [store_id],
                "is_sufficient": [False],
                "warning_message": [warning],
                "days_of_history": [days_count],
            })
            continue

        # Build both Prophet and XGBoost feature sets
        prophet_features = build_prophet_features(store_df, store_id)
        xgb_features = build_xgboost_features(store_df, store_id)

        # Store combined result with metadata
        results[store_id] = pd.DataFrame({
            "store_id": [store_id],
            "is_sufficient": [True],
            "days_of_history": [days_count],
            "prophet_rows": [len(prophet_features)],
            "xgb_rows": [len(xgb_features)],
        })

    return results
