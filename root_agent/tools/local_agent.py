"""本地 Agent 代理工具：通过 WebSocket 调用用户电脑上的 local_agent。

这些工具在 ADK Agent 中运行，通过 server 侧的 WebSocket 连接池
直接向用户的 local_agent 下发命令并等待结果。

支持指定 device 参数在特定设备上执行，不指定则由 AI 根据上下文选择。
"""

from __future__ import annotations

import json

from google.adk.tools import ToolContext


async def local_list_devices(tool_context: ToolContext) -> str:
    """列出用户所有已连接的本地设备。

    返回每个设备的 device_id、device_name 和 os_type。
    在需要操作特定设备时，先调用此工具确认目标设备。

    Returns:
        JSON 格式的设备列表。
    """
    user_id = tool_context.state.get("__user_id")
    if not user_id:
        return "错误：无法确定用户身份"

    from server.routers.local_agent import get_connected_devices

    devices = get_connected_devices(user_id)
    if not devices:
        return "没有在线的本地设备。请在电脑上运行 liteyuki-agent 并登录。"

    return json.dumps(devices, ensure_ascii=False)


async def local_run_command(
    command: str,
    tool_context: ToolContext,
    cwd: str = "",
    device: str = "",
) -> str:
    """在用户的本地电脑上执行 shell 命令。

    需要用户的 local_agent 已连接。危险操作会弹窗让用户确认。
    有多个设备时，通过 device 参数指定目标设备名称或 ID。

    Args:
        command: 要执行的 shell 命令。
        cwd: 工作目录（可选），支持 ~ 展开。
        device: 目标设备名称或 device_id（可选）。不指定则使用默认设备。

    Returns:
        命令输出或错误信息。
    """
    return await _call(tool_context, "run_command", {"command": command, "cwd": cwd}, device)


async def local_read_file(
    path: str,
    tool_context: ToolContext,
    device: str = "",
) -> str:
    """读取用户本地电脑上的文件内容。

    Args:
        path: 文件路径，支持 ~ 展开。
        device: 目标设备名称或 device_id（可选）。

    Returns:
        文件内容或错误信息。
    """
    return await _call(tool_context, "read_file", {"path": path}, device)


async def local_write_file(
    path: str,
    content: str,
    tool_context: ToolContext,
    device: str = "",
) -> str:
    """在用户本地电脑上写入文件。

    Args:
        path: 文件路径，支持 ~ 展开。
        content: 文件内容。
        device: 目标设备名称或 device_id（可选）。

    Returns:
        写入结果或错误信息。
    """
    return await _call(tool_context, "write_file", {"path": path, "content": content}, device)


async def local_list_files(
    path: str,
    tool_context: ToolContext,
    device: str = "",
) -> str:
    """列出用户本地电脑上某个目录的文件。

    Args:
        path: 目录路径，默认当前目录，支持 ~ 展开。
        device: 目标设备名称或 device_id（可选）。

    Returns:
        文件列表（JSON）或错误信息。
    """
    return await _call(tool_context, "list_files", {"path": path}, device)


async def _call(tool_context: ToolContext, tool: str, args: dict, device: str = "") -> str:
    """实际调用 local_agent 的内部方法。"""
    user_id = tool_context.state.get("__user_id")
    if not user_id:
        return "错误：无法确定用户身份"

    from server.routers.local_agent import (
        _connections,
        call_local_agent,
        is_connected,
    )

    if not is_connected(user_id):
        return "本地 Agent 未连接。请在电脑上运行 liteyuki-agent 并登录。"

    # 解析 device 参数：支持 device_name 或 device_id
    device_id: str | None = None
    if device:
        devices = _connections.get(user_id, {})
        # 先按 device_id 精确匹配
        if device in devices:
            device_id = device
        else:
            # 按 device_name 模糊匹配
            for did, info in devices.items():
                if device.lower() in info.device_name.lower():
                    device_id = did
                    break
            if not device_id:
                available = ", ".join(f"{d.device_name} ({d.os_type})" for d in devices.values())
                return f"未找到设备 '{device}'。在线设备: {available}"

    result = await call_local_agent(user_id=user_id, tool=tool, args=args, device_id=device_id)

    if "error" in result:
        return f"执行失败: {result['error']}"

    # 构造返回值，包含设备信息标记（前端解析用）
    output = result.get("result", "（无输出）")
    device_info = result.get("_device")
    if device_info:
        # 在结果末尾附加设备标记（JSON 格式，前端识别）
        meta = json.dumps({"_device": device_info}, ensure_ascii=False)
        return f"{output}\n<!--device:{meta}-->"
    return output


all_tools = [local_list_devices, local_run_command, local_read_file, local_write_file, local_list_files]
