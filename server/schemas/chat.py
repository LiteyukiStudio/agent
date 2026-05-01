"""聊天相关的 Pydantic 数据模型。"""

from __future__ import annotations

from datetime import UTC, datetime

from pydantic import BaseModel, field_serializer


class _BaseSchema(BaseModel):
    """带统一 datetime 序列化的基类：所有时间输出为 ISO 8601 UTC（带 Z 后缀）。"""

    model_config = {"from_attributes": True}

    @field_serializer("*", mode="plain")
    @classmethod
    def _serialize_datetime(cls, value: object) -> object:
        if isinstance(value, datetime):
            # 将 naive datetime（假定为 UTC）标记时区后输出
            if value.tzinfo is None:
                value = value.replace(tzinfo=UTC)
            return value.strftime("%Y-%m-%dT%H:%M:%SZ")
        return value


class SessionResponse(_BaseSchema):
    """聊天会话摘要。"""

    id: str
    title: str
    is_public: bool = False
    last_message: str | None = None
    created_at: datetime
    updated_at: datetime


class SessionCreate(BaseModel):
    """创建新聊天会话的请求体。"""

    title: str = "New Chat"


class SessionUpdate(BaseModel):
    """更新聊天会话的请求体（所有字段可选）。"""

    title: str | None = None
    is_public: bool | None = None


class MessageSend(BaseModel):
    """向 Agent 发送消息的请求体。"""

    content: str


class MessageResponse(_BaseSchema):
    """持久化的聊天消息响应。"""

    id: str
    session_id: str
    role: str
    content: str
    thinking: str | None = None
    tool_calls: str | None = None
    parts: str | None = None
    status: str = "done"
    created_at: datetime


class PublicSessionResponse(_BaseSchema):
    """公开会话的完整数据（含消息列表）。"""

    id: str
    title: str
    messages: list[MessageResponse]
    created_at: datetime
    updated_at: datetime
