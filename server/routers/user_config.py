"""用户配置路由：每个用户隔离的键值对配置管理。"""

from __future__ import annotations

from typing import TYPE_CHECKING

from fastapi import APIRouter, Depends, HTTPException, status

from server.deps import get_current_user, get_db
from server.schemas.user_config import UserConfigResponse, UserConfigSet
from server.services import user_config as config_service

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

    from server.models.user import User

router = APIRouter(prefix="/api/v1/user", tags=["user-config"])


@router.get("/configs", response_model=list[UserConfigResponse])
async def list_configs(
    namespace: str | None = None,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[dict]:
    """列出当前用户的配置（敏感值脱敏）。"""
    return await config_service.get_configs(db, user.id, namespace)


@router.put("/configs", response_model=UserConfigResponse)
async def set_config(
    body: UserConfigSet,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """设置配置项（存在则更新，不存在则创建）。"""
    config = await config_service.set_config(
        db,
        user_id=user.id,
        namespace=body.namespace,
        key=body.key,
        value=body.value,
        is_secret=body.is_secret,
    )
    return {
        "namespace": config.namespace,
        "key": config.key,
        "value": "******" if config.is_secret else config.value,
        "is_secret": config.is_secret,
        "updated_at": config.updated_at,
    }


@router.delete("/configs/{namespace}/{key}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_config(
    namespace: str,
    key: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> None:
    """删除配置项。"""
    deleted = await config_service.delete_config(db, user.id, namespace, key)
    if not deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Config not found")
