"""管理服务：OAuth 提供商和用户管理。"""

from __future__ import annotations

import contextlib
from typing import TYPE_CHECKING

from sqlalchemy import select

from server.models.access_list import AccessListEntry
from server.models.oauth_provider import OAuthProvider
from server.models.user import User
from server.services.auth import discover_oidc

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

    from server.schemas.admin import AccessListEntryCreate, OAuthProviderCreate, OAuthProviderUpdate, UserUpdate


async def list_providers(db: AsyncSession) -> list[OAuthProvider]:
    """列出所有 OAuth 提供商。

    Args:
        db: 异步数据库会话。

    Returns:
        所有 OAuthProvider 记录列表。
    """
    result = await db.execute(select(OAuthProvider).order_by(OAuthProvider.created_at.desc()))
    return list(result.scalars().all())


async def create_provider(db: AsyncSession, data: OAuthProviderCreate) -> OAuthProvider:
    """创建新的 OAuth 提供商，自动进行 OIDC 发现。

    Args:
        db: 异步数据库会话。
        data: 提供商创建数据。

    Returns:
        创建的 OAuthProvider 对象。
    """
    # 自动发现 OIDC 端点（失败不影响创建）
    oidc_info: dict[str, str] = {}
    with contextlib.suppress(Exception):
        oidc_info = await discover_oidc(data.issuer_url)

    provider = OAuthProvider(
        name=data.name,
        issuer_url=data.issuer_url,
        client_id=data.client_id,
        client_secret=data.client_secret,
        access_mode=data.access_mode,
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
    """更新现有 OAuth 提供商。issuer_url 变更时重新进行 OIDC 发现。

    Args:
        db: 异步数据库会话。
        provider_id: 要更新的提供商 ID。
        data: 部分更新数据。

    Returns:
        更新后的 OAuthProvider，未找到则返回 None。
    """
    result = await db.execute(select(OAuthProvider).where(OAuthProvider.id == provider_id))
    provider = result.scalar_one_or_none()
    if provider is None:
        return None

    update_fields = data.model_dump(exclude_unset=True)
    for key, value in update_fields.items():
        setattr(provider, key, value)

    # issuer_url 变更时重新发现
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
    """删除 OAuth 提供商。

    Args:
        db: 异步数据库会话。
        provider_id: 要删除的提供商 ID。

    Returns:
        已删除返回 True，未找到返回 False。
    """
    result = await db.execute(select(OAuthProvider).where(OAuthProvider.id == provider_id))
    provider = result.scalar_one_or_none()
    if provider is None:
        return False
    await db.delete(provider)
    await db.commit()
    return True


async def list_users(db: AsyncSession, page: int = 1, limit: int = 50) -> list[User]:
    """分页列出用户。"""
    offset = (page - 1) * limit
    result = await db.execute(
        select(User).order_by(User.created_at.desc()).offset(offset).limit(limit),
    )
    return list(result.scalars().all())


async def get_user_by_id(db: AsyncSession, user_id: str) -> User | None:
    """根据 ID 查找用户。"""
    result = await db.execute(select(User).where(User.id == user_id))
    return result.scalar_one_or_none()


async def update_user_role(db: AsyncSession, user_id: str, data: UserUpdate) -> User | None:
    """更新用户角色。

    Args:
        db: 异步数据库会话。
        user_id: 要更新的用户 ID。
        data: 包含新角色的更新数据。

    Returns:
        更新后的 User，未找到则返回 None。
    """
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if user is None:
        return None
    user.role = data.role
    await db.commit()
    await db.refresh(user)
    return user


# ---------------------------------------------------------------------------
# 访问名单
# ---------------------------------------------------------------------------


async def list_access_entries(db: AsyncSession, provider_id: str) -> list[AccessListEntry]:
    """列出提供商的所有访问名单条目。

    Args:
        db: 异步数据库会话。
        provider_id: OAuth 提供商 ID。

    Returns:
        AccessListEntry 列表。
    """
    result = await db.execute(
        select(AccessListEntry)
        .where(AccessListEntry.provider_id == provider_id)
        .order_by(AccessListEntry.created_at.desc()),
    )
    return list(result.scalars().all())


async def add_access_entry(
    db: AsyncSession,
    provider_id: str,
    data: AccessListEntryCreate,
) -> AccessListEntry:
    """添加访问名单条目。

    Args:
        db: 异步数据库会话。
        provider_id: OAuth 提供商 ID。
        data: 条目数据。

    Returns:
        创建的 AccessListEntry。
    """
    entry = AccessListEntry(
        provider_id=provider_id,
        group_name=data.group_name,
        note=data.note,
    )
    db.add(entry)
    await db.commit()
    await db.refresh(entry)
    return entry


async def remove_access_entry(db: AsyncSession, provider_id: str, entry_id: str) -> bool:
    """删除访问名单条目。

    Args:
        db: 异步数据库会话。
        provider_id: OAuth 提供商 ID。
        entry_id: 条目 ID。

    Returns:
        已删除返回 True，未找到返回 False。
    """
    result = await db.execute(
        select(AccessListEntry).where(
            AccessListEntry.id == entry_id,
            AccessListEntry.provider_id == provider_id,
        ),
    )
    entry = result.scalar_one_or_none()
    if entry is None:
        return False
    await db.delete(entry)
    await db.commit()
    return True


async def sync_access_groups(db: AsyncSession, provider_id: str, groups_csv: str) -> None:
    """同步 access_list_entries 表：以逗号分隔的 groups 字符串为准。

    删除不在列表中的旧条目，添加新条目。空字符串表示清空所有条目。
    """

    # 解析目标 group 列表
    target_groups = {g.strip().lower() for g in groups_csv.split(",") if g.strip()}

    # 获取现有条目
    result = await db.execute(
        select(AccessListEntry).where(AccessListEntry.provider_id == provider_id),
    )
    existing = list(result.scalars().all())
    existing_groups = {e.group_name.lower(): e for e in existing}

    # 删除不在目标列表中的
    for group_lower, entry in existing_groups.items():
        if group_lower not in target_groups:
            await db.delete(entry)

    # 添加新的
    for group in target_groups:
        if group not in existing_groups:
            # 保持原始大小写（从 csv 中取 strip 后的值）
            original = next(g.strip() for g in groups_csv.split(",") if g.strip().lower() == group)
            db.add(AccessListEntry(provider_id=provider_id, group_name=original))

    await db.commit()
