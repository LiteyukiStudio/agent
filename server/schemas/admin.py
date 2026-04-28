"""Admin-related Pydantic schemas."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel


class OAuthProviderCreate(BaseModel):
    """Request body for creating a new OAuth provider."""

    name: str
    issuer_url: str
    client_id: str
    client_secret: str


class OAuthProviderUpdate(BaseModel):
    """Request body for updating an OAuth provider (all fields optional)."""

    name: str | None = None
    issuer_url: str | None = None
    client_id: str | None = None
    client_secret: str | None = None
    enabled: bool | None = None


class OAuthProviderResponse(BaseModel):
    """OAuth provider info (excludes client_secret)."""

    id: str
    name: str
    issuer_url: str
    client_id: str
    enabled: bool
    authorization_endpoint: str | None = None
    token_endpoint: str | None = None
    userinfo_endpoint: str | None = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class UserUpdate(BaseModel):
    """Request body for updating a user's role."""

    role: str
