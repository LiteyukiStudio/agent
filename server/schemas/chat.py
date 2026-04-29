"""聊天相关的 Pydantic 数据模型。"""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel


class SessionResponse(BaseModel):
    """聊天会话摘要。"""

    id: str
    title: str
    is_public: bool = False
    last_message: str | None = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


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


class MessageResponse(BaseModel):
    """持久化的聊天消息响应。"""

    id: str
    session_id: str
    role: str
    content: str
    tool_calls: str | None = None
    created_at: datetime

    model_config = {"from_attributes": True}


class PublicSessionResponse(BaseModel):
    """公开会话的完整数据（含消息列表）。"""

    id: str
    title: str
    messages: list[MessageResponse]
    created_at: datetime
    updated_at: datetime
