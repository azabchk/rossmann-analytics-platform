from __future__ import annotations

from src.core.config import Settings
from src.core.errors import AuthenticationError, ValidationError
from src.repositories.local_auth_repository import LocalAuthRepository
from src.schemas.auth import AccessTokenResponse
from src.security.access_tokens import create_access_token_response
from src.security.passwords import hash_password, verify_password


class LocalAuthService:
    def __init__(self, repository: LocalAuthRepository, settings: Settings) -> None:
        self.repository = repository
        self.settings = settings

    async def sign_up(self, *, email: str, password: str) -> AccessTokenResponse:
        normalized_email = email.strip().lower()
        self._validate_password(password)

        existing_user = await self.repository.get_user_by_email(normalized_email)
        if existing_user is not None:
            raise ValidationError("An account with this email already exists")

        user = await self.repository.create_user(
            email=normalized_email,
            password_hash=hash_password(password),
        )
        return create_access_token_response(
            user_id=user.user_id,
            email=user.email,
            role=user.role,
            settings=self.settings,
        )

    async def sign_in(self, *, email: str, password: str) -> AccessTokenResponse:
        normalized_email = email.strip().lower()
        user = await self.repository.get_user_by_email(normalized_email)
        if user is None or not verify_password(password, user.password_hash):
            raise AuthenticationError("Invalid email or password")

        return create_access_token_response(
            user_id=user.user_id,
            email=user.email,
            role=user.role,
            settings=self.settings,
        )

    @staticmethod
    def _validate_password(password: str) -> None:
        if len(password) < 8:
            raise ValidationError("Password must be at least 8 characters long")
