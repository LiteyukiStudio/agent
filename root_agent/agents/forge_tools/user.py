"""代码托管平台通用用户工具生成器。"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from google.adk.tools import ToolContext

    from .client import ForgeClient


def make_user_tools(client_class: type[ForgeClient]) -> list:
    """为指定平台生成用户相关工具函数。"""

    def get_authenticated_user(tool_context: ToolContext) -> dict:
        """Get the authenticated user's profile (the user who owns the token)."""
        with client_class.from_context(tool_context) as c:
            return c.get("/user")

    def get_user(username: str, tool_context: ToolContext) -> dict:
        """Get a user's public profile by username.

        Args:
            username: The user's login name
        """
        with client_class.from_context(tool_context) as c:
            return c.get(f"/users/{username}")

    def list_user_repos(
        username: str,
        tool_context: ToolContext,
        page: int = 1,
        limit: int = 20,
    ) -> dict:
        """List repositories owned by a user.

        Args:
            username: The user's login name
            page: Page number
            limit: Results per page
        """
        with client_class.from_context(tool_context) as c:
            return c.get(f"/users/{username}/repos", params=client_class.paginate_params(page, limit))

    def search_users(
        query: str,
        tool_context: ToolContext,
        page: int = 1,
        limit: int = 20,
    ) -> dict:
        """Search users by keyword.

        Args:
            query: Search keyword
            page: Page number
            limit: Results per page
        """
        params: dict = {"q": query, **client_class.paginate_params(page, limit)}
        with client_class.from_context(tool_context) as c:
            return c.get("/users/search", params=params)

    return [get_authenticated_user, get_user, list_user_repos, search_users]
