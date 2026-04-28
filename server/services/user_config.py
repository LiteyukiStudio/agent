"""用户配置服务：隔离存储每个用户的 Agent 凭据和设置。"""

from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import select

from server.models.user_config import UserConfig

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession


async def get_configs(
    db: AsyncSession,
    user_id: str,
    namespace: str | None = None,
) -> list[dict]:
    """获取用户配置列表（敏感值脱敏）。

    Args:
        db: 异步数据库会话。
        user_id: 用户 ID。
        namespace: 可选过滤命名空间。

    Returns:
        配置列表，敏感值显示为 "******"。
    """
    query = select(UserConfig).where(UserConfig.user_id == user_id)
    if namespace:
        query = query.where(UserConfig.namespace == namespace)
    query = query.order_by(UserConfig.namespace, UserConfig.key)

    result = await db.execute(query)
    configs = result.scalars().all()

    return [
        {
            "namespace": c.namespace,
            "key": c.key,
            "value": "******" if c.is_secret else c.value,
            "is_secret": c.is_secret,
            "updated_at": c.updated_at,
        }
        for c in configs
    ]


async def set_config(
    db: AsyncSession,
    user_id: str,
    namespace: str,
    key: str,
    value: str,
    is_secret: bool = False,
) -> UserConfig:
    """设置用户配置（存在则更新，不存在则创建）。

    Args:
        db: 异步数据库会话。
        user_id: 用户 ID — 严格隔离，只能操作自己的配置。
        namespace: 命名空间（如 "gitea"）。
        key: 配置键（如 "base_url"）。
        value: 配置值。
        is_secret: 是否为敏感值。

    Returns:
        创建或更新后的 UserConfig。
    """
    result = await db.execute(
        select(UserConfig).where(
            UserConfig.user_id == user_id,
            UserConfig.namespace == namespace,
            UserConfig.key == key,
        ),
    )
    config = result.scalar_one_or_none()

    if config:
        config.value = value
        config.is_secret = is_secret
    else:
        config = UserConfig(
            user_id=user_id,
            namespace=namespace,
            key=key,
            value=value,
            is_secret=is_secret,
        )
        db.add(config)

    await db.commit()
    await db.refresh(config)
    return config


async def delete_config(
    db: AsyncSession,
    user_id: str,
    namespace: str,
    key: str,
) -> bool:
    """删除用户配置。

    Args:
        db: 异步数据库会话。
        user_id: 用户 ID — 严格隔离。
        namespace: 命名空间。
        key: 配置键。

    Returns:
        已删除返回 True，未找到返回 False。
    """
    result = await db.execute(
        select(UserConfig).where(
            UserConfig.user_id == user_id,
            UserConfig.namespace == namespace,
            UserConfig.key == key,
        ),
    )
    config = result.scalar_one_or_none()
    if config is None:
        return False
    await db.delete(config)
    await db.commit()
    return True


async def get_raw_value(
    db: AsyncSession,
    user_id: str,
    namespace: str,
    key: str,
) -> str | None:
    """获取配置原始值（内部使用，不脱敏）。

    Args:
        db: 异步数据库会话。
        user_id: 用户 ID。
        namespace: 命名空间。
        key: 配置键。

    Returns:
        配置值字符串，不存在返回 None。
    """
    result = await db.execute(
        select(UserConfig.value).where(
            UserConfig.user_id == user_id,
            UserConfig.namespace == namespace,
            UserConfig.key == key,
        ),
    )
    return result.scalar_one_or_none()


async def get_raw_configs_by_namespace(
    db: AsyncSession,
    user_id: str,
    namespace: str,
) -> dict[str, str]:
    """获取某命名空间下的所有原始配置（内部使用，用于预加载到 ADK state）。

    Args:
        db: 异步数据库会话。
        user_id: 用户 ID。
        namespace: 命名空间。

    Returns:
        key → value 的字典。
    """
    result = await db.execute(
        select(UserConfig).where(
            UserConfig.user_id == user_id,
            UserConfig.namespace == namespace,
        ),
    )
    return {c.key: c.value for c in result.scalars().all()}


async def get_all_raw_configs(
    db: AsyncSession,
    user_id: str,
) -> dict[str, dict[str, str]]:
    """获取用户所有命名空间的原始配置（用于预加载到 ADK session state）。

    Args:
        db: 异步数据库会话。
        user_id: 用户 ID。

    Returns:
        namespace → {key: value} 的嵌套字典。
    """
    result = await db.execute(
        select(UserConfig).where(UserConfig.user_id == user_id),
    )
    configs: dict[str, dict[str, str]] = {}
    for c in result.scalars().all():
        if c.namespace not in configs:
            configs[c.namespace] = {}
        configs[c.namespace][c.key] = c.value
    return configs
