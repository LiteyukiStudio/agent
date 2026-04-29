"""用户设备 ORM 模型：记录 Local Agent 设备信息。"""

from __future__ import annotations

from datetime import datetime
from uuid import uuid4

from sqlalchemy import DateTime, ForeignKey, String, func
from sqlalchemy.orm import Mapped, mapped_column

from server.database import Base


class Device(Base):
    """用户的 Local Agent 设备。"""

    __tablename__ = "devices"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), nullable=False)
    device_id: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)  # 客户端生成的 UUID
    device_name: Mapped[str] = mapped_column(String(200), nullable=False, default="unknown")
    token_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("api_tokens.id"), nullable=True)
    last_seen_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
