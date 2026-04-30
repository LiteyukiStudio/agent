"""聊天服务：会话 CRUD 和 ADK Runner 集成（含用量计量和消息持久化）。"""

from __future__ import annotations

import json
import logging
from typing import TYPE_CHECKING
from uuid import uuid4

from google.adk.agents.run_config import RunConfig, StreamingMode
from google.adk.runners import Runner
from google.adk.sessions.database_session_service import DatabaseSessionService
from google.genai import types
from sqlalchemy import select

from server.config import settings
from server.models.chat_session import ChatSession
from server.models.message import Message

if TYPE_CHECKING:
    from collections.abc import AsyncGenerator

    from google.adk.sessions import BaseSessionService
    from sqlalchemy.ext.asyncio import AsyncSession

    from server.models.user import User

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# ADK Runner（延迟初始化的单例）
# ---------------------------------------------------------------------------

_runner: Runner | None = None
_session_service: BaseSessionService | None = None

# Agent 凭据命名空间白名单：工具通过 tool_context.state 写入的这些 namespace 下的 key
# 会被自动持久化到 UserConfig 表，实现跨会话访问。
# 新增 Agent 时在这里添加对应的 namespace。
PERSIST_CREDENTIAL_NAMESPACES: set[str] = {"gitea", "misskey", "memory"}


def _get_adk_db_url() -> str:
    """将项目 DATABASE_URL 转换为 ADK DatabaseSessionService 可用的格式。

    ADK 内部自行创建 async engine，需要 async 驱动的 URL。
    """
    url = settings.database_url
    # 确保使用异步驱动
    if url.startswith("sqlite:///") and "aiosqlite" not in url:
        url = url.replace("sqlite:///", "sqlite+aiosqlite:///", 1)
    return url


def get_runner() -> Runner:
    """返回全局 ADK Runner，首次调用时创建。"""
    global _runner, _session_service
    if _runner is None:
        from root_agent.agent import root_agent

        _session_service = DatabaseSessionService(db_url=_get_adk_db_url())
        _runner = Runner(
            agent=root_agent,
            session_service=_session_service,
            app_name="liteyuki_sre",
        )
    return _runner


def get_session_service() -> BaseSessionService:
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


async def update_session(
    db: AsyncSession,
    user_id: str,
    session_id: str,
    data: object,
) -> ChatSession | None:
    """更新会话属性（标题、公开状态等）。"""
    result = await db.execute(
        select(ChatSession).where(ChatSession.id == session_id, ChatSession.user_id == user_id),
    )
    chat_session = result.scalar_one_or_none()
    if chat_session is None:
        return None

    if hasattr(data, "title") and data.title is not None:
        chat_session.title = data.title
        chat_session.title_custom = True
    if hasattr(data, "is_public") and data.is_public is not None:
        chat_session.is_public = data.is_public

    await db.commit()
    await db.refresh(chat_session)
    return chat_session


async def get_public_session(
    db: AsyncSession,
    session_id: str,
) -> tuple[ChatSession, list[Message]] | None:
    """获取公开会话及其消息（不验证用户身份）。"""
    result = await db.execute(
        select(ChatSession).where(ChatSession.id == session_id, ChatSession.is_public.is_(True)),
    )
    chat_session = result.scalar_one_or_none()
    if chat_session is None:
        return None

    result = await db.execute(
        select(Message).where(Message.session_id == session_id).order_by(Message.created_at),
    )
    messages = list(result.scalars().all())
    return chat_session, messages


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
    from server.services.user_config import get_all_raw_configs, set_config

    # 前置配额检查
    allowed, reason = await check_quota(db, user)
    if not allowed:
        logger.warning("stream_response: quota denied for user=%s reason=%s", user.username, reason)
        yield f"data: {json.dumps({'event': 'error', 'message': f'配额不足: {reason}'})}\n\n"
        return

    logger.info("stream_response: user=%s session=%s quota OK, starting stream", user.username, adk_session_id)

    # 预加载用户配置到 ADK session state（确保工具读取到正确的用户凭据）
    session_service = get_session_service()
    adk_session = await session_service.get_session(
        app_name="liteyuki_sre",
        user_id=user.id,
        session_id=adk_session_id,
    )

    # 如果 ADK session 不存在（后端重启后内存丢失），自动重建
    if adk_session is None:
        adk_session = await session_service.create_session(
            app_name="liteyuki_sre",
            user_id=user.id,
            session_id=adk_session_id,
        )

    # 注入用户配置到 state_delta（通过 run_async 参数传入，确保 ADK 正确持久化）
    injected_state: dict = {"__user_id": user.id}
    user_configs = await get_all_raw_configs(db, user.id)
    for namespace, kv in user_configs.items():
        for key, value in kv.items():
            injected_state[f"{namespace}_{key}"] = value

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
    # 去重：SSE 流式模式下 ADK 先发 partial=True 的逐 token 事件，
    # 最后发 partial=False/None 的完整文本事件，导致内容重复。
    # 只输出 partial 事件（流式 token），跳过最终的完整事件。
    has_partial_text = False

    try:
        async for event in runner.run_async(
            user_id=user.id,
            session_id=adk_session_id,
            new_message=message,
            state_delta=injected_state,
            run_config=RunConfig(streaming_mode=StreamingMode.SSE),
        ):
            # 调试：记录每个 ADK event 的基本信息
            parts_summary = ""
            if event.content and event.content.parts:
                parts_summary = ", ".join(
                    f"text({len(p.text)})"
                    if p.text
                    else f"func_call({p.function_call.name})"
                    if p.function_call
                    else f"func_resp({p.function_response.name})"
                    if p.function_response
                    else "other"
                    for p in event.content.parts
                )
            logger.info(
                "ADK event: author=%s, parts=[%s], actions=%s",
                event.author,
                parts_summary,
                bool(event.actions and event.actions.state_delta),
            )

            # 提取 token 用量（如果事件包含）
            if hasattr(event, "usage_metadata") and event.usage_metadata:
                total_input_tokens += getattr(event.usage_metadata, "prompt_token_count", 0) or 0
                total_output_tokens += getattr(event.usage_metadata, "candidates_token_count", 0) or 0

            # 检测 state 变更，将凭据类 key 回写到 UserConfig 表（跨会话持久化）
            if event.actions and event.actions.state_delta:
                for state_key, state_value in event.actions.state_delta.items():
                    # 解析 namespace_key 格式
                    parts = state_key.split("_", 1)
                    if len(parts) == 2 and parts[0] in PERSIST_CREDENTIAL_NAMESPACES:
                        namespace, key = parts
                        is_secret = key in ("token", "password", "secret")
                        await set_config(
                            db,
                            user.id,
                            namespace,
                            key,
                            str(state_value),
                            is_secret=is_secret,
                        )

            # 提取内容
            # ADK SSE 流式模式下的事件结构：
            # 1. 多个 partial=True 事件，每个含一小段 token（流式输出）
            # 2. 一个 partial=False/None 事件，含完整文本（汇总）
            # 只输出 partial 事件避免重复；如果没有 partial 事件才输出完整事件。
            if event.content and event.content.parts:
                author = event.author or "assistant"
                is_partial = bool(event.partial)

                for part in event.content.parts:
                    # --- 文本处理（去重逻辑只影响文本） ---
                    if part.text:
                        text = part.text

                        if is_partial:
                            # 流式 token，正常输出
                            has_partial_text = True
                        elif has_partial_text:
                            # 非 partial 的完整文本，但之前已经输出过 partial token
                            # 这是 ADK 的汇总事件，跳过以避免重复
                            logger.debug(
                                "skip non-partial summary event: author=%s len=%d",
                                author,
                                len(text),
                            )
                            # 注意：只跳过文本，不能 continue —— 同一个 part 可能还有其他内容
                        else:
                            # 非流式场景（没有 partial 事件），正常输出文本
                            is_thinking = bool(part.thought)
                            if not is_thinking:
                                assistant_text += text
                            sse_data = json.dumps(
                                {
                                    "event": "thinking" if is_thinking else "text",
                                    "author": author,
                                    "content": text,
                                }
                            )
                            yield f"data: {sse_data}\n\n"

                        # 流式场景下正常输出 partial 文本
                        if is_partial:
                            is_thinking = bool(part.thought)
                            if not is_thinking:
                                assistant_text += text
                            sse_data = json.dumps(
                                {
                                    "event": "thinking" if is_thinking else "text",
                                    "author": author,
                                    "content": text,
                                }
                            )
                            yield f"data: {sse_data}\n\n"

                    # --- 函数调用（不受去重影响） ---
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
                        response_data = part.function_response.response
                        result_str = str(response_data) if response_data else ""

                        # 检测工具是否返回了错误（on_tool_error_callback 包装的结果）
                        is_tool_error = isinstance(response_data, dict) and response_data.get("error") is True

                        for tc in reversed(collected_tool_calls):
                            if tc["name"] == part.function_response.name and "result" not in tc:
                                tc["result"] = result_str
                                if is_tool_error:
                                    tc["error"] = True
                                break

                        if is_tool_error:
                            sse_data = json.dumps(
                                {
                                    "event": "tool_error",
                                    "name": part.function_response.name,
                                    "error_type": response_data.get("error_type", "Error"),
                                    "error_message": response_data.get("error_message", "Unknown error"),
                                }
                            )
                        else:
                            sse_data = json.dumps(
                                {
                                    "event": "tool_result",
                                    "name": part.function_response.name,
                                    "result": result_str,
                                }
                            )
                        yield f"data: {sse_data}\n\n"

        # 兜底：流结束后从 ADK session state 回写凭据到 UserConfig
        # （防止 state_delta 在某些情况下未触发）
        final_session = await session_service.get_session(
            app_name="liteyuki_sre",
            user_id=user.id,
            session_id=adk_session_id,
        )
        if final_session:
            for state_key, state_value in final_session.state.to_dict().items():
                parts = state_key.split("_", 1)
                if len(parts) == 2 and parts[0] in PERSIST_CREDENTIAL_NAMESPACES and state_value:
                    namespace, key = parts
                    is_secret = key in ("token", "password", "secret")
                    await set_config(
                        db,
                        user.id,
                        namespace,
                        key,
                        str(state_value),
                        is_secret=is_secret,
                    )

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

                # AI 自动生成/更新标题（用户手动改过的不动）
                # 第 1 轮立即生成，之后每 5 轮更新一次以跟踪主题变化
                if not chat_session.title_custom and content.strip():
                    # 统计当前会话的消息轮次（user 消息数）
                    from sqlalchemy import func as sa_func

                    count_result = await db.execute(
                        select(sa_func.count())
                        .select_from(Message)
                        .where(Message.session_id == session_id, Message.role == "user"),
                    )
                    msg_count = count_result.scalar() or 0

                    should_update = msg_count == 1 or (msg_count > 0 and msg_count % 5 == 0)
                    if should_update:
                        from server.services.title_gen import generate_title

                        logger.info("Generating title for session=%s (msg_count=%d)", session_id, msg_count)
                        ai_title = await generate_title(content, assistant_text)
                        if ai_title:
                            chat_session.title = ai_title
                            logger.info("Title generated: %s", ai_title)
                        elif chat_session.title == "New Chat":
                            chat_session.title = "新对话"
                            logger.warning("Title generation returned None, fallback to '新对话'")

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
        logger.exception("stream_response: unhandled error for user=%s session=%s", user.username, adk_session_id)
        yield f"data: {json.dumps({'event': 'error', 'message': str(e)})}\n\n"
