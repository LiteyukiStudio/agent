"""访问名单条目 ORM 模型。

用于 OAuth 提供商的白名单/黑名单访问控制（基于 OIDC groups claim）。
"""

from __future__ import annotations

from datetime import datetime
from uuid import uuid4

from sqlalchemy import DateTime, ForeignKey, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from server.database import Base


class AccessListEntry(Base):
    """OAuth 提供商的 Group 访问名单条目。

    根据 OAuthProvider.access_mode 决定行为：
    - whitelist: 仅指定 group 内的用户允许登录（名单为空则允许所有人）
    - blacklist: 指定 group 内的用户禁止登录

    group_name 匹配 OIDC userinfo 中的 groups claim（如 Casdoor 的组名）。
    """

    __tablename__ = "access_list_entries"
    __table_args__ = (UniqueConstraint("provider_id", "group_name", name="uq_access_group"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    provider_id: Mapped[str] = mapped_column(String(36), ForeignKey("oauth_providers.id"), nullable=False)

    # OIDC group 名称，匹配 userinfo["groups"] 中的值
    group_name: Mapped[str] = mapped_column(String(255), nullable=False)
    # 备注
    note: Mapped[str | None] = mapped_column(String(500), nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
