"""Schemas for forecast-related API requests and responses."""

from datetime import date, datetime

from pydantic import BaseModel, Field

from src.schemas.common import PaginatedResponse


class ForecastPoint(BaseModel):
    forecast_date: date
    predicted_sales: float = Field(..., ge=0)
    lower_bound: float | None = Field(default=None, ge=0)
    upper_bound: float | None = Field(default=None, ge=0)
    confidence_level: float | None = Field(default=None, gt=0, le=100)


class ModelMetadata(BaseModel):
    model_id: str
    model_name: str
    model_type: str
    version: str
    is_active: bool
    published_at: datetime


class AccuracyMetrics(BaseModel):
    mape: float | None = Field(default=None, ge=0)
    rmse: float | None = Field(default=None, ge=0)
    mae: float | None = Field(default=None, ge=0)


class StoreForecast(BaseModel):
    store_id: int
    model_metadata: ModelMetadata
    accuracy_metrics: AccuracyMetrics | None = None
    forecasts: list[ForecastPoint]


class ForecastRequest(BaseModel):
    store_ids: list[int] = Field(default_factory=list)
    forecast_start_date: date | None = None
    forecast_end_date: date | None = None


class LowDataWarning(BaseModel):
    store_id: int
    warning_type: str
    warning_message: str
    days_of_history: int | None = None


class ForecastResponse(BaseModel):
    forecasts: list[StoreForecast]
    warnings: list[LowDataWarning] = Field(default_factory=list)


class PublishedForecastResponse(PaginatedResponse):
    store_id: int
    model_type: str
    forecast_start_date: date
    forecast_end_date: date
    model_metadata: ModelMetadata
    accuracy_metrics: AccuracyMetrics | None = None
    forecasts: list[ForecastPoint]


class ForecastListResponse(BaseModel):
    store_id: int
    available_forecasts: list[ModelMetadata]


class ForecastGenerationRequest(BaseModel):
    store_ids: list[int] = Field(default_factory=list)
    horizon_weeks: int = Field(default=6, ge=1, le=12)
    force_retrain: bool = False


class ForecastGenerationResponse(BaseModel):
    job_id: str
    status: str
    stores_requested: list[int]
    estimated_completion_time: datetime | None = None
    message: str
