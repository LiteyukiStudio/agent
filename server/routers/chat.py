"""聊天会话和消息路由。"""

from __future__ import annotations

from typing import TYPE_CHECKING

from fastapi import APIRouter, Depends, HTTPException, status
from starlette.responses import StreamingResponse

from server.deps import get_current_user, get_db
from server.schemas.chat import (
    MessageResponse,
    MessageSend,
    PublicSessionResponse,
    SessionCreate,
    SessionResponse,
    SessionUpdate,
)
from server.services import chat as chat_service

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

    from server.models.user import User

router = APIRouter(prefix="/api/v1/chat", tags=["chat"])


@router.get("/sessions", response_model=list[SessionResponse])
async def list_sessions(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[SessionResponse]:
    """列出当前用户的所有聊天会话。"""
    sessions = await chat_service.list_sessions(db, user.id)
    return [SessionResponse.model_validate(s) for s in sessions]


@router.post("/sessions", response_model=SessionResponse, status_code=status.HTTP_201_CREATED)
async def create_session(
    body: SessionCreate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> SessionResponse:
    """创建新的聊天会话。"""
    session = await chat_service.create_session(db, user.id, body.title)
    return SessionResponse.model_validate(session)


@router.delete("/sessions/{session_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_session(
    session_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> None:
    """删除聊天会话。"""
    deleted = await chat_service.delete_session(db, user.id, session_id)
    if not deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found")


@router.patch("/sessions/{session_id}", response_model=SessionResponse)
async def update_session(
    session_id: str,
    body: SessionUpdate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> SessionResponse:
    """更新聊天会话（标题、公开状态等）。"""
    session = await chat_service.update_session(db, user.id, session_id, body)
    if session is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found")
    return SessionResponse.model_validate(session)


@router.get("/sessions/{session_id}/messages", response_model=list[MessageResponse])
async def get_messages(
    session_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[MessageResponse]:
    """获取某会话的所有历史消息。"""
    messages = await chat_service.get_messages(db, session_id, user.id)
    return [MessageResponse.model_validate(m) for m in messages]


@router.get("/sessions/{session_id}/public", response_model=PublicSessionResponse)
async def get_public_session(
    session_id: str,
    db: AsyncSession = Depends(get_db),
) -> PublicSessionResponse:
    """获取公开会话的消息（不需要登录）。"""
    result = await chat_service.get_public_session(db, session_id)
    if result is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found or not public")
    session, messages = result
    return PublicSessionResponse(
        id=session.id,
        title=session.title,
        messages=[MessageResponse.model_validate(m) for m in messages],
        created_at=session.created_at,
        updated_at=session.updated_at,
    )


@router.post("/sessions/{session_id}/messages")
async def send_message(
    session_id: str,
    body: MessageSend,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> StreamingResponse:
    """发送消息并通过 SSE 流式返回 Agent 响应。"""
    sessions = await chat_service.list_sessions(db, user.id)
    chat_session = next((s for s in sessions if s.id == session_id), None)
    if chat_session is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found")

    return StreamingResponse(
        chat_service.stream_response(user, chat_session.adk_session_id, body.content, db, session_id),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
