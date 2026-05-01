"""聊天消息 ORM 模型。"""

from __future__ import annotations

from datetime import datetime
from uuid import uuid4

from sqlalchemy import DateTime, ForeignKey, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from server.database import Base


class Message(Base):
    """聊天消息记录，持久化每条用户和助手的消息。"""

    __tablename__ = "messages"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    session_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("chat_sessions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    role: Mapped[str] = mapped_column(String(20), nullable=False)  # 'user' 或 'assistant'
    content: Mapped[str] = mapped_column(Text, nullable=False)
    thinking: Mapped[str | None] = mapped_column(Text, nullable=True)  # thinking/推理过程
    tool_calls: Mapped[str | None] = mapped_column(Text, nullable=True)  # JSON 字符串
    parts: Mapped[str | None] = mapped_column(Text, nullable=True)  # 有序消息片段 JSON（text/thinking/tool_call）
    status: Mapped[str] = mapped_column(String(20), default="done")  # 'generating' 或 'done'

    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
