"""Build weekly and monthly KPI marts from daily KPI data."""

from __future__ import annotations

from datetime import date
from typing import Any

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession


def _build_daily_filters(
    *,
    start_date: date | None,
    end_date: date | None,
    store_id: int | None,
) -> tuple[str, dict[str, Any]]:
    filters: list[str] = []
    params: dict[str, Any] = {}

    if start_date is not None:
        filters.append("kd.kpi_date >= :start_date")
        params["start_date"] = start_date
    if end_date is not None:
        filters.append("kd.kpi_date <= :end_date")
        params["end_date"] = end_date
    if store_id is not None:
        filters.append("kd.store_id = :store_id")
        params["store_id"] = store_id

    return (" AND " + " AND ".join(filters)) if filters else "", params


async def build_weekly_kpi(
    db_session: AsyncSession,
    start_date: date | None = None,
    end_date: date | None = None,
    store_id: int | None = None,
) -> dict[str, Any]:
    """Populate `analytics.kpi_weekly` from `analytics.kpi_daily`."""

    where_clause, params = _build_daily_filters(
        start_date=start_date,
        end_date=end_date,
        store_id=store_id,
    )

    result = await db_session.execute(
        text(
            f"""
            WITH weekly_source AS (
                SELECT
                    kd.store_id,
                    date_trunc('week', kd.kpi_date)::date AS week_start_date,
                    (date_trunc('week', kd.kpi_date)::date + interval '6 days')::date AS week_end_date,
                    extract(week from kd.kpi_date)::integer AS iso_week,
                    extract(isoyear from kd.kpi_date)::integer AS year,
                    sum(kd.total_sales)::numeric(14, 2) AS total_sales,
                    sum(kd.total_customers)::integer AS total_customers,
                    sum(kd.transactions)::integer AS total_transactions,
                    round(avg(kd.total_sales)::numeric, 2) AS avg_daily_sales,
                    round(avg(kd.total_customers)::numeric, 2) AS avg_daily_customers,
                    round(avg(kd.transactions)::numeric, 2) AS avg_daily_transactions,
                    sum(case when kd.is_promo_day then 1 else 0 end)::integer AS promo_days_count,
                    sum(case when kd.has_state_holiday or kd.has_school_holiday then 1 else 0 end)::integer AS holiday_days_count,
                    sum(case when kd.is_store_open then 1 else 0 end)::integer AS open_days_count,
                    sum(case when not kd.is_store_open then 1 else 0 end)::integer AS closed_days_count,
                    (array_agg(kd.kpi_date order by kd.total_sales desc, kd.kpi_date asc))[1] AS best_sales_day_date,
                    max(kd.total_sales)::numeric(14, 2) AS best_sales_amount,
                    (array_agg(kd.kpi_date order by kd.total_sales asc, kd.kpi_date asc) filter (where kd.is_store_open))[1] AS worst_sales_day_date,
                    min(kd.total_sales)::numeric(14, 2) filter (where kd.is_store_open) AS worst_sales_amount
                FROM analytics.kpi_daily kd
                WHERE 1 = 1 {where_clause}
                GROUP BY kd.store_id, date_trunc('week', kd.kpi_date)::date
            ),
            upserted AS (
                INSERT INTO analytics.kpi_weekly (
                    store_id,
                    week_start_date,
                    week_end_date,
                    iso_week,
                    year,
                    total_sales,
                    total_customers,
                    total_transactions,
                    avg_daily_sales,
                    avg_daily_customers,
                    avg_daily_transactions,
                    promo_days_count,
                    holiday_days_count,
                    open_days_count,
                    closed_days_count,
                    best_sales_day_date,
                    best_sales_amount,
                    worst_sales_day_date,
                    worst_sales_amount
                )
                SELECT
                    store_id,
                    week_start_date,
                    week_end_date,
                    iso_week,
                    year,
                    total_sales,
                    total_customers,
                    total_transactions,
                    avg_daily_sales,
                    avg_daily_customers,
                    avg_daily_transactions,
                    promo_days_count,
                    holiday_days_count,
                    open_days_count,
                    closed_days_count,
                    best_sales_day_date,
                    best_sales_amount,
                    worst_sales_day_date,
                    worst_sales_amount
                FROM weekly_source
                ON CONFLICT (store_id, week_start_date) DO UPDATE SET
                    week_end_date = EXCLUDED.week_end_date,
                    iso_week = EXCLUDED.iso_week,
                    year = EXCLUDED.year,
                    total_sales = EXCLUDED.total_sales,
                    total_customers = EXCLUDED.total_customers,
                    total_transactions = EXCLUDED.total_transactions,
                    avg_daily_sales = EXCLUDED.avg_daily_sales,
                    avg_daily_customers = EXCLUDED.avg_daily_customers,
                    avg_daily_transactions = EXCLUDED.avg_daily_transactions,
                    promo_days_count = EXCLUDED.promo_days_count,
                    holiday_days_count = EXCLUDED.holiday_days_count,
                    open_days_count = EXCLUDED.open_days_count,
                    closed_days_count = EXCLUDED.closed_days_count,
                    best_sales_day_date = EXCLUDED.best_sales_day_date,
                    best_sales_amount = EXCLUDED.best_sales_amount,
                    worst_sales_day_date = EXCLUDED.worst_sales_day_date,
                    worst_sales_amount = EXCLUDED.worst_sales_amount,
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


async def build_monthly_kpi(
    db_session: AsyncSession,
    start_date: date | None = None,
    end_date: date | None = None,
    store_id: int | None = None,
) -> dict[str, Any]:
    """Populate `analytics.kpi_monthly` from `analytics.kpi_daily`."""

    where_clause, params = _build_daily_filters(
        start_date=start_date,
        end_date=end_date,
        store_id=store_id,
    )

    result = await db_session.execute(
        text(
            f"""
            WITH monthly_source AS (
                SELECT
                    kd.store_id,
                    extract(year from kd.kpi_date)::integer AS year,
                    extract(month from kd.kpi_date)::integer AS month,
                    to_char(kd.kpi_date, 'FMMonth') AS month_name,
                    extract(day from (date_trunc('month', kd.kpi_date) + interval '1 month - 1 day'))::integer AS days_in_month,
                    sum(kd.total_sales)::numeric(14, 2) AS total_sales,
                    sum(kd.total_customers)::integer AS total_customers,
                    sum(kd.transactions)::integer AS total_transactions,
                    round(avg(kd.total_sales)::numeric, 2) AS avg_daily_sales,
                    round(avg(kd.total_customers)::numeric, 2) AS avg_daily_customers,
                    round(avg(kd.transactions)::numeric, 2) AS avg_daily_transactions,
                    sum(case when kd.is_promo_day then 1 else 0 end)::integer AS promo_days_count,
                    sum(case when kd.has_state_holiday or kd.has_school_holiday then 1 else 0 end)::integer AS holiday_days_count,
                    sum(case when kd.is_store_open then 1 else 0 end)::integer AS open_days_count,
                    sum(case when not kd.is_store_open then 1 else 0 end)::integer AS closed_days_count,
                    count(distinct date_trunc('week', kd.kpi_date))::integer AS active_weeks_count,
                    (array_agg(kd.kpi_date order by kd.total_sales desc, kd.kpi_date asc))[1] AS best_sales_day_date,
                    max(kd.total_sales)::numeric(14, 2) AS best_sales_amount,
                    (array_agg(kd.kpi_date order by kd.total_sales asc, kd.kpi_date asc) filter (where kd.is_store_open))[1] AS worst_sales_day_date,
                    min(kd.total_sales)::numeric(14, 2) filter (where kd.is_store_open) AS worst_sales_amount
                FROM analytics.kpi_daily kd
                WHERE 1 = 1 {where_clause}
                GROUP BY
                    kd.store_id,
                    extract(year from kd.kpi_date)::integer,
                    extract(month from kd.kpi_date)::integer,
                    to_char(kd.kpi_date, 'FMMonth'),
                    extract(day from (date_trunc('month', kd.kpi_date) + interval '1 month - 1 day'))::integer
            ),
            monthly_with_growth AS (
                SELECT
                    monthly_source.*,
                    CASE
                        WHEN lag(total_sales) over (partition by store_id order by year, month) > 0 THEN
                            round(
                                (
                                    (total_sales - lag(total_sales) over (partition by store_id order by year, month))
                                    / lag(total_sales) over (partition by store_id order by year, month)
                                ) * 100,
                                2
                            )
                        ELSE NULL
                    END AS mom_sales_growth_pct,
                    CASE
                        WHEN lag(total_customers) over (partition by store_id order by year, month) > 0 THEN
                            round(
                                (
                                    (total_customers - lag(total_customers) over (partition by store_id order by year, month))::numeric
                                    / lag(total_customers) over (partition by store_id order by year, month)
                                ) * 100,
                                2
                            )
                        ELSE NULL
                    END AS mom_customers_growth_pct,
                    CASE
                        WHEN lag(total_sales, 12) over (partition by store_id order by year, month) > 0 THEN
                            round(
                                (
                                    (total_sales - lag(total_sales, 12) over (partition by store_id order by year, month))
                                    / lag(total_sales, 12) over (partition by store_id order by year, month)
                                ) * 100,
                                2
                            )
                        ELSE NULL
                    END AS yoy_sales_growth_pct,
                    CASE
                        WHEN lag(total_customers, 12) over (partition by store_id order by year, month) > 0 THEN
                            round(
                                (
                                    (total_customers - lag(total_customers, 12) over (partition by store_id order by year, month))::numeric
                                    / lag(total_customers, 12) over (partition by store_id order by year, month)
                                ) * 100,
                                2
                            )
                        ELSE NULL
                    END AS yoy_customers_growth_pct
                FROM monthly_source
            ),
            upserted AS (
                INSERT INTO analytics.kpi_monthly (
                    store_id,
                    year,
                    month,
                    month_name,
                    total_sales,
                    total_customers,
                    total_transactions,
                    avg_daily_sales,
                    avg_daily_customers,
                    avg_daily_transactions,
                    days_in_month,
                    promo_days_count,
                    holiday_days_count,
                    open_days_count,
                    closed_days_count,
                    active_weeks_count,
                    best_sales_day_date,
                    best_sales_amount,
                    worst_sales_day_date,
                    worst_sales_amount,
                    mom_sales_growth_pct,
                    mom_customers_growth_pct,
                    yoy_sales_growth_pct,
                    yoy_customers_growth_pct
                )
                SELECT
                    store_id,
                    year,
                    month,
                    month_name,
                    total_sales,
                    total_customers,
                    total_transactions,
                    avg_daily_sales,
                    avg_daily_customers,
                    avg_daily_transactions,
                    days_in_month,
                    promo_days_count,
                    holiday_days_count,
                    open_days_count,
                    closed_days_count,
                    active_weeks_count,
                    best_sales_day_date,
                    best_sales_amount,
                    worst_sales_day_date,
                    worst_sales_amount,
                    mom_sales_growth_pct,
                    mom_customers_growth_pct,
                    yoy_sales_growth_pct,
                    yoy_customers_growth_pct
                FROM monthly_with_growth
                ON CONFLICT (store_id, year, month) DO UPDATE SET
                    month_name = EXCLUDED.month_name,
                    total_sales = EXCLUDED.total_sales,
                    total_customers = EXCLUDED.total_customers,
                    total_transactions = EXCLUDED.total_transactions,
                    avg_daily_sales = EXCLUDED.avg_daily_sales,
                    avg_daily_customers = EXCLUDED.avg_daily_customers,
                    avg_daily_transactions = EXCLUDED.avg_daily_transactions,
                    days_in_month = EXCLUDED.days_in_month,
                    promo_days_count = EXCLUDED.promo_days_count,
                    holiday_days_count = EXCLUDED.holiday_days_count,
                    open_days_count = EXCLUDED.open_days_count,
                    closed_days_count = EXCLUDED.closed_days_count,
                    active_weeks_count = EXCLUDED.active_weeks_count,
                    best_sales_day_date = EXCLUDED.best_sales_day_date,
                    best_sales_amount = EXCLUDED.best_sales_amount,
                    worst_sales_day_date = EXCLUDED.worst_sales_day_date,
                    worst_sales_amount = EXCLUDED.worst_sales_amount,
                    mom_sales_growth_pct = EXCLUDED.mom_sales_growth_pct,
                    mom_customers_growth_pct = EXCLUDED.mom_customers_growth_pct,
                    yoy_sales_growth_pct = EXCLUDED.yoy_sales_growth_pct,
                    yoy_customers_growth_pct = EXCLUDED.yoy_customers_growth_pct,
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
