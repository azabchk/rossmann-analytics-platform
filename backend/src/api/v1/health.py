from fastapi import APIRouter, status

from src.core.config import get_settings
from src.db.session import database_is_configured
from src.schemas.common import HealthCheck, HealthResponse


router = APIRouter(prefix="/health", tags=["health"])


@router.get("/live", response_model=HealthResponse, status_code=status.HTTP_200_OK)
async def liveness() -> HealthResponse:
    """Return application liveness without checking external dependencies."""

    return HealthResponse(
        status="ok",
        checks=[HealthCheck(name="application", status="ok", detail="API process is running")],
    )


@router.get("/ready", response_model=HealthResponse, status_code=status.HTTP_200_OK)
async def readiness() -> HealthResponse:
    """Expose readiness based on foundational configuration only."""

    settings = get_settings()
    checks = [
        HealthCheck(
            name="database_config",
            status="ok" if database_is_configured(settings) else "missing",
            detail="DATABASE_URL is configured" if database_is_configured(settings) else "DATABASE_URL is not set",
        ),
        HealthCheck(
            name="jwt_secret",
            status="ok" if settings.supabase_jwt_secret else "missing",
            detail="JWT validation secret is configured"
            if settings.supabase_jwt_secret
            else "SUPABASE_JWT_SECRET is not set",
        ),
    ]
    overall_status = "ok" if all(check.status == "ok" for check in checks) else "degraded"
    return HealthResponse(status=overall_status, checks=checks)
