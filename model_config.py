"""统一模型配置。

解析每个 Agent 应使用的 LLM 模型。

优先级（每个参数独立回退）：
    1. Agent 级环境变量：{AGENT_NAME}_MODEL / {AGENT_NAME}_TOKEN / {AGENT_NAME}_API
    2. 全局环境变量：    AGENT_MODEL / AGENT_TOKEN / AGENT_API
    3. 硬编码兜底：      gemini-2.5-flash（原生 Gemini，无需 LiteLLM）

每个参数独立回退，可以全局设模型但为某个 Agent 单独覆盖 Token。

非 Gemini 模型（DeepSeek、OpenAI、Ollama 等）自动通过 LiteLlm 适配器返回。
Gemini 模型直接返回模型名字符串。

## .env 示例

    # --- 全局默认（所有 Agent 使用，除非被覆盖）---
    AGENT_MODEL=deepseek/deepseek-chat
    AGENT_TOKEN=sk-xxxxxxxxxxxxxxxx
    AGENT_API=https://api.deepseek.com

    # --- Agent 级覆盖（可选）---
    ROOT_AGENT_MODEL=gemini-2.5-flash
    # ROOT_AGENT_TOKEN=              # 回退到 AGENT_TOKEN
    # ROOT_AGENT_API=                # 回退到 AGENT_API

    GITEA_AGENT_MODEL=deepseek/deepseek-chat
    GITEA_AGENT_TOKEN=sk-yyyyyyyyyy
    # GITEA_AGENT_API=               # 回退到 AGENT_API
"""

from __future__ import annotations

import os
from typing import Any


def _resolve_env(agent_prefix: str, param: str) -> str:
    """解析单个配置参数，按 Agent 级 → 全局 顺序回退。

    查找顺序：
        1. {AGENT_PREFIX}_{PARAM}   例如 GITEA_AGENT_MODEL
        2. AGENT_{PARAM}            例如 AGENT_MODEL
    """
    # Agent 级
    value = os.getenv(f"{agent_prefix}_{param}", "")
    if value:
        return value
    # 全局回退
    return os.getenv(f"AGENT_{param}", "")


def _is_gemini(model_name: str) -> bool:
    """检查模型名是否为原生 Gemini 模型。"""
    return model_name.startswith("gemini")


def get_model(agent_name: str) -> Any:
    """返回指定 Agent 的模型对象。

    Args:
        agent_name: Agent 名称，例如 "root_agent" 或 "gitea_agent"。
                    用于推导环境变量前缀（大写，连字符转下划线）。

    Returns:
        Gemini 模型返回字符串，其他模型返回 LiteLlm 实例。
    """
    prefix = agent_name.upper().replace("-", "_")

    # 每个参数独立回退
    model_name = _resolve_env(prefix, "MODEL")
    token = _resolve_env(prefix, "TOKEN")
    api_url = _resolve_env(prefix, "API")

    # 硬编码兜底
    if not model_name:
        model_name = "gemini-2.5-flash"

    # Gemini 模型原生使用，直接返回字符串
    if _is_gemini(model_name):
        return model_name

    # 非 Gemini 模型通过 LiteLLM 适配器
    from google.adk.models.lite_llm import LiteLlm

    kwargs: dict[str, str] = {"model": model_name}
    if token:
        kwargs["api_key"] = token
    if api_url:
        kwargs["api_base"] = api_url
    return LiteLlm(**kwargs)
