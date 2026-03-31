"""Sales repository for historical sales retrieval."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from sqlalchemy import bindparam, text

from src.repositories.base import BaseRepository


@dataclass(slots=True)
class SalesRecord:
    sales_record_id: int
    store_id: int
    sales_date: date
    day_of_week: int
    sales: int
    customers: int | None
    is_open: bool
    promo: bool
    state_holiday: str | None
    school_holiday: bool


@dataclass(slots=True)
class SalesSummary:
    total_sales: int
    total_customers: int
    total_transactions: int
    avg_daily_sales: float
    avg_daily_customers: float
    promo_days: int
    holiday_days: int


class SalesRepository(BaseRepository):
    """Repository for operational historical sales queries."""

    async def get_sales_records(
        self,
        store_ids: list[int],
        start_date: date | None = None,
        end_date: date | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[SalesRecord]:
        if not store_ids:
            return []

        filters = ["store_id IN :store_ids"]
        params: dict[str, object] = {
            "store_ids": store_ids,
            "limit": limit,
            "offset": offset,
        }
        if start_date is not None:
            filters.append("sales_date >= :start_date")
            params["start_date"] = start_date
        if end_date is not None:
            filters.append("sales_date <= :end_date")
            params["end_date"] = end_date

        query = (
            text(
                f"""
                SELECT
                    sales_record_id,
                    store_id,
                    sales_date,
                    EXTRACT(ISODOW FROM sales_date)::integer AS day_of_week,
                    sales,
                    customers,
                    is_open,
                    promo,
                    state_holiday,
                    school_holiday
                FROM internal.sales_records
                WHERE {' AND '.join(filters)}
                ORDER BY sales_date DESC, store_id ASC
                LIMIT :limit OFFSET :offset
                """
            )
            .bindparams(bindparam("store_ids", expanding=True))
        )

        result = await self.session.execute(query, params)
        return [
            SalesRecord(
                sales_record_id=row[0],
                store_id=row[1],
                sales_date=row[2],
                day_of_week=row[3],
                sales=row[4],
                customers=row[5],
                is_open=row[6],
                promo=row[7],
                state_holiday=row[8],
                school_holiday=row[9],
            )
            for row in result.fetchall()
        ]

    async def count_sales_records(
        self,
        store_ids: list[int],
        start_date: date | None = None,
        end_date: date | None = None,
    ) -> int:
        if not store_ids:
            return 0

        filters = ["store_id IN :store_ids"]
        params: dict[str, object] = {"store_ids": store_ids}
        if start_date is not None:
            filters.append("sales_date >= :start_date")
            params["start_date"] = start_date
        if end_date is not None:
            filters.append("sales_date <= :end_date")
            params["end_date"] = end_date

        query = (
            text(
                f"""
                SELECT count(*)::integer
                FROM internal.sales_records
                WHERE {' AND '.join(filters)}
                """
            )
            .bindparams(bindparam("store_ids", expanding=True))
        )
        result = await self.session.execute(query, params)
        return int(result.scalar() or 0)

    async def get_sales_summary(
        self,
        store_ids: list[int],
        start_date: date | None = None,
        end_date: date | None = None,
    ) -> SalesSummary | None:
        if not store_ids:
            return None

        filters = ["store_id IN :store_ids"]
        params: dict[str, object] = {"store_ids": store_ids}
        if start_date is not None:
            filters.append("sales_date >= :start_date")
            params["start_date"] = start_date
        if end_date is not None:
            filters.append("sales_date <= :end_date")
            params["end_date"] = end_date

        query = (
            text(
                f"""
                SELECT
                    coalesce(sum(sales), 0)::integer AS total_sales,
                    coalesce(sum(coalesce(customers, 0)), 0)::integer AS total_customers,
                    coalesce(count(*) filter (where is_open), 0)::integer AS total_transactions,
                    coalesce(avg(sales), 0)::numeric AS avg_daily_sales,
                    coalesce(avg(coalesce(customers, 0)), 0)::numeric AS avg_daily_customers,
                    coalesce(sum(case when promo then 1 else 0 end), 0)::integer AS promo_days,
                    coalesce(sum(case when coalesce(state_holiday, '0') <> '0' or school_holiday then 1 else 0 end), 0)::integer AS holiday_days
                FROM internal.sales_records
                WHERE {' AND '.join(filters)}
                """
            )
            .bindparams(bindparam("store_ids", expanding=True))
        )
        result = await self.session.execute(query, params)
        row = result.fetchone()
        if row is None:
            return None
        return SalesSummary(
            total_sales=row[0],
            total_customers=row[1],
            total_transactions=row[2],
            avg_daily_sales=float(row[3]) if row[3] is not None else 0.0,
            avg_daily_customers=float(row[4]) if row[4] is not None else 0.0,
            promo_days=row[5],
            holiday_days=row[6],
        )
