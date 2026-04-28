"""配额方案 ORM 模型。"""

from __future__ import annotations

from datetime import datetime
from uuid import uuid4

from sqlalchemy import Boolean, DateTime, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column

from server.database import Base


class QuotaPlan(Base):
    """用量配额方案，定义各周期的 token 上限。"""

    __tablename__ = "quota_plans"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    name: Mapped[str] = mapped_column(String(100), nullable=False, unique=True)

    # 各周期 token 上限，None 表示不限制
    daily_tokens: Mapped[int | None] = mapped_column(Integer, nullable=True)
    weekly_tokens: Mapped[int | None] = mapped_column(Integer, nullable=True)
    monthly_tokens: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # 每分钟请求数限制
    requests_per_minute: Mapped[int] = mapped_column(Integer, default=10)

    # 是否为默认方案（新用户自动分配）
    is_default: Mapped[bool] = mapped_column(Boolean, default=False)

    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())
