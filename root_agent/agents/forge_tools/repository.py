"""代码托管平台通用仓库工具生成器。"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from google.adk.tools import ToolContext

    from .client import ForgeClient


def make_repo_tools(client_class: type[ForgeClient]) -> list:
    """为指定平台生成仓库相关工具函数。"""

    def search_repos(
        tool_context: ToolContext,
        keyword: str = "",
        owner: str = "",
        page: int = 1,
        limit: int = 20,
    ) -> dict:
        """Search repositories by keyword or owner.

        Args:
            keyword: Search keyword (matches repo name/description)
            owner: Filter by owner username or org name
            page: Page number
            limit: Results per page (max 50)
        """
        params: dict = {**client_class.paginate_params(page, limit)}
        if keyword:
            params["q"] = keyword
        if owner:
            params["owner"] = owner
        with client_class.from_context(tool_context) as c:
            return c.get("/repos/search", params=params)

    def get_repo(owner: str, repo: str, tool_context: ToolContext) -> dict:
        """Get detailed information about a repository.

        Args:
            owner: Repository owner
            repo: Repository name
        """
        with client_class.from_context(tool_context) as c:
            return c.get(f"/repos/{owner}/{repo}")

    def create_repo(
        name: str,
        tool_context: ToolContext,
        description: str = "",
        private: bool = False,
        auto_init: bool = True,
    ) -> dict:
        """Create a new repository for the authenticated user.

        Args:
            name: Repository name
            description: Repository description
            private: Whether the repo is private
            auto_init: Initialize with a README
        """
        data: dict = {
            "name": name,
            "private": private,
            "auto_init": auto_init,
        }
        if description:
            data["description"] = description
        with client_class.from_context(tool_context) as c:
            return c.post("/user/repos", json_data=data)

    def delete_repo(owner: str, repo: str, tool_context: ToolContext) -> dict:
        """Delete a repository. This action is irreversible!

        Args:
            owner: Repository owner
            repo: Repository name
        """
        with client_class.from_context(tool_context) as c:
            return c.delete(f"/repos/{owner}/{repo}")

    def list_branches(
        owner: str,
        repo: str,
        tool_context: ToolContext,
        page: int = 1,
        limit: int = 20,
    ) -> dict:
        """List branches in a repository.

        Args:
            owner: Repository owner
            repo: Repository name
            page: Page number
            limit: Results per page
        """
        with client_class.from_context(tool_context) as c:
            return c.get(f"/repos/{owner}/{repo}/branches", params=client_class.paginate_params(page, limit))

    def get_file_content(
        owner: str,
        repo: str,
        filepath: str,
        tool_context: ToolContext,
        ref: str = "",
    ) -> dict:
        """Get the content of a file in a repository.

        Args:
            owner: Repository owner
            repo: Repository name
            filepath: Path to the file
            ref: Branch or commit SHA (default: default branch)
        """
        params: dict = {}
        if ref:
            params["ref"] = ref
        with client_class.from_context(tool_context) as c:
            return c.get(f"/repos/{owner}/{repo}/contents/{filepath}", params=params or None)

    def list_releases(
        owner: str,
        repo: str,
        tool_context: ToolContext,
        page: int = 1,
        limit: int = 10,
    ) -> dict:
        """List releases in a repository.

        Args:
            owner: Repository owner
            repo: Repository name
            page: Page number
            limit: Results per page
        """
        with client_class.from_context(tool_context) as c:
            return c.get(f"/repos/{owner}/{repo}/releases", params=client_class.paginate_params(page, limit))

    return [search_repos, get_repo, create_repo, delete_repo, list_branches, get_file_content, list_releases]
