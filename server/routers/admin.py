"""管理路由：OAuth 提供商和用户管理。"""

from __future__ import annotations

from typing import TYPE_CHECKING

from fastapi import APIRouter, Depends, HTTPException, status

from server.config import settings
from server.deps import get_db, require_admin
from server.schemas.admin import (
    OAuthProviderCreate,
    OAuthProviderResponse,
    OAuthProviderUpdate,
    UserUpdate,
)
from server.schemas.auth import UserResponse
from server.services import admin as admin_service

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

    from server.models.oauth_provider import OAuthProvider
    from server.models.user import User

router = APIRouter(prefix="/api/v1/admin", tags=["admin"])


async def _provider_response(provider: OAuthProvider, db: AsyncSession) -> OAuthProviderResponse:
    """将 ORM 对象转为响应模型，附加 callback_url 和 allowed_groups。"""
    resp = OAuthProviderResponse.model_validate(provider)
    resp.callback_url = f"{settings.server_host}/api/v1/auth/oauth/callback/{provider.id}"
    # 从 access_list_entries 读取 groups 拼成逗号分隔字符串
    entries = await admin_service.list_access_entries(db, provider.id)
    resp.allowed_groups = ",".join(e.group_name for e in entries)
    return resp


# ---------------------------------------------------------------------------
# OAuth 提供商
# ---------------------------------------------------------------------------


@router.get("/oauth-providers", response_model=list[OAuthProviderResponse])
async def list_providers(
    _user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> list[OAuthProviderResponse]:
    """列出所有 OAuth 提供商（仅管理员）。"""
    providers = await admin_service.list_providers(db)
    return [await _provider_response(p, db) for p in providers]


@router.post("/oauth-providers", response_model=OAuthProviderResponse, status_code=status.HTTP_201_CREATED)
async def create_provider(
    body: OAuthProviderCreate,
    _user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> OAuthProviderResponse:
    """创建新的 OAuth 提供商，自动进行 OIDC 发现（仅管理员）。"""
    provider = await admin_service.create_provider(db, body)
    # 同步 groups 到 access_list_entries
    if body.allowed_groups:
        await admin_service.sync_access_groups(db, provider.id, body.allowed_groups)
    return await _provider_response(provider, db)


@router.patch("/oauth-providers/{provider_id}", response_model=OAuthProviderResponse)
async def update_provider(
    provider_id: str,
    body: OAuthProviderUpdate,
    _user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> OAuthProviderResponse:
    """更新 OAuth 提供商（仅管理员）。"""
    provider = await admin_service.update_provider(db, provider_id, body)
    if provider is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Provider not found")
    # 同步 groups（传了 allowed_groups 字段才同步）
    if body.allowed_groups is not None:
        await admin_service.sync_access_groups(db, provider.id, body.allowed_groups)
    return await _provider_response(provider, db)


@router.delete("/oauth-providers/{provider_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_provider(
    provider_id: str,
    _user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> None:
    """删除 OAuth 提供商（仅管理员）。"""
    deleted = await admin_service.delete_provider(db, provider_id)
    if not deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Provider not found")


# ---------------------------------------------------------------------------
# 用户
# ---------------------------------------------------------------------------


@router.get("/users", response_model=list[UserResponse])
async def list_users(
    page: int = 1,
    limit: int = 50,
    _user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> list[UserResponse]:
    """分页列出所有用户（仅管理员）。"""
    users = await admin_service.list_users(db, page, limit)
    return [UserResponse.model_validate(u) for u in users]


@router.patch("/users/{user_id}", response_model=UserResponse)
async def update_user(
    user_id: str,
    body: UserUpdate,
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> UserResponse:
    """更新用户角色。

    权限规则：
    - 不能修改 superuser 的角色
    - admin 只能将用户设为 user
    - superuser 可以将用户设为 user 或 admin
    - superuser 角色不可通过此接口分配
    """
    from server.services.auth import ROLE_ADMIN, ROLE_SUPERUSER, ROLE_USER

    # 不允许通过 API 分配 superuser
    if body.role == ROLE_SUPERUSER:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cannot assign superuser role via API",
        )

    # 查询目标用户
    target = await admin_service.get_user_by_id(db, user_id)
    if target is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    # 不能修改 superuser 的角色
    if target.role == ROLE_SUPERUSER:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cannot modify superuser role",
        )

    # admin 只能设为 user，不能提权为 admin
    if current_user.role == ROLE_ADMIN and body.role == ROLE_ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only superuser can assign admin role",
        )

    # admin 不能修改其他 admin 的角色
    if current_user.role == ROLE_ADMIN and target.role == ROLE_ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin cannot modify another admin",
        )

    # 验证角色值
    if body.role not in (ROLE_USER, ROLE_ADMIN):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f'Invalid role: {body.role}. Must be "user" or "admin"',
        )

    user = await admin_service.update_user_role(db, user_id, body)
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    return UserResponse.model_validate(user)


# ---------------------------------------------------------------------------
# 管理员查看用户会话（只读）
# ---------------------------------------------------------------------------


@router.get("/users/{user_id}/sessions")
async def admin_list_user_sessions(
    user_id: str,
    _admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """管理员查看指定用户的会话列表（只读）。"""
    from sqlalchemy import select as sa_select

    from server.models.chat_session import ChatSession

    result = await db.execute(
        sa_select(ChatSession).where(ChatSession.user_id == user_id).order_by(ChatSession.created_at.desc()),
    )
    sessions = result.scalars().all()
    return {
        "sessions": [
            {
                "id": s.id,
                "title": s.title,
                "created_at": s.created_at.isoformat() if s.created_at else None,
                "updated_at": s.updated_at.isoformat() if hasattr(s, "updated_at") and s.updated_at else None,
                "is_public": s.is_public,
            }
            for s in sessions
        ],
    }


@router.get("/users/{user_id}/sessions/{session_id}/messages")
async def admin_view_session_messages(
    user_id: str,
    session_id: str,
    _admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """管理员查看指定用户的某个会话的消息（只读）。"""
    from sqlalchemy import select as sa_select

    from server.models.chat_session import ChatSession
    from server.models.message import Message

    # 验证会话属于该用户
    result = await db.execute(
        sa_select(ChatSession).where(ChatSession.id == session_id, ChatSession.user_id == user_id),
    )
    chat_session = result.scalar_one_or_none()
    if chat_session is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found")

    result = await db.execute(
        sa_select(Message).where(Message.session_id == session_id).order_by(Message.created_at),
    )
    messages = result.scalars().all()

    return {
        "session": {
            "id": chat_session.id,
            "title": chat_session.title,
            "user_id": user_id,
        },
        "messages": [
            {
                "id": m.id,
                "role": m.role,
                "content": m.content,
                "tool_calls": m.tool_calls,
                "created_at": m.created_at.isoformat() if m.created_at else None,
            }
            for m in messages
        ],
    }
