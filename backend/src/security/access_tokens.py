import jwt

from src.core.config import Settings
from src.core.errors import ConfigurationError
from src.schemas.auth import AccessTokenResponse


def create_access_token_response(
    *,
    user_id: str,
    email: str,
    role: str,
    settings: Settings,
) -> AccessTokenResponse:
    if not settings.supabase_jwt_secret:
        raise ConfigurationError("SUPABASE_JWT_SECRET must be configured for access token issuance")

    payload = {
        "sub": user_id,
        "email": email,
        "aud": settings.supabase_jwt_audience,
        "app_metadata": {"role": role},
    }
    if settings.supabase_jwt_issuer:
        payload["iss"] = settings.supabase_jwt_issuer

    access_token = jwt.encode(payload, settings.supabase_jwt_secret, algorithm="HS256")
    return AccessTokenResponse(
        access_token=access_token,
        user_id=user_id,
        email=email,
        role=role,
    )
