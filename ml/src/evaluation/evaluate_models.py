"""Model evaluation for forecasting models.

This module provides functions for evaluating forecasting models and comparing
their performance on holdout test sets.
"""

from dataclasses import dataclass, field
from datetime import date
from typing import Dict, List, Optional

import numpy as np
import pandas as pd


def _resolve_date_column(df: pd.DataFrame, preferred: str) -> str:
    """Resolve the date column used when evaluating forecasts."""
    if preferred in df.columns:
        return preferred
    if preferred == "date" and "sales_date" in df.columns:
        return "sales_date"
    if preferred == "date" and "forecast_date" in df.columns:
        return "forecast_date"
    raise KeyError(preferred)


@dataclass
class ModelEvaluationResult:
    """Container for model evaluation results."""

    model_type: str
    model_id: str
    store_id: int
    evaluation_period_start: date
    evaluation_period_end: date
    mape: float
    rmse: float
    mae: float
    additional_metrics: Dict[str, float] = field(default_factory=dict)

    def to_dict(self) -> Dict:
        """Convert to dictionary."""
        return {
            "model_type": self.model_type,
            "model_id": self.model_id,
            "store_id": self.store_id,
            "evaluation_period_start": self.evaluation_period_start.isoformat(),
            "evaluation_period_end": self.evaluation_period_end.isoformat(),
            "mape": self.mape,
            "rmse": self.rmse,
            "mae": self.mae,
            "additional_metrics": self.additional_metrics,
        }


def calculate_mape(actual: np.ndarray, predicted: np.ndarray) -> float:
    """Calculate Mean Absolute Percentage Error.

    Args:
        actual: Actual values
        predicted: Predicted values

    Returns:
        MAPE as a percentage
    """
    mask = actual > 0
    if not np.any(mask):
        return np.inf
    return np.mean(np.abs((actual[mask] - predicted[mask]) / actual[mask])) * 100


def calculate_rmse(actual: np.ndarray, predicted: np.ndarray) -> float:
    """Calculate Root Mean Squared Error.

    Args:
        actual: Actual values
        predicted: Predicted values

    Returns:
        RMSE
    """
    return np.sqrt(np.mean((actual - predicted) ** 2))


def calculate_mae(actual: np.ndarray, predicted: np.ndarray) -> float:
    """Calculate Mean Absolute Error.

    Args:
        actual: Actual values
        predicted: Predicted values

    Returns:
        MAE
    """
    return np.mean(np.abs(actual - predicted))


def evaluate_forecast(
    actual_df: pd.DataFrame,
    forecast_df: pd.DataFrame,
    date_col: str = "date",
    sales_col: str = "sales",
    forecast_date_col: str = "forecast_date",
    predicted_sales_col: str = "predicted_sales",
) -> Dict[str, float]:
    """Evaluate forecast against actual values.

    Args:
        actual_df: DataFrame with actual sales
        forecast_df: DataFrame with forecasted values
        date_col: Date column name in actual_df
        sales_col: Sales column name in actual_df
        forecast_date_col: Forecast date column name in forecast_df
        predicted_sales_col: Predicted sales column name in forecast_df

    Returns:
        Dictionary with MAPE, RMSE, and MAE
    """
    date_col = _resolve_date_column(actual_df, date_col)
    forecast_date_col = _resolve_date_column(forecast_df, forecast_date_col)

    merged = actual_df.merge(
        forecast_df[[forecast_date_col, predicted_sales_col]],
        left_on=date_col,
        right_on=forecast_date_col,
        how="inner",
    )

    if len(merged) == 0:
        return {"mape": np.nan, "rmse": np.nan, "mae": np.nan}

    actual = merged[sales_col].values
    predicted = merged[predicted_sales_col].values

    return {
        "mape": calculate_mape(actual, predicted),
        "rmse": calculate_rmse(actual, predicted),
        "mae": calculate_mae(actual, predicted),
    }


def compare_models(evaluations: List[ModelEvaluationResult]) -> Dict[str, ModelEvaluationResult]:
    """Compare model evaluations and select best by metric.

    Args:
        evaluations: List of evaluation results

    Returns:
        Dictionary with best model by each metric
    """
    if not evaluations:
        return {}

    best_by_mape = min(evaluations, key=lambda x: x.mape)
    best_by_rmse = min(evaluations, key=lambda x: x.rmse)
    best_by_mae = min(evaluations, key=lambda x: x.mae)

    return {
        "best_mape": best_by_mape,
        "best_rmse": best_by_rmse,
        "best_mae": best_by_mae,
    }


def evaluate_all_models(
    actual_df: pd.DataFrame,
    forecasts: Dict[str, pd.DataFrame],
    evaluation_start: date,
    evaluation_end: date,
) -> Dict[str, ModelEvaluationResult]:
    """Evaluate all forecast models against actual values.

    Args:
        actual_df: DataFrame with actual sales
        forecasts: Dictionary mapping model_type to forecast DataFrame
        evaluation_start: Start date for evaluation period
        evaluation_end: End date for evaluation period

    Returns:
        Dictionary mapping model_type to evaluation results
    """
    results = {}

    # Filter actual data to evaluation period
    filtered_actual = actual_df[
        (actual_df["sales_date"] >= evaluation_start) &
        (actual_df["sales_date"] <= evaluation_end)
    ].copy()

    for model_type, forecast_df in forecasts.items():
        metrics = evaluate_forecast(
            filtered_actual,
            forecast_df,
            date_col="sales_date",
            sales_col="sales",
            forecast_date_col="forecast_date",
            predicted_sales_col="predicted_sales",
        )

        results[model_type] = ModelEvaluationResult(
            model_type=model_type,
            model_id=f"model_{model_type}",  # Will be updated with actual ID
            store_id=0,  # Will be updated with actual store_id
            evaluation_period_start=evaluation_start,
            evaluation_period_end=evaluation_end,
            mape=metrics["mape"],
            rmse=metrics["rmse"],
            mae=metrics["mae"],
        )

    return results


def check_acceptable_performance(
    mape: float,
    threshold: float = 15.0,
) -> bool:
    """Check if model performance is acceptable.

    Args:
        mape: Mean Absolute Percentage Error
        threshold: Acceptable MAPE threshold

    Returns:
        True if performance is acceptable
    """
    return mape < threshold


def create_evaluation_summary(
    evaluations: List[ModelEvaluationResult],
) -> Dict:
    """Create a summary of all evaluations.

    Args:
        evaluations: List of evaluation results

    Returns:
        Summary dictionary
    """
    if not evaluations:
        return {"count": 0, "models": []}

    model_types = set(e.model_type for e in evaluations)

    summary = {
        "count": len(evaluations),
        "model_types": list(model_types),
        "by_model_type": {},
        "best_by_mape": None,
        "best_by_rmse": None,
        "best_by_mae": None,
    }

    for model_type in model_types:
        type_evals = [e for e in evaluations if e.model_type == model_type]
        summary["by_model_type"][model_type] = {
            "count": len(type_evals),
            "avg_mape": np.mean([e.mape for e in type_evals]),
            "avg_rmse": np.mean([e.rmse for e in type_evals]),
            "avg_mae": np.mean([e.mae for e in type_evals]),
        }

    if evaluations:
        summary["best_by_mape"] = min(evaluations, key=lambda x: x.mape).to_dict()
        summary["best_by_rmse"] = min(evaluations, key=lambda x: x.rmse).to_dict()
        summary["best_by_mae"] = min(evaluations, key=lambda x: x.mae).to_dict()

    return summary
