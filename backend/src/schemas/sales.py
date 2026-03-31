"""Request and response schemas for historical sales endpoints."""

from __future__ import annotations

from datetime import date

from pydantic import BaseModel, ConfigDict, Field, model_validator


class SalesRecordResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    sales_record_id: int
    store_id: int
    sales_date: date
    day_of_week: int = Field(..., ge=1, le=7)
    sales: int = Field(..., ge=0)
    customers: int | None = Field(default=None, ge=0)
    is_open: bool
    promo: bool
    state_holiday: str | None = None
    school_holiday: bool


class SalesSummaryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    total_sales: int = Field(..., ge=0)
    total_customers: int = Field(..., ge=0)
    total_transactions: int = Field(..., ge=0)
    avg_daily_sales: float = Field(..., ge=0)
    avg_daily_customers: float = Field(..., ge=0)
    promo_days: int = Field(..., ge=0)
    holiday_days: int = Field(..., ge=0)


class SalesListResponse(BaseModel):
    data: list[SalesRecordResponse] = Field(default_factory=list)
    count: int = Field(..., ge=0)
    total: int = Field(..., ge=0)
    summary: SalesSummaryResponse | None = None


class SalesFilterRequest(BaseModel):
    store_id: int | None = Field(default=None, ge=1)
    start_date: date | None = None
    end_date: date | None = None
    is_open: bool | None = None
    promo: bool | None = None

    @model_validator(mode="after")
    def validate_range(self) -> "SalesFilterRequest":
        if self.start_date and self.end_date and self.start_date > self.end_date:
            raise ValueError("start_date must be before or equal to end_date")
        return self


class SalesListRequest(SalesFilterRequest):
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=100, ge=1, le=1000)
