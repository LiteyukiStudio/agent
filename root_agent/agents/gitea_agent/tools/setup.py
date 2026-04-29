"""Gitea 凭证配置工具。

允许 Agent 在对话中查看和配置 Gitea 连接信息。
凭据存储在 ADK session state 中，由 server 端持久化到 UserConfig。
"""

from __future__ import annotations

from google.adk.tools import ToolContext

from credential_provider import mask_secret

from ..client import GiteaClient


def setup_gitea(token: str, tool_context: ToolContext, base_url: str = "https://git.liteyuki.org") -> dict:
    """Configure Gitea connection credentials for the current user.

    Args:
        token: Gitea API access token
        base_url: Gitea instance URL, defaults to https://git.liteyuki.org
    """
    # 写入 ADK session state（由 server 端自动持久化到 UserConfig）
    tool_context.state["gitea_base_url"] = base_url
    tool_context.state["gitea_token"] = token

    # 快速连通性检查
    try:
        client = GiteaClient(base_url=base_url, token=token)
        result = client.get("/version")
        client.close()
        version = result.get("version", "unknown")
        return {
            "status": "ok",
            "message": f"Gitea configured: {base_url} (version {version})",
        }
    except Exception as e:
        return {
            "status": "warning",
            "message": f"Credentials saved but connectivity check failed: {e}. "
            "The base_url or token might be incorrect.",
        }


def show_gitea_config(tool_context: ToolContext) -> dict:
    """Show current Gitea configuration status for the current user."""
    session_url = tool_context.state.get("gitea_base_url", "")
    session_token = tool_context.state.get("gitea_token", "")

    if not session_url and not session_token:
        return {
            "configured": False,
            "message": "Gitea is not configured. Use setup_gitea to configure.",
        }

    return {
        "configured": True,
        "base_url": session_url or "(not set)",
        "has_token": bool(session_token),
        "token_preview": mask_secret(session_token) if session_token else None,
    }
