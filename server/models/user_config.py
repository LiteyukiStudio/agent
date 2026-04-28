"""用户配置 ORM 模型。

存储每个用户的 Agent 级别隔离配置（如 Gitea 凭据）。
"""

from __future__ import annotations

from datetime import datetime
from uuid import uuid4

from sqlalchemy import Boolean, DateTime, ForeignKey, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from server.database import Base


class UserConfig(Base):
    """用户隔离的键值对配置。

    每个用户 + namespace + key 组合唯一。
    namespace 对应 agent 名称（如 "gitea"、"registry"）。
    """

    __tablename__ = "user_configs"
    __table_args__ = (UniqueConstraint("user_id", "namespace", "key", name="uq_user_config"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), nullable=False)
    namespace: Mapped[str] = mapped_column(String(100), nullable=False)
    key: Mapped[str] = mapped_column(String(100), nullable=False)
    value: Mapped[str] = mapped_column(String(2000), nullable=False)
    is_secret: Mapped[bool] = mapped_column(Boolean, default=False)

    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())
