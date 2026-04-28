"""Admin service: OAuth provider and user management."""

from __future__ import annotations

import contextlib
from typing import TYPE_CHECKING

from sqlalchemy import select

from server.models.oauth_provider import OAuthProvider
from server.models.user import User
from server.services.auth import discover_oidc

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

    from server.schemas.admin import OAuthProviderCreate, OAuthProviderUpdate, UserUpdate


async def list_providers(db: AsyncSession) -> list[OAuthProvider]:
    """List all OAuth providers.

    Args:
        db: Async database session.

    Returns:
        List of all OAuthProvider records.
    """
    result = await db.execute(select(OAuthProvider).order_by(OAuthProvider.created_at.desc()))
    return list(result.scalars().all())


async def create_provider(db: AsyncSession, data: OAuthProviderCreate) -> OAuthProvider:
    """Create a new OAuth provider with automatic OIDC discovery.

    Args:
        db: Async database session.
        data: Provider creation data.

    Returns:
        The created OAuthProvider.
    """
    # Auto-discover OIDC endpoints (non-fatal if it fails)
    oidc_info: dict[str, str] = {}
    with contextlib.suppress(Exception):
        oidc_info = await discover_oidc(data.issuer_url)

    provider = OAuthProvider(
        name=data.name,
        issuer_url=data.issuer_url,
        client_id=data.client_id,
        client_secret=data.client_secret,
        authorization_endpoint=oidc_info.get("authorization_endpoint"),
        token_endpoint=oidc_info.get("token_endpoint"),
        userinfo_endpoint=oidc_info.get("userinfo_endpoint"),
    )
    db.add(provider)
    await db.commit()
    await db.refresh(provider)
    return provider


async def update_provider(
    db: AsyncSession,
    provider_id: str,
    data: OAuthProviderUpdate,
) -> OAuthProvider | None:
    """Update an existing OAuth provider. Re-discovers OIDC if issuer_url changes.

    Args:
        db: Async database session.
        provider_id: The provider ID to update.
        data: Partial update data.

    Returns:
        The updated OAuthProvider, or None if not found.
    """
    result = await db.execute(select(OAuthProvider).where(OAuthProvider.id == provider_id))
    provider = result.scalar_one_or_none()
    if provider is None:
        return None

    update_fields = data.model_dump(exclude_unset=True)
    for key, value in update_fields.items():
        setattr(provider, key, value)

    # Re-discover if issuer_url changed
    if "issuer_url" in update_fields:
        with contextlib.suppress(Exception):
            oidc_info = await discover_oidc(provider.issuer_url)
            provider.authorization_endpoint = oidc_info.get("authorization_endpoint")
            provider.token_endpoint = oidc_info.get("token_endpoint")
            provider.userinfo_endpoint = oidc_info.get("userinfo_endpoint")

    await db.commit()
    await db.refresh(provider)
    return provider


async def delete_provider(db: AsyncSession, provider_id: str) -> bool:
    """Delete an OAuth provider.

    Args:
        db: Async database session.
        provider_id: The provider ID to delete.

    Returns:
        True if deleted, False if not found.
    """
    result = await db.execute(select(OAuthProvider).where(OAuthProvider.id == provider_id))
    provider = result.scalar_one_or_none()
    if provider is None:
        return False
    await db.delete(provider)
    await db.commit()
    return True


async def list_users(db: AsyncSession, page: int = 1, limit: int = 50) -> list[User]:
    """List users with pagination.

    Args:
        db: Async database session.
        page: Page number (1-indexed).
        limit: Results per page.

    Returns:
        List of User records.
    """
    offset = (page - 1) * limit
    result = await db.execute(
        select(User).order_by(User.created_at.desc()).offset(offset).limit(limit),
    )
    return list(result.scalars().all())


async def update_user_role(db: AsyncSession, user_id: str, data: UserUpdate) -> User | None:
    """Update a user's role.

    Args:
        db: Async database session.
        user_id: The user ID to update.
        data: Update data containing the new role.

    Returns:
        The updated User, or None if not found.
    """
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if user is None:
        return None
    user.role = data.role
    await db.commit()
    await db.refresh(user)
    return user
