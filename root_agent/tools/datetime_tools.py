"""时间工具：为 Agent 提供获取当前真实时间的能力。"""

from __future__ import annotations

import json
from datetime import datetime, timezone


def get_current_time() -> str:
    """获取当前的真实时间，以 ISO 8601 格式返回。

    任何需要"当前时间"的场景（例如：用户询问现在几点、计算时间差、生成时间戳、
    判断日期/星期、记录事件发生时间、与时间相关的计算或推理等）都必须调用本工具，
    **不要凭借自己的训练数据猜测当前时间**，模型自身的时间感知是不准确的。

    这是一个内部工具，调用过程对用户是透明的：不要在回复正文中提及"我调用了时间工具"
    或"我查询了系统时间"等表述，直接以自然语言把时间信息融入回答即可。

    Returns:
        JSON 字符串，包含以下字段：
        - iso_utc: UTC 时间，ISO 8601 格式，例如 "2026-05-06T10:23:45.123456+00:00"
        - iso_local: 服务器本地时间（带时区偏移），ISO 8601 格式
        - timestamp: Unix 时间戳（秒，浮点数）
        - timezone: 服务器本地时区名称
    """
    now_local = datetime.now().astimezone()
    now_utc = now_local.astimezone(timezone.utc)
    return json.dumps(
        {
            "iso_utc": now_utc.isoformat(),
            "iso_local": now_local.isoformat(),
            "timestamp": now_local.timestamp(),
            "timezone": str(now_local.tzinfo),
        },
        ensure_ascii=False,
    )


all_tools = [get_current_time]
