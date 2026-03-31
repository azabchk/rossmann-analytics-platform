"""Repository for persisted forecast results and model metadata."""

from datetime import date
from typing import Any

from sqlalchemy import text

from src.repositories.base import BaseRepository


class ForecastRepository(BaseRepository):
    """Read persisted forecasts from the controlled ML schema."""

    async def get_published_forecasts(
        self,
        store_id: int,
        start_date: date | None = None,
        end_date: date | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> tuple[list[dict[str, Any]], int]:
        filters = [
            "fr.store_id = :store_id",
            "fr.is_published = true",
            "mr.is_active = true",
        ]
        params: dict[str, Any] = {
            "store_id": store_id,
            "limit": limit,
            "offset": offset,
        }

        if start_date:
            filters.append("fr.forecast_date >= :start_date")
            params["start_date"] = start_date
        if end_date:
            filters.append("fr.forecast_date <= :end_date")
            params["end_date"] = end_date

        where_clause = " AND ".join(filters)

        count_query = text(
            f"""
            SELECT COUNT(*)
            FROM ml.forecast_results fr
            JOIN ml.model_registry mr ON mr.model_id = fr.model_id
            WHERE {where_clause}
            """
        )
        total = int((await self.session.execute(count_query, params)).scalar() or 0)

        query = text(
            f"""
            SELECT
                fr.forecast_id,
                fr.store_id,
                fr.forecast_date,
                fr.predicted_sales,
                fr.lower_bound,
                fr.upper_bound,
                fr.confidence_level,
                mr.model_id,
                mr.model_name,
                mr.model_type,
                mr.version,
                mr.is_active,
                mr.published_at
            FROM ml.forecast_results fr
            JOIN ml.model_registry mr ON mr.model_id = fr.model_id
            WHERE {where_clause}
            ORDER BY fr.forecast_date ASC
            LIMIT :limit OFFSET :offset
            """
        )

        rows = (await self.session.execute(query, params)).mappings().all()
        return [dict(row) for row in rows], total

    async def get_active_model(self, model_type: str) -> dict[str, Any] | None:
        query = text(
            """
            SELECT
                model_id,
                model_name,
                model_type,
                version,
                is_active,
                published_at
            FROM ml.model_registry
            WHERE model_type = :model_type
              AND is_active = true
            ORDER BY published_at DESC
            LIMIT 1
            """
        )
        row = (await self.session.execute(query, {"model_type": model_type})).mappings().first()
        return dict(row) if row else None

    async def get_model_evaluations(self, model_id: str) -> list[dict[str, Any]]:
        query = text(
            """
            SELECT
                evaluation_id,
                model_id,
                evaluation_period_start,
                evaluation_period_end,
                mape,
                rmse,
                mae,
                eval_metrics,
                evaluation_date
            FROM ml.model_evaluations
            WHERE model_id = :model_id
            ORDER BY evaluation_date DESC
            """
        )
        rows = (await self.session.execute(query, {"model_id": model_id})).mappings().all()
        return [dict(row) for row in rows]

    async def get_low_data_warnings(self, store_ids: list[int]) -> list[dict[str, Any]]:
        if not store_ids:
            return []

        query = text(
            """
            SELECT
                warning_id,
                store_id,
                warning_type,
                days_of_history,
                warning_message,
                is_active,
                created_at
            FROM ml.low_data_warnings
            WHERE store_id = ANY(:store_ids)
              AND is_active = true
            ORDER BY store_id ASC, created_at DESC
            """
        )
        rows = (await self.session.execute(query, {"store_ids": store_ids})).mappings().all()
        return [dict(row) for row in rows]

    async def get_forecast_metadata(self, forecast_job_id: str) -> dict[str, Any] | None:
        query = text(
            """
            SELECT
                forecast_job_id,
                model_id,
                forecast_horizon_days,
                forecast_start_date,
                forecast_end_date,
                stores_included,
                total_forecasts_generated,
                job_status,
                started_at,
                completed_at,
                error_message
            FROM ml.forecast_metadata
            WHERE forecast_job_id = :forecast_job_id
            """
        )
        row = (
            await self.session.execute(query, {"forecast_job_id": forecast_job_id})
        ).mappings().first()
        return dict(row) if row else None
