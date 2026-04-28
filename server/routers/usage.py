"""用量计费路由：配额管理和用量查询。"""

from __future__ import annotations

from typing import TYPE_CHECKING

from fastapi import APIRouter, Depends, HTTPException, status

from server.deps import get_current_user, get_db, require_admin
from server.schemas.usage import (
    AssignQuotaPlan,
    GlobalUsageStats,
    MyUsageResponse,
    QuotaPlanCreate,
    QuotaPlanResponse,
    QuotaPlanUpdate,
    UserUsageResponse,
)
from server.services import usage as usage_service

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

    from server.models.user import User

router = APIRouter(tags=["usage"])


# ---------------------------------------------------------------------------
# 用户端
# ---------------------------------------------------------------------------


@router.get("/api/v1/usage/me", response_model=MyUsageResponse)
async def my_usage(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> MyUsageResponse:
    """查看当前用户的用量和剩余配额。"""
    data = await usage_service.get_my_usage(db, user.id)
    return MyUsageResponse(**data)


# ---------------------------------------------------------------------------
# 管理端 — 用量统计
# ---------------------------------------------------------------------------


@router.get("/api/v1/admin/usage/stats", response_model=GlobalUsageStats)
async def global_stats(
    _user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> GlobalUsageStats:
    """获取全局用量统计（仅管理员）。"""
    data = await usage_service.get_global_stats(db)
    return GlobalUsageStats(**data)


@router.get("/api/v1/admin/usage/users/{user_id}", response_model=UserUsageResponse)
async def user_usage(
    user_id: str,
    _user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> UserUsageResponse:
    """查看指定用户的用量（仅管理员）。"""
    from sqlalchemy import select

    from server.models.user import User as UserModel

    result = await db.execute(select(UserModel).where(UserModel.id == user_id))
    target_user = result.scalar_one_or_none()
    if target_user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    data = await usage_service.get_my_usage(db, user_id)
    return UserUsageResponse(user_id=user_id, username=target_user.username, **data)


# ---------------------------------------------------------------------------
# 管理端 — 配额方案 CRUD
# ---------------------------------------------------------------------------


@router.get("/api/v1/admin/quota-plans", response_model=list[QuotaPlanResponse])
async def list_plans(
    _user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> list[QuotaPlanResponse]:
    """列出所有配额方案（仅管理员）。"""
    plans = await usage_service.list_plans(db)
    return [QuotaPlanResponse.model_validate(p) for p in plans]


@router.post("/api/v1/admin/quota-plans", response_model=QuotaPlanResponse, status_code=status.HTTP_201_CREATED)
async def create_plan(
    body: QuotaPlanCreate,
    _user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> QuotaPlanResponse:
    """创建配额方案（仅管理员）。"""
    plan = await usage_service.create_plan(db, body)
    return QuotaPlanResponse.model_validate(plan)


@router.patch("/api/v1/admin/quota-plans/{plan_id}", response_model=QuotaPlanResponse)
async def update_plan(
    plan_id: str,
    body: QuotaPlanUpdate,
    _user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> QuotaPlanResponse:
    """更新配额方案（仅管理员）。"""
    plan = await usage_service.update_plan(db, plan_id, body)
    if plan is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Plan not found")
    return QuotaPlanResponse.model_validate(plan)


@router.delete("/api/v1/admin/quota-plans/{plan_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_plan(
    plan_id: str,
    _user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> None:
    """删除配额方案（仅管理员）。"""
    deleted = await usage_service.delete_plan(db, plan_id)
    if not deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Plan not found")


# ---------------------------------------------------------------------------
# 管理端 — 用户配额分配
# ---------------------------------------------------------------------------


@router.patch("/api/v1/admin/users/{user_id}/quota", status_code=status.HTTP_204_NO_CONTENT)
async def assign_quota(
    user_id: str,
    body: AssignQuotaPlan,
    _user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> None:
    """给用户分配配额方案（仅管理员）。"""
    success = await usage_service.assign_plan(db, user_id, body.quota_plan_id)
    if not success:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
