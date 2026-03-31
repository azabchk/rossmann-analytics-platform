"""Forecast result publishing.

This module provides functions for publishing forecast results to the database.
"""

import json
from datetime import date, datetime
from typing import Dict, List, Optional, Tuple
from uuid import uuid4

import pandas as pd


class ForecastJobResult:
    """Container for forecast job results."""

    def __init__(
        self,
        model_id: str,
        forecast_horizon_days: int,
        forecast_start_date: date,
        forecast_end_date: date,
        stores_included: List[int],
        total_forecasts_generated: int,
        job_status: str,
        error_message: Optional[str] = None,
    ):
        """Initialize forecast job result.

        Args:
            model_id: ID of the model used for forecasting
            forecast_horizon_days: Number of days forecasted
            forecast_start_date: Start date of forecasts
            forecast_end_date: End date of forecasts
            stores_included: List of store IDs with forecasts
            total_forecasts_generated: Total number of forecasts generated
            job_status: Status of the job
            error_message: Error message if job failed
        """
        self.forecast_job_id = str(uuid4())
        self.model_id = model_id
        self.forecast_horizon_days = forecast_horizon_days
        self.forecast_start_date = forecast_start_date
        self.forecast_end_date = forecast_end_date
        self.stores_included = stores_included
        self.total_forecasts_generated = total_forecasts_generated
        self.job_status = job_status
        self.started_at = datetime.utcnow()
        self.completed_at = datetime.utcnow() if job_status != "running" else None
        self.error_message = error_message

    def to_dict(self) -> Dict:
        """Convert to dictionary."""
        return {
            "forecast_job_id": self.forecast_job_id,
            "model_id": self.model_id,
            "forecast_horizon_days": self.forecast_horizon_days,
            "forecast_start_date": self.forecast_start_date.isoformat(),
            "forecast_end_date": self.forecast_end_date.isoformat(),
            "stores_included": self.stores_included,
            "total_forecasts_generated": self.total_forecasts_generated,
            "job_status": self.job_status,
            "started_at": self.started_at.isoformat(),
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "error_message": self.error_message,
        }


class ForecastPublisher:
    """Publisher for forecast results."""

    def __init__(self, model_id: str, confidence_level: float = 0.95):
        """Initialize the forecast publisher.

        Args:
            model_id: ID of the model generating forecasts
            confidence_level: Confidence level for intervals
        """
        self.model_id = model_id
        self.confidence_level = confidence_level
        self.forecasts: List[Dict] = []

    def add_forecast(
        self,
        store_id: int,
        forecast_date: date,
        predicted_sales: float,
        lower_bound: Optional[float] = None,
        upper_bound: Optional[float] = None,
    ) -> None:
        """Add a forecast result.

        Args:
            store_id: Store ID
            forecast_date: Date of the forecast
            predicted_sales: Predicted sales value
            lower_bound: Lower confidence bound
            upper_bound: Upper confidence bound
        """
        self.forecasts.append({
            "forecast_id": str(uuid4()),
            "model_id": self.model_id,
            "store_id": store_id,
            "forecast_date": forecast_date,
            "predicted_sales": predicted_sales,
            "lower_bound": lower_bound,
            "upper_bound": upper_bound,
            "confidence_level": self.confidence_level,
            "is_published": False,
            "generation_timestamp": datetime.utcnow(),
        })

    def add_forecasts_from_dataframe(
        self,
        df: pd.DataFrame,
        store_id_col: str = "store_id",
        forecast_date_col: str = "forecast_date",
        predicted_sales_col: str = "predicted_sales",
        lower_bound_col: str = "lower_bound",
        upper_bound_col: str = "upper_bound",
    ) -> None:
        """Add forecasts from a DataFrame.

        Args:
            df: DataFrame with forecast data
            store_id_col: Name of store ID column
            forecast_date_col: Name of forecast date column
            predicted_sales_col: Name of predicted sales column
            lower_bound_col: Name of lower bound column
            upper_bound_col: Name of upper bound column
        """
        for _, row in df.iterrows():
            self.add_forecast(
                store_id=row[store_id_col],
                forecast_date=pd.to_datetime(row[forecast_date_col]).date(),
                predicted_sales=row[predicted_sales_col],
                lower_bound=row.get(lower_bound_col),
                upper_bound=row.get(upper_bound_col),
            )

    def publish(self) -> Tuple[List[Dict], ForecastJobResult]:
        """Publish all added forecasts.

        Returns:
            Tuple of (forecast_records, job_result)
        """
        job_result = ForecastJobResult(
            model_id=self.model_id,
            forecast_horizon_days=max(
                (f["forecast_date"] - min(f["forecast_date"] for f in self.forecasts)).days + 1,
                0,
            ) if self.forecasts else 0,
            forecast_start_date=min(f["forecast_date"] for f in self.forecasts) if self.forecasts else date.today(),
            forecast_end_date=max(f["forecast_date"] for f in self.forecasts) if self.forecasts else date.today(),
            stores_included=list(set(f["store_id"] for f in self.forecasts)),
            total_forecasts_generated=len(self.forecasts),
            job_status="completed",
        )

        return self.forecasts, job_result


def publish_forecasts(
    forecasts: Dict[int, pd.DataFrame],
    model_id: str,
    horizon_weeks: int = 6,
) -> Tuple[ForecastJobResult, Dict[int, List[Dict]]]:
    """Publish forecasts for multiple stores.

    Args:
        forecasts: Dictionary mapping store_id to forecast DataFrame
        model_id: ID of the model used for forecasting
        horizon_weeks: Number of weeks forecasted

    Returns:
        Tuple of (job_result, forecast_records_by_store)
    """
    publisher = ForecastPublisher(model_id=model_id, confidence_level=0.95)

    forecast_records_by_store: Dict[int, List[Dict]] = {}

    for store_id, forecast_df in forecasts.items():
        if forecast_df is None:
            continue

        try:
            publisher.add_forecasts_from_dataframe(forecast_df)
            records = []
            for _, row in forecast_df.iterrows():
                records.append({
                    "store_id": store_id,
                    "forecast_date": pd.to_datetime(row["forecast_date"]).date(),
                    "predicted_sales": row["predicted_sales"],
                    "lower_bound": row.get("lower_bound"),
                    "upper_bound": row.get("upper_bound"),
                    "confidence_level": 95.0,
                })
            forecast_records_by_store[store_id] = records
        except Exception:
            continue

    forecast_records, job_result = publisher.publish()

    return job_result, forecast_records_by_store


def create_low_data_warning(
    store_id: int,
    warning_type: str,
    days_of_history: int,
    warning_message: str,
) -> Dict:
    """Create a low data warning record.

    Args:
        store_id: Store ID with insufficient data
        warning_type: Type of warning (insufficient_history, sparse_data, high_variance)
        days_of_history: Number of days of history available
        warning_message: Warning message

    Returns:
        Dictionary with warning record
    """
    return {
        "warning_id": str(uuid4()),
        "store_id": store_id,
        "warning_type": warning_type,
        "days_of_history": days_of_history,
        "warning_message": warning_message,
        "is_active": True,
    }
