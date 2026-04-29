"""代码托管平台通用 Issue 工具生成器。"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from google.adk.tools import ToolContext

    from .client import ForgeClient


def make_issue_tools(client_class: type[ForgeClient]) -> list:
    """为指定平台生成 Issue 相关工具函数。"""

    def list_issues(
        owner: str,
        repo: str,
        tool_context: ToolContext,
        state: str = "open",
        page: int = 1,
        limit: int = 20,
    ) -> dict:
        """List issues in a repository.

        Args:
            owner: Repository owner
            repo: Repository name
            state: Filter by state — "open", "closed", "all"
            page: Page number
            limit: Results per page
        """
        params: dict = {"state": state, **client_class.paginate_params(page, limit)}
        with client_class.from_context(tool_context) as c:
            return c.get(f"/repos/{owner}/{repo}/issues", params=params)

    def get_issue(owner: str, repo: str, index: int, tool_context: ToolContext) -> dict:
        """Get a single issue by number.

        Args:
            owner: Repository owner
            repo: Repository name
            index: Issue number
        """
        with client_class.from_context(tool_context) as c:
            return c.get(f"/repos/{owner}/{repo}/issues/{index}")

    def create_issue(
        owner: str,
        repo: str,
        title: str,
        tool_context: ToolContext,
        body: str = "",
        labels: list[str] | None = None,
        assignees: list[str] | None = None,
    ) -> dict:
        """Create a new issue.

        Args:
            owner: Repository owner
            repo: Repository name
            title: Issue title
            body: Issue body (Markdown)
            labels: Label names to assign
            assignees: Usernames to assign
        """
        data: dict = {"title": title}
        if body:
            data["body"] = body
        if labels:
            data["labels"] = labels
        if assignees:
            data["assignees"] = assignees
        with client_class.from_context(tool_context) as c:
            return c.post(f"/repos/{owner}/{repo}/issues", json_data=data)

    def edit_issue(
        owner: str,
        repo: str,
        index: int,
        tool_context: ToolContext,
        title: str = "",
        body: str = "",
        state: str = "",
    ) -> dict:
        """Edit an existing issue.

        Args:
            owner: Repository owner
            repo: Repository name
            index: Issue number
            title: New title (leave empty to keep)
            body: New body (leave empty to keep)
            state: New state — "open" or "closed" (leave empty to keep)
        """
        data: dict = {}
        if title:
            data["title"] = title
        if body:
            data["body"] = body
        if state:
            data["state"] = state
        with client_class.from_context(tool_context) as c:
            return c.patch(f"/repos/{owner}/{repo}/issues/{index}", json_data=data)

    def create_issue_comment(
        owner: str,
        repo: str,
        index: int,
        body: str,
        tool_context: ToolContext,
    ) -> dict:
        """Add a comment to an issue.

        Args:
            owner: Repository owner
            repo: Repository name
            index: Issue number
            body: Comment body (Markdown)
        """
        with client_class.from_context(tool_context) as c:
            return c.post(f"/repos/{owner}/{repo}/issues/{index}/comments", json_data={"body": body})

    def list_issue_comments(
        owner: str,
        repo: str,
        index: int,
        tool_context: ToolContext,
        page: int = 1,
        limit: int = 20,
    ) -> dict:
        """List comments on an issue.

        Args:
            owner: Repository owner
            repo: Repository name
            index: Issue number
            page: Page number
            limit: Results per page
        """
        with client_class.from_context(tool_context) as c:
            return c.get(
                f"/repos/{owner}/{repo}/issues/{index}/comments",
                params=client_class.paginate_params(page, limit),
            )

    return [list_issues, get_issue, create_issue, edit_issue, create_issue_comment, list_issue_comments]
