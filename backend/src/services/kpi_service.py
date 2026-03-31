"""Access-aware KPI service for dashboard analytics."""

from __future__ import annotations

from datetime import date

from sqlalchemy.ext.asyncio import AsyncSession

from src.core.errors import AuthorizationError, NotFoundError
from src.observability.analytics_logging import event_logger
from src.repositories.kpi_repository import KPIRepository
from src.schemas.kpis import (
    DailyKPIResponse,
    KPIListResponse,
    KPISummaryResponse,
    MonthlyKPIResponse,
    WeeklyKPIResponse,
)
from src.services.store_service import StoreService


class KPIService:
    """Business logic for governed KPI retrieval."""

    def __init__(self, db_session: AsyncSession) -> None:
        self.kpi_repo = KPIRepository(db_session)
        self.store_service = StoreService(db_session)

    async def get_daily_kpis(
        self,
        *,
        user_id: str,
        role: str | None = None,
        store_id: int | None = None,
        start_date: date | None = None,
        end_date: date | None = None,
        page: int = 1,
        page_size: int = 100,
    ) -> KPIListResponse:
        store_ids = await self._resolve_store_ids(user_id=user_id, role=role, store_id=store_id)
        if not store_ids:
            return KPIListResponse(kpis=[], count=0, total=0, summary=None)

        offset = (page - 1) * page_size
        kpis = await self.kpi_repo.get_daily_kpis(
            store_ids=store_ids,
            start_date=start_date,
            end_date=end_date,
            limit=page_size,
            offset=offset,
        )
        total = await self.kpi_repo.count_daily_kpis(
            store_ids=store_ids,
            start_date=start_date,
            end_date=end_date,
        )
        summary = await self.kpi_repo.get_daily_summary(
            store_ids=store_ids,
            start_date=start_date,
            end_date=end_date,
        )
        event_logger.log_kpi_query(
            user_id=user_id,
            aggregation="daily",
            store_id=store_id,
            date_range_start=start_date.isoformat() if start_date else None,
            date_range_end=end_date.isoformat() if end_date else None,
            records_returned=len(kpis),
        )
        return KPIListResponse(
            kpis=[DailyKPIResponse.model_validate(kpi) for kpi in kpis],
            count=len(kpis),
            total=total,
            summary=KPISummaryResponse.model_validate(summary) if summary else None,
        )

    async def get_weekly_kpis(
        self,
        *,
        user_id: str,
        role: str | None = None,
        store_id: int | None = None,
        start_date: date | None = None,
        end_date: date | None = None,
        page: int = 1,
        page_size: int = 52,
    ) -> KPIListResponse:
        store_ids = await self._resolve_store_ids(user_id=user_id, role=role, store_id=store_id)
        if not store_ids:
            return KPIListResponse(kpis=[], count=0, total=0, summary=None)

        offset = (page - 1) * page_size
        kpis = await self.kpi_repo.get_weekly_kpis(
            store_ids=store_ids,
            start_date=start_date,
            end_date=end_date,
            limit=page_size,
            offset=offset,
        )
        total = await self.kpi_repo.count_weekly_kpis(
            store_ids=store_ids,
            start_date=start_date,
            end_date=end_date,
        )
        event_logger.log_kpi_query(
            user_id=user_id,
            aggregation="weekly",
            store_id=store_id,
            date_range_start=start_date.isoformat() if start_date else None,
            date_range_end=end_date.isoformat() if end_date else None,
            records_returned=len(kpis),
        )
        return KPIListResponse(
            kpis=[WeeklyKPIResponse.model_validate(kpi) for kpi in kpis],
            count=len(kpis),
            total=total,
            summary=None,
        )

    async def get_monthly_kpis(
        self,
        *,
        user_id: str,
        role: str | None = None,
        store_id: int | None = None,
        year: int | None = None,
        page: int = 1,
        page_size: int = 12,
    ) -> KPIListResponse:
        store_ids = await self._resolve_store_ids(user_id=user_id, role=role, store_id=store_id)
        if not store_ids:
            return KPIListResponse(kpis=[], count=0, total=0, summary=None)

        offset = (page - 1) * page_size
        kpis = await self.kpi_repo.get_monthly_kpis(
            store_ids=store_ids,
            year=year,
            limit=page_size,
            offset=offset,
        )
        total = await self.kpi_repo.count_monthly_kpis(store_ids=store_ids, year=year)
        event_logger.log_kpi_query(
            user_id=user_id,
            aggregation="monthly",
            store_id=store_id,
            date_range_start=str(year) if year else None,
            date_range_end=None,
            records_returned=len(kpis),
        )
        return KPIListResponse(
            kpis=[MonthlyKPIResponse.model_validate(kpi) for kpi in kpis],
            count=len(kpis),
            total=total,
            summary=None,
        )

    async def get_daily_summary(
        self,
        *,
        user_id: str,
        role: str | None = None,
        store_id: int,
        start_date: date | None = None,
        end_date: date | None = None,
    ) -> KPISummaryResponse:
        store_ids = await self._resolve_store_ids(user_id=user_id, role=role, store_id=store_id)
        summary = await self.kpi_repo.get_daily_summary(
            store_ids=store_ids,
            start_date=start_date,
            end_date=end_date,
        )
        if summary is None or summary.total_records == 0:
            raise NotFoundError(f"No KPI data found for store {store_id}")
        event_logger.log_dashboard_view(
            user_id=user_id,
            store_id=store_id,
            date_range_start=start_date.isoformat() if start_date else None,
            date_range_end=end_date.isoformat() if end_date else None,
        )
        return KPISummaryResponse.model_validate(summary)

    async def _resolve_store_ids(
        self,
        *,
        user_id: str,
        role: str | None = None,
        store_id: int | None,
    ) -> list[int]:
        if store_id is None:
            return await self.store_service.get_accessible_store_ids(user_id, role=role)

        if not await self.store_service.can_access_store(user_id, store_id, role=role):
            raise AuthorizationError(f"You do not have access to store {store_id}")
        return [store_id]
