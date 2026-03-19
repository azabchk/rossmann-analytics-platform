from typing import Annotated

from fastapi import Depends, Header

from src.core.config import Settings
from src.core.dependencies import get_settings_dependency
from src.core.errors import AuthenticationError
from src.security.context import AuthContext, build_auth_context
from src.security.jwt import decode_access_token


def _extract_bearer_token(authorization: str | None) -> str:
    if not authorization:
        raise AuthenticationError()

    scheme, _, token = authorization.partition(" ")
    if scheme.lower() != "bearer" or not token:
        raise AuthenticationError("Bearer token is required")
    return token


async def require_auth_context(
    authorization: Annotated[str | None, Header(alias="Authorization")] = None,
    settings: Settings = Depends(get_settings_dependency),
) -> AuthContext:
    token = _extract_bearer_token(authorization)
    claims = decode_access_token(token, settings)
    try:
        return build_auth_context(claims)
    except ValueError as exc:
        raise AuthenticationError("Token payload is incomplete") from exc
