"""Historical sales endpoints for dashboard analytics."""

from __future__ import annotations

from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.dependencies import get_database_session
from src.core.errors import NotFoundError
from src.repositories.sales_repository import SalesRepository
from src.schemas.sales import SalesListRequest, SalesListResponse, SalesRecordResponse, SalesSummaryResponse
from src.security.context import AuthContext
from src.security.dependencies import require_auth_context
from src.services.store_service import StoreService

router = APIRouter(prefix="/sales", tags=["sales"])


async def get_sales_repository(
    db_session: Annotated[AsyncSession, Depends(get_database_session)],
) -> SalesRepository:
    return SalesRepository(db_session)


async def get_store_service(
    db_session: Annotated[AsyncSession, Depends(get_database_session)],
) -> StoreService:
    return StoreService(db_session)


@router.get("", response_model=SalesListResponse, status_code=status.HTTP_200_OK)
async def list_sales(
    params: Annotated[SalesListRequest, Depends()],
    sales_repository: Annotated[SalesRepository, Depends(get_sales_repository)],
    store_service: Annotated[StoreService, Depends(get_store_service)],
    current_user: Annotated[AuthContext, Depends(require_auth_context)],
) -> SalesListResponse:
    if params.store_id is not None:
        if not await store_service.can_access_store(
            current_user.user_id,
            params.store_id,
            role=current_user.role,
        ):
            from src.core.errors import AuthorizationError

            raise AuthorizationError(f"You do not have access to store {params.store_id}")
        store_ids = [params.store_id]
    else:
        store_ids = await store_service.get_accessible_store_ids(
            current_user.user_id,
            role=current_user.role,
        )

    if not store_ids:
        return SalesListResponse(data=[], count=0, total=0, summary=None)

    offset = (params.page - 1) * params.page_size
    records = await sales_repository.get_sales_records(
        store_ids=store_ids,
        start_date=params.start_date,
        end_date=params.end_date,
        limit=params.page_size,
        offset=offset,
    )
    total = await sales_repository.count_sales_records(
        store_ids=store_ids,
        start_date=params.start_date,
        end_date=params.end_date,
    )
    summary = await sales_repository.get_sales_summary(
        store_ids=store_ids,
        start_date=params.start_date,
        end_date=params.end_date,
    )

    return SalesListResponse(
        data=[SalesRecordResponse.model_validate(record) for record in records],
        count=len(records),
        total=total,
        summary=SalesSummaryResponse.model_validate(summary) if summary else None,
    )


@router.get("/summary", response_model=SalesSummaryResponse, status_code=status.HTTP_200_OK)
async def get_sales_summary(
    *,
    store_id: int = Query(..., ge=1),
    start_date: date | None = Query(default=None),
    end_date: date | None = Query(default=None),
    sales_repository: Annotated[SalesRepository, Depends(get_sales_repository)],
    store_service: Annotated[StoreService, Depends(get_store_service)],
    current_user: Annotated[AuthContext, Depends(require_auth_context)],
) -> SalesSummaryResponse:
    if not await store_service.can_access_store(
        current_user.user_id,
        store_id,
        role=current_user.role,
    ):
        from src.core.errors import AuthorizationError

        raise AuthorizationError(f"You do not have access to store {store_id}")

    summary = await sales_repository.get_sales_summary(
        store_ids=[store_id],
        start_date=start_date,
        end_date=end_date,
    )
    if summary is None:
        raise NotFoundError(f"No sales data found for store {store_id}")
    return SalesSummaryResponse.model_validate(summary)
