from fastapi import APIRouter, Depends, status

from src.schemas.common import CurrentUserResponse
from src.security.context import AuthContext
from src.security.dependencies import require_auth_context


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
