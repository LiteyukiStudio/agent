"""Gitea 杂项 API 工具。

涵盖：版本信息、Markdown 渲染、服务器状态。
参考：https://gitea.com/api/swagger#/miscellaneous
"""

from __future__ import annotations

from ..client import GiteaClient


def get_gitea_version() -> dict:
    """Get the Gitea server version."""
    with GiteaClient() as c:
        return c.get("/version")


def render_markdown(text: str, mode: str = "gfm", wiki: bool = False) -> dict:
    """Render a Markdown string to HTML using Gitea's renderer.

    Args:
        text: Markdown text to render
        mode: Render mode — "gfm" (GitHub Flavored) or "comment" or "wiki"
        wiki: Whether to parse wiki links
    """
    with GiteaClient() as c:
        return c.post("/markdown", json_data={"Text": text, "Mode": mode, "Wiki": wiki})


def get_signing_key() -> dict:
    """Get the Gitea server's default GPG signing key."""
    with GiteaClient() as c:
        return c.get("/signing-key.gpg")


# ---------------------------------------------------------------------------
# 导出
# ---------------------------------------------------------------------------

all_tools: list = [
    get_gitea_version,
    render_markdown,
    get_signing_key,
]
