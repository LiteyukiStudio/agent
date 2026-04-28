"""FastAPI 依赖注入辅助函数。"""

from __future__ import annotations

from typing import TYPE_CHECKING

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select

from server.config import settings
from server.database import async_session_factory
from server.services.auth import ROLE_ADMIN, ROLE_SUPERUSER, is_at_least, resolve_api_token, verify_jwt

if TYPE_CHECKING:
    from collections.abc import AsyncGenerator

    from sqlalchemy.ext.asyncio import AsyncSession

    from server.models.user import User

_bearer_scheme = HTTPBearer(auto_error=False)


async def get_db() -> AsyncGenerator[AsyncSession]:
    """生成一个异步数据库会话。"""
    async with async_session_factory() as session:
        yield session


async def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer_scheme),
    db: AsyncSession = Depends(get_db),
) -> User:
    """提取并验证认证令牌，支持 JWT 和 API Token 两种方式。

    JWT: 以 'eyJ' 开头的标准 JWT 令牌（网页端）。
    API Token: 以 'lys_' 开头的访问令牌（外部 API 调用）。
    """
    from server.models.user import User as UserModel

    if credentials is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")

    token = credentials.credentials

    # API Token 认证（lys_ 前缀）
    if token.startswith("lys_"):
        user = await resolve_api_token(db, token)
        if user is None:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired API token")
        return user

    # JWT 认证
    payload = verify_jwt(token, settings.secret_key, settings.jwt_algorithm)
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
    """类似 get_current_user，但未提供 token 时返回 None。"""
    if credentials is None:
        return None
    try:
        return await get_current_user(credentials, db)
    except HTTPException:
        return None


async def require_admin(user: User = Depends(get_current_user)) -> User:
    """确保当前用户至少是管理员（admin 或 superuser）。"""
    if not is_at_least(user.role, ROLE_ADMIN):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin access required")
    return user


async def require_superuser(user: User = Depends(get_current_user)) -> User:
    """确保当前用户是超级用户。"""
    if user.role != ROLE_SUPERUSER:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Superuser access required")
    return user
