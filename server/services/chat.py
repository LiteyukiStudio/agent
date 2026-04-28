"""聊天服务：会话 CRUD 和 ADK Runner 集成（含用量计量和消息持久化）。"""

from __future__ import annotations

import json
from typing import TYPE_CHECKING
from uuid import uuid4

from google.adk.agents.run_config import RunConfig, StreamingMode
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types
from sqlalchemy import select

from server.models.chat_session import ChatSession
from server.models.message import Message

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


async def rename_session(
    db: AsyncSession,
    user_id: str,
    session_id: str,
    title: str,
) -> ChatSession | None:
    """重命名会话并标记为用户自定义标题。"""
    result = await db.execute(
        select(ChatSession).where(ChatSession.id == session_id, ChatSession.user_id == user_id),
    )
    chat_session = result.scalar_one_or_none()
    if chat_session is None:
        return None
    chat_session.title = title
    chat_session.title_custom = True
    await db.commit()
    await db.refresh(chat_session)
    return chat_session


# ---------------------------------------------------------------------------
# 消息持久化
# ---------------------------------------------------------------------------


async def save_message(
    db: AsyncSession,
    session_id: str,
    role: str,
    content: str,
    tool_calls_json: str | None = None,
) -> Message:
    """保存一条消息到数据库。"""
    msg = Message(
        session_id=session_id,
        role=role,
        content=content,
        tool_calls=tool_calls_json,
    )
    db.add(msg)
    await db.commit()
    await db.refresh(msg)
    return msg


async def get_messages(db: AsyncSession, session_id: str, user_id: str) -> list[Message]:
    """获取某会话的所有消息（验证所有权）。"""
    # 先验证会话属于该用户
    result = await db.execute(
        select(ChatSession).where(ChatSession.id == session_id, ChatSession.user_id == user_id),
    )
    if result.scalar_one_or_none() is None:
        return []

    result = await db.execute(
        select(Message).where(Message.session_id == session_id).order_by(Message.created_at),
    )
    return list(result.scalars().all())


# ---------------------------------------------------------------------------
# Agent 流式响应（集成配额检查、用量记录和消息持久化）
# ---------------------------------------------------------------------------


async def stream_response(
    user: User,
    adk_session_id: str,
    content: str,
    db: AsyncSession,
    session_id: str | None = None,
) -> AsyncGenerator[str]:
    """向 ADK Agent 发送消息并生成 SSE 格式的事件。

    在流开始前检查配额，流结束后记录用量并保存消息。
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

    # 保存用户消息
    if session_id:
        await save_message(db, session_id, "user", content)

    runner = get_runner()
    message = types.Content(
        role="user",
        parts=[types.Part(text=content)],
    )

    # 累计本次调用的 token 用量
    total_input_tokens = 0
    total_output_tokens = 0
    assistant_text = ""
    # 收集工具调用数据
    collected_tool_calls: list[dict] = []

    try:
        async for event in runner.run_async(
            user_id=user.id,
            session_id=adk_session_id,
            new_message=message,
            run_config=RunConfig(streaming_mode=StreamingMode.SSE),
        ):
            # 提取 token 用量（如果事件包含）
            if hasattr(event, "usage_metadata") and event.usage_metadata:
                total_input_tokens += getattr(event.usage_metadata, "prompt_token_count", 0) or 0
                total_output_tokens += getattr(event.usage_metadata, "candidates_token_count", 0) or 0

            # 提取内容
            if event.content and event.content.parts:
                for part in event.content.parts:
                    if part.text:
                        assistant_text += part.text
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
                        tc_data = {
                            "name": part.function_call.name,
                            "args": dict(part.function_call.args) if part.function_call.args else {},
                        }
                        collected_tool_calls.append(tc_data)
                        sse_data = json.dumps(
                            {
                                "event": "tool_call",
                                "author": event.author or "assistant",
                                **tc_data,
                            }
                        )
                        yield f"data: {sse_data}\n\n"

                    # 函数响应
                    if part.function_response:
                        # 更新最近的同名工具调用结果
                        result_str = str(part.function_response.response) if part.function_response.response else ""
                        for tc in reversed(collected_tool_calls):
                            if tc["name"] == part.function_response.name and "result" not in tc:
                                tc["result"] = result_str
                                break
                        sse_data = json.dumps(
                            {
                                "event": "tool_result",
                                "name": part.function_response.name,
                                "result": result_str,
                            }
                        )
                        yield f"data: {sse_data}\n\n"

        # 记录用量
        if total_input_tokens > 0 or total_output_tokens > 0:
            await record_usage(
                db=db,
                user_id=user.id,
                model="agent",
                input_tokens=total_input_tokens,
                output_tokens=total_output_tokens,
                agent_name="root_agent",
                session_id=session_id,
            )

        # 保存助手消息
        if session_id and assistant_text:
            tool_calls_json = json.dumps(collected_tool_calls) if collected_tool_calls else None
            await save_message(db, session_id, "assistant", assistant_text, tool_calls_json)

        # 更新会话的最近消息摘要 + 自动标题
        if session_id:
            result = await db.execute(
                select(ChatSession).where(ChatSession.id == session_id),
            )
            chat_session = result.scalar_one_or_none()
            if chat_session:
                if assistant_text:
                    chat_session.last_message = assistant_text[:200]
                # 自动生成标题：仅在用户未手动修改时更新
                if not chat_session.title_custom and content.strip():
                    auto_title = content.strip()[:30]
                    if len(content.strip()) > 30:
                        auto_title += "..."
                    chat_session.title = auto_title
                await db.commit()

        # 获取更新后的标题（用于通知前端）
        updated_title = None
        if session_id:
            result = await db.execute(
                select(ChatSession.title).where(ChatSession.id == session_id),
            )
            updated_title = result.scalar_one_or_none()

        # 发送完成信号（附带用量信息和更新后的标题）
        done_data: dict = {
            "event": "done",
            "usage": {
                "input_tokens": total_input_tokens,
                "output_tokens": total_output_tokens,
                "total_tokens": total_input_tokens + total_output_tokens,
            },
        }
        if updated_title:
            done_data["title"] = updated_title
        yield f"data: {json.dumps(done_data)}\n\n"

    except Exception as e:
        yield f"data: {json.dumps({'event': 'error', 'message': str(e)})}\n\n"
