from typing import Any

import httpx
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


async def fetch_supabase_user_claims(token: str, settings: Settings) -> dict[str, Any]:
    public_key = settings.supabase_publishable_key or settings.supabase_anon_key
    if not settings.supabase_url or not public_key:
        raise AuthenticationError("Invalid or expired access token")

    user_endpoint = f"{settings.supabase_url.rstrip('/')}/auth/v1/user"
    headers = {
        "Authorization": f"Bearer {token}",
        "apikey": public_key,
    }

    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(user_endpoint, headers=headers)
    except httpx.HTTPError as exc:
        raise AuthenticationError("Unable to validate the access token with Supabase") from exc

    if response.status_code != 200:
        raise AuthenticationError("Invalid or expired access token")

    payload = response.json()
    user_id = payload.get("id")
    if not user_id:
        raise AuthenticationError("Supabase user response did not include a subject")

    return {
        "sub": user_id,
        "email": payload.get("email"),
        "role": payload.get("role"),
        "app_metadata": payload.get("app_metadata") or {},
        "user_metadata": payload.get("user_metadata") or {},
        "aud": payload.get("aud"),
    }


async def resolve_access_token_claims(token: str, settings: Settings) -> dict[str, Any]:
    try:
        return decode_access_token(token, settings)
    except (AuthenticationError, ConfigurationError):
        return await fetch_supabase_user_claims(token, settings)
