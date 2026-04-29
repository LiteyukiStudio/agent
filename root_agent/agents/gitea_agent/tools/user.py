"""Gitea 用户 API 工具。

涵盖：当前用户、用户查询、仓库、组织、关注者/正在关注。
参考：https://gitea.com/api/swagger#/user
"""

from __future__ import annotations

from google.adk.tools import ToolContext

from ..client import GiteaClient


def get_current_user(tool_context: ToolContext) -> dict:
    """Get the authenticated user's profile (the user who owns the token)."""
    with GiteaClient.from_context(tool_context) as c:
        return c.get("/user")


def get_user(username: str, tool_context: ToolContext) -> dict:
    """Get a user's public profile by username.

    Args:
        username: The user's login name
    """
    with GiteaClient.from_context(tool_context) as c:
        return c.get(f"/users/{username}")


def list_user_repos(username: str, tool_context: ToolContext, page: int = 1, limit: int = 20) -> dict:
    """List public repositories owned by a user.

    Args:
        username: The user's login name
        page: Page number
        limit: Results per page
    """
    with GiteaClient.from_context(tool_context) as c:
        return c.get(f"/users/{username}/repos", params={"page": page, "limit": limit})


def list_my_repos(tool_context: ToolContext, page: int = 1, limit: int = 20) -> dict:
    """List repositories accessible to the authenticated user (including private ones).

    Args:
        page: Page number
        limit: Results per page
    """
    with GiteaClient.from_context(tool_context) as c:
        return c.get("/user/repos", params={"page": page, "limit": limit})


def list_user_orgs(username: str, tool_context: ToolContext, page: int = 1, limit: int = 20) -> dict:
    """List organizations that a user is a member of.

    Args:
        username: The user's login name
        page: Page number
        limit: Results per page
    """
    with GiteaClient.from_context(tool_context) as c:
        return c.get(f"/users/{username}/orgs", params={"page": page, "limit": limit})


def list_followers(username: str, tool_context: ToolContext, page: int = 1, limit: int = 20) -> dict:
    """List a user's followers.

    Args:
        username: The user's login name
        page: Page number
        limit: Results per page
    """
    with GiteaClient.from_context(tool_context) as c:
        return c.get(f"/users/{username}/followers", params={"page": page, "limit": limit})


def list_following(username: str, tool_context: ToolContext, page: int = 1, limit: int = 20) -> dict:
    """List users that a user is following.

    Args:
        username: The user's login name
        page: Page number
        limit: Results per page
    """
    with GiteaClient.from_context(tool_context) as c:
        return c.get(f"/users/{username}/following", params={"page": page, "limit": limit})


# ---------------------------------------------------------------------------
# 导出
# ---------------------------------------------------------------------------

all_tools: list = [
    get_current_user,
    get_user,
    list_user_repos,
    list_my_repos,
    list_user_orgs,
    list_followers,
    list_following,
]
