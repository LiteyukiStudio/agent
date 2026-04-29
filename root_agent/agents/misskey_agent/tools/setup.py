"""Misskey 凭证配置工具。"""

from __future__ import annotations

from google.adk.tools import ToolContext

from credential_provider import mask_secret

from ..client import MisskeyClient


def setup_misskey(token: str, tool_context: ToolContext, base_url: str = "https://lab.liteyuki.org") -> dict:
    """Configure Misskey connection credentials for the current user.

    Args:
        token: Misskey API access token
        base_url: Misskey instance URL, defaults to https://lab.liteyuki.org
    """
    tool_context.state["misskey_base_url"] = base_url
    tool_context.state["misskey_token"] = token

    try:
        client = MisskeyClient(base_url=base_url, token=token)
        result = client.request("/meta")
        client.close()
        name = result.get("name", "unknown")
        version = result.get("version", "unknown")
        return {
            "status": "ok",
            "message": f"Misskey configured: {base_url} ({name}, version {version})",
        }
    except Exception as e:
        return {
            "status": "warning",
            "message": f"Credentials saved but connectivity check failed: {e}.",
        }


def show_misskey_config(tool_context: ToolContext) -> dict:
    """Show current Misskey configuration status for the current user."""
    session_url = tool_context.state.get("misskey_base_url", "")
    session_token = tool_context.state.get("misskey_token", "")

    if not session_url and not session_token:
        return {
            "configured": False,
            "message": "Misskey is not configured. Use setup_misskey to configure. "
            "Default instance: https://lab.liteyuki.org",
        }

    return {
        "configured": True,
        "base_url": session_url or "(not set, default: https://lab.liteyuki.org)",
        "has_token": bool(session_token),
        "token_preview": mask_secret(session_token) if session_token else None,
    }


all_tools: list = [setup_misskey, show_misskey_config]
