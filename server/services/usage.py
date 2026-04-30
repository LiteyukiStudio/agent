"""用量计费服务：配额检查、用量记录、统计查询。"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta
from typing import TYPE_CHECKING

from sqlalchemy import func, select

from server.models.quota_plan import QuotaPlan
from server.models.usage_record import UsageRecord
from server.models.user import User

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

    from server.schemas.usage import QuotaPlanCreate, QuotaPlanUpdate

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# 周期起始时间计算
# ---------------------------------------------------------------------------


def _today_start() -> datetime:
    """获取今天 00:00:00 UTC（naive，匹配数据库 TIMESTAMP WITHOUT TIME ZONE）。"""
    now = datetime.utcnow()
    return now.replace(hour=0, minute=0, second=0, microsecond=0)


def _week_start() -> datetime:
    """获取本周一 00:00:00 UTC（naive）。"""
    now = datetime.utcnow()
    monday = now - timedelta(days=now.weekday())
    return monday.replace(hour=0, minute=0, second=0, microsecond=0)


def _month_start() -> datetime:
    """获取本月 1 日 00:00:00 UTC（naive）。"""
    now = datetime.utcnow()
    return now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)


# ---------------------------------------------------------------------------
# 用量聚合
# ---------------------------------------------------------------------------


async def _get_usage_since(db: AsyncSession, user_id: str, since: datetime) -> int:
    """获取指定时间以来的累计 token 用量。"""
    result = await db.execute(
        select(func.coalesce(func.sum(UsageRecord.total_tokens), 0)).where(
            UsageRecord.user_id == user_id,
            UsageRecord.created_at >= since,
        ),
    )
    return result.scalar() or 0


# ---------------------------------------------------------------------------
# 配额检查
# ---------------------------------------------------------------------------


async def check_quota(db: AsyncSession, user: User) -> tuple[bool, str]:
    """检查用户是否有足够配额继续使用。

    管理员和超级用户不受限制。

    Returns:
        (allowed, reason) — allowed 为 False 时 reason 描述拒绝原因。
    """
    # 管理员不受限制
    if user.role in ("admin", "superuser"):
        return (True, "")

    # 无配额方案 → 尝试加载默认方案
    try:
        plan = await _get_user_plan(db, user)
    except Exception:
        logger.exception("check_quota: failed to load user plan for user=%s", user.id)
        return (True, "")  # 查询失败时放行，不阻塞用户

    if plan is None:
        return (True, "")  # 无方案也无默认方案，放行

    logger.info(
        "check_quota: user=%s plan=%s (daily=%s, weekly=%s, monthly=%s)",
        user.username,
        plan.name,
        plan.daily_tokens,
        plan.weekly_tokens,
        plan.monthly_tokens,
    )

    # 检查各周期
    try:
        if plan.daily_tokens is not None:
            used = await _get_usage_since(db, user.id, _today_start())
            logger.info("check_quota: daily used=%d / limit=%d", used, plan.daily_tokens)
            if used >= plan.daily_tokens:
                return (False, f"已达每日上限 {plan.daily_tokens} tokens")

        if plan.weekly_tokens is not None:
            used = await _get_usage_since(db, user.id, _week_start())
            logger.info("check_quota: weekly used=%d / limit=%d", used, plan.weekly_tokens)
            if used >= plan.weekly_tokens:
                return (False, f"已达每周上限 {plan.weekly_tokens} tokens")

        if plan.monthly_tokens is not None:
            used = await _get_usage_since(db, user.id, _month_start())
            logger.info("check_quota: monthly used=%d / limit=%d", used, plan.monthly_tokens)
            if used >= plan.monthly_tokens:
                return (False, f"已达每月上限 {plan.monthly_tokens} tokens")
    except Exception:
        logger.exception("check_quota: usage query failed for user=%s", user.id)
        return (True, "")  # 查询失败时放行

    return (True, "")


async def _get_user_plan(db: AsyncSession, user: User) -> QuotaPlan | None:
    """获取用户的配额方案，优先用户绑定的，其次默认方案。"""
    if user.quota_plan_id:
        result = await db.execute(select(QuotaPlan).where(QuotaPlan.id == user.quota_plan_id))
        plan = result.scalar_one_or_none()
        if plan:
            return plan

    # 尝试获取默认方案
    result = await db.execute(select(QuotaPlan).where(QuotaPlan.is_default.is_(True)))
    return result.scalar_one_or_none()


# ---------------------------------------------------------------------------
# 用量记录
# ---------------------------------------------------------------------------


async def record_usage(
    db: AsyncSession,
    user_id: str,
    model: str,
    input_tokens: int,
    output_tokens: int,
    agent_name: str = "root_agent",
    session_id: str | None = None,
) -> UsageRecord:
    """记录一次 LLM 调用的 token 用量。"""
    record = UsageRecord(
        user_id=user_id,
        model=model,
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        total_tokens=input_tokens + output_tokens,
        agent_name=agent_name,
        session_id=session_id,
    )
    db.add(record)
    await db.commit()
    return record


# ---------------------------------------------------------------------------
# 用量查询
# ---------------------------------------------------------------------------


async def get_my_usage(db: AsyncSession, user_id: str) -> dict:
    """获取用户的用量概览（今日/本周/本月 + 配额信息）。"""
    # 获取用户
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    plan = await _get_user_plan(db, user) if user else None

    daily_used = await _get_usage_since(db, user_id, _today_start())
    weekly_used = await _get_usage_since(db, user_id, _week_start())
    monthly_used = await _get_usage_since(db, user_id, _month_start())

    def _make_period(used: int, limit: int | None) -> dict:
        return {
            "used": used,
            "limit": limit,
            "remaining": (limit - used) if limit is not None else None,
        }

    return {
        "plan_name": plan.name if plan else None,
        "daily": _make_period(daily_used, plan.daily_tokens if plan else None),
        "weekly": _make_period(weekly_used, plan.weekly_tokens if plan else None),
        "monthly": _make_period(monthly_used, plan.monthly_tokens if plan else None),
    }


async def get_global_stats(db: AsyncSession) -> dict:
    """获取全局用量统计摘要。"""
    # 总用户数
    user_count = (await db.execute(select(func.count()).select_from(User))).scalar() or 0

    # 今日总 token
    today_tokens = await _get_usage_since_global(db, _today_start())

    # 本月总 token
    month_tokens = await _get_usage_since_global(db, _month_start())

    # 总记录数
    total_records = (await db.execute(select(func.count()).select_from(UsageRecord))).scalar() or 0

    return {
        "total_users": user_count,
        "total_tokens_today": today_tokens,
        "total_tokens_this_month": month_tokens,
        "total_records": total_records,
    }


async def _get_usage_since_global(db: AsyncSession, since: datetime) -> int:
    """获取所有用户在指定时间以来的累计 token 用量。"""
    result = await db.execute(
        select(func.coalesce(func.sum(UsageRecord.total_tokens), 0)).where(
            UsageRecord.created_at >= since,
        ),
    )
    return result.scalar() or 0


# ---------------------------------------------------------------------------
# 配额方案 CRUD
# ---------------------------------------------------------------------------


async def list_plans(db: AsyncSession) -> list[QuotaPlan]:
    """列出所有配额方案。"""
    result = await db.execute(select(QuotaPlan).order_by(QuotaPlan.created_at.desc()))
    return list(result.scalars().all())


async def create_plan(db: AsyncSession, data: QuotaPlanCreate) -> QuotaPlan:
    """创建新的配额方案。"""
    # 如果设为默认，先取消其他默认
    if data.is_default:
        await _clear_default_plans(db)

    plan = QuotaPlan(
        name=data.name,
        daily_tokens=data.daily_tokens,
        weekly_tokens=data.weekly_tokens,
        monthly_tokens=data.monthly_tokens,
        requests_per_minute=data.requests_per_minute,
        is_default=data.is_default,
    )
    db.add(plan)
    await db.commit()
    await db.refresh(plan)
    return plan


async def update_plan(db: AsyncSession, plan_id: str, data: QuotaPlanUpdate) -> QuotaPlan | None:
    """更新配额方案。"""
    result = await db.execute(select(QuotaPlan).where(QuotaPlan.id == plan_id))
    plan = result.scalar_one_or_none()
    if plan is None:
        return None

    update_fields = data.model_dump(exclude_unset=True)

    # 如果设为默认，先取消其他默认
    if update_fields.get("is_default"):
        await _clear_default_plans(db)

    for key, value in update_fields.items():
        setattr(plan, key, value)

    await db.commit()
    await db.refresh(plan)
    return plan


async def delete_plan(db: AsyncSession, plan_id: str) -> bool:
    """删除配额方案。"""
    result = await db.execute(select(QuotaPlan).where(QuotaPlan.id == plan_id))
    plan = result.scalar_one_or_none()
    if plan is None:
        return False
    await db.delete(plan)
    await db.commit()
    return True


async def assign_plan(db: AsyncSession, user_id: str, plan_id: str | None) -> bool:
    """给用户分配配额方案。"""
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if user is None:
        return False
    user.quota_plan_id = plan_id
    await db.commit()
    return True


async def _clear_default_plans(db: AsyncSession) -> None:
    """取消所有默认方案标记。"""
    result = await db.execute(select(QuotaPlan).where(QuotaPlan.is_default.is_(True)))
    for plan in result.scalars().all():
        plan.is_default = False


# ---------------------------------------------------------------------------
# 初始化默认配额方案
# ---------------------------------------------------------------------------


async def init_default_plan(db: AsyncSession) -> None:
    """如果不存在任何配额方案，创建默认的 free 方案。"""
    result = await db.execute(select(func.count()).select_from(QuotaPlan))
    count = result.scalar() or 0
    if count > 0:
        return

    plan = QuotaPlan(
        name="free",
        daily_tokens=1_000_000,
        weekly_tokens=5_000_000,
        monthly_tokens=15_000_000,
        requests_per_minute=20,
        is_default=True,
    )
    db.add(plan)
    await db.commit()
