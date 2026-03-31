"""Store endpoints for authorized dashboard access."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Path, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.dependencies import get_database_session
from src.schemas.stores import StoreListResponse, StoreResponse
from src.security.context import AuthContext
from src.security.dependencies import require_auth_context
from src.services.store_service import StoreService

router = APIRouter(prefix="/stores", tags=["stores"])


async def get_store_service(
    db_session: Annotated[AsyncSession, Depends(get_database_session)],
) -> StoreService:
    return StoreService(db_session)


@router.get("", response_model=StoreListResponse, status_code=status.HTTP_200_OK)
async def list_stores(
    store_service: Annotated[StoreService, Depends(get_store_service)],
    current_user: Annotated[AuthContext, Depends(require_auth_context)],
) -> StoreListResponse:
    return await store_service.get_accessible_stores(
        current_user.user_id,
        role=current_user.role,
    )


@router.get(
    "/{store_id}",
    response_model=StoreResponse,
    status_code=status.HTTP_200_OK,
)
async def get_store(
    *,
    store_id: int = Path(..., ge=1, description="Store identifier"),
    store_service: Annotated[StoreService, Depends(get_store_service)],
    current_user: Annotated[AuthContext, Depends(require_auth_context)],
) -> StoreResponse:
    return await store_service.get_store_by_id(
        current_user.user_id,
        store_id,
        role=current_user.role,
    )
