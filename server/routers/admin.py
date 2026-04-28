"""Admin routes: OAuth provider and user management."""

from __future__ import annotations

from typing import TYPE_CHECKING

from fastapi import APIRouter, Depends, HTTPException, status

from server.deps import get_db, require_admin
from server.schemas.admin import OAuthProviderCreate, OAuthProviderResponse, OAuthProviderUpdate, UserUpdate
from server.schemas.auth import UserResponse
from server.services import admin as admin_service

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

    from server.models.user import User

router = APIRouter(prefix="/api/v1/admin", tags=["admin"])


# ---------------------------------------------------------------------------
# OAuth Providers
# ---------------------------------------------------------------------------


@router.get("/oauth-providers", response_model=list[OAuthProviderResponse])
async def list_providers(
    _user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> list[OAuthProviderResponse]:
    """List all OAuth providers (admin only)."""
    providers = await admin_service.list_providers(db)
    return [OAuthProviderResponse.model_validate(p) for p in providers]


@router.post("/oauth-providers", response_model=OAuthProviderResponse, status_code=status.HTTP_201_CREATED)
async def create_provider(
    body: OAuthProviderCreate,
    _user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> OAuthProviderResponse:
    """Create a new OAuth provider with automatic OIDC discovery (admin only)."""
    provider = await admin_service.create_provider(db, body)
    return OAuthProviderResponse.model_validate(provider)


@router.patch("/oauth-providers/{provider_id}", response_model=OAuthProviderResponse)
async def update_provider(
    provider_id: str,
    body: OAuthProviderUpdate,
    _user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> OAuthProviderResponse:
    """Update an OAuth provider (admin only)."""
    provider = await admin_service.update_provider(db, provider_id, body)
    if provider is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Provider not found")
    return OAuthProviderResponse.model_validate(provider)


@router.delete("/oauth-providers/{provider_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_provider(
    provider_id: str,
    _user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> None:
    """Delete an OAuth provider (admin only)."""
    deleted = await admin_service.delete_provider(db, provider_id)
    if not deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Provider not found")


# ---------------------------------------------------------------------------
# Users
# ---------------------------------------------------------------------------


@router.get("/users", response_model=list[UserResponse])
async def list_users(
    page: int = 1,
    limit: int = 50,
    _user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> list[UserResponse]:
    """List all users with pagination (admin only)."""
    users = await admin_service.list_users(db, page, limit)
    return [UserResponse.model_validate(u) for u in users]


@router.patch("/users/{user_id}", response_model=UserResponse)
async def update_user(
    user_id: str,
    body: UserUpdate,
    _user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> UserResponse:
    """Update a user's role (admin only)."""
    user = await admin_service.update_user_role(db, user_id, body)
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    return UserResponse.model_validate(user)
