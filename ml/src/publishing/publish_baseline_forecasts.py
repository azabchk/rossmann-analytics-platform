"""Baseline forecast publishing utilities.

This module provides convenience functions for publishing baseline forecasts.
"""

from datetime import date
from typing import Dict, List, Optional, Tuple

import pandas as pd

from .publish_forecasts import ForecastJobResult, ForecastPublisher, create_low_data_warning


def publish_baseline_forecasts(
    df: pd.DataFrame,
    store_ids: List[int],
    horizon_weeks: int = 6,
    min_history_days: int = 30,
) -> Tuple[Optional[ForecastJobResult], Dict[int, List[Dict]], List[Dict]]:
    """Generate and publish baseline forecasts for multiple stores.

    Args:
        df: DataFrame with sales data for all stores
        store_ids: List of store IDs to generate forecasts for
        horizon_weeks: Number of weeks to forecast
        min_history_days: Minimum days of history required

    Returns:
        Tuple of (job_result, forecast_records_by_store, warnings)
    """
    from ..training.train_baseline import generate_baseline_forecasts

    # Generate forecasts
    forecast_results = generate_baseline_forecasts(
        df=df,
        store_ids=store_ids,
        horizon_weeks=horizon_weeks,
        min_history_days=min_history_days,
    )

    # Create publisher
    publisher = ForecastPublisher(model_id="baseline_model", confidence_level=0.95)

    forecast_records_by_store: Dict[int, List[Dict]] = {}
    warnings: List[Dict] = []

    for store_id, (forecast_df, warning_message) in forecast_results.items():
        if forecast_df is None:
            # Create low data warning
            if warning_message:
                warnings.append(
                    create_low_data_warning(
                        store_id=store_id,
                        warning_type="insufficient_history",
                        days_of_history=len(df[df["store_id"] == store_id]),
                        warning_message=warning_message,
                    )
                )
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

    if not forecast_records_by_store:
        return None, {}, warnings

    forecast_records, job_result = publisher.publish()
    job_result.model_id = "baseline_model"

    return job_result, forecast_records_by_store, warnings
