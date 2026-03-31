"""Service layer for governed forecast retrieval and publication."""

from __future__ import annotations

import asyncio
import sys
from datetime import date, datetime, timedelta
from pathlib import Path

from src.core.config import get_settings
from src.core.errors import ConfigurationError, NotFoundError, ValidationError
from src.repositories.forecast_repository import ForecastRepository
from src.schemas.forecasts import (
    AccuracyMetrics,
    ForecastGenerationResponse,
    ForecastPoint,
    ForecastResponse,
    LowDataWarning,
    ModelMetadata,
    PublishedForecastResponse,
    StoreForecast,
)


class ForecastService:
    def __init__(self, repository: ForecastRepository) -> None:
        self.repository = repository

    async def get_published_forecasts(
        self,
        store_id: int,
        start_date: date | None = None,
        end_date: date | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> PublishedForecastResponse:
        if start_date and end_date and start_date > end_date:
            raise ValidationError("Start date must be before or equal to end date")

        forecasts, total = await self.repository.get_published_forecasts(
            store_id=store_id,
            start_date=start_date,
            end_date=end_date,
            limit=limit,
            offset=offset,
        )
        if not forecasts:
            raise NotFoundError(f"No published forecasts found for store {store_id}")

        model_metadata = self._build_model_metadata(forecasts[0])
        accuracy = await self.get_model_accuracy(model_metadata.model_id, raise_on_missing=False)
        points = [self._build_forecast_point(row) for row in forecasts]

        return PublishedForecastResponse(
            store_id=store_id,
            model_type=model_metadata.model_type,
            forecast_start_date=min(point.forecast_date for point in points),
            forecast_end_date=max(point.forecast_date for point in points),
            model_metadata=model_metadata,
            accuracy_metrics=accuracy,
            forecasts=points,
            total=total,
            offset=offset,
            limit=limit,
        )

    async def get_forecasts_for_stores(
        self,
        store_ids: list[int],
        start_date: date | None = None,
        end_date: date | None = None,
    ) -> ForecastResponse:
        warnings = await self.get_store_warnings(store_ids)
        forecasts: list[StoreForecast] = []

        for store_id in store_ids:
            try:
                published = await self.get_published_forecasts(
                    store_id=store_id,
                    start_date=start_date,
                    end_date=end_date,
                )
            except NotFoundError:
                continue

            forecasts.append(
                StoreForecast(
                    store_id=store_id,
                    model_metadata=published.model_metadata,
                    accuracy_metrics=published.accuracy_metrics,
                    forecasts=published.forecasts,
                )
            )

        return ForecastResponse(forecasts=forecasts, warnings=warnings)

    async def get_active_model(self, model_type: str) -> ModelMetadata | None:
        model = await self.repository.get_active_model(model_type)
        if not model:
            return None
        return self._build_model_metadata(model)

    async def get_store_warnings(self, store_ids: list[int]) -> list[LowDataWarning]:
        warning_rows = await self.repository.get_low_data_warnings(store_ids)
        return [LowDataWarning.model_validate(row) for row in warning_rows]

    async def get_model_accuracy(
        self,
        model_id: str,
        raise_on_missing: bool = True,
    ) -> AccuracyMetrics | None:
        evaluations = await self.repository.get_model_evaluations(model_id)
        if not evaluations:
            if raise_on_missing:
                raise NotFoundError(f"No evaluations found for model {model_id}")
            return None

        latest = evaluations[0]
        return AccuracyMetrics(
            mape=float(latest["mape"]) if latest["mape"] is not None else None,
            rmse=float(latest["rmse"]) if latest["rmse"] is not None else None,
            mae=float(latest["mae"]) if latest["mae"] is not None else None,
        )

    async def generate_forecasts(
        self,
        store_ids: list[int],
        horizon_weeks: int,
        triggered_by: str | None,
    ) -> ForecastGenerationResponse:
        if not store_ids:
            raise ValidationError("At least one store ID must be provided")

        repo_root = Path(__file__).resolve().parents[3]
        if str(repo_root) not in sys.path:
            sys.path.insert(0, str(repo_root))

        settings = get_settings()
        if not settings.database_url:
            raise ConfigurationError("DATABASE_URL must be configured for forecast publication")

        try:
            from ml.src.publishing.run_baseline_publication import (
                publish_baseline_forecasts_from_database,
            )
        except ImportError as exc:
            raise ConfigurationError(
                "ML publication module is not available on the current Python path"
            ) from exc

        publication_result = await asyncio.to_thread(
            publish_baseline_forecasts_from_database,
            database_url=settings.database_url,
            store_ids=store_ids,
            horizon_weeks=horizon_weeks,
            triggered_by=triggered_by,
        )

        return ForecastGenerationResponse(
            job_id=publication_result["forecast_job_id"],
            status=publication_result["job_status"],
            stores_requested=store_ids,
            estimated_completion_time=datetime.utcnow() + timedelta(seconds=1),
            message=(
                f"Published {publication_result['total_forecasts_generated']} "
                f"forecast points using model {publication_result['model_id']}"
            ),
        )

    @staticmethod
    def _build_model_metadata(row: dict) -> ModelMetadata:
        return ModelMetadata(
            model_id=str(row["model_id"]),
            model_name=row["model_name"],
            model_type=row["model_type"],
            version=row["version"],
            is_active=bool(row["is_active"]),
            published_at=row["published_at"],
        )

    @staticmethod
    def _build_forecast_point(row: dict) -> ForecastPoint:
        return ForecastPoint(
            forecast_date=row["forecast_date"],
            predicted_sales=float(row["predicted_sales"]),
            lower_bound=float(row["lower_bound"]) if row["lower_bound"] is not None else None,
            upper_bound=float(row["upper_bound"]) if row["upper_bound"] is not None else None,
            confidence_level=(
                float(row["confidence_level"]) if row["confidence_level"] is not None else None
            ),
        )
