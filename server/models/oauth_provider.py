"""OAuth 提供商 ORM 模型。"""

from __future__ import annotations

from datetime import datetime
from uuid import uuid4

from sqlalchemy import Boolean, DateTime, String, func
from sqlalchemy.orm import Mapped, mapped_column

from server.database import Base


class OAuthProvider(Base):
    """OAuth / OIDC 提供商配置。"""

    __tablename__ = "oauth_providers"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    issuer_url: Mapped[str] = mapped_column(String(500), nullable=False)
    client_id: Mapped[str] = mapped_column(String(500), nullable=False)
    client_secret: Mapped[str] = mapped_column(String(500), nullable=False)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)

    # 访问控制：whitelist（默认，仅名单内允许）或 blacklist（名单内禁止）
    access_mode: Mapped[str] = mapped_column(String(20), default="whitelist")

    # 由 OIDC 发现端点自动填充
    authorization_endpoint: Mapped[str | None] = mapped_column(String(500), nullable=True)
    token_endpoint: Mapped[str | None] = mapped_column(String(500), nullable=True)
    userinfo_endpoint: Mapped[str | None] = mapped_column(String(500), nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())
