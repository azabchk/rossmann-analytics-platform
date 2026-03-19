from typing import Any

import jwt
from jwt import InvalidTokenError

from src.core.config import Settings
from src.core.errors import AuthenticationError, ConfigurationError


def decode_access_token(token: str, settings: Settings) -> dict[str, Any]:
    if not settings.supabase_jwt_secret:
        raise ConfigurationError("SUPABASE_JWT_SECRET must be configured for JWT validation")

    try:
        return jwt.decode(
            token,
            settings.supabase_jwt_secret,
            algorithms=["HS256"],
            audience=settings.supabase_jwt_audience,
            issuer=settings.supabase_jwt_issuer or None,
            options={"require": ["sub"]},
        )
    except InvalidTokenError as exc:
        raise AuthenticationError("Invalid or expired access token") from exc
