"""User ORM model."""

from __future__ import annotations

from datetime import datetime
from uuid import uuid4

from sqlalchemy import DateTime, ForeignKey, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from server.database import Base


class User(Base):
    """Application user, linked to an OAuth provider."""

    __tablename__ = "users"
    __table_args__ = (UniqueConstraint("oauth_provider_id", "oauth_user_id", name="uq_user_oauth"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    username: Mapped[str] = mapped_column(String(100), nullable=False)
    email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    avatar_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    role: Mapped[str] = mapped_column(String(20), default="user")  # 'admin' or 'user'

    oauth_provider_id: Mapped[str] = mapped_column(String(36), ForeignKey("oauth_providers.id"), nullable=False)
    oauth_user_id: Mapped[str] = mapped_column(String(255), nullable=False)

    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())
