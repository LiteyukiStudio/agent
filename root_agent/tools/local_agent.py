"""本地 Agent 代理工具：通过 WebSocket 调用用户电脑上的 local_agent。"""

from __future__ import annotations

from google.adk.tools import ToolContext


def local_run_command(command: str, tool_context: ToolContext, cwd: str = "") -> str:
    """在用户的本地电脑上执行 shell 命令。

    需要用户的 local_agent 已连接。危险操作会弹窗让用户确认。

    Args:
        command: 要执行的 shell 命令。
        cwd: 工作目录（可选），支持 ~ 展开。

    Returns:
        命令输出或错误信息。
    """
    # 通过 state 传递请求，由 stream_response 中的回写机制处理
    # 实际调用在 server 侧完成，这里只是触发
    tool_context.state["__local_agent_request"] = {
        "tool": "run_command",
        "args": {"command": command, "cwd": cwd},
    }
    return "正在等待本地 Agent 执行..."


def local_read_file(path: str, tool_context: ToolContext) -> str:
    """读取用户本地电脑上的文件内容。

    Args:
        path: 文件路径，支持 ~ 展开。

    Returns:
        文件内容或错误信息。
    """
    tool_context.state["__local_agent_request"] = {
        "tool": "read_file",
        "args": {"path": path},
    }
    return "正在等待本地 Agent 读取文件..."


def local_write_file(path: str, content: str, tool_context: ToolContext) -> str:
    """在用户本地电脑上写入文件。

    Args:
        path: 文件路径，支持 ~ 展开。
        content: 文件内容。

    Returns:
        写入结果或错误信息。
    """
    tool_context.state["__local_agent_request"] = {
        "tool": "write_file",
        "args": {"path": path, "content": content},
    }
    return "正在等待本地 Agent 写入文件..."


def local_list_files(path: str, tool_context: ToolContext) -> str:
    """列出用户本地电脑上某个目录的文件。

    Args:
        path: 目录路径，默认当前目录，支持 ~ 展开。

    Returns:
        文件列表（JSON）或错误信息。
    """
    tool_context.state["__local_agent_request"] = {
        "tool": "list_files",
        "args": {"path": path},
    }
    return "正在等待本地 Agent 列出文件..."


all_tools = [local_run_command, local_read_file, local_write_file, local_list_files]
