"""Gitea 组织 API 工具。

涵盖：列出/获取组织、组织仓库、成员、团队。
参考：https://gitea.com/api/swagger#/organization
"""

from __future__ import annotations

from google.adk.tools import ToolContext

from ..client import GiteaClient


def list_my_orgs(tool_context: ToolContext, page: int = 1, limit: int = 20) -> dict:
    """List organizations the authenticated user belongs to.

    Args:
        page: Page number
        limit: Results per page
    """
    with GiteaClient.from_context(tool_context) as c:
        return c.get("/user/orgs", params={"page": page, "limit": limit})


def get_org(org: str, tool_context: ToolContext) -> dict:
    """Get details of an organization.

    Args:
        org: Organization name
    """
    with GiteaClient.from_context(tool_context) as c:
        return c.get(f"/orgs/{org}")


def list_org_repos(org: str, tool_context: ToolContext, page: int = 1, limit: int = 20) -> dict:
    """List repositories owned by an organization.

    Args:
        org: Organization name
        page: Page number
        limit: Results per page
    """
    with GiteaClient.from_context(tool_context) as c:
        return c.get(f"/orgs/{org}/repos", params={"page": page, "limit": limit})


def list_org_members(org: str, tool_context: ToolContext, page: int = 1, limit: int = 20) -> dict:
    """List members of an organization.

    Args:
        org: Organization name
        page: Page number
        limit: Results per page
    """
    with GiteaClient.from_context(tool_context) as c:
        return c.get(f"/orgs/{org}/members", params={"page": page, "limit": limit})


def list_org_teams(org: str, tool_context: ToolContext, page: int = 1, limit: int = 20) -> dict:
    """List teams in an organization.

    Args:
        org: Organization name
        page: Page number
        limit: Results per page
    """
    with GiteaClient.from_context(tool_context) as c:
        return c.get(f"/orgs/{org}/teams", params={"page": page, "limit": limit})


def get_team(team_id: int, tool_context: ToolContext) -> dict:
    """Get details of a team by its ID.

    Args:
        team_id: Team ID
    """
    with GiteaClient.from_context(tool_context) as c:
        return c.get(f"/teams/{team_id}")


def list_team_members(team_id: int, tool_context: ToolContext, page: int = 1, limit: int = 20) -> dict:
    """List members of a team.

    Args:
        team_id: Team ID
        page: Page number
        limit: Results per page
    """
    with GiteaClient.from_context(tool_context) as c:
        return c.get(f"/teams/{team_id}/members", params={"page": page, "limit": limit})


def list_team_repos(team_id: int, tool_context: ToolContext, page: int = 1, limit: int = 20) -> dict:
    """List repositories managed by a team.

    Args:
        team_id: Team ID
        page: Page number
        limit: Results per page
    """
    with GiteaClient.from_context(tool_context) as c:
        return c.get(f"/teams/{team_id}/repos", params={"page": page, "limit": limit})


# ---------------------------------------------------------------------------
# 导出
# ---------------------------------------------------------------------------

all_tools: list = [
    list_my_orgs,
    get_org,
    list_org_repos,
    list_org_members,
    list_org_teams,
    get_team,
    list_team_members,
    list_team_repos,
]
