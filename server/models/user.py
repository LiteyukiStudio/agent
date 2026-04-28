"""用户 ORM 模型。"""

from __future__ import annotations

from datetime import datetime
from uuid import uuid4

from sqlalchemy import DateTime, ForeignKey, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from server.database import Base


class User(Base):
    """应用用户，支持 OAuth 绑定和密码登录。

    角色层级: superuser > admin > user
    - superuser: 最高权限，可分配/撤销 admin
    - admin: 管理权限，不能修改其他人的 admin/superuser 角色
    - user: 普通用户
    """

    __tablename__ = "users"
    __table_args__ = (UniqueConstraint("oauth_provider_id", "oauth_user_id", name="uq_user_oauth"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    username: Mapped[str] = mapped_column(String(100), nullable=False, unique=True)
    email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    avatar_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    role: Mapped[str] = mapped_column(String(20), default="user")  # superuser / admin / user
    password_hash: Mapped[str | None] = mapped_column(String(255), nullable=True)  # bcrypt 哈希，密码登录用

    # OAuth 绑定（可选，密码用户可以没有）
    oauth_provider_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("oauth_providers.id"),
        nullable=True,
    )
    oauth_user_id: Mapped[str | None] = mapped_column(String(255), nullable=True)

    # 配额方案绑定（可选，为空则无限制或使用默认方案）
    quota_plan_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("quota_plans.id"),
        nullable=True,
    )

    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())
