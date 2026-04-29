"""Misskey 网盘（Drive）文件管理工具。"""

from __future__ import annotations

from google.adk.tools import ToolContext

from ..client import MisskeyClient


def get_drive_info(tool_context: ToolContext) -> dict:
    """Get drive usage information (capacity and used space)."""
    with MisskeyClient.from_context(tool_context) as c:
        return c.request("/drive")


def list_drive_files(
    tool_context: ToolContext,
    limit: int = 10,
    since_id: str = "",
    until_id: str = "",
    folder_id: str = "",
    file_type: str = "",
) -> dict:
    """List files in the drive.

    Args:
        limit: Max results
        since_id: Cursor for pagination
        until_id: Cursor for pagination
        folder_id: Filter by folder ID (empty for root)
        file_type: Filter by MIME type prefix, e.g. "image/" for images
    """
    data: dict = {"limit": limit}
    if since_id:
        data["sinceId"] = since_id
    if until_id:
        data["untilId"] = until_id
    if folder_id:
        data["folderId"] = folder_id
    if file_type:
        data["type"] = file_type
    with MisskeyClient.from_context(tool_context) as c:
        return c.request("/drive/files", data)


def show_drive_file(
    tool_context: ToolContext,
    file_id: str = "",
    url: str = "",
) -> dict:
    """Get detailed information about a drive file.

    Args:
        file_id: The file ID (use this or url)
        url: The file URL
    """
    data: dict = {}
    if file_id:
        data["fileId"] = file_id
    elif url:
        data["url"] = url
    with MisskeyClient.from_context(tool_context) as c:
        return c.request("/drive/files/show", data)


def delete_drive_file(file_id: str, tool_context: ToolContext) -> dict:
    """Delete a file from the drive.

    Args:
        file_id: The file ID to delete
    """
    with MisskeyClient.from_context(tool_context) as c:
        return c.request("/drive/files/delete", {"fileId": file_id})


def upload_from_url(
    url: str,
    tool_context: ToolContext,
    folder_id: str = "",
    is_sensitive: bool = False,
    comment: str = "",
) -> dict:
    """Upload a file to the drive from a URL.

    Args:
        url: The URL to download the file from
        folder_id: Target folder ID (empty for root)
        is_sensitive: Mark the file as sensitive (NSFW)
        comment: File description/comment
    """
    data: dict = {"url": url, "isSensitive": is_sensitive}
    if folder_id:
        data["folderId"] = folder_id
    if comment:
        data["comment"] = comment
    with MisskeyClient.from_context(tool_context) as c:
        return c.request("/drive/files/upload-from-url", data)


all_tools: list = [
    get_drive_info,
    list_drive_files,
    show_drive_file,
    delete_drive_file,
    upload_from_url,
]
