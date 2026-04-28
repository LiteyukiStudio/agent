"""管理路由：OAuth 提供商和用户管理。"""

from __future__ import annotations

from typing import TYPE_CHECKING

from fastapi import APIRouter, Depends, HTTPException, status

from server.deps import get_db, require_admin
from server.schemas.admin import (
    AccessListEntryCreate,
    AccessListEntryResponse,
    OAuthProviderCreate,
    OAuthProviderResponse,
    OAuthProviderUpdate,
    UserUpdate,
)
from server.schemas.auth import UserResponse
from server.services import admin as admin_service

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

    from server.models.user import User

router = APIRouter(prefix="/api/v1/admin", tags=["admin"])


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
    return [OAuthProviderResponse.model_validate(p) for p in providers]


@router.post("/oauth-providers", response_model=OAuthProviderResponse, status_code=status.HTTP_201_CREATED)
async def create_provider(
    body: OAuthProviderCreate,
    _user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> OAuthProviderResponse:
    """创建新的 OAuth 提供商，自动进行 OIDC 发现（仅管理员）。"""
    provider = await admin_service.create_provider(db, body)
    return OAuthProviderResponse.model_validate(provider)


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
    return OAuthProviderResponse.model_validate(provider)


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
# 访问名单
# ---------------------------------------------------------------------------


@router.get("/oauth-providers/{provider_id}/access-list", response_model=list[AccessListEntryResponse])
async def list_access_entries(
    provider_id: str,
    _user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> list[AccessListEntryResponse]:
    """列出 OAuth 提供商的访问名单（仅管理员）。"""
    entries = await admin_service.list_access_entries(db, provider_id)
    return [AccessListEntryResponse.model_validate(e) for e in entries]


@router.post(
    "/oauth-providers/{provider_id}/access-list",
    response_model=AccessListEntryResponse,
    status_code=status.HTTP_201_CREATED,
)
async def add_access_entry(
    provider_id: str,
    body: AccessListEntryCreate,
    _user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> AccessListEntryResponse:
    """添加访问名单条目（仅管理员）。"""
    entry = await admin_service.add_access_entry(db, provider_id, body)
    return AccessListEntryResponse.model_validate(entry)


@router.delete(
    "/oauth-providers/{provider_id}/access-list/{entry_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def remove_access_entry(
    provider_id: str,
    entry_id: str,
    _user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> None:
    """删除访问名单条目（仅管理员）。"""
    deleted = await admin_service.remove_access_entry(db, provider_id, entry_id)
    if not deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Entry not found")
