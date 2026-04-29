"""Gitea 仓库与 Pull Request API 工具。

涵盖：仓库 CRUD、分支、Release、Pull Request。
参考：https://gitea.com/api/swagger#/repository
"""

from __future__ import annotations

from google.adk.tools import ToolContext

from ..client import GiteaClient

# ---------------------------------------------------------------------------
# 仓库
# ---------------------------------------------------------------------------


def search_repos(
    tool_context: ToolContext,
    keyword: str = "",
    owner: str = "",
    page: int = 1,
    limit: int = 20,
    sort: str = "updated",
    order: str = "desc",
) -> dict:
    """Search repositories by keyword or owner.

    Args:
        keyword: Search keyword (matches repo name/description)
        owner: Filter by owner username or org name
        page: Page number
        limit: Results per page
        sort: Sort field — "alpha", "created", "updated", "size", "stars", "forks"
        order: Sort order — "asc" or "desc"
    """
    params: dict = {"page": page, "limit": limit, "sort": sort, "order": order}
    if keyword:
        params["q"] = keyword
    if owner:
        params["owner"] = owner
    with GiteaClient.from_context(tool_context) as c:
        return c.get("/repos/search", params=params)


def get_repo(owner: str, repo: str, tool_context: ToolContext) -> dict:
    """Get detailed information about a repository.

    Args:
        owner: Repository owner
        repo: Repository name
    """
    with GiteaClient.from_context(tool_context) as c:
        return c.get(f"/repos/{owner}/{repo}")


def create_repo(
    name: str,
    tool_context: ToolContext,
    description: str = "",
    private: bool = False,
    auto_init: bool = True,
    default_branch: str = "main",
    org: str = "",
) -> dict:
    """Create a new repository.

    Args:
        name: Repository name
        description: Repository description
        private: Whether the repo is private
        auto_init: Initialize with a README
        default_branch: Default branch name
        org: If set, create under this organization instead of current user
    """
    data: dict = {
        "name": name,
        "description": description,
        "private": private,
        "auto_init": auto_init,
        "default_branch": default_branch,
    }
    with GiteaClient.from_context(tool_context) as c:
        if org:
            return c.post(f"/orgs/{org}/repos", json_data=data)
        return c.post("/user/repos", json_data=data)


def delete_repo(owner: str, repo: str, tool_context: ToolContext) -> dict:
    """Delete a repository. This is IRREVERSIBLE.

    Args:
        owner: Repository owner
        repo: Repository name
    """
    with GiteaClient.from_context(tool_context) as c:
        return c.delete(f"/repos/{owner}/{repo}")


def list_branches(owner: str, repo: str, tool_context: ToolContext, page: int = 1, limit: int = 20) -> dict:
    """List branches in a repository.

    Args:
        owner: Repository owner
        repo: Repository name
        page: Page number
        limit: Results per page
    """
    with GiteaClient.from_context(tool_context) as c:
        return c.get(f"/repos/{owner}/{repo}/branches", params={"page": page, "limit": limit})


def get_file_content(owner: str, repo: str, filepath: str, tool_context: ToolContext, ref: str = "") -> dict:
    """Get the content of a file in a repository.

    Args:
        owner: Repository owner
        repo: Repository name
        filepath: Path to the file, e.g. "src/main.py"
        ref: Branch, tag, or commit SHA (default: repo's default branch)
    """
    params: dict = {}
    if ref:
        params["ref"] = ref
    with GiteaClient.from_context(tool_context) as c:
        return c.get(f"/repos/{owner}/{repo}/contents/{filepath}", params=params)


def list_releases(owner: str, repo: str, tool_context: ToolContext, page: int = 1, limit: int = 10) -> dict:
    """List releases in a repository.

    Args:
        owner: Repository owner
        repo: Repository name
        page: Page number
        limit: Results per page
    """
    with GiteaClient.from_context(tool_context) as c:
        return c.get(f"/repos/{owner}/{repo}/releases", params={"page": page, "limit": limit})


# ---------------------------------------------------------------------------
# Pull Request
# ---------------------------------------------------------------------------


def list_pull_requests(
    owner: str,
    repo: str,
    tool_context: ToolContext,
    state: str = "open",
    sort: str = "newest",
    page: int = 1,
    limit: int = 20,
) -> dict:
    """List pull requests in a repository.

    Args:
        owner: Repository owner
        repo: Repository name
        state: Filter by state — "open", "closed", "all"
        sort: Sort method — "oldest", "newest", "leastupdate", "mostupdate"
        page: Page number
        limit: Results per page
    """
    with GiteaClient.from_context(tool_context) as c:
        return c.get(
            f"/repos/{owner}/{repo}/pulls",
            params={"state": state, "sort": sort, "page": page, "limit": limit},
        )


def get_pull_request(owner: str, repo: str, index: int, tool_context: ToolContext) -> dict:
    """Get details of a pull request.

    Args:
        owner: Repository owner
        repo: Repository name
        index: PR number
    """
    with GiteaClient.from_context(tool_context) as c:
        return c.get(f"/repos/{owner}/{repo}/pulls/{index}")


def create_pull_request(
    owner: str,
    repo: str,
    title: str,
    head: str,
    base: str,
    tool_context: ToolContext,
    body: str = "",
    assignees: list[str] | None = None,
    labels: list[int] | None = None,
) -> dict:
    """Create a new pull request.

    Args:
        owner: Repository owner
        repo: Repository name
        title: PR title
        head: Source branch name (e.g. "feature/login")
        base: Target branch name (e.g. "main")
        body: PR description (Markdown supported)
        assignees: Usernames to assign as reviewers
        labels: Label IDs to attach
    """
    data: dict = {"title": title, "head": head, "base": base}
    if body:
        data["body"] = body
    if assignees:
        data["assignees"] = assignees
    if labels:
        data["labels"] = labels
    with GiteaClient.from_context(tool_context) as c:
        return c.post(f"/repos/{owner}/{repo}/pulls", json_data=data)


def merge_pull_request(
    owner: str, repo: str, index: int, tool_context: ToolContext, merge_method: str = "merge", message: str = ""
) -> dict:
    """Merge a pull request.

    Args:
        owner: Repository owner
        repo: Repository name
        index: PR number
        merge_method: Merge strategy — "merge", "rebase", "squash", "rebase-merge"
        message: Custom merge commit message (optional)
    """
    data: dict = {"Do": merge_method}
    if message:
        data["merge_message_field"] = message
    with GiteaClient.from_context(tool_context) as c:
        return c.post(f"/repos/{owner}/{repo}/pulls/{index}/merge", json_data=data)


def list_pr_commits(
    owner: str, repo: str, index: int, tool_context: ToolContext, page: int = 1, limit: int = 20
) -> dict:
    """List commits in a pull request.

    Args:
        owner: Repository owner
        repo: Repository name
        index: PR number
        page: Page number
        limit: Results per page
    """
    with GiteaClient.from_context(tool_context) as c:
        return c.get(f"/repos/{owner}/{repo}/pulls/{index}/commits", params={"page": page, "limit": limit})


# ---------------------------------------------------------------------------
# 导出
# ---------------------------------------------------------------------------

all_tools: list = [
    # 仓库
    search_repos,
    get_repo,
    create_repo,
    delete_repo,
    list_branches,
    get_file_content,
    list_releases,
    # Pull Request
    list_pull_requests,
    get_pull_request,
    create_pull_request,
    merge_pull_request,
    list_pr_commits,
]
