"""通用的用户凭据隔离方案。

为所有 Agent 提供统一的、用户隔离的凭据读取机制。
每个 Agent 只需声明自己的 namespace 和所需的 key，
就能自动从当前用户的 session state 中读取凭据。

凭据分两类：
- **用户隔离凭据** (user_only=True)：如平台 Token，每个用户独立，
  只从 session state 读取，不回退到环境变量。用户通过对话配置。
- **共享配置** (user_only=False)：如实例地址，可以有全局默认值（环境变量或 default），
  用户也可以覆盖。

使用示例::

    from credential_provider import credentials

    creds = credentials("gitea", ["base_url", "token"], tool_context)

凭据解析优先级（每个 key 独立 fallback）：

1. ADK session state: ``tool_context.state["{namespace}_{key}"]``
   — 用户专属，由 server 在每次请求前从 UserConfig 注入
2. 环境变量（仅 user_only=False 时）
3. 默认值（如果声明了的话）

安全边界：
- 工具函数 **只通过本模块读取凭据**，禁止直接 os.getenv 或读文件
- 敏感值（secret=True）在日志和错误信息中自动脱敏
- 每次请求级别的隔离，不缓存跨请求状态
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Any


@dataclass
class CredentialKey:
    """单个凭据 key 的元信息。"""

    env_var: str = ""  # 环境变量名（仅 user_only=False 时有效）
    required: bool = False  # 是否必须
    secret: bool = False  # 是否敏感（影响日志脱敏）
    default: str = ""  # 默认值
    user_only: bool = False  # 用户隔离凭据，不回退到环境变量


@dataclass
class CredentialSchema:
    """Agent 凭据声明，描述一个 namespace 下需要哪些 key。

    示例::

        gitea_creds = CredentialSchema(
            namespace="gitea",
            keys={
                "base_url": CredentialKey(default="https://git.example.com"),
                "token": CredentialKey(secret=True, user_only=True),
            },
        )
    """

    namespace: str
    keys: dict[str, CredentialKey] = field(default_factory=dict)

    def resolve(self, tool_context: Any) -> dict[str, str]:
        """从 tool_context 解析所有凭据。"""
        return credentials(self.namespace, list(self.keys.keys()), tool_context, schema=self)


def credentials(
    namespace: str,
    keys: list[str],
    tool_context: Any,
    *,
    schema: CredentialSchema | None = None,
) -> dict[str, str]:
    """从 tool_context 中获取用户隔离的凭据。

    这是最核心的 API。工具函数调用此函数获取当前用户的凭据。

    Args:
        namespace: 凭据命名空间（如 "gitea"、"harbor"）。
        keys: 需要的凭据 key 列表（如 ["base_url", "token"]）。
        tool_context: ADK ToolContext 实例。
        schema: 可选的 CredentialSchema，提供元信息。

    Returns:
        key → value 的字典。未配置的 key 值为空字符串。

    Raises:
        ValueError: 当 schema 中标记为 required 的 key 未找到值时抛出。
    """
    result: dict[str, str] = {}
    state: dict = tool_context.state if hasattr(tool_context, "state") else {}
    key_metas = schema.keys if schema else {}

    for key in keys:
        meta = key_metas.get(key, CredentialKey())

        # 1. ADK session state（用户专属）
        state_key = f"{namespace}_{key}"
        value = state.get(state_key, "")

        # 2. 环境变量（仅非 user_only 的 key 才回退）
        if not value and not meta.user_only:
            env_name = meta.env_var or f"{namespace.upper()}_{key.upper()}"
            value = os.getenv(env_name, "")

        # 3. 默认值
        if not value:
            value = meta.default

        # 必填检查
        if not value and meta.required:
            hint = "请在对话中使用配置工具设置" if meta.user_only else "请配置后再试"
            raise ValueError(f"凭据 [{namespace}.{key}] 未配置。{hint}")

        result[key] = value

    return result


def mask_secret(value: str) -> str:
    """脱敏显示敏感值。"""
    if len(value) <= 6:
        return "******"
    return f"{value[:2]}{'*' * (len(value) - 4)}{value[-2:]}"
