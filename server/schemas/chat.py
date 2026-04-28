"""聊天相关的 Pydantic 数据模型。"""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel


class SessionResponse(BaseModel):
    """聊天会话摘要。"""

    id: str
    title: str
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class SessionCreate(BaseModel):
    """创建新聊天会话的请求体。"""

    title: str = "New Chat"


class MessageSend(BaseModel):
    """向 Agent 发送消息的请求体。"""

    content: str


class MessageEvent(BaseModel):
    """Agent 响应流中的单个 SSE 事件。"""

    event: str  # 'text', 'tool_call', 'done', 'error'
    data: str
