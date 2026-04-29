"""Gitea 通知 API 工具。

涵盖：列出通知、标记已读。
参考：https://gitea.com/api/swagger#/notification
"""

from __future__ import annotations

from google.adk.tools import ToolContext

from ..client import GiteaClient


def list_notifications(tool_context: ToolContext, page: int = 1, limit: int = 20, status_types: str = "unread") -> dict:
    """List notifications for the authenticated user.

    Args:
        page: Page number
        limit: Results per page
        status_types: Comma-separated statuses — "unread", "read", "pinned"
    """
    with GiteaClient.from_context(tool_context) as c:
        return c.get("/notifications", params={"page": page, "limit": limit, "status-types": status_types})


def mark_notifications_read(tool_context: ToolContext) -> dict:
    """Mark all notifications as read for the authenticated user."""
    with GiteaClient.from_context(tool_context) as c:
        return c.put("/notifications")


def mark_notification_read(notification_id: int, tool_context: ToolContext) -> dict:
    """Mark a single notification as read.

    Args:
        notification_id: Notification ID
    """
    with GiteaClient.from_context(tool_context) as c:
        return c.patch(f"/notifications/threads/{notification_id}", json_data={"status": "read"})


# ---------------------------------------------------------------------------
# 导出
# ---------------------------------------------------------------------------

all_tools: list = [
    list_notifications,
    mark_notifications_read,
    mark_notification_read,
]
