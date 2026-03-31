from dataclasses import dataclass

from src.core.config import Settings
from src.schemas.auth import DemoAccessTokenResponse
from src.security.access_tokens import create_access_token_response


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
    token_response = create_access_token_response(
        user_id=ANALYST_DEMO_ACCOUNT.user_id,
        email=ANALYST_DEMO_ACCOUNT.email,
        role=ANALYST_DEMO_ACCOUNT.role,
        settings=settings,
    )
    return DemoAccessTokenResponse(**token_response.model_dump())
