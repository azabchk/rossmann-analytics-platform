"""Publish baseline forecasts from prepared database data.

This module is the minimum governed publication path for the demo-ready MVP:

prepared sales data -> baseline forecast generation -> persisted model metadata
and forecast results -> backend retrieval through FastAPI.
"""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from typing import Any

import pandas as pd
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine

from ml.src.training.train_baseline import BaselineForecaster


def _to_sync_database_url(database_url: str) -> str:
    if database_url.startswith("postgresql+asyncpg://"):
        return database_url.replace("postgresql+asyncpg://", "postgresql+psycopg2://", 1)
    if database_url.startswith("postgresql://"):
        return database_url.replace("postgresql://", "postgresql+psycopg2://", 1)
    if database_url.startswith("sqlite+aiosqlite://"):
        return database_url.replace("sqlite+aiosqlite://", "sqlite://", 1)
    return database_url


def _table_exists(engine: Engine, schema: str, table: str) -> bool:
    query = text(
        """
        SELECT EXISTS (
            SELECT 1
            FROM information_schema.tables
            WHERE table_schema = :schema_name
              AND table_name = :table_name
        )
        """
    )
    with engine.connect() as connection:
        return bool(
            connection.execute(
                query,
                {"schema_name": schema, "table_name": table},
            ).scalar()
        )


def _load_prepared_sales(engine: Engine, store_ids: list[int] | None = None) -> pd.DataFrame:
    params: dict[str, Any] = {}
    store_filter = ""
    if store_ids:
        params["store_ids"] = store_ids

    candidates: list[tuple[str, str, str, str]] = [
        (
            "internal",
            "sales_records",
            "internal",
            "stores",
        ),
        (
            "internal",
            "sales_operational",
            "internal",
            "stores_operational",
        ),
        (
            "internal",
            "sales_operational_staging",
            "internal",
            "stores_operational_staging",
        ),
    ]

    for sales_schema, sales_table, stores_schema, stores_table in candidates:
        if not _table_exists(engine, sales_schema, sales_table):
            continue
        if not _table_exists(engine, stores_schema, stores_table):
            continue

        if sales_table == "sales_records":
            sales_date_column = "sr.sales_date"
            open_column = "sr.is_open"
            promo_column = "sr.promo"
            school_holiday_column = "sr.school_holiday"
            state_holiday_column = "COALESCE(sr.state_holiday, '0')"
            sales_value_column = "sr.sales"
            customers_column = "sr.customers"
            stores_join = "internal.stores s ON s.store_id = sr.store_id"
            store_type_column = "s.store_type"
            assortment_column = "s.assortment"
            competition_distance_column = "s.competition_distance"
            promo2_column = "s.promo2"
            if store_ids:
                store_filter = "AND sr.store_id = ANY(:store_ids)"
        else:
            sales_date_column = "sr.date"
            open_column = "(sr.open = 1)"
            promo_column = "(sr.promo = 1)"
            school_holiday_column = "(sr.school_holiday = 1)"
            state_holiday_column = "COALESCE(sr.state_holiday, '0')"
            sales_value_column = "sr.sales"
            customers_column = "sr.customers"
            stores_join = f"{stores_schema}.{stores_table} s ON s.store_id = sr.store_id"
            store_type_column = "UPPER(s.store_type)"
            assortment_column = "LOWER(s.assortment)"
            competition_distance_column = "COALESCE(s.competition_distance, 0)"
            promo2_column = "(COALESCE(s.promo2, 0) = 1)"
            if store_ids:
                store_filter = "AND sr.store_id = ANY(:store_ids)"

        query = text(
            f"""
            SELECT
                sr.store_id,
                {sales_date_column} AS sales_date,
                {sales_value_column} AS sales,
                {customers_column} AS customers,
                {open_column} AS is_open,
                {promo_column} AS promo,
                {state_holiday_column} AS state_holiday,
                {school_holiday_column} AS school_holiday,
                {store_type_column} AS store_type,
                {assortment_column} AS assortment,
                {competition_distance_column} AS competition_distance,
                {promo2_column} AS promo2
            FROM {sales_schema}.{sales_table} sr
            JOIN {stores_join}
            WHERE 1=1
              {store_filter}
            ORDER BY sr.store_id, {sales_date_column}
            """
        )

        df = pd.read_sql(query, engine, params=params, parse_dates=["sales_date"])
        if not df.empty:
            df["store_type"] = df["store_type"].astype(str).str.upper()
            df["assortment"] = df["assortment"].astype(str).str.lower()
            return df

    raise ValueError(
        "No prepared sales dataset was found in the approved database tables. "
        "Run ingestion first and ensure operational or core tables are populated."
    )


def _evaluate_store(store_df: pd.DataFrame, horizon_days: int) -> dict[str, float] | None:
    if len(store_df) < max(60, horizon_days + 14):
        return None

    holdout_days = min(14, max(7, horizon_days // 3))
    train_df = store_df.iloc[:-holdout_days].copy()
    test_df = store_df.iloc[-holdout_days:].copy()
    if train_df.empty or test_df.empty:
        return None

    forecaster = BaselineForecaster(window_days=28)
    forecaster.fit(train_df)
    return forecaster.evaluate(test_df)


def _build_store_forecast(store_df: pd.DataFrame, horizon_days: int) -> pd.DataFrame:
    forecaster = BaselineForecaster(window_days=28)
    forecaster.fit(store_df)
    forecast_df = forecaster.predict(horizon_days=horizon_days, include_ci=True)
    forecast_df["store_id"] = int(store_df["store_id"].iloc[0])
    return forecast_df


def publish_baseline_forecasts_from_database(
    database_url: str,
    store_ids: list[int] | None = None,
    horizon_weeks: int = 6,
    min_history_days: int = 60,
    triggered_by: str | None = None,
) -> dict[str, Any]:
    sync_url = _to_sync_database_url(database_url)
    engine = create_engine(sync_url, future=True)
    sales_df = _load_prepared_sales(engine, store_ids=store_ids)
    horizon_days = horizon_weeks * 7

    requested_store_ids = (
        sorted(store_ids) if store_ids else sorted(int(value) for value in sales_df["store_id"].unique())
    )

    forecast_frames: list[pd.DataFrame] = []
    warnings: list[dict[str, Any]] = []
    evaluation_metrics: list[dict[str, float]] = []

    for store_id in requested_store_ids:
        store_df = sales_df[sales_df["store_id"] == store_id].copy()
        store_df = store_df.sort_values("sales_date")

        if len(store_df) < min_history_days:
            warnings.append(
                {
                    "store_id": store_id,
                    "warning_type": "insufficient_history",
                    "days_of_history": len(store_df),
                    "warning_message": (
                        f"Store {store_id} has only {len(store_df)} days of history; "
                        f"minimum {min_history_days} required"
                    ),
                }
            )
            continue

        metrics = _evaluate_store(store_df, horizon_days=horizon_days)
        if metrics:
            evaluation_metrics.append(metrics)

        forecast_frames.append(_build_store_forecast(store_df, horizon_days=horizon_days))

    if not forecast_frames:
        raise ValueError("No stores had enough prepared history to generate demo forecasts")

    published_at = datetime.now(timezone.utc)
    model_name = f"baseline-mvp-{published_at.strftime('%Y%m%d%H%M%S')}"

    with engine.begin() as connection:
        training_run_id = connection.execute(
            text(
                """
                INSERT INTO ml.training_runs (
                    run_name,
                    model_type,
                    status,
                    dataset_version,
                    feature_version,
                    parameters,
                    started_at,
                    completed_at
                )
                VALUES (
                    :run_name,
                    'baseline',
                    'completed',
                    'rossmann-prepared',
                    'baseline-v1',
                    CAST(:parameters AS jsonb),
                    :started_at,
                    :completed_at
                )
                RETURNING run_id
                """
            ),
            {
                "run_name": model_name,
                "parameters": json.dumps(
                    {
                        "horizon_weeks": horizon_weeks,
                        "min_history_days": min_history_days,
                        "store_count": len(requested_store_ids),
                    }
                ),
                "started_at": published_at,
                "completed_at": published_at,
            },
        ).scalar_one()

        connection.execute(
            text(
                """
                UPDATE ml.model_registry
                SET is_active = false
                WHERE model_type = 'baseline'
                  AND is_active = true
                """
            )
        )

        model_id = connection.execute(
            text(
                """
                INSERT INTO ml.model_registry (
                    model_name,
                    model_type,
                    training_run_id,
                    is_active,
                    version,
                    metadata,
                    published_at
                )
                VALUES (
                    :model_name,
                    'baseline',
                    :training_run_id,
                    true,
                    :version,
                    CAST(:metadata AS jsonb),
                    :published_at
                )
                RETURNING model_id
                """
            ),
            {
                "model_name": model_name,
                "training_run_id": str(training_run_id),
                "version": published_at.strftime("%Y.%m.%d"),
                "metadata": json.dumps(
                    {
                        "publication_type": "demo_mvp",
                        "stores_requested": requested_store_ids,
                        "triggered_by": triggered_by,
                    }
                ),
                "published_at": published_at,
            },
        ).scalar_one()

        if evaluation_metrics:
            avg_mape = sum(metric["mape"] for metric in evaluation_metrics) / len(evaluation_metrics)
            avg_rmse = sum(metric["rmse"] for metric in evaluation_metrics) / len(evaluation_metrics)
            avg_mae = sum(metric["mae"] for metric in evaluation_metrics) / len(evaluation_metrics)
            connection.execute(
                text(
                    """
                    INSERT INTO ml.model_evaluations (
                        model_id,
                        evaluation_period_start,
                        evaluation_period_end,
                        mape,
                        rmse,
                        mae,
                        eval_metrics,
                        evaluation_date
                    )
                    VALUES (
                        :model_id,
                        :evaluation_period_start,
                        :evaluation_period_end,
                        :mape,
                        :rmse,
                        :mae,
                        CAST(:eval_metrics AS jsonb),
                        :evaluation_date
                    )
                    """
                ),
                {
                    "model_id": str(model_id),
                    "evaluation_period_start": sales_df["sales_date"].min().date(),
                    "evaluation_period_end": sales_df["sales_date"].max().date(),
                    "mape": avg_mape,
                    "rmse": avg_rmse,
                    "mae": avg_mae,
                    "eval_metrics": json.dumps({"store_level_count": len(evaluation_metrics)}),
                    "evaluation_date": published_at,
                },
            )

        combined_forecasts = pd.concat(forecast_frames, ignore_index=True)

        forecast_job_id = connection.execute(
            text(
                """
                INSERT INTO ml.forecast_metadata (
                    model_id,
                    forecast_horizon_days,
                    forecast_start_date,
                    forecast_end_date,
                    stores_included,
                    total_forecasts_generated,
                    job_status,
                    started_at,
                    completed_at
                )
                VALUES (
                    :model_id,
                    :forecast_horizon_days,
                    :forecast_start_date,
                    :forecast_end_date,
                    :stores_included,
                    :total_forecasts_generated,
                    'completed',
                    :started_at,
                    :completed_at
                )
                RETURNING forecast_job_id
                """
            ),
            {
                "model_id": str(model_id),
                "forecast_horizon_days": horizon_days,
                "forecast_start_date": combined_forecasts["forecast_date"].min(),
                "forecast_end_date": combined_forecasts["forecast_date"].max(),
                "stores_included": requested_store_ids,
                "total_forecasts_generated": len(combined_forecasts),
                "started_at": published_at,
                "completed_at": published_at,
            },
        ).scalar_one()

        connection.execute(
            text(
                """
                UPDATE ml.low_data_warnings
                SET is_active = false
                WHERE store_id = ANY(:store_ids)
                """
            ),
            {"store_ids": requested_store_ids},
        )

        for warning in warnings:
            connection.execute(
                text(
                    """
                    INSERT INTO ml.low_data_warnings (
                        store_id,
                        warning_type,
                        days_of_history,
                        warning_message,
                        is_active
                    )
                    VALUES (
                        :store_id,
                        :warning_type,
                        :days_of_history,
                        :warning_message,
                        true
                    )
                    """
                ),
                warning,
            )

        for row in combined_forecasts.itertuples(index=False):
            connection.execute(
                text(
                    """
                    INSERT INTO ml.forecast_results (
                        model_id,
                        store_id,
                        forecast_date,
                        predicted_sales,
                        lower_bound,
                        upper_bound,
                        confidence_level,
                        is_published,
                        generation_timestamp
                    )
                    VALUES (
                        :model_id,
                        :store_id,
                        :forecast_date,
                        :predicted_sales,
                        :lower_bound,
                        :upper_bound,
                        95.0,
                        true,
                        :generation_timestamp
                    )
                    """
                ),
                {
                    "model_id": str(model_id),
                    "store_id": int(row.store_id),
                    "forecast_date": row.forecast_date,
                    "predicted_sales": float(row.predicted_sales),
                    "lower_bound": float(row.lower_bound) if pd.notna(row.lower_bound) else None,
                    "upper_bound": float(row.upper_bound) if pd.notna(row.upper_bound) else None,
                    "generation_timestamp": published_at,
                },
            )

    return {
        "forecast_job_id": str(forecast_job_id),
        "model_id": str(model_id),
        "job_status": "completed",
        "stores_included": requested_store_ids,
        "total_forecasts_generated": int(len(combined_forecasts)),
        "warnings_created": len(warnings),
    }


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Publish baseline demo forecasts")
    parser.add_argument("--database-url", default=None)
    parser.add_argument("--store-id", action="append", type=int, dest="store_ids")
    parser.add_argument("--horizon-weeks", type=int, default=6)
    parser.add_argument("--min-history-days", type=int, default=60)
    parser.add_argument("--triggered-by", default="demo-operator")
    return parser.parse_args()


def main() -> None:
    args = _parse_args()
    database_url = args.database_url
    if not database_url:
        raise SystemExit("--database-url is required")

    result = publish_baseline_forecasts_from_database(
        database_url=database_url,
        store_ids=args.store_ids,
        horizon_weeks=args.horizon_weeks,
        min_history_days=args.min_history_days,
        triggered_by=args.triggered_by,
    )
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
