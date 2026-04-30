"""用户画像记忆工具：AI 主动记住、读取和遗忘用户信息。"""

from __future__ import annotations

from google.adk.tools import ToolContext


def recall_memories(tool_context: ToolContext) -> str:
    """读取关于当前用户的所有记忆。

    在以下情况应主动调用此工具：
    - 会话开始时，了解用户的背景和偏好
    - 需要个性化回复但不确定用户信息时
    - 用户问"你还记得我吗"、"你知道我是谁吗"等问题时

    Returns:
        JSON 格式的所有记忆内容，如果没有记忆则返回提示。
    """
    memories = {}
    for k, v in tool_context.state.to_dict().items():
        if k.startswith("memory_") and v:
            key = k[7:]  # 去掉 "memory_" 前缀
            memories[key] = v

    if not memories:
        return "暂无关于该用户的记忆。"

    lines = [f"- {k}: {v}" for k, v in memories.items()]
    return "用户记忆:\n" + "\n".join(lines)


def remember_user(key: str, content: str, tool_context: ToolContext) -> str:
    """记住关于用户的一条信息，持久化保存供后续所有会话使用。

    当用户表达了个人偏好、习惯、身份信息、工作背景等值得长期记住的信息时，
    主动调用此工具保存。不需要用户明确要求"记住"，你应该主动判断。

    适合记住的信息类型：
    - 技术偏好（编程语言、框架、工具链）
    - 工作背景（职业、公司、项目）
    - 沟通偏好（回复风格、语言、详细程度）
    - 个人信息（名字、昵称、时区）
    - 习惯和约定（代码风格、命名规范）

    不应该记住的信息：
    - 一次性的临时信息
    - 密码、密钥等敏感信息（使用凭据系统）
    - 过于细碎无意义的内容

    Args:
        key: 记忆的分类标识，使用 snake_case，如：
            "preference_language", "work_project", "name",
            "communication_style", "coding_convention"
        content: 要记住的内容，用简洁的自然语言描述，不超过 200 字。

    Returns:
        确认信息。
    """
    tool_context.state[f"memory_{key}"] = content
    return f"已记住: {key} = {content}"


def forget_user(key: str | None, tool_context: ToolContext) -> str:
    """清除关于用户的记忆。

    当用户明确要求忘掉某些信息时调用。

    Args:
        key: 要清除的记忆标识。传 None 或空字符串则清除所有记忆。
            例如 "preference_language" 清除语言偏好。

    Returns:
        确认信息。
    """
    if not key:
        # 清除所有记忆
        keys_to_remove = [k for k in tool_context.state.to_dict() if k.startswith("memory_")]
        for k in keys_to_remove:
            tool_context.state[k] = ""
        return f"已清除所有记忆（共 {len(keys_to_remove)} 条）"

    state_key = f"memory_{key}"
    if state_key in tool_context.state:
        tool_context.state[state_key] = ""
        return f"已清除记忆: {key}"
    return f"未找到记忆: {key}"


all_tools = [recall_memories, remember_user, forget_user]
