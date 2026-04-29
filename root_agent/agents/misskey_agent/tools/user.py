"""Misskey 用户相关工具。

涵盖：当前用户、用户查询、关注/取关。
"""

from __future__ import annotations

from google.adk.tools import ToolContext

from ..client import MisskeyClient

# ---------------------------------------------------------------------------
# 用户信息
# ---------------------------------------------------------------------------


def get_me(tool_context: ToolContext) -> dict:
    """Get the authenticated user's own profile."""
    with MisskeyClient.from_context(tool_context) as c:
        return c.request("/i")


def show_user(
    tool_context: ToolContext,
    user_id: str = "",
    username: str = "",
    host: str = "",
) -> dict:
    """Get a user's profile by ID or username.

    Args:
        user_id: The user ID (use this or username)
        username: The username to look up
        host: The host of the user (for remote/federated users, leave empty for local)
    """
    data: dict = {}
    if user_id:
        data["userId"] = user_id
    elif username:
        data["username"] = username
        if host:
            data["host"] = host
    with MisskeyClient.from_context(tool_context) as c:
        return c.request("/users/show", data)


def search_users(
    query: str,
    tool_context: ToolContext,
    limit: int = 10,
    offset: int = 0,
    origin: str = "combined",
) -> dict:
    """Search users by keyword.

    Args:
        query: Search keyword
        limit: Max results (default 10)
        offset: Offset for pagination
        origin: "local", "remote", or "combined"
    """
    with MisskeyClient.from_context(tool_context) as c:
        return c.request(
            "/users/search",
            {
                "query": query,
                "limit": limit,
                "offset": offset,
                "origin": origin,
            },
        )


# ---------------------------------------------------------------------------
# 关注
# ---------------------------------------------------------------------------


def get_followers(
    user_id: str,
    tool_context: ToolContext,
    limit: int = 20,
    since_id: str = "",
    until_id: str = "",
) -> dict:
    """List followers of a user.

    Args:
        user_id: The user ID
        limit: Max results
        since_id: Cursor for pagination
        until_id: Cursor for pagination
    """
    data: dict = {"userId": user_id, "limit": limit}
    if since_id:
        data["sinceId"] = since_id
    if until_id:
        data["untilId"] = until_id
    with MisskeyClient.from_context(tool_context) as c:
        return c.request("/users/followers", data)


def get_following(
    user_id: str,
    tool_context: ToolContext,
    limit: int = 20,
    since_id: str = "",
    until_id: str = "",
) -> dict:
    """List users that a user is following.

    Args:
        user_id: The user ID
        limit: Max results
        since_id: Cursor for pagination
        until_id: Cursor for pagination
    """
    data: dict = {"userId": user_id, "limit": limit}
    if since_id:
        data["sinceId"] = since_id
    if until_id:
        data["untilId"] = until_id
    with MisskeyClient.from_context(tool_context) as c:
        return c.request("/users/following", data)


def follow_user(user_id: str, tool_context: ToolContext) -> dict:
    """Follow a user.

    Args:
        user_id: The user ID to follow
    """
    with MisskeyClient.from_context(tool_context) as c:
        return c.request("/following/create", {"userId": user_id})


def unfollow_user(user_id: str, tool_context: ToolContext) -> dict:
    """Unfollow a user.

    Args:
        user_id: The user ID to unfollow
    """
    with MisskeyClient.from_context(tool_context) as c:
        return c.request("/following/delete", {"userId": user_id})


all_tools: list = [
    get_me,
    show_user,
    search_users,
    get_followers,
    get_following,
    follow_user,
    unfollow_user,
]
