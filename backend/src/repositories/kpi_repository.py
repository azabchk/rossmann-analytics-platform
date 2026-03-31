"""KPI repository for governed access to analytical marts."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from sqlalchemy import bindparam, text

from src.repositories.base import BaseRepository


@dataclass(slots=True)
class DailyKPI:
    kpi_id: int
    store_id: int
    kpi_date: date
    day_of_week: int
    total_sales: float
    total_customers: int
    transactions: int
    avg_sales_per_transaction: float | None
    sales_per_customer: float | None
    is_promo_day: bool
    has_state_holiday: bool
    has_school_holiday: bool
    is_store_open: bool


@dataclass(slots=True)
class WeeklyKPI:
    kpi_id: int
    store_id: int
    week_start_date: date
    week_end_date: date
    iso_week: int
    year: int
    total_sales: float
    total_customers: int
    total_transactions: int
    avg_daily_sales: float | None
    avg_daily_customers: float | None
    avg_daily_transactions: float | None
    promo_days_count: int
    holiday_days_count: int
    open_days_count: int
    closed_days_count: int


@dataclass(slots=True)
class MonthlyKPI:
    kpi_id: int
    store_id: int
    year: int
    month: int
    month_name: str
    total_sales: float
    total_customers: int
    total_transactions: int
    avg_daily_sales: float | None
    avg_daily_customers: float | None
    avg_daily_transactions: float | None
    days_in_month: int
    promo_days_count: int
    holiday_days_count: int
    open_days_count: int
    closed_days_count: int
    active_weeks_count: int
    mom_sales_growth_pct: float | None
    mom_customers_growth_pct: float | None
    yoy_sales_growth_pct: float | None
    yoy_customers_growth_pct: float | None


@dataclass(slots=True)
class KPISummary:
    total_records: int
    total_sales: float
    total_customers: int
    avg_daily_sales: float
    promo_days: int
    holiday_days: int


class KPIRepository(BaseRepository):
    """Repository for analytics mart retrieval."""

    async def get_daily_kpis(
        self,
        store_ids: list[int],
        start_date: date | None = None,
        end_date: date | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[DailyKPI]:
        if not store_ids:
            return []

        filters = ["store_id IN :store_ids"]
        params: dict[str, object] = {
            "store_ids": store_ids,
            "limit": limit,
            "offset": offset,
        }
        if start_date is not None:
            filters.append("kpi_date >= :start_date")
            params["start_date"] = start_date
        if end_date is not None:
            filters.append("kpi_date <= :end_date")
            params["end_date"] = end_date

        query = (
            text(
                f"""
                SELECT
                    kpi_id,
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
                FROM analytics.kpi_daily
                WHERE {' AND '.join(filters)}
                ORDER BY kpi_date DESC, store_id ASC
                LIMIT :limit OFFSET :offset
                """
            )
            .bindparams(bindparam("store_ids", expanding=True))
        )
        result = await self.session.execute(query, params)
        return [
            DailyKPI(
                kpi_id=row[0],
                store_id=row[1],
                kpi_date=row[2],
                day_of_week=row[3],
                total_sales=float(row[4]),
                total_customers=row[5],
                transactions=row[6],
                avg_sales_per_transaction=float(row[7]) if row[7] is not None else None,
                sales_per_customer=float(row[8]) if row[8] is not None else None,
                is_promo_day=row[9],
                has_state_holiday=row[10],
                has_school_holiday=row[11],
                is_store_open=row[12],
            )
            for row in result.fetchall()
        ]

    async def count_daily_kpis(
        self,
        store_ids: list[int],
        start_date: date | None = None,
        end_date: date | None = None,
    ) -> int:
        return await self._count_rows(
            table_name="analytics.kpi_daily",
            date_column="kpi_date",
            store_ids=store_ids,
            start_date=start_date,
            end_date=end_date,
        )

    async def get_daily_summary(
        self,
        store_ids: list[int],
        start_date: date | None = None,
        end_date: date | None = None,
    ) -> KPISummary | None:
        if not store_ids:
            return None

        filters = ["store_id IN :store_ids"]
        params: dict[str, object] = {"store_ids": store_ids}
        if start_date is not None:
            filters.append("kpi_date >= :start_date")
            params["start_date"] = start_date
        if end_date is not None:
            filters.append("kpi_date <= :end_date")
            params["end_date"] = end_date

        query = (
            text(
                f"""
                SELECT
                    count(*)::integer AS total_records,
                    coalesce(sum(total_sales), 0)::numeric AS total_sales,
                    coalesce(sum(total_customers), 0)::integer AS total_customers,
                    coalesce(avg(total_sales), 0)::numeric AS avg_daily_sales,
                    coalesce(sum(case when is_promo_day then 1 else 0 end), 0)::integer AS promo_days,
                    coalesce(sum(case when has_state_holiday or has_school_holiday then 1 else 0 end), 0)::integer AS holiday_days
                FROM analytics.kpi_daily
                WHERE {' AND '.join(filters)}
                """
            )
            .bindparams(bindparam("store_ids", expanding=True))
        )
        result = await self.session.execute(query, params)
        row = result.fetchone()
        if row is None:
            return None
        return KPISummary(
            total_records=row[0],
            total_sales=float(row[1]) if row[1] is not None else 0.0,
            total_customers=row[2],
            avg_daily_sales=float(row[3]) if row[3] is not None else 0.0,
            promo_days=row[4],
            holiday_days=row[5],
        )

    async def get_weekly_kpis(
        self,
        store_ids: list[int],
        start_date: date | None = None,
        end_date: date | None = None,
        limit: int = 52,
        offset: int = 0,
    ) -> list[WeeklyKPI]:
        if not store_ids:
            return []

        filters = ["store_id IN :store_ids"]
        params: dict[str, object] = {
            "store_ids": store_ids,
            "limit": limit,
            "offset": offset,
        }
        if start_date is not None:
            filters.append("week_start_date >= :start_date")
            params["start_date"] = start_date
        if end_date is not None:
            filters.append("week_end_date <= :end_date")
            params["end_date"] = end_date

        query = (
            text(
                f"""
                SELECT
                    kpi_id,
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
                    closed_days_count
                FROM analytics.kpi_weekly
                WHERE {' AND '.join(filters)}
                ORDER BY week_start_date DESC, store_id ASC
                LIMIT :limit OFFSET :offset
                """
            )
            .bindparams(bindparam("store_ids", expanding=True))
        )
        result = await self.session.execute(query, params)
        return [
            WeeklyKPI(
                kpi_id=row[0],
                store_id=row[1],
                week_start_date=row[2],
                week_end_date=row[3],
                iso_week=row[4],
                year=row[5],
                total_sales=float(row[6]),
                total_customers=row[7],
                total_transactions=row[8],
                avg_daily_sales=float(row[9]) if row[9] is not None else None,
                avg_daily_customers=float(row[10]) if row[10] is not None else None,
                avg_daily_transactions=float(row[11]) if row[11] is not None else None,
                promo_days_count=row[12],
                holiday_days_count=row[13],
                open_days_count=row[14],
                closed_days_count=row[15],
            )
            for row in result.fetchall()
        ]

    async def count_weekly_kpis(
        self,
        store_ids: list[int],
        start_date: date | None = None,
        end_date: date | None = None,
    ) -> int:
        return await self._count_rows(
            table_name="analytics.kpi_weekly",
            date_column="week_start_date",
            store_ids=store_ids,
            start_date=start_date,
            end_date=end_date,
        )

    async def get_monthly_kpis(
        self,
        store_ids: list[int],
        year: int | None = None,
        limit: int = 12,
        offset: int = 0,
    ) -> list[MonthlyKPI]:
        if not store_ids:
            return []

        filters = ["store_id IN :store_ids"]
        params: dict[str, object] = {
            "store_ids": store_ids,
            "limit": limit,
            "offset": offset,
        }
        if year is not None:
            filters.append("year = :year")
            params["year"] = year

        query = (
            text(
                f"""
                SELECT
                    kpi_id,
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
                    mom_sales_growth_pct,
                    mom_customers_growth_pct,
                    yoy_sales_growth_pct,
                    yoy_customers_growth_pct
                FROM analytics.kpi_monthly
                WHERE {' AND '.join(filters)}
                ORDER BY year DESC, month DESC, store_id ASC
                LIMIT :limit OFFSET :offset
                """
            )
            .bindparams(bindparam("store_ids", expanding=True))
        )
        result = await self.session.execute(query, params)
        return [
            MonthlyKPI(
                kpi_id=row[0],
                store_id=row[1],
                year=row[2],
                month=row[3],
                month_name=row[4],
                total_sales=float(row[5]),
                total_customers=row[6],
                total_transactions=row[7],
                avg_daily_sales=float(row[8]) if row[8] is not None else None,
                avg_daily_customers=float(row[9]) if row[9] is not None else None,
                avg_daily_transactions=float(row[10]) if row[10] is not None else None,
                days_in_month=row[11],
                promo_days_count=row[12],
                holiday_days_count=row[13],
                open_days_count=row[14],
                closed_days_count=row[15],
                active_weeks_count=row[16],
                mom_sales_growth_pct=float(row[17]) if row[17] is not None else None,
                mom_customers_growth_pct=float(row[18]) if row[18] is not None else None,
                yoy_sales_growth_pct=float(row[19]) if row[19] is not None else None,
                yoy_customers_growth_pct=float(row[20]) if row[20] is not None else None,
            )
            for row in result.fetchall()
        ]

    async def count_monthly_kpis(
        self,
        store_ids: list[int],
        year: int | None = None,
    ) -> int:
        if not store_ids:
            return 0

        filters = ["store_id IN :store_ids"]
        params: dict[str, object] = {"store_ids": store_ids}
        if year is not None:
            filters.append("year = :year")
            params["year"] = year

        query = (
            text(
                f"""
                SELECT count(*)::integer
                FROM analytics.kpi_monthly
                WHERE {' AND '.join(filters)}
                """
            )
            .bindparams(bindparam("store_ids", expanding=True))
        )
        result = await self.session.execute(query, params)
        return int(result.scalar() or 0)

    async def _count_rows(
        self,
        *,
        table_name: str,
        date_column: str,
        store_ids: list[int],
        start_date: date | None,
        end_date: date | None,
    ) -> int:
        if not store_ids:
            return 0

        filters = ["store_id IN :store_ids"]
        params: dict[str, object] = {"store_ids": store_ids}
        if start_date is not None:
            filters.append(f"{date_column} >= :start_date")
            params["start_date"] = start_date
        if end_date is not None:
            filters.append(f"{date_column} <= :end_date")
            params["end_date"] = end_date

        query = (
            text(
                f"""
                SELECT count(*)::integer
                FROM {table_name}
                WHERE {' AND '.join(filters)}
                """
            )
            .bindparams(bindparam("store_ids", expanding=True))
        )
        result = await self.session.execute(query, params)
        return int(result.scalar() or 0)
