"""Gitea Issue API 工具。

涵盖：列出 Issue、获取/创建/编辑 Issue、评论、标签。
参考：https://gitea.com/api/swagger#/issue
"""

from __future__ import annotations

from google.adk.tools import ToolContext

from ..client import GiteaClient

# ---------------------------------------------------------------------------
# Issue
# ---------------------------------------------------------------------------


def list_repo_issues(
    owner: str,
    repo: str,
    tool_context: ToolContext,
    state: str = "open",
    labels: str = "",
    page: int = 1,
    limit: int = 20,
) -> dict:
    """List issues in a repository.

    Args:
        owner: Repository owner (user or org)
        repo: Repository name
        state: Filter by state — "open", "closed", or "all"
        labels: Comma-separated label names to filter by, e.g. "bug,help wanted"
        page: Page number (starts at 1)
        limit: Results per page (max 50)
    """
    params: dict = {"state": state, "page": page, "limit": limit, "type": "issues"}
    if labels:
        params["labels"] = labels
    with GiteaClient.from_context(tool_context) as c:
        return c.get(f"/repos/{owner}/{repo}/issues", params=params)


def get_issue(owner: str, repo: str, index: int, tool_context: ToolContext) -> dict:
    """Get a single issue by its index number.

    Args:
        owner: Repository owner
        repo: Repository name
        index: Issue number (the #N shown in the UI)
    """
    with GiteaClient.from_context(tool_context) as c:
        return c.get(f"/repos/{owner}/{repo}/issues/{index}")


def create_issue(
    owner: str,
    repo: str,
    title: str,
    tool_context: ToolContext,
    body: str = "",
    labels: list[int] | None = None,
    assignees: list[str] | None = None,
    milestone: int | None = None,
) -> dict:
    """Create a new issue in a repository.

    Args:
        owner: Repository owner
        repo: Repository name
        title: Issue title
        body: Issue body (Markdown supported)
        labels: List of label IDs to attach
        assignees: List of usernames to assign
        milestone: Milestone ID to associate
    """
    data: dict = {"title": title}
    if body:
        data["body"] = body
    if labels:
        data["labels"] = labels
    if assignees:
        data["assignees"] = assignees
    if milestone is not None:
        data["milestone"] = milestone
    with GiteaClient.from_context(tool_context) as c:
        return c.post(f"/repos/{owner}/{repo}/issues", json_data=data)


def edit_issue(
    owner: str,
    repo: str,
    index: int,
    tool_context: ToolContext,
    title: str | None = None,
    body: str | None = None,
    state: str | None = None,
    assignees: list[str] | None = None,
    milestone: int | None = None,
) -> dict:
    """Edit an existing issue.

    Args:
        owner: Repository owner
        repo: Repository name
        index: Issue number
        title: New title (leave empty to keep current)
        body: New body (leave empty to keep current)
        state: Set to "open" or "closed"
        assignees: New assignee usernames (replaces existing)
        milestone: New milestone ID
    """
    data: dict = {}
    if title is not None:
        data["title"] = title
    if body is not None:
        data["body"] = body
    if state is not None:
        data["state"] = state
    if assignees is not None:
        data["assignees"] = assignees
    if milestone is not None:
        data["milestone"] = milestone
    with GiteaClient.from_context(tool_context) as c:
        return c.patch(f"/repos/{owner}/{repo}/issues/{index}", json_data=data)


# ---------------------------------------------------------------------------
# 评论
# ---------------------------------------------------------------------------


def list_issue_comments(
    owner: str, repo: str, index: int, tool_context: ToolContext, page: int = 1, limit: int = 20
) -> dict:
    """List comments on an issue.

    Args:
        owner: Repository owner
        repo: Repository name
        index: Issue number
        page: Page number
        limit: Results per page
    """
    with GiteaClient.from_context(tool_context) as c:
        return c.get(f"/repos/{owner}/{repo}/issues/{index}/comments", params={"page": page, "limit": limit})


def create_issue_comment(owner: str, repo: str, index: int, body: str, tool_context: ToolContext) -> dict:
    """Add a comment to an issue.

    Args:
        owner: Repository owner
        repo: Repository name
        index: Issue number
        body: Comment content (Markdown supported)
    """
    with GiteaClient.from_context(tool_context) as c:
        return c.post(f"/repos/{owner}/{repo}/issues/{index}/comments", json_data={"body": body})


# ---------------------------------------------------------------------------
# 标签
# ---------------------------------------------------------------------------


def list_issue_labels(owner: str, repo: str, index: int, tool_context: ToolContext) -> dict:
    """List labels on an issue.

    Args:
        owner: Repository owner
        repo: Repository name
        index: Issue number
    """
    with GiteaClient.from_context(tool_context) as c:
        return c.get(f"/repos/{owner}/{repo}/issues/{index}/labels")


def add_issue_labels(owner: str, repo: str, index: int, labels: list[int], tool_context: ToolContext) -> dict:
    """Add labels to an issue.

    Args:
        owner: Repository owner
        repo: Repository name
        index: Issue number
        labels: List of label IDs to add
    """
    with GiteaClient.from_context(tool_context) as c:
        return c.post(f"/repos/{owner}/{repo}/issues/{index}/labels", json_data={"labels": labels})


def remove_issue_label(owner: str, repo: str, index: int, label_id: int, tool_context: ToolContext) -> dict:
    """Remove a label from an issue.

    Args:
        owner: Repository owner
        repo: Repository name
        index: Issue number
        label_id: ID of the label to remove
    """
    with GiteaClient.from_context(tool_context) as c:
        return c.delete(f"/repos/{owner}/{repo}/issues/{index}/labels/{label_id}")


# ---------------------------------------------------------------------------
# 导出
# ---------------------------------------------------------------------------

all_tools: list = [
    list_repo_issues,
    get_issue,
    create_issue,
    edit_issue,
    list_issue_comments,
    create_issue_comment,
    list_issue_labels,
    add_issue_labels,
    remove_issue_label,
]
