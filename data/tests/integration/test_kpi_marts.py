"""Integration coverage for KPI mart building."""

from __future__ import annotations

from datetime import date, timedelta

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from src.marts.build_daily_kpi import build_daily_kpi
from src.marts.build_periodic_kpis import build_monthly_kpi, build_weekly_kpi
from src.marts.refresh_kpis import refresh_kpis

pytestmark = pytest.mark.asyncio


async def _prepare_store_sales_data(db_session: AsyncSession, store_id: int) -> None:
    for statement in (
        "DELETE FROM analytics.kpi_monthly WHERE store_id = :store_id",
        "DELETE FROM analytics.kpi_weekly WHERE store_id = :store_id",
        "DELETE FROM analytics.kpi_daily WHERE store_id = :store_id",
        "DELETE FROM internal.sales_records WHERE store_id = :store_id",
        "DELETE FROM internal.stores WHERE store_id = :store_id",
    ):
        await db_session.execute(text(statement), {"store_id": store_id})
    await db_session.execute(
        text(
            """
            INSERT INTO internal.stores (
                store_id,
                store_type,
                assortment,
                competition_distance,
                promo2
            )
            VALUES (:store_id, 'A', 'a', 1500, false)
            """
        ),
        {"store_id": store_id},
    )

    sales_rows = [
        {
            "store_id": store_id,
            "sales_date": date(2023, 7, 3) + timedelta(days=offset),
            "day_of_week": offset + 1,
            "sales": 1000 + (offset * 100),
            "customers": 100 + (offset * 10),
            "is_open": True,
            "promo": offset in {1, 4},
            "state_holiday": "a" if offset == 5 else "0",
            "school_holiday": offset == 2,
        }
        for offset in range(7)
    ]
    for row in sales_rows:
        await db_session.execute(
            text(
                """
                INSERT INTO internal.sales_records (
                    store_id,
                    sales_date,
                    day_of_week,
                    sales,
                    customers,
                    is_open,
                    promo,
                    state_holiday,
                    school_holiday
                )
                VALUES (
                    :store_id,
                    :sales_date,
                    :day_of_week,
                    :sales,
                    :customers,
                    :is_open,
                    :promo,
                    :state_holiday,
                    :school_holiday
                )
                """
            ),
            row,
        )
    await db_session.commit()


async def test_daily_kpi_build_creates_expected_rows(db_session: AsyncSession) -> None:
    store_id = 9101
    await _prepare_store_sales_data(db_session, store_id)

    result = await build_daily_kpi(
        db_session=db_session,
        start_date=date(2023, 7, 3),
        end_date=date(2023, 7, 9),
        store_id=store_id,
    )

    assert result["records_affected"] == 7

    row = (
        await db_session.execute(
            text(
                """
                SELECT
                    store_id,
                    kpi_date,
                    total_sales,
                    total_customers,
                    transactions,
                    is_promo_day,
                    has_school_holiday,
                    has_state_holiday,
                    is_store_open
                FROM analytics.kpi_daily
                WHERE store_id = :store_id AND kpi_date = :kpi_date
                """
            ),
            {"store_id": store_id, "kpi_date": date(2023, 7, 5)},
        )
    ).fetchone()

    assert row is not None
    assert row[0] == store_id
    assert row[1] == date(2023, 7, 5)
    assert float(row[2]) == 1200.0
    assert row[3] == 120
    assert row[4] == 1
    assert row[5] is False
    assert row[6] is True
    assert row[7] is False
    assert row[8] is True


async def test_weekly_kpi_build_aggregates_daily_rows(db_session: AsyncSession) -> None:
    store_id = 9102
    await _prepare_store_sales_data(db_session, store_id)
    await build_daily_kpi(db_session=db_session, store_id=store_id)

    result = await build_weekly_kpi(db_session=db_session, store_id=store_id)
    assert result["records_affected"] == 1

    row = (
        await db_session.execute(
            text(
                """
                SELECT
                    week_start_date,
                    week_end_date,
                    total_sales,
                    total_customers,
                    total_transactions,
                    promo_days_count,
                    holiday_days_count,
                    open_days_count
                FROM analytics.kpi_weekly
                WHERE store_id = :store_id
                """
            ),
            {"store_id": store_id},
        )
    ).fetchone()

    assert row is not None
    assert row[0] == date(2023, 7, 3)
    assert row[1] == date(2023, 7, 9)
    assert float(row[2]) == 9100.0
    assert row[3] == 910
    assert row[4] == 7
    assert row[5] == 2
    assert row[6] == 2
    assert row[7] == 7


async def test_monthly_kpi_build_aggregates_month_and_refresh_orchestrates(
    db_session: AsyncSession,
) -> None:
    store_id = 9103
    await _prepare_store_sales_data(db_session, store_id)

    refresh_result = await refresh_kpis(
        db_session=db_session,
        start_date=date(2023, 7, 3),
        end_date=date(2023, 7, 9),
        store_id=store_id,
    )

    assert refresh_result.success is True
    assert refresh_result.daily_result["records_affected"] == 7
    assert refresh_result.weekly_result["records_affected"] == 1
    assert refresh_result.monthly_result["records_affected"] == 1

    row = (
        await db_session.execute(
            text(
                """
                SELECT
                    year,
                    month,
                    month_name,
                    total_sales,
                    total_customers,
                    total_transactions,
                    promo_days_count,
                    holiday_days_count,
                    open_days_count,
                    active_weeks_count,
                    mom_sales_growth_pct,
                    yoy_sales_growth_pct
                FROM analytics.kpi_monthly
                WHERE store_id = :store_id AND year = 2023 AND month = 7
                """
            ),
            {"store_id": store_id},
        )
    ).fetchone()

    assert row is not None
    assert row[0] == 2023
    assert row[1] == 7
    assert row[2] == "July"
    assert float(row[3]) == 9100.0
    assert row[4] == 910
    assert row[5] == 7
    assert row[6] == 2
    assert row[7] == 2
    assert row[8] == 7
    assert row[9] == 1
    assert row[10] is None
    assert row[11] is None
