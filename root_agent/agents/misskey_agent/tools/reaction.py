"""Misskey 表情反应工具。"""

from __future__ import annotations

from google.adk.tools import ToolContext

from ..client import MisskeyClient


def create_reaction(note_id: str, reaction: str, tool_context: ToolContext) -> dict:
    """Add an emoji reaction to a note.

    Args:
        note_id: The note ID to react to
        reaction: The reaction emoji, e.g. "👍", "❤️", or custom emoji like ":misskey:"
    """
    with MisskeyClient.from_context(tool_context) as c:
        return c.request(
            "/notes/reactions/create",
            {
                "noteId": note_id,
                "reaction": reaction,
            },
        )


def delete_reaction(note_id: str, tool_context: ToolContext) -> dict:
    """Remove your reaction from a note.

    Args:
        note_id: The note ID to remove reaction from
    """
    with MisskeyClient.from_context(tool_context) as c:
        return c.request("/notes/reactions/delete", {"noteId": note_id})


def get_reactions(
    note_id: str,
    tool_context: ToolContext,
    limit: int = 10,
    reaction_type: str = "",
) -> dict:
    """Get reactions on a note.

    Args:
        note_id: The note ID
        limit: Max results
        reaction_type: Filter by reaction type (leave empty for all)
    """
    data: dict = {"noteId": note_id, "limit": limit}
    if reaction_type:
        data["type"] = reaction_type
    with MisskeyClient.from_context(tool_context) as c:
        return c.request("/notes/reactions", data)


all_tools: list = [create_reaction, delete_reaction, get_reactions]
