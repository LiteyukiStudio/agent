"""Gitea API HTTP 客户端。

基于 httpx 封装的可复用、带认证的 Gitea REST API 客户端。
支持通过环境变量或运行时交互式配置。
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

import httpx

# 持久化凭证文件（位于项目根目录旁）
_CREDENTIALS_FILE = Path(__file__).resolve().parent.parent / ".credentials.json"


def _load_credentials() -> dict[str, Any]:
    if _CREDENTIALS_FILE.exists():
        return json.loads(_CREDENTIALS_FILE.read_text())
    return {}


def _save_credentials(data: dict[str, Any]) -> None:
    _CREDENTIALS_FILE.write_text(json.dumps(data, indent=2, ensure_ascii=False))


class GiteaClient:
    """基于 httpx 的轻量 Gitea API 客户端。"""

    def __init__(self, base_url: str | None = None, token: str | None = None) -> None:
        resolved_url, resolved_token = self._resolve_config(base_url, token)
        if not resolved_url:
            raise ValueError(
                "Gitea base URL is not configured. Set GITEA_BASE_URL env var or call setup_gitea tool first."
            )
        # 规范化：去除末尾斜杠
        self.base_url = resolved_url.rstrip("/")
        self.token = resolved_token or ""
        self._client = httpx.Client(
            base_url=f"{self.base_url}/api/v1",
            headers=self._build_headers(),
            timeout=30.0,
        )

    # ------------------------------------------------------------------
    # 配置解析：运行时参数 > 环境变量 > 凭证文件
    # ------------------------------------------------------------------

    @staticmethod
    def _resolve_config(base_url: str | None, token: str | None) -> tuple[str | None, str | None]:
        # 1. 显式参数优先
        if base_url and token:
            return base_url, token

        # 2. 环境变量
        env_url = os.getenv("GITEA_BASE_URL", "")
        env_token = os.getenv("GITEA_TOKEN", "")
        if env_url:
            return env_url, env_token or token or ""

        # 3. 凭证文件（由 setup_gitea 工具写入）
        creds = _load_credentials()
        gitea = creds.get("gitea", {})
        file_url = gitea.get("base_url", "")
        file_token = gitea.get("token", "")
        if file_url:
            return file_url, file_token or token or ""

        return base_url, token

    def _build_headers(self) -> dict[str, str]:
        headers: dict[str, str] = {"Accept": "application/json"}
        if self.token:
            headers["Authorization"] = f"token {self.token}"
        return headers

    # ------------------------------------------------------------------
    # 凭证持久化（由 setup_gitea 工具调用）
    # ------------------------------------------------------------------

    @staticmethod
    def save_credentials(base_url: str, token: str) -> None:
        creds = _load_credentials()
        creds["gitea"] = {"base_url": base_url, "token": token}
        _save_credentials(creds)

    @staticmethod
    def load_saved_credentials() -> dict[str, str]:
        creds = _load_credentials()
        return creds.get("gitea", {})

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
