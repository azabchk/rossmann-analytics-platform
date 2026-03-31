from typing import Literal

from pydantic import BaseModel, EmailStr


class AccessTokenResponse(BaseModel):
    access_token: str
    token_type: Literal["bearer"] = "bearer"
    user_id: str
    email: EmailStr
    role: str


class EmailPasswordAuthRequest(BaseModel):
    email: EmailStr
    password: str


class DemoAccessTokenResponse(AccessTokenResponse):
    pass
