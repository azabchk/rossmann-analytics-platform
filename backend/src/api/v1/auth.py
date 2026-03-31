from fastapi import APIRouter, Depends, status

from src.core.config import Settings
from src.core.dependencies import get_settings_dependency
from src.core.errors import NotFoundError
from src.schemas.auth import DemoAccessTokenResponse
from src.schemas.common import CurrentUserResponse
from src.security.context import AuthContext
from src.security.dependencies import require_auth_context
from src.security.demo_auth import create_demo_access_token


router = APIRouter(prefix="/auth", tags=["auth"])


@router.get(
    "/me",
    response_model=CurrentUserResponse,
    status_code=status.HTTP_200_OK,
)
async def get_current_user(
    current_user: AuthContext = Depends(require_auth_context),
) -> CurrentUserResponse:
    """Return the authenticated user derived from the validated JWT."""

    return CurrentUserResponse(
        user_id=current_user.user_id,
        email=current_user.email,
        role=current_user.role,
    )


@router.post(
    "/demo-token",
    response_model=DemoAccessTokenResponse,
    status_code=status.HTTP_200_OK,
)
async def get_local_demo_token(
    settings: Settings = Depends(get_settings_dependency),
) -> DemoAccessTokenResponse:
    """Return a local analyst demo token when the helper is explicitly enabled."""

    if not settings.enable_local_demo_auth:
        raise NotFoundError("Local demo login is disabled")

    return create_demo_access_token(settings)
