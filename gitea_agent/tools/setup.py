"""Interactive Gitea credential setup tools.

Allows the agent to configure Gitea connection at runtime via conversation,
with fallback to .env environment variables.
"""

from __future__ import annotations

from google.adk.tools import ToolContext

from ..client import GiteaClient


def setup_gitea(base_url: str, token: str, tool_context: ToolContext) -> dict:
    """Configure Gitea connection credentials. Saves to both session state and persistent file.

    Args:
        base_url: Gitea instance URL, e.g. https://gitea.example.com
        token: Gitea API access token
    """
    # Write to ADK session state (available to all tools in this session)
    tool_context.state["gitea_base_url"] = base_url
    tool_context.state["gitea_token"] = token

    # Persist to file (survives across sessions)
    GiteaClient.save_credentials(base_url, token)

    # Quick connectivity check
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
    """Show current Gitea configuration status. Shows where the config comes from (session/env/file).

    Useful when the user wants to verify or debug the Gitea connection.
    """
    import os

    sources: list[str] = []
    base_url = ""
    has_token = False

    # Check session state
    session_url = tool_context.state.get("gitea_base_url", "")
    session_token = tool_context.state.get("gitea_token", "")
    if session_url:
        sources.append("session")
        base_url = session_url
        has_token = bool(session_token)

    # Check env
    env_url = os.getenv("GITEA_BASE_URL", "")
    env_token = os.getenv("GITEA_TOKEN", "")
    if env_url:
        sources.append("env")
        if not base_url:
            base_url = env_url
            has_token = bool(env_token)

    # Check file
    saved = GiteaClient.load_saved_credentials()
    if saved.get("base_url"):
        sources.append("file")
        if not base_url:
            base_url = saved["base_url"]
            has_token = bool(saved.get("token"))

    if not base_url:
        return {
            "configured": False,
            "message": "Gitea is not configured. Use setup_gitea to configure, "
            "or set GITEA_BASE_URL and GITEA_TOKEN in .env",
        }

    return {
        "configured": True,
        "base_url": base_url,
        "has_token": has_token,
        "sources": sources,
    }
