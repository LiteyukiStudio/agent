"""代码托管平台 HTTP 客户端基类。

子类需覆盖：platform, default_base_url, _api_base(), _build_headers(), _paginate_params()。
"""

from __future__ import annotations

from typing import Any

import httpx


class ForgeClient:
    """代码托管平台 HTTP 客户端基类（Gitea / GitHub / Forgejo 等）。"""

    platform: str = ""  # 子类覆盖："gitea" / "github"
    default_base_url: str = ""  # 子类覆盖

    def __init__(self, base_url: str, token: str = "") -> None:
        self.base_url = base_url.rstrip("/")
        self.token = token
        self._client = httpx.Client(
            base_url=self._api_base(),
            headers=self._build_headers(),
            timeout=30.0,
        )

    # ------------------------------------------------------------------
    # 子类必须覆盖
    # ------------------------------------------------------------------

    def _api_base(self) -> str:
        """返回完整的 API base URL。"""
        return self.base_url

    def _build_headers(self) -> dict[str, str]:
        """构建认证和 Accept 头。"""
        return {"Accept": "application/json"}

    @classmethod
    def paginate_params(cls, page: int, limit: int) -> dict[str, int]:
        """返回分页查询参数。子类可覆盖。"""
        return {"page": page, "limit": limit}

    # ------------------------------------------------------------------
    # 工厂方法
    # ------------------------------------------------------------------

    @classmethod
    def from_context(cls, tool_context: Any) -> ForgeClient:
        """从 ADK ToolContext 构造客户端，自动使用当前活跃凭据。"""
        from credential_provider import CredentialKey, CredentialSchema

        # 检查是否有活跃凭据切换
        state = tool_context.state if hasattr(tool_context, "state") else {}
        active_id = state.get(f"{cls.platform}___active_credential", "")

        if active_id:
            # 多凭据模式：读 {platform}:{credential_id}_xxx
            ns = f"{cls.platform}:{active_id}"
        else:
            # 检查是否有 __default 指针
            default_id = state.get(f"{cls.platform}___default", "")
            ns = f"{cls.platform}:{default_id}" if default_id else cls.platform

        schema = CredentialSchema(
            namespace=ns,
            keys={
                "base_url": CredentialKey(default=cls.default_base_url),
                "token": CredentialKey(secret=True, user_only=True),
            },
        )
        creds = schema.resolve(tool_context)
        return cls(base_url=creds["base_url"] or cls.default_base_url, token=creds["token"])

    # ------------------------------------------------------------------
    # HTTP 方法
    # ------------------------------------------------------------------

    def get(self, path: str, params: dict | None = None) -> Any:
        return self._request("GET", path, params=params)

    def post(self, path: str, json_data: dict | None = None) -> Any:
        return self._request("POST", path, json_data=json_data)

    def put(self, path: str, json_data: dict | None = None) -> Any:
        return self._request("PUT", path, json_data=json_data)

    def patch(self, path: str, json_data: dict | None = None) -> Any:
        return self._request("PATCH", path, json_data=json_data)

    def delete(self, path: str) -> Any:
        return self._request("DELETE", path)

    def _request(
        self,
        method: str,
        path: str,
        params: dict | None = None,
        json_data: dict | None = None,
    ) -> Any:
        try:
            resp = self._client.request(method, path, params=params, json=json_data)
            resp.raise_for_status()
            if resp.status_code == 204:
                return {"status": "ok", "code": 204}
            if not resp.content:
                return {"status": "ok", "code": resp.status_code}
            return resp.json()
        except httpx.HTTPStatusError as e:
            return {
                "error": True,
                "status_code": e.response.status_code,
                "message": e.response.text[:500],
            }
        except httpx.RequestError as e:
            return {"error": True, "message": str(e)}

    # ------------------------------------------------------------------
    # 生命周期
    # ------------------------------------------------------------------

    def close(self) -> None:
        self._client.close()

    def __enter__(self) -> ForgeClient:
        return self

    def __exit__(self, *args: Any) -> None:
        self.close()
