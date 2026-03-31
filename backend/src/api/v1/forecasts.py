"""Forecast API endpoints."""

from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.dependencies import get_database_session
from src.core.errors import AuthorizationError, NotFoundError, ValidationError
from src.repositories.forecast_repository import ForecastRepository
from src.schemas.forecasts import (
    AccuracyMetrics,
    ForecastGenerationRequest,
    ForecastGenerationResponse,
    ForecastRequest,
    ForecastResponse,
    LowDataWarning,
    ModelMetadata,
    PublishedForecastResponse,
)
from src.security.context import AuthContext
from src.security.dependencies import require_auth_context
from src.services.forecast_service import ForecastService
from src.services.store_service import StoreService

router = APIRouter(prefix="/forecasts", tags=["forecasts"])


async def get_forecast_service(
    db_session: Annotated[AsyncSession, Depends(get_database_session)],
) -> ForecastService:
    return ForecastService(ForecastRepository(db_session))


async def get_store_service(
    db_session: Annotated[AsyncSession, Depends(get_database_session)],
) -> StoreService:
    return StoreService(db_session)


async def _require_store_access(
    current_user: AuthContext,
    store_service: StoreService,
    store_id: int,
) -> None:
    if current_user.role == "admin":
        return

    has_access = await store_service.can_access_store(current_user.user_id, store_id)
    if not has_access:
        raise AuthorizationError(f"You do not have access to store {store_id}")


@router.get(
    "/stores/{store_id}",
    response_model=PublishedForecastResponse,
    status_code=status.HTTP_200_OK,
)
async def get_store_forecasts(
    store_id: int,
    service: Annotated[ForecastService, Depends(get_forecast_service)],
    store_service: Annotated[StoreService, Depends(get_store_service)],
    current_user: Annotated[AuthContext, Depends(require_auth_context)],
    start_date: date | None = Query(None, description="Filter forecasts from this date"),
    end_date: date | None = Query(None, description="Filter forecasts to this date"),
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
) -> PublishedForecastResponse:
    await _require_store_access(current_user, store_service, store_id)
    return await service.get_published_forecasts(
        store_id=store_id,
        start_date=start_date,
        end_date=end_date,
        limit=limit,
        offset=offset,
    )


@router.post(
    "/batch",
    response_model=ForecastResponse,
    status_code=status.HTTP_200_OK,
)
async def get_batch_forecasts(
    request: ForecastRequest,
    service: Annotated[ForecastService, Depends(get_forecast_service)],
    store_service: Annotated[StoreService, Depends(get_store_service)],
    current_user: Annotated[AuthContext, Depends(require_auth_context)],
) -> ForecastResponse:
    if not request.store_ids:
        raise ValidationError("At least one store ID must be provided")

    if current_user.role != "admin":
        accessible_store_ids: list[int] = []
        for store_id in request.store_ids:
            if await store_service.can_access_store(current_user.user_id, store_id):
                accessible_store_ids.append(store_id)
        if not accessible_store_ids:
            raise AuthorizationError("You do not have access to the requested stores")
    else:
        accessible_store_ids = request.store_ids

    return await service.get_forecasts_for_stores(
        store_ids=accessible_store_ids,
        start_date=request.forecast_start_date,
        end_date=request.forecast_end_date,
    )


@router.get(
    "/models/{model_type}/active",
    response_model=ModelMetadata,
    status_code=status.HTTP_200_OK,
)
async def get_active_model(
    model_type: str,
    service: Annotated[ForecastService, Depends(get_forecast_service)],
    _: Annotated[AuthContext, Depends(require_auth_context)],
) -> ModelMetadata:
    valid_types = {"baseline", "prophet", "xgboost"}
    if model_type not in valid_types:
        raise ValidationError(
            f"Invalid model type. Must be one of: {', '.join(sorted(valid_types))}"
        )

    model = await service.get_active_model(model_type)
    if model is None:
        raise NotFoundError(f"No active {model_type} model is available")
    return model


@router.get(
    "/warnings/{store_id}",
    response_model=list[LowDataWarning],
    status_code=status.HTTP_200_OK,
)
async def get_store_warnings(
    store_id: int,
    service: Annotated[ForecastService, Depends(get_forecast_service)],
    store_service: Annotated[StoreService, Depends(get_store_service)],
    current_user: Annotated[AuthContext, Depends(require_auth_context)],
) -> list[LowDataWarning]:
    await _require_store_access(current_user, store_service, store_id)
    return await service.get_store_warnings([store_id])


@router.get(
    "/accuracy/{model_id}",
    response_model=AccuracyMetrics,
    status_code=status.HTTP_200_OK,
)
async def get_model_accuracy(
    model_id: str,
    service: Annotated[ForecastService, Depends(get_forecast_service)],
    _: Annotated[AuthContext, Depends(require_auth_context)],
) -> AccuracyMetrics:
    accuracy = await service.get_model_accuracy(model_id)
    if accuracy is None:
        raise NotFoundError(f"No evaluation metrics are available for model {model_id}")
    return accuracy


@router.post(
    "/generate",
    response_model=ForecastGenerationResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
async def generate_forecasts(
    request: ForecastGenerationRequest,
    service: Annotated[ForecastService, Depends(get_forecast_service)],
    current_user: Annotated[AuthContext, Depends(require_auth_context)],
) -> ForecastGenerationResponse:
    if current_user.role not in {"admin", "data_analyst"}:
        raise AuthorizationError("You do not have permission to trigger forecast generation")

    return await service.generate_forecasts(
        store_ids=request.store_ids,
        horizon_weeks=request.horizon_weeks,
        triggered_by=current_user.email or current_user.user_id,
    )
