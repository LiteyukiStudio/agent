"""用量记录 ORM 模型。"""

from __future__ import annotations

from datetime import datetime
from uuid import uuid4

from sqlalchemy import DateTime, ForeignKey, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column

from server.database import Base


class UsageRecord(Base):
    """单次 LLM 调用的用量记录，追加写入不修改。"""

    __tablename__ = "usage_records"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), nullable=False)

    model: Mapped[str] = mapped_column(String(200), nullable=False)  # 如 deepseek/deepseek-v4-flash
    input_tokens: Mapped[int] = mapped_column(Integer, default=0)
    output_tokens: Mapped[int] = mapped_column(Integer, default=0)
    total_tokens: Mapped[int] = mapped_column(Integer, default=0)  # input + output

    agent_name: Mapped[str] = mapped_column(String(100), default="root_agent")
    session_id: Mapped[str | None] = mapped_column(String(36), nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
