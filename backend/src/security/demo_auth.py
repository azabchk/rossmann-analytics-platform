from dataclasses import dataclass

import jwt

from src.core.config import Settings
from src.core.errors import ConfigurationError
from src.schemas.auth import DemoAccessTokenResponse


@dataclass(frozen=True, slots=True)
class DemoAccount:
    user_id: str
    email: str
    role: str


ANALYST_DEMO_ACCOUNT = DemoAccount(
    user_id="00000000-0000-0000-0000-000000000002",
    email="analyst@example.com",
    role="data_analyst",
)


def create_demo_access_token(settings: Settings) -> DemoAccessTokenResponse:
    if not settings.supabase_jwt_secret:
        raise ConfigurationError("SUPABASE_JWT_SECRET must be configured for local demo auth")

    payload = {
        "sub": ANALYST_DEMO_ACCOUNT.user_id,
        "email": ANALYST_DEMO_ACCOUNT.email,
        "aud": settings.supabase_jwt_audience,
        "app_metadata": {"role": ANALYST_DEMO_ACCOUNT.role},
    }
    if settings.supabase_jwt_issuer:
        payload["iss"] = settings.supabase_jwt_issuer

    access_token = jwt.encode(payload, settings.supabase_jwt_secret, algorithm="HS256")
    return DemoAccessTokenResponse(
        access_token=access_token,
        user_id=ANALYST_DEMO_ACCOUNT.user_id,
        email=ANALYST_DEMO_ACCOUNT.email,
        role=ANALYST_DEMO_ACCOUNT.role,
    )
