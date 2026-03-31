"""Structured logging helpers for analytics and dashboard use cases."""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import Any

analytics_logger = logging.getLogger("analytics")


def _timestamp() -> str:
    return datetime.now(UTC).isoformat()


class AnalyticsEventLogger:
    """Small wrapper around a named logger for dashboard-related events."""

    def __init__(self, logger: logging.Logger | None = None) -> None:
        self.logger = logger or analytics_logger

    def log_dashboard_view(
        self,
        *,
        user_id: str,
        store_id: int | None,
        date_range_start: str | None,
        date_range_end: str | None,
    ) -> None:
        self.logger.info(
            "dashboard_view",
            extra={
                "event_type": "dashboard_view",
                "user_id": user_id,
                "store_id": store_id,
                "date_range_start": date_range_start,
                "date_range_end": date_range_end,
                "timestamp": _timestamp(),
            },
        )

    def log_kpi_query(
        self,
        *,
        user_id: str,
        aggregation: str,
        store_id: int | None,
        date_range_start: str | None,
        date_range_end: str | None,
        records_returned: int,
    ) -> None:
        self.logger.info(
            "kpi_query",
            extra={
                "event_type": "kpi_query",
                "user_id": user_id,
                "aggregation": aggregation,
                "store_id": store_id,
                "date_range_start": date_range_start,
                "date_range_end": date_range_end,
                "records_returned": records_returned,
                "timestamp": _timestamp(),
            },
        )

    def log_store_access(
        self,
        *,
        user_id: str,
        store_id: int,
        granted: bool,
        reason: str | None = None,
    ) -> None:
        self.logger.log(
            logging.INFO if granted else logging.WARNING,
            "store_access",
            extra={
                "event_type": "store_access",
                "user_id": user_id,
                "store_id": store_id,
                "granted": granted,
                "reason": reason,
                "timestamp": _timestamp(),
            },
        )

    def log_dashboard_error(
        self,
        *,
        user_id: str,
        error_type: str,
        error_message: str,
        context: dict[str, Any] | None = None,
    ) -> None:
        self.logger.error(
            "dashboard_error",
            extra={
                "event_type": "dashboard_error",
                "user_id": user_id,
                "error_type": error_type,
                "error_message": error_message,
                "context": context or {},
                "timestamp": _timestamp(),
            },
        )


event_logger = AnalyticsEventLogger()
