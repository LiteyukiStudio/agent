"""Misskey API HTTP 客户端。

基于 httpx 封装的 Misskey REST API 客户端。
Misskey API 全部使用 POST 方法，认证通过 Bearer Token。
凭据通过 credential_provider 统一管理，支持用户级隔离。
"""

from __future__ import annotations

from typing import Any

import httpx

from credential_provider import CredentialKey, CredentialSchema

# Misskey 凭据声明
MISSKEY_CREDENTIALS = CredentialSchema(
    namespace="misskey",
    keys={
        "base_url": CredentialKey(default="https://lab.liteyuki.org"),
        "token": CredentialKey(secret=True, user_only=True),
    },
)


class MisskeyClient:
    """基于 httpx 的 Misskey API 客户端。

    Misskey API 的特殊性：
    - 所有端点都使用 POST 方法（包括查询操作）
    - 认证通过 Bearer Token
    - Base URL 格式为 {instance}/api
    """

    def __init__(self, base_url: str, token: str = "") -> None:
        self.base_url = base_url.rstrip("/")
        self.token = token
        self._client = httpx.Client(
            base_url=f"{self.base_url}/api",
            headers=self._build_headers(),
            timeout=30.0,
        )

    @classmethod
    def from_context(cls, tool_context: Any) -> MisskeyClient:
        """从 ADK ToolContext 构造客户端，自动使用用户隔离的凭据。"""
        creds = MISSKEY_CREDENTIALS.resolve(tool_context)
        return cls(base_url=creds["base_url"], token=creds["token"])

    def _build_headers(self) -> dict[str, str]:
        headers: dict[str, str] = {
            "Accept": "application/json",
            "Content-Type": "application/json",
        }
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        return headers

    # ------------------------------------------------------------------
    # 核心方法：Misskey 全部用 POST
    # ------------------------------------------------------------------

    def request(self, endpoint: str, data: dict | None = None) -> Any:
        """向 Misskey API 发送 POST 请求。

        Args:
            endpoint: API 路径，如 "/notes/create"。
            data: 请求体 JSON 数据。

        Returns:
            解析后的 JSON 响应，或错误字典。
        """
        try:
            resp = self._client.post(endpoint, json=data or {})
            resp.raise_for_status()
            if resp.status_code == 204:
                return {"status": "ok", "code": 204}
            # 部分端点返回空 body
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

    def __enter__(self) -> MisskeyClient:
        return self

    def __exit__(self, *args: Any) -> None:
        self.close()
