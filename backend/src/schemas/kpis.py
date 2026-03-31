"""Request and response schemas for KPI endpoints."""

from __future__ import annotations

from datetime import date
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


AggregationLevel = Literal["daily", "weekly", "monthly"]


class DailyKPIResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    kpi_id: int
    store_id: int
    kpi_date: date
    day_of_week: int = Field(..., ge=1, le=7)
    total_sales: float = Field(..., ge=0)
    total_customers: int = Field(..., ge=0)
    transactions: int = Field(..., ge=0)
    avg_sales_per_transaction: float | None = Field(default=None, ge=0)
    sales_per_customer: float | None = Field(default=None, ge=0)
    is_promo_day: bool
    has_state_holiday: bool
    has_school_holiday: bool
    is_store_open: bool


class WeeklyKPIResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    kpi_id: int
    store_id: int
    week_start_date: date
    week_end_date: date
    iso_week: int = Field(..., ge=1, le=53)
    year: int
    total_sales: float = Field(..., ge=0)
    total_customers: int = Field(..., ge=0)
    total_transactions: int = Field(..., ge=0)
    avg_daily_sales: float | None = Field(default=None, ge=0)
    avg_daily_customers: float | None = Field(default=None, ge=0)
    avg_daily_transactions: float | None = Field(default=None, ge=0)
    promo_days_count: int = Field(..., ge=0)
    holiday_days_count: int = Field(..., ge=0)
    open_days_count: int = Field(..., ge=0)
    closed_days_count: int = Field(..., ge=0)


class MonthlyKPIResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    kpi_id: int
    store_id: int
    year: int
    month: int = Field(..., ge=1, le=12)
    month_name: str
    total_sales: float = Field(..., ge=0)
    total_customers: int = Field(..., ge=0)
    total_transactions: int = Field(..., ge=0)
    avg_daily_sales: float | None = Field(default=None, ge=0)
    avg_daily_customers: float | None = Field(default=None, ge=0)
    avg_daily_transactions: float | None = Field(default=None, ge=0)
    days_in_month: int = Field(..., ge=28, le=31)
    promo_days_count: int = Field(..., ge=0)
    holiday_days_count: int = Field(..., ge=0)
    open_days_count: int = Field(..., ge=0)
    closed_days_count: int = Field(..., ge=0)
    active_weeks_count: int = Field(..., ge=1, le=6)
    mom_sales_growth_pct: float | None = None
    mom_customers_growth_pct: float | None = None
    yoy_sales_growth_pct: float | None = None
    yoy_customers_growth_pct: float | None = None


KPIRecordResponse = DailyKPIResponse | WeeklyKPIResponse | MonthlyKPIResponse


class KPISummaryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    total_records: int = Field(..., ge=0)
    total_sales: float = Field(..., ge=0)
    total_customers: int = Field(..., ge=0)
    avg_daily_sales: float = Field(..., ge=0)
    promo_days: int = Field(..., ge=0)
    holiday_days: int = Field(..., ge=0)


class KPIListResponse(BaseModel):
    kpis: list[KPIRecordResponse] = Field(default_factory=list)
    count: int = Field(..., ge=0)
    total: int = Field(..., ge=0)
    summary: KPISummaryResponse | None = None


class KPIFilterRequest(BaseModel):
    store_id: int | None = Field(default=None, ge=1)
    start_date: date | None = None
    end_date: date | None = None
    aggregation: AggregationLevel | None = None
    year: int | None = Field(default=None, ge=2013)

    @model_validator(mode="after")
    def validate_range(self) -> "KPIFilterRequest":
        if self.start_date and self.end_date and self.start_date > self.end_date:
            raise ValueError("start_date must be before or equal to end_date")
        return self


class KPIListRequest(KPIFilterRequest):
    aggregation: AggregationLevel = "daily"
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=100, ge=1, le=1000)
