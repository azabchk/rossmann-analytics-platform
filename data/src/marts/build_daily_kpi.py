"""Build the daily KPI mart from operational sales records."""

from __future__ import annotations

from datetime import date
from typing import Any

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession


def _build_filters(
    alias: str,
    *,
    start_date: date | None,
    end_date: date | None,
    store_id: int | None,
) -> tuple[str, dict[str, Any]]:
    filters: list[str] = []
    params: dict[str, Any] = {}

    if start_date is not None:
        filters.append(f"{alias}.sales_date >= :start_date")
        params["start_date"] = start_date
    if end_date is not None:
        filters.append(f"{alias}.sales_date <= :end_date")
        params["end_date"] = end_date
    if store_id is not None:
        filters.append(f"{alias}.store_id = :store_id")
        params["store_id"] = store_id

    return (" AND " + " AND ".join(filters)) if filters else "", params


async def build_daily_kpi(
    db_session: AsyncSession,
    start_date: date | None = None,
    end_date: date | None = None,
    store_id: int | None = None,
) -> dict[str, Any]:
    """Populate `analytics.kpi_daily` from `internal.sales_records`."""

    where_clause, params = _build_filters(
        "sr",
        start_date=start_date,
        end_date=end_date,
        store_id=store_id,
    )

    result = await db_session.execute(
        text(
            f"""
            WITH source_data AS (
                SELECT
                    sr.store_id,
                    sr.sales_date AS kpi_date,
                    coalesce(max(sr.day_of_week), extract(isodow from sr.sales_date)::integer) AS day_of_week,
                    coalesce(sum(sr.sales), 0)::numeric(14, 2) AS total_sales,
                    coalesce(sum(coalesce(sr.customers, 0)), 0)::integer AS total_customers,
                    coalesce(count(*) filter (where sr.is_open), 0)::integer AS transactions,
                    CASE
                        WHEN count(*) filter (where sr.is_open) > 0 THEN
                            round(sum(sr.sales)::numeric / (count(*) filter (where sr.is_open)), 2)
                        ELSE NULL
                    END AS avg_sales_per_transaction,
                    CASE
                        WHEN sum(coalesce(sr.customers, 0)) > 0 THEN
                            round(sum(sr.sales)::numeric / sum(coalesce(sr.customers, 0)), 2)
                        ELSE NULL
                    END AS sales_per_customer,
                    coalesce(bool_or(sr.promo), false) AS is_promo_day,
                    coalesce(bool_or(coalesce(sr.state_holiday, '0') <> '0'), false) AS has_state_holiday,
                    coalesce(bool_or(sr.school_holiday), false) AS has_school_holiday,
                    coalesce(bool_or(sr.is_open), false) AS is_store_open
                FROM internal.sales_records sr
                WHERE 1 = 1 {where_clause}
                GROUP BY sr.store_id, sr.sales_date
            ),
            upserted AS (
                INSERT INTO analytics.kpi_daily (
                    store_id,
                    kpi_date,
                    day_of_week,
                    total_sales,
                    total_customers,
                    transactions,
                    avg_sales_per_transaction,
                    sales_per_customer,
                    is_promo_day,
                    has_state_holiday,
                    has_school_holiday,
                    is_store_open
                )
                SELECT
                    store_id,
                    kpi_date,
                    day_of_week,
                    total_sales,
                    total_customers,
                    transactions,
                    avg_sales_per_transaction,
                    sales_per_customer,
                    is_promo_day,
                    has_state_holiday,
                    has_school_holiday,
                    is_store_open
                FROM source_data
                ON CONFLICT (store_id, kpi_date) DO UPDATE SET
                    day_of_week = EXCLUDED.day_of_week,
                    total_sales = EXCLUDED.total_sales,
                    total_customers = EXCLUDED.total_customers,
                    transactions = EXCLUDED.transactions,
                    avg_sales_per_transaction = EXCLUDED.avg_sales_per_transaction,
                    sales_per_customer = EXCLUDED.sales_per_customer,
                    is_promo_day = EXCLUDED.is_promo_day,
                    has_state_holiday = EXCLUDED.has_state_holiday,
                    has_school_holiday = EXCLUDED.has_school_holiday,
                    is_store_open = EXCLUDED.is_store_open,
                    updated_at = timezone('utc', now())
                RETURNING 1
            )
            SELECT count(*)::integer AS affected_rows FROM upserted
            """
        ),
        params,
    )
    affected_rows = int(result.scalar_one() or 0)
    await db_session.commit()

    return {
        "records_affected": affected_rows,
        "start_date": start_date,
        "end_date": end_date,
        "store_id": store_id,
    }


async def get_daily_kpi_stats(
    db_session: AsyncSession,
    store_id: int | None = None,
    start_date: date | None = None,
    end_date: date | None = None,
) -> dict[str, Any]:
    """Return daily KPI mart statistics for observability and validation."""

    filters: list[str] = []
    params: dict[str, Any] = {}

    if store_id is not None:
        filters.append("store_id = :store_id")
        params["store_id"] = store_id
    if start_date is not None:
        filters.append("kpi_date >= :start_date")
        params["start_date"] = start_date
    if end_date is not None:
        filters.append("kpi_date <= :end_date")
        params["end_date"] = end_date

    where_clause = " AND ".join(filters) if filters else "1 = 1"
    result = await db_session.execute(
        text(
            f"""
            SELECT
                count(*)::integer AS total_records,
                count(*) filter (where is_store_open)::integer AS open_days,
                count(*) filter (where is_promo_day)::integer AS promo_days,
                coalesce(sum(total_sales), 0)::numeric AS total_sales,
                coalesce(sum(total_customers), 0)::integer AS total_customers,
                avg(avg_sales_per_transaction)::numeric AS avg_transaction_value,
                min(total_sales)::numeric AS min_daily_sales,
                max(total_sales)::numeric AS max_daily_sales
            FROM analytics.kpi_daily
            WHERE {where_clause}
            """
        ),
        params,
    )
    row = result.fetchone()

    return {
        "total_records": row[0] if row else 0,
        "open_days": row[1] if row else 0,
        "promo_days": row[2] if row else 0,
        "total_sales": float(row[3]) if row and row[3] is not None else 0.0,
        "total_customers": row[4] if row else 0,
        "avg_transaction_value": float(row[5]) if row and row[5] is not None else 0.0,
        "min_daily_sales": float(row[6]) if row and row[6] is not None else 0.0,
        "max_daily_sales": float(row[7]) if row and row[7] is not None else 0.0,
    }
