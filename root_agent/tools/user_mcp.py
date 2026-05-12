"""用户级 MCP 工具：动态连接用户配置的 MCP 服务器，实现多租户隔离。

用户通过 setup_mcp 工具或 Web 设置页配置 MCP 服务器（namespace=mcp），
这些工具在运行时根据 tool_context.state 中注入的用户配置动态连接对应的 MCP 服务器。

数据格式：UserConfig 表中 namespace="mcp", key=服务器标识, value=JSON:
  {"name": "显示名", "url": "http://...", "headers": {"Authorization": "..."}}
"""

from __future__ import annotations

import json

from google.adk.tools import ToolContext


async def setup_mcp(
    server_key: str,
    url: str,
    tool_context: ToolContext,
    name: str = "",
    headers: str = "{}",
) -> str:
    """配置一个 MCP 服务器连接。

    在用户账户下注册一个 MCP 服务器，以便后续通过 mcp_list_tools / mcp_call_tool 使用。
    每个用户的 MCP 配置互相隔离。

    Args:
        server_key: 服务器标识（英文，如 "my_db"、"github"），用于后续引用。
        url: MCP 服务器的 HTTP/SSE 端点 URL。
        name: 服务器显示名称（可选，默认与 server_key 相同）。
        headers: 自定义请求头（JSON 字符串），如 '{"Authorization": "Bearer sk-xxx"}'。

    Returns:
        配置结果。
    """
    # 验证 URL
    if not url.startswith(("http://", "https://")):
        return "错误：URL 必须以 http:// 或 https:// 开头。"

    # 验证 server_key（只允许字母、数字、下划线、短横线）
    import re

    if not re.match(r"^[a-zA-Z][a-zA-Z0-9_-]*$", server_key):
        return "错误：server_key 只能包含字母、数字、下划线和短横线，且必须以字母开头。"

    # 解析 headers
    try:
        headers_dict = json.loads(headers)
        if not isinstance(headers_dict, dict):
            return "错误：headers 必须是 JSON 对象。"
    except json.JSONDecodeError:
        return "错误：headers 不是有效的 JSON。"

    config_value = json.dumps(
        {
            "name": name or server_key,
            "url": url,
            "headers": headers_dict,
        },
        ensure_ascii=False,
    )

    # 写入 state（会被 PERSIST_CREDENTIAL_NAMESPACES 自动持久化到 UserConfig）
    tool_context.state[f"mcp_{server_key}"] = config_value

    return f'已配置 MCP 服务器 "{name or server_key}"（{url}）。可以用 mcp_list_tools("{server_key}") 查看可用工具。'


async def remove_mcp(
    server_key: str,
    tool_context: ToolContext,
) -> str:
    """移除一个已配置的 MCP 服务器。

    Args:
        server_key: 要移除的服务器标识。

    Returns:
        操作结果。
    """
    state_key = f"mcp_{server_key}"
    if not tool_context.state.get(state_key):
        return f'错误：未找到 MCP 服务器 "{server_key}"。'

    tool_context.state[state_key] = ""  # 清空即删除
    return f'已移除 MCP 服务器 "{server_key}"。'


async def mcp_list_servers(tool_context: ToolContext) -> str:
    """列出当前用户已配置的所有 MCP 服务器。

    Returns:
        MCP 服务器列表（JSON），包含 key、name、url。
    """
    servers = []
    state_dict = tool_context.state.to_dict() if hasattr(tool_context.state, "to_dict") else dict(tool_context.state)
    for state_key, value in state_dict.items():
        if state_key.startswith("mcp_") and value and state_key != "__mcp_cache":
            server_key = state_key[4:]  # 去掉 "mcp_" 前缀
            # 跳过内部 key
            if server_key.startswith("_"):
                continue
            try:
                config = json.loads(value)
                servers.append(
                    {
                        "key": server_key,
                        "name": config.get("name", server_key),
                        "url": config.get("url", ""),
                    }
                )
            except json.JSONDecodeError:
                continue

    if not servers:
        return "当前没有配置任何 MCP 服务器。使用 setup_mcp 工具添加。"
    return json.dumps(servers, ensure_ascii=False)


async def mcp_list_tools(
    server_key: str,
    tool_context: ToolContext,
) -> str:
    """列出指定 MCP 服务器上的可用工具。

    Args:
        server_key: MCP 服务器标识（从 mcp_list_servers 获取）。

    Returns:
        该服务器上可用的工具列表（名称和描述）。
    """
    config = _get_server_config(server_key, tool_context)
    if isinstance(config, str):
        return config

    from google.adk.tools.mcp_tool.mcp_session_manager import SseConnectionParams
    from google.adk.tools.mcp_tool.mcp_toolset import McpToolset

    try:
        toolset = McpToolset(
            connection_params=SseConnectionParams(
                url=config["url"],
                headers=config.get("headers", {}),
            ),
        )
        tools = await toolset.get_tools()
        tool_list = [{"name": t.name, "description": getattr(t, "description", "")} for t in tools]
        await toolset.close()
        return json.dumps(tool_list, ensure_ascii=False)
    except Exception as e:
        return f"连接 MCP 服务器失败: {e}"


async def mcp_call_tool(
    server_key: str,
    tool_name: str,
    tool_context: ToolContext,
    arguments: str = "{}",
) -> str:
    """调用用户 MCP 服务器上的指定工具。

    Args:
        server_key: MCP 服务器标识。
        tool_name: 要调用的工具名称（从 mcp_list_tools 获取）。
        arguments: 工具参数（JSON 字符串），根据工具的 inputSchema 传参。

    Returns:
        工具执行结果。
    """
    config = _get_server_config(server_key, tool_context)
    if isinstance(config, str):
        return config

    try:
        args = json.loads(arguments)
    except json.JSONDecodeError:
        return "错误：arguments 不是有效的 JSON。"

    from google.adk.tools.mcp_tool.mcp_session_manager import SseConnectionParams
    from google.adk.tools.mcp_tool.mcp_toolset import McpToolset

    try:
        toolset = McpToolset(
            connection_params=SseConnectionParams(
                url=config["url"],
                headers=config.get("headers", {}),
            ),
        )
        tools = await toolset.get_tools()
        target_tool = next((t for t in tools if t.name == tool_name), None)
        if not target_tool:
            available = ", ".join(t.name for t in tools)
            await toolset.close()
            return f'错误：服务器上没有名为 "{tool_name}" 的工具。可用工具: {available}'

        result = await target_tool.run_async(args=args, tool_context=tool_context)
        await toolset.close()

        if isinstance(result, dict):
            return json.dumps(result, ensure_ascii=False)
        return str(result)
    except Exception as e:
        return f"调用工具失败: {e}"


def _get_server_config(server_key: str, tool_context: ToolContext) -> dict | str:
    """从 tool_context.state 中获取 MCP 服务器配置。"""
    state_key = f"mcp_{server_key}"
    config_raw = tool_context.state.get(state_key)
    if not config_raw:
        return f'错误：未找到 MCP 服务器 "{server_key}"。请先使用 setup_mcp 配置，或用 mcp_list_servers 查看已有配置。'

    try:
        config = json.loads(config_raw)
        if "url" not in config:
            return f'错误：MCP 配置 "{server_key}" 缺少 url 字段。'
        return config
    except json.JSONDecodeError:
        return f'错误：MCP 配置 "{server_key}" 格式无效。'


all_tools = [setup_mcp, remove_mcp, mcp_list_servers, mcp_list_tools, mcp_call_tool]
