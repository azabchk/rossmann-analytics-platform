"""Request and response schemas for store-related endpoints."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class StoreResponse(BaseModel):
    """Store metadata returned to authorized clients."""

    model_config = ConfigDict(from_attributes=True)

    store_id: int = Field(..., ge=1)
    store_type: Literal["A", "B", "C", "D"]
    assortment: Literal["a", "b", "c"]
    competition_distance: int = Field(..., ge=0)
    promo2: bool = False


class StoreListResponse(BaseModel):
    stores: list[StoreResponse] = Field(default_factory=list)
    count: int = Field(..., ge=0)
    total: int = Field(..., ge=0)


class StoreFilterRequest(BaseModel):
    """Optional future-facing filter schema kept for stable API documentation."""

    store_type: Literal["A", "B", "C", "D"] | None = None
    assortment: Literal["a", "b", "c"] | None = None
    has_promo2: bool | None = None
