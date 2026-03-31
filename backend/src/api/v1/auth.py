from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.config import Settings
from src.core.dependencies import get_database_session
from src.core.dependencies import get_settings_dependency
from src.core.errors import NotFoundError
from src.repositories.local_auth_repository import LocalAuthRepository
from src.schemas.auth import AccessTokenResponse, DemoAccessTokenResponse, EmailPasswordAuthRequest
from src.schemas.common import CurrentUserResponse
from src.security.context import AuthContext
from src.security.dependencies import require_auth_context
from src.security.demo_auth import create_demo_access_token
from src.services.local_auth_service import LocalAuthService


router = APIRouter(prefix="/auth", tags=["auth"])


def _build_local_auth_service(
    session: AsyncSession,
    settings: Settings,
) -> LocalAuthService:
    return LocalAuthService(LocalAuthRepository(session), settings)


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
    "/signup",
    response_model=AccessTokenResponse,
    status_code=status.HTTP_201_CREATED,
)
async def sign_up_local_account(
    payload: EmailPasswordAuthRequest,
    session: AsyncSession = Depends(get_database_session),
    settings: Settings = Depends(get_settings_dependency),
) -> AccessTokenResponse:
    service = _build_local_auth_service(session, settings)
    return await service.sign_up(email=payload.email, password=payload.password)


@router.post(
    "/login",
    response_model=AccessTokenResponse,
    status_code=status.HTTP_200_OK,
)
async def sign_in_local_account(
    payload: EmailPasswordAuthRequest,
    session: AsyncSession = Depends(get_database_session),
    settings: Settings = Depends(get_settings_dependency),
) -> AccessTokenResponse:
    service = _build_local_auth_service(session, settings)
    return await service.sign_in(email=payload.email, password=payload.password)


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
