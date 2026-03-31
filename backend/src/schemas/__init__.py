"""Shared API schemas."""

from src.schemas.auth import DemoAccessTokenResponse
from src.schemas.common import (
    CurrentUserResponse,
    ErrorEnvelope,
    HealthCheck,
    HealthResponse,
)
from src.schemas.forecasts import (
    AccuracyMetrics,
    ForecastGenerationRequest,
    ForecastGenerationResponse,
    ForecastPoint,
    ForecastResponse,
    LowDataWarning,
    ModelMetadata,
    PublishedForecastResponse,
    StoreForecast,
)
from src.schemas.kpis import (
    DailyKPIResponse,
    KPIFilterRequest,
    KPIListRequest,
    KPIListResponse,
    KPIRecordResponse,
    KPISummaryResponse,
    MonthlyKPIResponse,
    WeeklyKPIResponse,
)
from src.schemas.sales import (
    SalesFilterRequest,
    SalesListRequest,
    SalesListResponse,
    SalesRecordResponse,
    SalesSummaryResponse,
)
from src.schemas.stores import (
    StoreFilterRequest,
    StoreListResponse,
    StoreResponse,
)

__all__ = [
    # Auth schemas
    "DemoAccessTokenResponse",
    # Common schemas
    "CurrentUserResponse",
    "ErrorEnvelope",
    "HealthCheck",
    "HealthResponse",
    # Forecast schemas
    "AccuracyMetrics",
    "ForecastGenerationRequest",
    "ForecastGenerationResponse",
    "ForecastPoint",
    "ForecastResponse",
    "LowDataWarning",
    "ModelMetadata",
    "PublishedForecastResponse",
    "StoreForecast",
    # Store schemas
    "StoreResponse",
    "StoreListResponse",
    "StoreFilterRequest",
    # Sales schemas
    "SalesRecordResponse",
    "SalesSummaryResponse",
    "SalesListResponse",
    "SalesFilterRequest",
    "SalesListRequest",
    # KPI schemas
    "DailyKPIResponse",
    "WeeklyKPIResponse",
    "MonthlyKPIResponse",
    "KPIRecordResponse",
    "KPISummaryResponse",
    "KPIListResponse",
    "KPIFilterRequest",
    "KPIListRequest",
]
