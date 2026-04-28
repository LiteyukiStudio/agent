"""聊天服务：会话 CRUD 和 ADK Runner 集成（含用量计量）。"""

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

    from server.models.user import User

# ---------------------------------------------------------------------------
# ADK Runner（延迟初始化的单例）
# ---------------------------------------------------------------------------

_runner: Runner | None = None
_session_service: InMemorySessionService | None = None


def get_runner() -> Runner:
    """返回全局 ADK Runner，首次调用时创建。"""
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
    """返回全局 ADK 会话服务。"""
    get_runner()  # 确保已初始化
    assert _session_service is not None
    return _session_service


# ---------------------------------------------------------------------------
# 会话 CRUD
# ---------------------------------------------------------------------------


async def list_sessions(db: AsyncSession, user_id: str) -> list[ChatSession]:
    """列出用户的所有聊天会话，按最近更新排序。"""
    result = await db.execute(
        select(ChatSession).where(ChatSession.user_id == user_id).order_by(ChatSession.updated_at.desc()),
    )
    return list(result.scalars().all())


async def create_session(db: AsyncSession, user_id: str, title: str = "New Chat") -> ChatSession:
    """创建新的聊天会话及其对应的 ADK session。"""
    adk_session_id = str(uuid4())

    # 创建 ADK session
    session_service = get_session_service()
    await session_service.create_session(
        app_name="liteyuki_sre",
        user_id=user_id,
        session_id=adk_session_id,
    )

    # 创建数据库记录
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
    """删除用户拥有的聊天会话。"""
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
# Agent 流式响应（集成配额检查和用量记录）
# ---------------------------------------------------------------------------


async def stream_response(
    user: User,
    adk_session_id: str,
    content: str,
    db: AsyncSession,
    session_id: str | None = None,
) -> AsyncGenerator[str]:
    """向 ADK Agent 发送消息并生成 SSE 格式的事件。

    在流开始前检查配额，流结束后记录用量。

    Args:
        user: 当前用户对象。
        adk_session_id: ADK session ID。
        content: 用户的消息文本。
        db: 异步数据库会话（用于配额检查和用量记录）。
        session_id: 聊天会话 ID（用于用量记录关联）。

    Yields:
        SSE 格式字符串。
    """
    from server.services.usage import check_quota, record_usage
    from server.services.user_config import get_all_raw_configs

    # 前置配额检查
    allowed, reason = await check_quota(db, user)
    if not allowed:
        yield f"data: {json.dumps({'event': 'error', 'message': f'配额不足: {reason}'})}\n\n"
        return

    # 预加载用户配置到 ADK session state（确保工具读取到正确的用户凭据）
    session_service = get_session_service()
    adk_session = await session_service.get_session(
        app_name="liteyuki_sre",
        user_id=user.id,
        session_id=adk_session_id,
    )
    if adk_session:
        # 注入用户 ID 供工具使用
        adk_session.state["__user_id"] = user.id
        # 注入用户配置（如 gitea_base_url, gitea_token 等）
        user_configs = await get_all_raw_configs(db, user.id)
        for namespace, kv in user_configs.items():
            for key, value in kv.items():
                adk_session.state[f"{namespace}_{key}"] = value

    runner = get_runner()
    message = types.Content(
        role="user",
        parts=[types.Part(text=content)],
    )

    # 累计本次调用的 token 用量
    total_input_tokens = 0
    total_output_tokens = 0

    try:
        async for event in runner.run_async(
            user_id=user.id,
            session_id=adk_session_id,
            new_message=message,
        ):
            # 提取 token 用量（如果事件包含）
            if hasattr(event, "usage_metadata") and event.usage_metadata:
                total_input_tokens += getattr(event.usage_metadata, "prompt_token_count", 0) or 0
                total_output_tokens += getattr(event.usage_metadata, "candidates_token_count", 0) or 0

            # 提取内容
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

                    # 函数调用
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

                    # 函数响应
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

        # 记录用量（即使 token 为 0 也记录，用于请求计数）
        if total_input_tokens > 0 or total_output_tokens > 0:
            await record_usage(
                db=db,
                user_id=user.id,
                model="agent",  # 实际模型由 model_config 决定
                input_tokens=total_input_tokens,
                output_tokens=total_output_tokens,
                agent_name="root_agent",
                session_id=session_id,
            )

        # 发送完成信号（附带用量信息）
        done_data = {
            "event": "done",
            "usage": {
                "input_tokens": total_input_tokens,
                "output_tokens": total_output_tokens,
                "total_tokens": total_input_tokens + total_output_tokens,
            },
        }
        yield f"data: {json.dumps(done_data)}\n\n"

    except Exception as e:
        yield f"data: {json.dumps({'event': 'error', 'message': str(e)})}\n\n"
