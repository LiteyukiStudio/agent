"""用量计费相关的 Pydantic 数据模型。"""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel

# ---------------------------------------------------------------------------
# 配额方案
# ---------------------------------------------------------------------------


class QuotaPlanCreate(BaseModel):
    """创建配额方案。"""

    name: str
    daily_tokens: int | None = None
    weekly_tokens: int | None = None
    monthly_tokens: int | None = None
    requests_per_minute: int = 10
    is_default: bool = False


class QuotaPlanUpdate(BaseModel):
    """更新配额方案（所有字段可选）。"""

    name: str | None = None
    daily_tokens: int | None = None
    weekly_tokens: int | None = None
    monthly_tokens: int | None = None
    requests_per_minute: int | None = None
    is_default: bool | None = None


class QuotaPlanResponse(BaseModel):
    """配额方案响应。"""

    id: str
    name: str
    daily_tokens: int | None = None
    weekly_tokens: int | None = None
    monthly_tokens: int | None = None
    requests_per_minute: int
    is_default: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


# ---------------------------------------------------------------------------
# 用量统计
# ---------------------------------------------------------------------------


class PeriodUsage(BaseModel):
    """单个周期的用量信息。"""

    used: int
    limit: int | None = None  # None 表示不限制
    remaining: int | None = None  # None 表示无限


class MyUsageResponse(BaseModel):
    """当前用户的用量概览。"""

    plan_name: str | None = None
    daily: PeriodUsage
    weekly: PeriodUsage
    monthly: PeriodUsage


class UserUsageResponse(BaseModel):
    """管理员查看某用户的用量。"""

    user_id: str
    username: str
    plan_name: str | None = None
    daily: PeriodUsage
    weekly: PeriodUsage
    monthly: PeriodUsage


class GlobalUsageStats(BaseModel):
    """全局用量统计摘要。"""

    total_users: int
    total_tokens_today: int
    total_tokens_this_month: int
    total_records: int


# ---------------------------------------------------------------------------
# 配额分配
# ---------------------------------------------------------------------------


class AssignQuotaPlan(BaseModel):
    """给用户分配配额方案。"""

    quota_plan_id: str | None = None  # None 表示移除配额限制
