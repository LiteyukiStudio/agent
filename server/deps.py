"""FastAPI dependency injection helpers."""

from __future__ import annotations

from typing import TYPE_CHECKING

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select

from server.config import settings
from server.database import async_session_factory
from server.services.auth import verify_jwt

if TYPE_CHECKING:
    from collections.abc import AsyncGenerator

    from sqlalchemy.ext.asyncio import AsyncSession

    from server.models.user import User

_bearer_scheme = HTTPBearer(auto_error=False)


async def get_db() -> AsyncGenerator[AsyncSession]:
    """Yield an async database session."""
    async with async_session_factory() as session:
        yield session


async def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer_scheme),
    db: AsyncSession = Depends(get_db),
) -> User:
    """Extract and validate the JWT, then return the corresponding User."""
    from server.models.user import User as UserModel

    if credentials is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")
    payload = verify_jwt(credentials.credentials, settings.secret_key, settings.jwt_algorithm)
    if payload is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired token")
    user_id: str | None = payload.get("sub")
    if user_id is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token payload")
    result = await db.execute(select(UserModel).where(UserModel.id == user_id))
    user = result.scalar_one_or_none()
    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")
    return user


async def get_optional_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer_scheme),
    db: AsyncSession = Depends(get_db),
) -> User | None:
    """Like get_current_user but returns None if no token is provided."""
    from server.models.user import User as UserModel

    if credentials is None:
        return None
    payload = verify_jwt(credentials.credentials, settings.secret_key, settings.jwt_algorithm)
    if payload is None:
        return None
    user_id: str | None = payload.get("sub")
    if user_id is None:
        return None
    result = await db.execute(select(UserModel).where(UserModel.id == user_id))
    return result.scalar_one_or_none()


async def require_admin(user: User = Depends(get_current_user)) -> User:
    """Ensure the current user has admin role."""
    if user.role != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin access required")
    return user
