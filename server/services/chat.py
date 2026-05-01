"""聊天服务：会话 CRUD 和 ADK Runner 集成（含用量计量和消息持久化）。"""

from __future__ import annotations

import asyncio
import json
import logging
from typing import TYPE_CHECKING
from uuid import uuid4

from google.adk.agents.run_config import RunConfig, StreamingMode
from google.adk.runners import Runner
from google.adk.sessions.database_session_service import DatabaseSessionService
from google.genai import types
from sqlalchemy import case, select, update

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
PERSIST_CREDENTIAL_NAMESPACES: set[str] = {"gitea", "misskey", "memory", "push"}

# Token 估算参数：当 LLM provider 未上报 token 用量时，按字节长度粗略推算。
# 使用 UTF-8 字节数而非字符数，可更好地适应多字节语言（如中文每字约 3 字节）。
_BYTES_PER_TOKEN_ESTIMATE = 4


def _estimate_tokens(text: str) -> int:
    """根据 UTF-8 字节长度估算 token 数量（至少 1）。"""
    return max(1, len(text.encode("utf-8")) // _BYTES_PER_TOKEN_ESTIMATE)


def _extract_title_update(response_data: object) -> str | None:
    """从 set_conversation_title 工具响应中提取成功更新后的标题。"""
    if isinstance(response_data, dict):
        if response_data.get("ok") is True and isinstance(response_data.get("title"), str):
            return response_data["title"].strip() or None
        result = response_data.get("result")
        if isinstance(result, str):
            return _extract_title_update(result)
    if isinstance(response_data, str):
        try:
            return _extract_title_update(json.loads(response_data))
        except json.JSONDecodeError:
            return None
    return None


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


async def get_latest_message_previews(db: AsyncSession, session_ids: list[str]) -> dict[str, str]:
    """读取每个会话的最新非空消息预览，作为 last_message 的兜底来源。

    这是有意采用的笨办法：逐个会话查询，避免复杂窗口函数和跨数据库兼容问题。
    """
    previews: dict[str, str] = {}
    for session_id in session_ids:
        result = await db.execute(
            select(Message.content)
            .where(Message.session_id == session_id, Message.content != "")
            .order_by(
                Message.created_at.desc(),
                case((Message.role == "assistant", 0), else_=1),
            )
            .limit(1),
        )
        content = result.scalar_one_or_none()
        if content:
            previews[session_id] = content[:200]
    return previews


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


_FLUSH_INTERVAL = 5.0  # 每 5 秒 flush 一次助手消息到数据库


async def stream_response(
    user: User,
    adk_session_id: str,
    content: str,
    db: AsyncSession,
    session_id: str | None = None,
) -> AsyncGenerator[str]:
    """向 ADK Agent 发送消息并生成 SSE 格式的事件。

    架构：LLM 生成在独立的后台 task 中运行，SSE generator 从 queue 读取。
    即使前端断开连接，后台 task 仍会跑完并把结果保存到数据库。
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
    if session_id:
        injected_state["__chat_session_id"] = session_id
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

    # 预创建助手消息（流开始前就写入数据库，中途刷新不丢失）
    assistant_msg: Message | None = None
    if session_id:
        assistant_msg = Message(
            session_id=session_id,
            role="assistant",
            content="",
            status="generating",
        )
        db.add(assistant_msg)
        await db.commit()
        await db.refresh(assistant_msg)

    # ─── 后台任务：独立驱动 LLM 生成，不依赖前端连接 ───
    # 用 queue 做 SSE 事件缓冲；后台 task 即使前端断开也跑完
    queue: asyncio.Queue[str | None] = asyncio.Queue()

    # 保存后台 task 需要的参数（避免闭包引用请求级 db）
    _assistant_msg_id = assistant_msg.id if assistant_msg else None

    # 预先在请求级 db 中计算 msg_count（此时用户消息已 commit，一定能查到）
    _user_msg_count = 0
    if session_id:
        from sqlalchemy import func as sa_func

        _count_result = await db.execute(
            select(sa_func.count())
            .select_from(Message)
            .where(Message.session_id == session_id, Message.role == "user"),
        )
        _user_msg_count = _count_result.scalar() or 0

    async def _run_llm_background() -> None:
        """后台运行 LLM 并定期 flush 到数据库。前端断开不影响此 task。"""
        from server.database import async_session_factory

        # 使用独立的 db session，避免与请求级 session 冲突
        async with async_session_factory() as bg_db:
            # 重新加载 assistant_msg 到本 session
            bg_assistant_msg: Message | None = None
            if _assistant_msg_id:
                result = await bg_db.execute(select(Message).where(Message.id == _assistant_msg_id))
                bg_assistant_msg = result.scalar_one_or_none()

            total_input_tokens = 0
            total_output_tokens = 0
            assistant_text = ""
            thinking_text = ""
            collected_tool_calls: list[dict] = []
            collected_parts: list[dict] = []
            has_partial_text = False
            last_flush = asyncio.get_event_loop().time()

            def _append_text_part(part_type: str, text: str) -> None:
                """追加或合并连续文本类片段，保留刷新后的展示顺序。"""
                if collected_parts and collected_parts[-1].get("type") == part_type:
                    collected_parts[-1]["content"] = f"{collected_parts[-1].get('content', '')}{text}"
                else:
                    collected_parts.append({"type": part_type, "content": text})

            async def _flush_to_db() -> None:
                """将当前累积的内容写入数据库。"""
                nonlocal last_flush
                if bg_assistant_msg and (assistant_text or collected_tool_calls or thinking_text):
                    tool_calls_json = json.dumps(collected_tool_calls) if collected_tool_calls else None
                    parts_json = json.dumps(collected_parts) if collected_parts else None
                    bg_assistant_msg.content = assistant_text
                    bg_assistant_msg.thinking = thinking_text or None
                    bg_assistant_msg.tool_calls = tool_calls_json
                    bg_assistant_msg.parts = parts_json
                    await bg_db.commit()
                last_flush = asyncio.get_event_loop().time()

            try:
                async for event in runner.run_async(
                    user_id=user.id,
                    session_id=adk_session_id,
                    new_message=message,
                    state_delta=injected_state,
                    run_config=RunConfig(streaming_mode=StreamingMode.SSE),
                ):
                    # 提取 token 用量
                    if hasattr(event, "usage_metadata") and event.usage_metadata:
                        total_input_tokens += getattr(event.usage_metadata, "prompt_token_count", 0) or 0
                        total_output_tokens += getattr(event.usage_metadata, "candidates_token_count", 0) or 0

                    # state 变更 → 回写凭据
                    if event.actions and event.actions.state_delta:
                        for state_key, state_value in event.actions.state_delta.items():
                            parts = state_key.split("_", 1)
                            if len(parts) == 2 and parts[0] in PERSIST_CREDENTIAL_NAMESPACES:
                                namespace, key = parts
                                is_secret = key in ("token", "password", "secret")
                                await set_config(bg_db, user.id, namespace, key, str(state_value), is_secret=is_secret)

                    # 提取内容 → 放入 queue + 累积文本
                    if event.content and event.content.parts:
                        author = event.author or "assistant"
                        is_partial = bool(event.partial)

                        for part in event.content.parts:
                            # ── 文本 ──
                            if part.text:
                                text = part.text
                                if is_partial:
                                    has_partial_text = True
                                    is_thinking = bool(part.thought)
                                    if is_thinking:
                                        thinking_text += text
                                        _append_text_part("thinking", text)
                                    else:
                                        assistant_text += text
                                        _append_text_part("text", text)
                                    sse_data = json.dumps(
                                        {
                                            "event": "thinking" if is_thinking else "text",
                                            "author": author,
                                            "content": text,
                                        }
                                    )
                                    await queue.put(f"data: {sse_data}\n\n")
                                elif has_partial_text:
                                    pass  # 跳过汇总事件
                                else:
                                    is_thinking = bool(part.thought)
                                    if is_thinking:
                                        thinking_text += text
                                        _append_text_part("thinking", text)
                                    else:
                                        assistant_text += text
                                        _append_text_part("text", text)
                                    sse_data = json.dumps(
                                        {
                                            "event": "thinking" if is_thinking else "text",
                                            "author": author,
                                            "content": text,
                                        }
                                    )
                                    await queue.put(f"data: {sse_data}\n\n")

                            # ── 函数调用 ──
                            if part.function_call:
                                tc_data = {
                                    "name": part.function_call.name,
                                    "args": dict(part.function_call.args) if part.function_call.args else {},
                                }
                                collected_tool_calls.append(tc_data)
                                is_options_tool = tc_data["name"] == "present_options" and bool(
                                    tc_data.get("args", {}).get("options"),
                                )
                                part_type = "options" if is_options_tool else "tool_call"
                                collected_parts.append({"type": part_type, "toolCall": tc_data})
                                sse_data = json.dumps({"event": "tool_call", "author": author, **tc_data})
                                await queue.put(f"data: {sse_data}\n\n")

                            # ── 函数响应 ──
                            if part.function_response:
                                response_data = part.function_response.response
                                result_str = str(response_data) if response_data else ""
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
                                await queue.put(f"data: {sse_data}\n\n")

                                if not is_tool_error and part.function_response.name == "set_conversation_title":
                                    updated_title = _extract_title_update(response_data)
                                    if updated_title:
                                        title_data = json.dumps(
                                            {
                                                "event": "session_title_updated",
                                                "session_id": session_id,
                                                "title": updated_title,
                                            },
                                            ensure_ascii=False,
                                        )
                                        await queue.put(f"data: {title_data}\n\n")

                    # 定期 flush（每 _FLUSH_INTERVAL 秒）
                    now = asyncio.get_event_loop().time()
                    if now - last_flush >= _FLUSH_INTERVAL:
                        await _flush_to_db()

                # ─── 流正常结束：收尾工作 ───

                # 兜底回写凭据
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
                            await set_config(bg_db, user.id, namespace, key, str(state_value), is_secret=is_secret)

                # 记录用量
                # 如果模型未返回 token 用量（部分 LLM provider 在流式模式下不上报），
                # 则根据 UTF-8 字节长度进行估算以确保计费正常工作。
                if total_input_tokens == 0 and total_output_tokens == 0:
                    total_input_tokens = _estimate_tokens(content)
                    total_output_tokens = _estimate_tokens(assistant_text) if assistant_text else 1
                    logger.info(
                        "record_usage: no token usage from model, estimating: user=%s input=%d output=%d",
                        user.username,
                        total_input_tokens,
                        total_output_tokens,
                    )
                else:
                    logger.info(
                        "record_usage: user=%s input=%d output=%d",
                        user.username,
                        total_input_tokens,
                        total_output_tokens,
                    )
                await record_usage(
                    db=bg_db,
                    user_id=user.id,
                    model="agent",
                    input_tokens=total_input_tokens,
                    output_tokens=total_output_tokens,
                    agent_name="root_agent",
                    session_id=session_id,
                )

                # 最终 flush 消息到数据库
                if bg_assistant_msg and (assistant_text or collected_tool_calls or thinking_text):
                    tool_calls_json = json.dumps(collected_tool_calls) if collected_tool_calls else None
                    parts_json = json.dumps(collected_parts) if collected_parts else None
                    bg_assistant_msg.content = assistant_text
                    bg_assistant_msg.thinking = thinking_text or None
                    bg_assistant_msg.tool_calls = tool_calls_json
                    bg_assistant_msg.parts = parts_json
                    bg_assistant_msg.status = "done"
                    await bg_db.commit()
                elif bg_assistant_msg and not assistant_text and not collected_tool_calls:
                    await bg_db.delete(bg_assistant_msg)
                    await bg_db.commit()

                # 更新会话摘要。会话标题由 set_conversation_title 工具在 Agent 回复过程中静默维护。
                if session_id:
                    last_msg_preview = (assistant_text[:200]) if assistant_text else content[:200]
                    await bg_db.execute(
                        update(ChatSession).where(ChatSession.id == session_id).values(last_message=last_msg_preview)
                    )
                    await bg_db.commit()

                # 发送 done 信号
                done_data: dict = {
                    "event": "done",
                    "usage": {
                        "input_tokens": total_input_tokens,
                        "output_tokens": total_output_tokens,
                        "total_tokens": total_input_tokens + total_output_tokens,
                    },
                }
                await queue.put(f"data: {json.dumps(done_data)}\n\n")

            except Exception as e:
                logger.exception("LLM background task error: user=%s session=%s", user.username, adk_session_id)
                await queue.put(f"data: {json.dumps({'event': 'error', 'message': str(e)})}\n\n")
                # 异常时保存已累积的内容
                if bg_assistant_msg:
                    try:
                        tool_calls_json = json.dumps(collected_tool_calls) if collected_tool_calls else None
                        parts_json = json.dumps(collected_parts) if collected_parts else None
                        bg_assistant_msg.content = assistant_text or "(生成中断)"
                        bg_assistant_msg.thinking = thinking_text or None
                        bg_assistant_msg.tool_calls = tool_calls_json
                        bg_assistant_msg.parts = parts_json
                        bg_assistant_msg.status = "done"
                        await bg_db.commit()
                    except Exception:
                        logger.warning("Failed to flush assistant message after error")
                # 异常时也记录已产生的用量，若尚无 token 数据则同样按字节估算
                try:
                    if total_input_tokens == 0 and total_output_tokens == 0:
                        total_input_tokens = _estimate_tokens(content)
                        total_output_tokens = _estimate_tokens(assistant_text) if assistant_text else 1
                    await record_usage(
                        db=bg_db,
                        user_id=user.id,
                        model="agent",
                        input_tokens=total_input_tokens,
                        output_tokens=total_output_tokens,
                        agent_name="root_agent",
                        session_id=session_id,
                    )
                except Exception:
                    logger.warning("Failed to record usage after error")
            finally:
                await queue.put(None)  # 结束信号

    # 启动后台 task（前端断开不影响它继续运行）
    task = asyncio.create_task(_run_llm_background())

    # ─── SSE generator：从 queue 读取事件推给前端 ───
    try:
        while True:
            item = await queue.get()
            if item is None:
                break
            yield item
    except (asyncio.CancelledError, GeneratorExit):
        # 前端断开连接 → generator 被 cancel
        # 后台 task 会继续跑完，不需要干预
        logger.info("SSE disconnected (user=%s), LLM task continues in background", user.username)
    finally:
        # 确保 task 最终完成（如果还在跑，等它结束以免孤儿 task）
        if not task.done():
            # 不 cancel task，让它自然完成
            pass
