"""Auth-related Pydantic schemas."""

from __future__ import annotations

from pydantic import BaseModel


class ProviderInfo(BaseModel):
    """Public OAuth provider info (no secrets)."""

    id: str
    name: str
    issuer_url: str


class UserResponse(BaseModel):
    """User profile returned to the frontend."""

    id: str
    username: str
    email: str | None = None
    avatar_url: str | None = None
    role: str

    model_config = {"from_attributes": True}


class TokenResponse(BaseModel):
    """JWT token response after successful OAuth login."""

    access_token: str
    token_type: str = "bearer"
