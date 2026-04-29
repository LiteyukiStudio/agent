"""Misskey 帖子（Note）相关工具。

涵盖：发帖、删帖、查看、搜索、时间线、转帖、翻译。
参考：https://misskey-hub.net/docs/api/
"""

from __future__ import annotations

from google.adk.tools import ToolContext

from ..client import MisskeyClient

# ---------------------------------------------------------------------------
# 帖子 CRUD
# ---------------------------------------------------------------------------


def create_note(
    tool_context: ToolContext,
    text: str = "",
    visibility: str = "public",
    cw: str = "",
    reply_id: str = "",
    renote_id: str = "",
    file_ids: list[str] | None = None,
    local_only: bool = False,
) -> dict:
    """Create a new note (post) on Misskey.

    Args:
        text: The text content of the note. Can be empty if renoting
        visibility: Visibility — "public", "home", "followers", "specified"
        cw: Content warning text (spoiler). Leave empty for none
        reply_id: Note ID to reply to (leave empty for new post)
        renote_id: Note ID to renote/boost (leave empty for original post)
        file_ids: List of drive file IDs to attach
        local_only: If true, the note will not be federated
    """
    data: dict = {"visibility": visibility, "localOnly": local_only}
    if text:
        data["text"] = text
    if cw:
        data["cw"] = cw
    if reply_id:
        data["replyId"] = reply_id
    if renote_id:
        data["renoteId"] = renote_id
    if file_ids:
        data["fileIds"] = file_ids
    with MisskeyClient.from_context(tool_context) as c:
        return c.request("/notes/create", data)


def delete_note(note_id: str, tool_context: ToolContext) -> dict:
    """Delete a note by ID.

    Args:
        note_id: The ID of the note to delete
    """
    with MisskeyClient.from_context(tool_context) as c:
        return c.request("/notes/delete", {"noteId": note_id})


def show_note(note_id: str, tool_context: ToolContext) -> dict:
    """Get detailed information about a note.

    Args:
        note_id: The ID of the note to show
    """
    with MisskeyClient.from_context(tool_context) as c:
        return c.request("/notes/show", {"noteId": note_id})


def search_notes(
    query: str,
    tool_context: ToolContext,
    limit: int = 10,
    offset: int = 0,
) -> dict:
    """Search notes by keyword.

    Args:
        query: Search keyword
        limit: Max results (default 10, max 100)
        offset: Offset for pagination
    """
    with MisskeyClient.from_context(tool_context) as c:
        return c.request(
            "/notes/search",
            {
                "query": query,
                "limit": limit,
                "offset": offset,
            },
        )


# ---------------------------------------------------------------------------
# 时间线
# ---------------------------------------------------------------------------


def get_timeline(
    tool_context: ToolContext,
    limit: int = 10,
    since_id: str = "",
    until_id: str = "",
    with_renotes: bool = True,
    with_replies: bool = False,
) -> dict:
    """Get the home timeline (notes from followed users).

    Args:
        limit: Number of notes to fetch (default 10, max 100)
        since_id: Only show notes after this ID
        until_id: Only show notes before this ID
        with_renotes: Include renotes in timeline
        with_replies: Include replies in timeline
    """
    data: dict = {
        "limit": limit,
        "includeMyRenotes": with_renotes,
        "includeRenotedMyNotes": with_renotes,
        "withReplies": with_replies,
    }
    if since_id:
        data["sinceId"] = since_id
    if until_id:
        data["untilId"] = until_id
    with MisskeyClient.from_context(tool_context) as c:
        return c.request("/notes/timeline", data)


def get_local_timeline(
    tool_context: ToolContext,
    limit: int = 10,
    since_id: str = "",
    until_id: str = "",
    with_renotes: bool = True,
    with_replies: bool = False,
) -> dict:
    """Get the local timeline (notes from this instance only).

    Args:
        limit: Number of notes to fetch (default 10, max 100)
        since_id: Only show notes after this ID
        until_id: Only show notes before this ID
        with_renotes: Include renotes
        with_replies: Include replies
    """
    data: dict = {
        "limit": limit,
        "withRenotes": with_renotes,
        "withReplies": with_replies,
    }
    if since_id:
        data["sinceId"] = since_id
    if until_id:
        data["untilId"] = until_id
    with MisskeyClient.from_context(tool_context) as c:
        return c.request("/notes/local-timeline", data)


def get_global_timeline(
    tool_context: ToolContext,
    limit: int = 10,
    since_id: str = "",
    until_id: str = "",
    with_renotes: bool = True,
) -> dict:
    """Get the global timeline (notes from all federated instances).

    Args:
        limit: Number of notes to fetch (default 10, max 100)
        since_id: Only show notes after this ID
        until_id: Only show notes before this ID
        with_renotes: Include renotes
    """
    data: dict = {"limit": limit, "withRenotes": with_renotes}
    if since_id:
        data["sinceId"] = since_id
    if until_id:
        data["untilId"] = until_id
    with MisskeyClient.from_context(tool_context) as c:
        return c.request("/notes/global-timeline", data)


# ---------------------------------------------------------------------------
# 帖子关联
# ---------------------------------------------------------------------------


def get_note_replies(
    note_id: str,
    tool_context: ToolContext,
    limit: int = 10,
    since_id: str = "",
    until_id: str = "",
) -> dict:
    """Get replies to a note.

    Args:
        note_id: The note ID
        limit: Max results
        since_id: Only show notes after this ID
        until_id: Only show notes before this ID
    """
    data: dict = {"noteId": note_id, "limit": limit}
    if since_id:
        data["sinceId"] = since_id
    if until_id:
        data["untilId"] = until_id
    with MisskeyClient.from_context(tool_context) as c:
        return c.request("/notes/replies", data)


def get_note_renotes(
    note_id: str,
    tool_context: ToolContext,
    limit: int = 10,
    since_id: str = "",
    until_id: str = "",
) -> dict:
    """Get renotes (boosts) of a note.

    Args:
        note_id: The note ID
        limit: Max results
        since_id: Only show after this ID
        until_id: Only show before this ID
    """
    data: dict = {"noteId": note_id, "limit": limit}
    if since_id:
        data["sinceId"] = since_id
    if until_id:
        data["untilId"] = until_id
    with MisskeyClient.from_context(tool_context) as c:
        return c.request("/notes/renotes", data)


def get_user_notes(
    user_id: str,
    tool_context: ToolContext,
    limit: int = 10,
    since_id: str = "",
    until_id: str = "",
    with_replies: bool = False,
    with_renotes: bool = True,
    with_files: bool = False,
) -> dict:
    """Get notes posted by a specific user.

    Args:
        user_id: The user ID
        limit: Max results
        since_id: Only show after this ID
        until_id: Only show before this ID
        with_replies: Include replies
        with_renotes: Include renotes
        with_files: Only show notes with file attachments
    """
    data: dict = {
        "userId": user_id,
        "limit": limit,
        "withReplies": with_replies,
        "withRenotes": with_renotes,
        "withFiles": with_files,
    }
    if since_id:
        data["sinceId"] = since_id
    if until_id:
        data["untilId"] = until_id
    with MisskeyClient.from_context(tool_context) as c:
        return c.request("/users/notes", data)


def translate_note(note_id: str, target_lang: str, tool_context: ToolContext) -> dict:
    """Translate a note to the specified language.

    Args:
        note_id: The note ID to translate
        target_lang: Target language code, e.g. "zh-CN", "en", "ja"
    """
    with MisskeyClient.from_context(tool_context) as c:
        return c.request(
            "/notes/translate",
            {
                "noteId": note_id,
                "targetLang": target_lang,
            },
        )


all_tools: list = [
    create_note,
    delete_note,
    show_note,
    search_notes,
    get_timeline,
    get_local_timeline,
    get_global_timeline,
    get_note_replies,
    get_note_renotes,
    get_user_notes,
    translate_note,
]
