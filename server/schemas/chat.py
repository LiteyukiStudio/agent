"""聊天相关的 Pydantic 数据模型。"""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel


class SessionResponse(BaseModel):
    """聊天会话摘要。"""

    id: str
    title: str
    last_message: str | None = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class SessionCreate(BaseModel):
    """创建新聊天会话的请求体。"""

    title: str = "New Chat"


class SessionRename(BaseModel):
    """重命名聊天会话的请求体。"""

    title: str


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


class MessageEvent(BaseModel):
    """Agent 响应流中的单个 SSE 事件。"""

    event: str  # 'text', 'tool_call', 'done', 'error'
    data: str
