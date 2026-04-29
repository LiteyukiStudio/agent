"""Gitea API HTTP 客户端。

基于 httpx 封装的可复用、带认证的 Gitea REST API 客户端。
凭据通过 credential_provider 统一管理，支持用户级隔离。
"""

from __future__ import annotations

from typing import Any

import httpx

from credential_provider import CredentialKey, CredentialSchema

# Gitea 凭据声明
GITEA_CREDENTIALS = CredentialSchema(
    namespace="gitea",
    keys={
        "base_url": CredentialKey(default="https://git.liteyuki.org"),
        "token": CredentialKey(secret=True, user_only=True),
    },
)


class GiteaClient:
    """基于 httpx 的轻量 Gitea API 客户端。"""

    def __init__(self, base_url: str, token: str = "") -> None:
        # 规范化：去除末尾斜杠
        self.base_url = base_url.rstrip("/")
        self.token = token
        self._client = httpx.Client(
            base_url=f"{self.base_url}/api/v1",
            headers=self._build_headers(),
            timeout=30.0,
        )

    @classmethod
    def from_context(cls, tool_context: Any) -> GiteaClient:
        """从 ADK ToolContext 构造客户端，自动使用用户隔离的凭据。

        凭据优先级：session state（用户配置）> 环境变量。
        """
        creds = GITEA_CREDENTIALS.resolve(tool_context)
        return cls(base_url=creds["base_url"], token=creds["token"])

    def _build_headers(self) -> dict[str, str]:
        headers: dict[str, str] = {"Accept": "application/json"}
        if self.token:
            headers["Authorization"] = f"token {self.token}"
        return headers

    # ------------------------------------------------------------------
    # 核心 HTTP 方法
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

    def __enter__(self) -> GiteaClient:
        return self

    def __exit__(self, *args: Any) -> None:
        self.close()
