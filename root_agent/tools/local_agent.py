"""本地 Agent 代理工具：通过 WebSocket 调用用户电脑上的 local_agent。

这些工具在 ADK Agent 中运行，通过 server 侧的 WebSocket 连接池
直接向用户的 local_agent 下发命令并等待结果。
"""

from __future__ import annotations

from google.adk.tools import ToolContext


async def local_run_command(command: str, tool_context: ToolContext, cwd: str = "") -> str:
    """在用户的本地电脑上执行 shell 命令。

    需要用户的 local_agent 已连接。危险操作会弹窗让用户确认。

    Args:
        command: 要执行的 shell 命令。
        cwd: 工作目录（可选），支持 ~ 展开。

    Returns:
        命令输出或错误信息。
    """
    return await _call(tool_context, "run_command", {"command": command, "cwd": cwd})


async def local_read_file(path: str, tool_context: ToolContext) -> str:
    """读取用户本地电脑上的文件内容。

    Args:
        path: 文件路径，支持 ~ 展开。

    Returns:
        文件内容或错误信息。
    """
    return await _call(tool_context, "read_file", {"path": path})


async def local_write_file(path: str, content: str, tool_context: ToolContext) -> str:
    """在用户本地电脑上写入文件。

    Args:
        path: 文件路径，支持 ~ 展开。
        content: 文件内容。

    Returns:
        写入结果或错误信息。
    """
    return await _call(tool_context, "write_file", {"path": path, "content": content})


async def local_list_files(path: str, tool_context: ToolContext) -> str:
    """列出用户本地电脑上某个目录的文件。

    Args:
        path: 目录路径，默认当前目录，支持 ~ 展开。

    Returns:
        文件列表（JSON）或错误信息。
    """
    return await _call(tool_context, "list_files", {"path": path})


async def _call(tool_context: ToolContext, tool: str, args: dict) -> str:
    """实际调用 local_agent 的内部方法。"""
    # 从 state 中获取 user_id（在 stream_response 中注入）
    user_id = tool_context.state.get("__user_id")
    if not user_id:
        return "错误：无法确定用户身份"

    from server.routers.local_agent import call_local_agent, is_connected

    if not is_connected(user_id):
        return "本地 Agent 未连接。请在电脑上运行 liteyuki-agent 并登录。"

    result = await call_local_agent(user_id=user_id, tool=tool, args=args)

    if "error" in result:
        return f"执行失败: {result['error']}"
    return result.get("result", "（无输出）")


all_tools = [local_run_command, local_read_file, local_write_file, local_list_files]
