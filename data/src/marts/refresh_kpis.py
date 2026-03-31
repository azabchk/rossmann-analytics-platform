"""KPI mart refresh workflow."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import date
from typing import Any

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from .build_daily_kpi import build_daily_kpi
from .build_periodic_kpis import build_monthly_kpi, build_weekly_kpi

logger = logging.getLogger(__name__)


@dataclass(slots=True)
class KpiRefreshResult:
    """Structured result for a KPI refresh run."""

    success: bool
    daily_result: dict[str, Any] = field(default_factory=dict)
    weekly_result: dict[str, Any] = field(default_factory=dict)
    monthly_result: dict[str, Any] = field(default_factory=dict)
    error: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "success": self.success,
            "daily": self.daily_result,
            "weekly": self.weekly_result,
            "monthly": self.monthly_result,
            "error": self.error,
            "summary": {
                "total_records_affected": (
                    self.daily_result.get("records_affected", 0)
                    + self.weekly_result.get("records_affected", 0)
                    + self.monthly_result.get("records_affected", 0)
                )
            },
        }


async def refresh_kpis(
    db_session: AsyncSession,
    start_date: date | None = None,
    end_date: date | None = None,
    store_id: int | None = None,
    skip_periodic: bool = False,
) -> KpiRefreshResult:
    """Refresh daily, weekly, and monthly KPI marts in the correct order."""

    logger.info(
        "Refreshing KPI marts",
        extra={
            "start_date": start_date.isoformat() if start_date else None,
            "end_date": end_date.isoformat() if end_date else None,
            "store_id": store_id,
            "skip_periodic": skip_periodic,
        },
    )

    try:
        daily_result = await build_daily_kpi(
            db_session=db_session,
            start_date=start_date,
            end_date=end_date,
            store_id=store_id,
        )
        weekly_result: dict[str, Any] = {}
        monthly_result: dict[str, Any] = {}

        if not skip_periodic:
            weekly_result = await build_weekly_kpi(
                db_session=db_session,
                start_date=start_date,
                end_date=end_date,
                store_id=store_id,
            )
            monthly_result = await build_monthly_kpi(
                db_session=db_session,
                start_date=start_date,
                end_date=end_date,
                store_id=store_id,
            )

        return KpiRefreshResult(
            success=True,
            daily_result=daily_result,
            weekly_result=weekly_result,
            monthly_result=monthly_result,
        )
    except Exception as exc:
        logger.exception("KPI refresh failed")
        return KpiRefreshResult(success=False, error=f"{type(exc).__name__}: {exc}")


async def get_kpi_refresh_status(db_session: AsyncSession) -> dict[str, Any]:
    """Return freshness and row-count metadata for KPI marts."""

    queries = {
        "daily": text(
            """
            SELECT
                count(*)::integer AS total_records,
                count(distinct store_id)::integer AS unique_stores,
                min(kpi_date) AS earliest_date,
                max(kpi_date) AS latest_date,
                max(updated_at) AS last_refreshed_at
            FROM analytics.kpi_daily
            """
        ),
        "weekly": text(
            """
            SELECT
                count(*)::integer AS total_records,
                count(distinct store_id)::integer AS unique_stores,
                min(week_start_date) AS earliest_date,
                max(week_start_date) AS latest_date,
                max(updated_at) AS last_refreshed_at
            FROM analytics.kpi_weekly
            """
        ),
        "monthly": text(
            """
            SELECT
                count(*)::integer AS total_records,
                count(distinct store_id)::integer AS unique_stores,
                min(make_date(year, month, 1)) AS earliest_date,
                max(make_date(year, month, 1)) AS latest_date,
                max(updated_at) AS last_refreshed_at
            FROM analytics.kpi_monthly
            """
        ),
    }

    status: dict[str, Any] = {}
    for mart_name, query in queries.items():
        result = await db_session.execute(query)
        row = result.fetchone()
        status[mart_name] = {
            "total_records": row[0] if row else 0,
            "unique_stores": row[1] if row else 0,
            "earliest_date": row[2].isoformat() if row and row[2] else None,
            "latest_date": row[3].isoformat() if row and row[3] else None,
            "last_refreshed_at": row[4].isoformat() if row and row[4] else None,
        }

    return status
