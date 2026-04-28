"""Centralized model configuration.

Resolves which LLM model each agent should use.

Priority (per parameter, independently):
    1. Agent-specific env var:  {AGENT_NAME}_MODEL / {AGENT_NAME}_TOKEN / {AGENT_NAME}_API
    2. Global env var:          AGENT_MODEL / AGENT_TOKEN / AGENT_API
    3. Hardcoded fallback:      gemini-2.5-flash (native Gemini, no LiteLLM needed)

Each parameter falls back independently, so you can set the model globally
but override only the token for a specific agent.

For non-Gemini models (DeepSeek, OpenAI, Ollama, etc.), the function returns a LiteLlm
wrapper automatically. For Gemini models, it returns the plain model string.

## .env example

    # --- Global defaults (all agents use this unless overridden) ---
    AGENT_MODEL=deepseek/deepseek-chat
    AGENT_TOKEN=sk-xxxxxxxxxxxxxxxx
    AGENT_API=https://api.deepseek.com

    # --- Per-agent overrides (optional) ---
    ROOT_AGENT_MODEL=gemini-2.5-flash
    # ROOT_AGENT_TOKEN=              # falls back to AGENT_TOKEN
    # ROOT_AGENT_API=                # falls back to AGENT_API

    GITEA_AGENT_MODEL=deepseek/deepseek-chat
    GITEA_AGENT_TOKEN=sk-yyyyyyyyyy
    # GITEA_AGENT_API=               # falls back to AGENT_API
"""

from __future__ import annotations

import os
from typing import Any


def _resolve_env(agent_prefix: str, param: str) -> str:
    """Resolve a single config parameter with agent → global fallback.

    Lookup order:
        1. {AGENT_PREFIX}_{PARAM}   e.g. GITEA_AGENT_MODEL
        2. AGENT_{PARAM}            e.g. AGENT_MODEL
    """
    # Agent-specific
    value = os.getenv(f"{agent_prefix}_{param}", "")
    if value:
        return value
    # Global fallback
    return os.getenv(f"AGENT_{param}", "")


def _is_gemini(model_name: str) -> bool:
    """Check if a model string refers to a native Gemini model."""
    return model_name.startswith("gemini")


def get_model(agent_name: str) -> Any:
    """Return the model object for a given agent.

    Args:
        agent_name: The agent's name, e.g. "root_agent" or "gitea_agent".
                    Used to derive the env var prefix (uppercased, hyphens to underscores).

    Returns:
        Either a plain model string (for Gemini) or a LiteLlm instance (for everything else).
    """
    prefix = agent_name.upper().replace("-", "_")

    # Each parameter falls back independently
    model_name = _resolve_env(prefix, "MODEL")
    token = _resolve_env(prefix, "TOKEN")
    api_url = _resolve_env(prefix, "API")

    # Hardcoded fallback
    if not model_name:
        model_name = "gemini-2.5-flash"

    # Gemini models are used natively — just return the string
    if _is_gemini(model_name):
        return model_name

    # Non-Gemini models go through LiteLLM adapter
    from google.adk.models.lite_llm import LiteLlm

    kwargs: dict[str, str] = {"model": model_name}
    if token:
        kwargs["api_key"] = token
    if api_url:
        kwargs["api_base"] = api_url
    return LiteLlm(**kwargs)
