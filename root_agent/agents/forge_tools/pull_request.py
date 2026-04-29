"""代码托管平台通用 Pull Request 工具生成器。"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from google.adk.tools import ToolContext

    from .client import ForgeClient


def make_pr_tools(client_class: type[ForgeClient]) -> list:
    """为指定平台生成 PR 相关工具函数。"""

    def list_pull_requests(
        owner: str,
        repo: str,
        tool_context: ToolContext,
        state: str = "open",
        page: int = 1,
        limit: int = 20,
    ) -> dict:
        """List pull requests in a repository.

        Args:
            owner: Repository owner
            repo: Repository name
            state: Filter by state — "open", "closed", "all"
            page: Page number
            limit: Results per page
        """
        params: dict = {"state": state, **client_class.paginate_params(page, limit)}
        with client_class.from_context(tool_context) as c:
            return c.get(f"/repos/{owner}/{repo}/pulls", params=params)

    def get_pull_request(owner: str, repo: str, index: int, tool_context: ToolContext) -> dict:
        """Get a single pull request by number.

        Args:
            owner: Repository owner
            repo: Repository name
            index: PR number
        """
        with client_class.from_context(tool_context) as c:
            return c.get(f"/repos/{owner}/{repo}/pulls/{index}")

    def create_pull_request(
        owner: str,
        repo: str,
        title: str,
        head: str,
        base: str,
        tool_context: ToolContext,
        body: str = "",
    ) -> dict:
        """Create a new pull request.

        Args:
            owner: Repository owner
            repo: Repository name
            title: PR title
            head: Source branch
            base: Target branch
            body: PR description (Markdown)
        """
        data: dict = {"title": title, "head": head, "base": base}
        if body:
            data["body"] = body
        with client_class.from_context(tool_context) as c:
            return c.post(f"/repos/{owner}/{repo}/pulls", json_data=data)

    def merge_pull_request(
        owner: str,
        repo: str,
        index: int,
        tool_context: ToolContext,
        merge_method: str = "merge",
        message: str = "",
    ) -> dict:
        """Merge a pull request.

        Args:
            owner: Repository owner
            repo: Repository name
            index: PR number
            merge_method: Merge method — "merge", "rebase", "squash"
            message: Merge commit message (optional)
        """
        data: dict = {"Do": merge_method}
        if message:
            data["merge_message_field"] = message
        with client_class.from_context(tool_context) as c:
            return c.post(f"/repos/{owner}/{repo}/pulls/{index}/merge", json_data=data)

    return [list_pull_requests, get_pull_request, create_pull_request, merge_pull_request]
