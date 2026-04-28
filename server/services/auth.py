"""Authentication service: OIDC discovery, OAuth code exchange, JWT, user management."""

from __future__ import annotations

import secrets
from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING

import httpx
from jose import JWTError, jwt
from sqlalchemy import func, select

from server.config import settings
from server.models.user import User

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

    from server.models.oauth_provider import OAuthProvider


async def discover_oidc(issuer_url: str) -> dict[str, str]:
    """Fetch OIDC discovery document from the issuer's well-known endpoint.

    Args:
        issuer_url: The OAuth issuer base URL, e.g. https://git.liteyuki.icu

    Returns:
        Dict with authorization_endpoint, token_endpoint, userinfo_endpoint.
    """
    url = issuer_url.rstrip("/") + "/.well-known/openid-configuration"
    async with httpx.AsyncClient(timeout=15) as client:
        resp = await client.get(url)
        resp.raise_for_status()
        data = resp.json()
    return {
        "authorization_endpoint": data.get("authorization_endpoint", ""),
        "token_endpoint": data.get("token_endpoint", ""),
        "userinfo_endpoint": data.get("userinfo_endpoint", ""),
    }


async def exchange_code(
    provider: OAuthProvider,
    code: str,
    redirect_uri: str,
) -> dict:
    """Exchange an authorization code for an access token, then fetch user info.

    Args:
        provider: The OAuthProvider with token/userinfo endpoints.
        code: The authorization code from the OAuth callback.
        redirect_uri: The redirect URI used in the authorization request.

    Returns:
        User info dict from the provider's userinfo endpoint.
    """
    async with httpx.AsyncClient(timeout=15) as client:
        # Exchange code for token
        token_resp = await client.post(
            provider.token_endpoint or "",
            data={
                "grant_type": "authorization_code",
                "code": code,
                "redirect_uri": redirect_uri,
                "client_id": provider.client_id,
                "client_secret": provider.client_secret,
            },
            headers={"Accept": "application/json"},
        )
        token_resp.raise_for_status()
        token_data = token_resp.json()
        access_token = token_data.get("access_token", "")

        # Fetch user info
        userinfo_resp = await client.get(
            provider.userinfo_endpoint or "",
            headers={"Authorization": f"Bearer {access_token}"},
        )
        userinfo_resp.raise_for_status()
        return userinfo_resp.json()


async def find_or_create_user(
    db: AsyncSession,
    provider_id: str,
    userinfo: dict,
) -> User:
    """Find an existing user or create a new one from OAuth user info.

    The first user ever registered automatically gets the 'admin' role.

    Args:
        db: Async database session.
        provider_id: The OAuthProvider ID.
        userinfo: User info dict from the OAuth provider.

    Returns:
        The User object.
    """
    # Try to extract a stable user ID — providers vary in field names
    oauth_user_id = str(
        userinfo.get("sub") or userinfo.get("id") or userinfo.get("login") or secrets.token_hex(16),
    )

    result = await db.execute(
        select(User).where(User.oauth_provider_id == provider_id, User.oauth_user_id == oauth_user_id),
    )
    user = result.scalar_one_or_none()

    if user is not None:
        # Update mutable fields
        user.username = userinfo.get("login") or userinfo.get("preferred_username") or user.username
        user.email = userinfo.get("email") or user.email
        user.avatar_url = userinfo.get("avatar_url") or userinfo.get("picture") or user.avatar_url
        await db.commit()
        await db.refresh(user)
        return user

    # Check if this is the first user ever
    count_result = await db.execute(select(func.count()).select_from(User))
    total_users = count_result.scalar() or 0
    role = "admin" if total_users == 0 else "user"

    user = User(
        username=userinfo.get("login") or userinfo.get("preferred_username") or "user",
        email=userinfo.get("email"),
        avatar_url=userinfo.get("avatar_url") or userinfo.get("picture"),
        role=role,
        oauth_provider_id=provider_id,
        oauth_user_id=oauth_user_id,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user


def create_jwt(user: User) -> str:
    """Sign a JWT containing the user's ID and role.

    Args:
        user: The authenticated User.

    Returns:
        Encoded JWT string.
    """
    now = datetime.now(tz=UTC)
    payload = {
        "sub": user.id,
        "role": user.role,
        "iat": now,
        "exp": now + timedelta(hours=settings.jwt_expire_hours),
    }
    return jwt.encode(payload, settings.secret_key, algorithm=settings.jwt_algorithm)


def verify_jwt(token: str, secret_key: str, algorithm: str) -> dict | None:
    """Decode and verify a JWT token.

    Args:
        token: The JWT string.
        secret_key: Secret used for verification.
        algorithm: JWT algorithm.

    Returns:
        Decoded payload dict, or None if invalid/expired.
    """
    try:
        return jwt.decode(token, secret_key, algorithms=[algorithm])
    except JWTError:
        return None


def build_authorization_url(provider: OAuthProvider, redirect_uri: str, state: str) -> str:
    """Build the OAuth authorization URL to redirect the user to.

    Args:
        provider: The OAuthProvider.
        redirect_uri: Where the provider should redirect back to.
        state: CSRF state parameter.

    Returns:
        Full authorization URL string.
    """
    params = {
        "response_type": "code",
        "client_id": provider.client_id,
        "redirect_uri": redirect_uri,
        "scope": "openid profile email",
        "state": state,
    }
    query = "&".join(f"{k}={v}" for k, v in params.items())
    return f"{provider.authorization_endpoint}?{query}"
