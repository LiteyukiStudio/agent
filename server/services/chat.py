"""Chat service: session CRUD and ADK Runner integration."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING
from uuid import uuid4

from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types
from sqlalchemy import select

from server.models.chat_session import ChatSession

if TYPE_CHECKING:
    from collections.abc import AsyncGenerator

    from sqlalchemy.ext.asyncio import AsyncSession

# ---------------------------------------------------------------------------
# ADK Runner (lazy-initialized singleton)
# ---------------------------------------------------------------------------

_runner: Runner | None = None
_session_service: InMemorySessionService | None = None


def get_runner() -> Runner:
    """Return the global ADK Runner, creating it on first call."""
    global _runner, _session_service
    if _runner is None:
        from root_agent.agent import root_agent

        _session_service = InMemorySessionService()
        _runner = Runner(
            agent=root_agent,
            session_service=_session_service,
            app_name="liteyuki_sre",
        )
    return _runner


def get_session_service() -> InMemorySessionService:
    """Return the global ADK session service."""
    get_runner()  # ensure initialized
    assert _session_service is not None
    return _session_service


# ---------------------------------------------------------------------------
# Session CRUD
# ---------------------------------------------------------------------------


async def list_sessions(db: AsyncSession, user_id: str) -> list[ChatSession]:
    """List all chat sessions for a user, ordered by most recently updated.

    Args:
        db: Async database session.
        user_id: The user's ID.

    Returns:
        List of ChatSession objects.
    """
    result = await db.execute(
        select(ChatSession).where(ChatSession.user_id == user_id).order_by(ChatSession.updated_at.desc()),
    )
    return list(result.scalars().all())


async def create_session(db: AsyncSession, user_id: str, title: str = "New Chat") -> ChatSession:
    """Create a new chat session and its corresponding ADK session.

    Args:
        db: Async database session.
        user_id: The user's ID.
        title: Session title.

    Returns:
        The created ChatSession.
    """
    adk_session_id = str(uuid4())

    # Create ADK session
    session_service = get_session_service()
    await session_service.create_session(
        app_name="liteyuki_sre",
        user_id=user_id,
        session_id=adk_session_id,
    )

    # Create DB record
    chat_session = ChatSession(
        user_id=user_id,
        title=title,
        adk_session_id=adk_session_id,
    )
    db.add(chat_session)
    await db.commit()
    await db.refresh(chat_session)
    return chat_session


async def delete_session(db: AsyncSession, user_id: str, session_id: str) -> bool:
    """Delete a chat session owned by the user.

    Args:
        db: Async database session.
        user_id: The user's ID (for ownership check).
        session_id: The ChatSession ID to delete.

    Returns:
        True if deleted, False if not found or not owned.
    """
    result = await db.execute(
        select(ChatSession).where(ChatSession.id == session_id, ChatSession.user_id == user_id),
    )
    chat_session = result.scalar_one_or_none()
    if chat_session is None:
        return False
    await db.delete(chat_session)
    await db.commit()
    return True


# ---------------------------------------------------------------------------
# Agent streaming
# ---------------------------------------------------------------------------


async def stream_response(
    user_id: str,
    adk_session_id: str,
    content: str,
) -> AsyncGenerator[str]:
    """Send a message to the ADK agent and yield SSE-formatted events.

    Args:
        user_id: The user's ID (for ADK Runner).
        adk_session_id: The ADK session ID.
        content: The user's message text.

    Yields:
        SSE-formatted strings (e.g. 'data: {...}\\n\\n').
    """
    runner = get_runner()
    message = types.Content(
        role="user",
        parts=[types.Part(text=content)],
    )

    try:
        async for event in runner.run_async(
            user_id=user_id,
            session_id=adk_session_id,
            new_message=message,
        ):
            # Extract text content
            if event.content and event.content.parts:
                for part in event.content.parts:
                    if part.text:
                        sse_data = json.dumps(
                            {
                                "event": "text",
                                "author": event.author or "assistant",
                                "content": part.text,
                            }
                        )
                        yield f"data: {sse_data}\n\n"

                    # Handle function calls
                    if part.function_call:
                        sse_data = json.dumps(
                            {
                                "event": "tool_call",
                                "author": event.author or "assistant",
                                "name": part.function_call.name,
                                "args": dict(part.function_call.args) if part.function_call.args else {},
                            }
                        )
                        yield f"data: {sse_data}\n\n"

                    # Handle function responses
                    if part.function_response:
                        sse_data = json.dumps(
                            {
                                "event": "tool_result",
                                "name": part.function_response.name,
                                "result": str(part.function_response.response)
                                if part.function_response.response
                                else "",
                            }
                        )
                        yield f"data: {sse_data}\n\n"

        # Signal completion
        yield f"data: {json.dumps({'event': 'done'})}\n\n"

    except Exception as e:
        yield f"data: {json.dumps({'event': 'error', 'message': str(e)})}\n\n"
