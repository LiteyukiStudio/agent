"""Misskey 通知工具。"""

from __future__ import annotations

from google.adk.tools import ToolContext

from ..client import MisskeyClient


def get_notifications(
    tool_context: ToolContext,
    limit: int = 10,
    since_id: str = "",
    until_id: str = "",
    mark_as_read: bool = True,
    include_types: list[str] | None = None,
    exclude_types: list[str] | None = None,
) -> dict:
    """Get notifications for the authenticated user.

    Args:
        limit: Max results (default 10)
        since_id: Only show after this ID
        until_id: Only show before this ID
        mark_as_read: Mark fetched notifications as read
        include_types: Only include these types, e.g. ["follow", "mention", "reply", "renote", "reaction"]
        exclude_types: Exclude these types
    """
    data: dict = {"limit": limit, "markAsRead": mark_as_read}
    if since_id:
        data["sinceId"] = since_id
    if until_id:
        data["untilId"] = until_id
    if include_types:
        data["includeTypes"] = include_types
    if exclude_types:
        data["excludeTypes"] = exclude_types
    with MisskeyClient.from_context(tool_context) as c:
        return c.request("/i/notifications", data)


def mark_all_notifications_read(tool_context: ToolContext) -> dict:
    """Mark all notifications as read."""
    with MisskeyClient.from_context(tool_context) as c:
        return c.request("/notifications/mark-all-as-read")


def get_mentions(
    tool_context: ToolContext,
    limit: int = 10,
    since_id: str = "",
    until_id: str = "",
    following: bool = False,
) -> dict:
    """Get notes where the authenticated user is mentioned.

    Args:
        limit: Max results
        since_id: Only show after this ID
        until_id: Only show before this ID
        following: Only show mentions from users you follow
    """
    data: dict = {"limit": limit, "following": following}
    if since_id:
        data["sinceId"] = since_id
    if until_id:
        data["untilId"] = until_id
    with MisskeyClient.from_context(tool_context) as c:
        return c.request("/notes/mentions", data)


all_tools: list = [get_notifications, mark_all_notifications_read, get_mentions]
