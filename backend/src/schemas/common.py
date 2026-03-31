from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class ErrorEnvelope(BaseModel):
    error: str
    code: str
    details: dict[str, Any] = Field(default_factory=dict)


class HealthCheck(BaseModel):
    name: str
    status: Literal["ok", "degraded", "missing"]
    detail: str


class HealthResponse(BaseModel):
    status: Literal["ok", "degraded"]
    checks: list[HealthCheck]


class CurrentUserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    user_id: str
    email: EmailStr | None = None
    role: str


class PaginatedResponse(BaseModel):
    total: int = Field(..., ge=0)
    offset: int = Field(..., ge=0)
    limit: int = Field(..., ge=1)
