"""会话元信息工具：供 Agent 静默维护当前会话的 UI 元数据。"""

from __future__ import annotations

import json
import re

from google.adk.tools import ToolContext
from sqlalchemy import update

_SECRET_PATTERNS = (
    re.compile(r"sk-[A-Za-z0-9_-]{8,}"),
    re.compile(r"gh[pousr]_[A-Za-z0-9_]{12,}"),
    re.compile(r"[A-Za-z0-9_\-]{20,}\.[A-Za-z0-9_\-]{20,}\.[A-Za-z0-9_\-]{20,}"),
)


def _clean_title(title: str) -> str:
    """清理模型生成的标题，避免过长、多行或明显敏感内容。"""
    cleaned = " ".join(title.strip().split())
    cleaned = cleaned.strip("'\"“”‘’「」《》.,，。!！?？:：")
    for pattern in _SECRET_PATTERNS:
        cleaned = pattern.sub("[已隐藏]", cleaned)
    if len(cleaned) > 30:
        cleaned = f"{cleaned[:27]}..."
    return cleaned


async def set_conversation_title(title: str, tool_context: ToolContext) -> str:
    """静默设置当前会话标题。

    这是内部 UI 元数据工具。你应该在每个新会话首次回答用户前悄悄调用它，设置一个简短中文标题，
    不要在回复正文中告诉用户你调用了本工具，也不要解释标题更新过程。

    Args:
        title: 简短会话标题，概括用户本轮问题，不超过 20 个中文字符，不包含密钥、Token、邮箱、手机号等敏感信息。
    """
    from server.database import async_session_factory
    from server.models.chat_session import ChatSession

    session_id = tool_context.state.get("__chat_session_id")
    user_id = tool_context.state.get("__user_id")
    cleaned_title = _clean_title(title)

    if not session_id or not user_id:
        return json.dumps({"ok": False, "reason": "missing_session"}, ensure_ascii=False)
    if not cleaned_title:
        return json.dumps({"ok": False, "reason": "empty_title"}, ensure_ascii=False)

    async with async_session_factory() as db:
        result = await db.execute(
            update(ChatSession)
            .where(
                ChatSession.id == session_id,
                ChatSession.user_id == user_id,
                ChatSession.title_custom.is_(False),
                ChatSession.title.in_(["New Chat", "新对话"]),
            )
            .values(title=cleaned_title),
        )
        await db.commit()

    if result.rowcount == 0:
        return json.dumps({"ok": False, "reason": "title_not_changed"}, ensure_ascii=False)
    return json.dumps({"ok": True, "title": cleaned_title}, ensure_ascii=False)


all_tools = [set_conversation_title]
