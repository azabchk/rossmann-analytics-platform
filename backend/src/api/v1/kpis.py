"""KPI endpoints for dashboard analytics."""

from __future__ import annotations

from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.dependencies import get_database_session
from src.core.errors import ValidationError
from src.schemas.kpis import KPIListRequest, KPIListResponse, KPISummaryResponse
from src.security.context import AuthContext
from src.security.dependencies import require_auth_context
from src.services.kpi_service import KPIService

router = APIRouter(prefix="/kpis", tags=["kpis"])


async def get_kpi_service(
    db_session: Annotated[AsyncSession, Depends(get_database_session)],
) -> KPIService:
    return KPIService(db_session)


@router.get("", response_model=KPIListResponse, status_code=status.HTTP_200_OK)
async def list_kpis(
    params: Annotated[KPIListRequest, Depends()],
    kpi_service: Annotated[KPIService, Depends(get_kpi_service)],
    current_user: Annotated[AuthContext, Depends(require_auth_context)],
) -> KPIListResponse:
    if params.aggregation == "daily":
        return await kpi_service.get_daily_kpis(
            user_id=current_user.user_id,
            role=current_user.role,
            store_id=params.store_id,
            start_date=params.start_date,
            end_date=params.end_date,
            page=params.page,
            page_size=params.page_size,
        )
    if params.aggregation == "weekly":
        return await kpi_service.get_weekly_kpis(
            user_id=current_user.user_id,
            role=current_user.role,
            store_id=params.store_id,
            start_date=params.start_date,
            end_date=params.end_date,
            page=params.page,
            page_size=params.page_size,
        )
    if params.aggregation == "monthly":
        return await kpi_service.get_monthly_kpis(
            user_id=current_user.user_id,
            role=current_user.role,
            store_id=params.store_id,
            year=params.year,
            page=params.page,
            page_size=params.page_size,
        )
    raise ValidationError(
        "Invalid aggregation value. Expected one of: daily, weekly, monthly"
    )


@router.get("/daily", response_model=KPIListResponse, status_code=status.HTTP_200_OK)
async def list_daily_kpis(
    params: Annotated[KPIListRequest, Depends()],
    kpi_service: Annotated[KPIService, Depends(get_kpi_service)],
    current_user: Annotated[AuthContext, Depends(require_auth_context)],
) -> KPIListResponse:
    return await kpi_service.get_daily_kpis(
        user_id=current_user.user_id,
        role=current_user.role,
        store_id=params.store_id,
        start_date=params.start_date,
        end_date=params.end_date,
        page=params.page,
        page_size=params.page_size,
    )


@router.get("/weekly", response_model=KPIListResponse, status_code=status.HTTP_200_OK)
async def list_weekly_kpis(
    params: Annotated[KPIListRequest, Depends()],
    kpi_service: Annotated[KPIService, Depends(get_kpi_service)],
    current_user: Annotated[AuthContext, Depends(require_auth_context)],
) -> KPIListResponse:
    return await kpi_service.get_weekly_kpis(
        user_id=current_user.user_id,
        role=current_user.role,
        store_id=params.store_id,
        start_date=params.start_date,
        end_date=params.end_date,
        page=params.page,
        page_size=params.page_size,
    )


@router.get("/monthly", response_model=KPIListResponse, status_code=status.HTTP_200_OK)
async def list_monthly_kpis(
    params: Annotated[KPIListRequest, Depends()],
    kpi_service: Annotated[KPIService, Depends(get_kpi_service)],
    current_user: Annotated[AuthContext, Depends(require_auth_context)],
) -> KPIListResponse:
    return await kpi_service.get_monthly_kpis(
        user_id=current_user.user_id,
        role=current_user.role,
        store_id=params.store_id,
        year=params.year,
        page=params.page,
        page_size=params.page_size,
    )


@router.get("/summary", response_model=KPISummaryResponse, status_code=status.HTTP_200_OK)
async def get_kpi_summary(
    *,
    store_id: int = Query(..., ge=1),
    start_date: date | None = Query(default=None),
    end_date: date | None = Query(default=None),
    kpi_service: Annotated[KPIService, Depends(get_kpi_service)],
    current_user: Annotated[AuthContext, Depends(require_auth_context)],
) -> KPISummaryResponse:
    return await kpi_service.get_daily_summary(
        user_id=current_user.user_id,
        role=current_user.role,
        store_id=store_id,
        start_date=start_date,
        end_date=end_date,
    )
