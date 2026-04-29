"""代码托管平台通用组织工具生成器。"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from google.adk.tools import ToolContext

    from .client import ForgeClient


def make_org_tools(client_class: type[ForgeClient]) -> list:
    """为指定平台生成组织相关工具函数。"""

    def list_my_orgs(
        tool_context: ToolContext,
        page: int = 1,
        limit: int = 20,
    ) -> dict:
        """List organizations the authenticated user belongs to.

        Args:
            page: Page number
            limit: Results per page
        """
        with client_class.from_context(tool_context) as c:
            return c.get("/user/orgs", params=client_class.paginate_params(page, limit))

    def get_org(org: str, tool_context: ToolContext) -> dict:
        """Get organization details.

        Args:
            org: Organization name
        """
        with client_class.from_context(tool_context) as c:
            return c.get(f"/orgs/{org}")

    def list_org_repos(
        org: str,
        tool_context: ToolContext,
        page: int = 1,
        limit: int = 20,
    ) -> dict:
        """List repositories owned by an organization.

        Args:
            org: Organization name
            page: Page number
            limit: Results per page
        """
        with client_class.from_context(tool_context) as c:
            return c.get(f"/orgs/{org}/repos", params=client_class.paginate_params(page, limit))

    def list_org_members(
        org: str,
        tool_context: ToolContext,
        page: int = 1,
        limit: int = 20,
    ) -> dict:
        """List members of an organization.

        Args:
            org: Organization name
            page: Page number
            limit: Results per page
        """
        with client_class.from_context(tool_context) as c:
            return c.get(f"/orgs/{org}/members", params=client_class.paginate_params(page, limit))

    return [list_my_orgs, get_org, list_org_repos, list_org_members]
