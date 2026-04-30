"""共享的 Agent 回调函数。"""

from __future__ import annotations

import logging
import traceback
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from google.adk.tools import BaseTool, ToolContext

logger = logging.getLogger(__name__)


def on_tool_error(tool: BaseTool, args: dict[str, Any], tool_context: ToolContext, error: Exception) -> dict:
    """全局工具错误兜底：把异常转为 function_response 返回给 LLM，避免整个 stream 崩溃。"""
    tb = traceback.format_exception(type(error), error, error.__traceback__)
    short_tb = "".join(tb[-3:])  # 只保留最后几帧
    logger.error("Tool '%s' raised %s: %s\n%s", tool.name, type(error).__name__, error, short_tb)
    return {
        "error": True,
        "error_type": type(error).__name__,
        "error_message": str(error),
    }
