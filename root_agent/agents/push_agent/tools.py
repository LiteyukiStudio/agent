"""Push Agent 工具：发送通知、管理推送通道。"""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

from .adapters import PushAdapter, get_adapter_class, list_adapter_types

if TYPE_CHECKING:
    from google.adk.tools import ToolContext


def _get_channels(tool_context: ToolContext) -> dict:
    """从 state 中读取用户的推送通道配置。"""
    raw = tool_context.state.get("push_channels") or "{}"
    try:
        return json.loads(raw) if isinstance(raw, str) else raw
    except (json.JSONDecodeError, TypeError):
        return {}


def _save_channels(tool_context: ToolContext, channels: dict) -> None:
    """保存推送通道配置到 state。"""
    tool_context.state["push_channels"] = json.dumps(channels, ensure_ascii=False)


async def send_notification(
    title: str,
    content: str,
    tool_context: ToolContext,
    channel_name: str = "",
    content_type: str = "text",
) -> str:
    """发送通知消息到用户配置的推送通道。

    Args:
        title: 通知标题。
        content: 通知内容。
        channel_name: 目标通道名称。留空则发送到所有已配置的通道。
        content_type: 内容类型：text（纯文本）、markdown、html。

    Returns:
        每个通道的发送结果。
    """
    channels = _get_channels(tool_context)

    if not channels:
        return "尚未配置任何推送通道。请先使用 configure_push_channel 添加通道。"

    # 选择目标通道
    if channel_name:
        if channel_name not in channels:
            available = ", ".join(channels.keys())
            return f"未找到通道 '{channel_name}'。已配置的通道: {available}"
        targets = {channel_name: channels[channel_name]}
    else:
        targets = channels

    results = []
    for name, cfg in targets.items():
        adapter_type = cfg.get("type", "")
        adapter_cls = get_adapter_class(adapter_type)
        if not adapter_cls:
            results.append(f"  {name}: 错误 - 未知类型 '{adapter_type}'")
            continue

        adapter: PushAdapter = adapter_cls(cfg)
        result = await adapter.send(title, content, content_type)
        results.append(f"  {name} ({adapter_cls.display_name}): {result}")

    return "发送结果:\n" + "\n".join(results)


async def list_push_channels(tool_context: ToolContext) -> str:
    """列出当前用户已配置的所有推送通道。

    Returns:
        已配置通道的列表信息，包含名称、类型和配置摘要。
    """
    channels = _get_channels(tool_context)

    if not channels:
        # 列出可用类型帮助用户了解选择
        types = list_adapter_types()
        type_list = "\n".join(f"  - {t['type']}: {t['display_name']}" for t in types)
        return f"尚未配置推送通道。\n\n可用的通道类型:\n{type_list}\n\n使用 configure_push_channel 添加通道。"

    lines = ["已配置的推送通道:"]
    for name, cfg in channels.items():
        ch_type = cfg.get("type", "unknown")
        adapter_cls = get_adapter_class(ch_type)
        display = adapter_cls.display_name if adapter_cls else ch_type
        # 摘要：显示关键字段（脱敏）
        summary_parts = []
        for k, v in cfg.items():
            if k == "type":
                continue
            if k in ("password", "access_token", "app_token") and v:
                summary_parts.append(f"{k}=***")
            elif v:
                val = str(v)
                summary_parts.append(f"{k}={val[:30]}{'...' if len(val) > 30 else ''}")
        summary = ", ".join(summary_parts)
        lines.append(f"  [{name}] {display} | {summary}")

    return "\n".join(lines)


async def configure_push_channel(
    channel_type: str,
    channel_name: str,
    config: dict,
    tool_context: ToolContext,
) -> str:
    """添加或更新一个推送通道配置。

    Args:
        channel_type: 通道类型（feishu / wecom / onebot / smtp / gotify）。
        channel_name: 通道名称（用户自定义，如 "我的飞书群"）。
        config: 通道配置字典，字段取决于类型。

    Returns:
        配置结果。
    """
    # 验证类型
    adapter_cls = get_adapter_class(channel_type)
    if not adapter_cls:
        types = list_adapter_types()
        type_list = ", ".join(t["type"] for t in types)
        return f"未知的通道类型 '{channel_type}'。可用类型: {type_list}"

    # 验证配置
    full_config = {"type": channel_type, **config}
    adapter = adapter_cls(full_config)
    error = adapter.validate_config()
    if error:
        schema_help = "\n".join(f"  - {k}: {v}" for k, v in adapter_cls.config_schema.items())
        return f"配置不完整: {error}\n\n{adapter_cls.display_name} 需要以下配置:\n{schema_help}"

    # 保存
    channels = _get_channels(tool_context)
    channels[channel_name] = full_config
    _save_channels(tool_context, channels)

    return f"✅ 通道 '{channel_name}' ({adapter_cls.display_name}) 配置成功！"


async def remove_push_channel(
    channel_name: str,
    tool_context: ToolContext,
) -> str:
    """删除一个推送通道配置。

    Args:
        channel_name: 要删除的通道名称。

    Returns:
        删除结果。
    """
    channels = _get_channels(tool_context)
    if channel_name not in channels:
        available = ", ".join(channels.keys()) or "（无）"
        return f"未找到通道 '{channel_name}'。已配置的通道: {available}"

    del channels[channel_name]
    _save_channels(tool_context, channels)
    return f"✅ 通道 '{channel_name}' 已删除。"


async def test_push_channel(
    channel_name: str,
    tool_context: ToolContext,
) -> str:
    """测试一个推送通道是否能正常发送。

    Args:
        channel_name: 要测试的通道名称。

    Returns:
        测试结果。
    """
    channels = _get_channels(tool_context)
    if channel_name not in channels:
        return f"未找到通道 '{channel_name}'。"

    cfg = channels[channel_name]
    adapter_cls = get_adapter_class(cfg.get("type", ""))
    if not adapter_cls:
        return f"通道类型未知: {cfg.get('type')}"

    adapter = adapter_cls(cfg)
    result = await adapter.send("测试通知", "这是一条来自 Liteyuki Flow 的测试消息 ✓", "text")
    if result == "ok":
        return f"✅ 通道 '{channel_name}' 测试成功！消息已发送。"
    return f"❌ 通道 '{channel_name}' 测试失败: {result}"


all_tools = [
    send_notification,
    list_push_channels,
    configure_push_channel,
    remove_push_channel,
    test_push_channel,
]
