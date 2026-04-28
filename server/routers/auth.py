"""OAuth authentication routes."""

from __future__ import annotations

import secrets
from typing import TYPE_CHECKING

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import RedirectResponse
from sqlalchemy import select

from server.config import settings
from server.deps import get_current_user, get_db
from server.models.oauth_provider import OAuthProvider
from server.schemas.auth import ProviderInfo, TokenResponse, UserResponse
from server.services.auth import build_authorization_url, create_jwt, exchange_code, find_or_create_user

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

    from server.models.user import User

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])

# In-memory state store for CSRF protection (production should use Redis/DB)
_oauth_states: dict[str, str] = {}


@router.get("/providers", response_model=list[ProviderInfo])
async def list_providers(db: AsyncSession = Depends(get_db)) -> list[ProviderInfo]:
    """List all enabled OAuth providers (public endpoint)."""
    result = await db.execute(select(OAuthProvider).where(OAuthProvider.enabled.is_(True)))
    providers = result.scalars().all()
    return [ProviderInfo(id=p.id, name=p.name, issuer_url=p.issuer_url) for p in providers]


@router.get("/login/{provider_id}")
async def login(provider_id: str, db: AsyncSession = Depends(get_db)) -> RedirectResponse:
    """Redirect to the OAuth provider's authorization page."""
    result = await db.execute(
        select(OAuthProvider).where(OAuthProvider.id == provider_id, OAuthProvider.enabled.is_(True)),
    )
    provider = result.scalar_one_or_none()
    if provider is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Provider not found")
    if not provider.authorization_endpoint:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Provider has no authorization endpoint configured",
        )

    state = secrets.token_urlsafe(32)
    _oauth_states[state] = provider_id
    redirect_uri = f"{settings.server_host}/api/v1/auth/callback/{provider_id}"
    url = build_authorization_url(provider, redirect_uri, state)
    return RedirectResponse(url=url)


@router.get("/callback/{provider_id}")
async def callback(
    provider_id: str,
    code: str,
    state: str = "",
    db: AsyncSession = Depends(get_db),
) -> TokenResponse:
    """Handle the OAuth callback: exchange code, create/find user, return JWT."""
    # Verify state
    if state and _oauth_states.pop(state, None) != provider_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid OAuth state")

    result = await db.execute(select(OAuthProvider).where(OAuthProvider.id == provider_id))
    provider = result.scalar_one_or_none()
    if provider is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Provider not found")

    redirect_uri = f"{settings.server_host}/api/v1/auth/callback/{provider_id}"

    try:
        userinfo = await exchange_code(provider, code, redirect_uri)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"OAuth code exchange failed: {e}",
        ) from e

    user = await find_or_create_user(db, provider_id, userinfo)
    token = create_jwt(user)
    return TokenResponse(access_token=token)


@router.get("/me", response_model=UserResponse)
async def me(user: User = Depends(get_current_user)) -> UserResponse:
    """Get the current authenticated user's profile."""
    return UserResponse.model_validate(user)
