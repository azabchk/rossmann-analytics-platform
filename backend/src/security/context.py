from dataclasses import dataclass
from typing import Any


@dataclass(slots=True)
class AuthContext:
    user_id: str
    role: str
    email: str | None
    claims: dict[str, Any]


def build_auth_context(claims: dict[str, Any]) -> AuthContext:
    role = (
        claims.get("app_metadata", {}).get("role")
        or claims.get("role")
        or claims.get("user_role")
        or "authenticated"
    )
    email = claims.get("email")
    user_id = claims.get("sub")
    if not user_id:
        raise ValueError("JWT payload is missing subject")
    return AuthContext(user_id=user_id, role=role, email=email, claims=claims)
