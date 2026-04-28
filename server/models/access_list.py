"""访问名单条目 ORM 模型。

用于 OAuth 提供商的白名单/黑名单访问控制。
"""

from __future__ import annotations

from datetime import datetime
from uuid import uuid4

from sqlalchemy import DateTime, ForeignKey, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from server.database import Base


class AccessListEntry(Base):
    """OAuth 提供商的访问名单条目。

    根据 OAuthProvider.access_mode 决定行为：
    - whitelist: 名单内的用户允许登录
    - blacklist: 名单内的用户禁止登录

    identity 字段存储 OAuth 用户标识（用户名、邮箱或 OAuth ID 均可匹配）。
    """

    __tablename__ = "access_list_entries"
    __table_args__ = (UniqueConstraint("provider_id", "identity", name="uq_access_entry"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    provider_id: Mapped[str] = mapped_column(String(36), ForeignKey("oauth_providers.id"), nullable=False)

    # 匹配用户的标识，可以是用户名、邮箱或 OAuth ID
    identity: Mapped[str] = mapped_column(String(255), nullable=False)
    # 备注，方便管理员识别
    note: Mapped[str | None] = mapped_column(String(500), nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
