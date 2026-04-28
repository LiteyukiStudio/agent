"""Gitea API HTTP client.

Wraps httpx to provide a reusable, authenticated client for the Gitea REST API.
Supports configuration via environment variables or runtime setup.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

import httpx

# Persistent credentials file (next to the project root)
_CREDENTIALS_FILE = Path(__file__).resolve().parent.parent / ".credentials.json"


def _load_credentials() -> dict[str, Any]:
    if _CREDENTIALS_FILE.exists():
        return json.loads(_CREDENTIALS_FILE.read_text())
    return {}


def _save_credentials(data: dict[str, Any]) -> None:
    _CREDENTIALS_FILE.write_text(json.dumps(data, indent=2, ensure_ascii=False))


class GiteaClient:
    """Lightweight Gitea API client built on httpx."""

    def __init__(self, base_url: str | None = None, token: str | None = None) -> None:
        resolved_url, resolved_token = self._resolve_config(base_url, token)
        if not resolved_url:
            raise ValueError(
                "Gitea base URL is not configured. Set GITEA_BASE_URL env var or call setup_gitea tool first."
            )
        # Normalize: strip trailing slash
        self.base_url = resolved_url.rstrip("/")
        self.token = resolved_token or ""
        self._client = httpx.Client(
            base_url=f"{self.base_url}/api/v1",
            headers=self._build_headers(),
            timeout=30.0,
        )

    # ------------------------------------------------------------------
    # Config resolution: runtime args > env vars > credentials file
    # ------------------------------------------------------------------

    @staticmethod
    def _resolve_config(base_url: str | None, token: str | None) -> tuple[str | None, str | None]:
        # 1. Explicit arguments take priority
        if base_url and token:
            return base_url, token

        # 2. Environment variables
        env_url = os.getenv("GITEA_BASE_URL", "")
        env_token = os.getenv("GITEA_TOKEN", "")
        if env_url:
            return env_url, env_token or token or ""

        # 3. Credentials file (set via interactive setup_gitea tool)
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
    # Credential persistence (called by the setup_gitea tool)
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
    # Core HTTP helpers
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
    # Lifecycle
    # ------------------------------------------------------------------

    def close(self) -> None:
        self._client.close()

    def __enter__(self) -> GiteaClient:
        return self

    def __exit__(self, *args: Any) -> None:
        self.close()
