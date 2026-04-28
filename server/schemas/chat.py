"""Chat-related Pydantic schemas."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel


class SessionResponse(BaseModel):
    """Chat session summary."""

    id: str
    title: str
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class SessionCreate(BaseModel):
    """Request body for creating a new chat session."""

    title: str = "New Chat"


class MessageSend(BaseModel):
    """Request body for sending a message to the agent."""

    content: str


class MessageEvent(BaseModel):
    """A single SSE event from the agent response stream."""

    event: str  # 'text', 'tool_call', 'done', 'error'
    data: str
