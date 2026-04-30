"""Gotify 推送适配器。"""

from __future__ import annotations

from typing import ClassVar

import httpx

from . import PushAdapter, register_adapter


@register_adapter
class GotifyAdapter(PushAdapter):
    name = "gotify"
    display_name = "Gotify"
    config_schema: ClassVar[dict[str, str]] = {
        "server_url": "Gotify 服务器地址（如 https://gotify.example.com）",
        "app_token": "Application Token（在 Gotify 后台的 Apps 页面创建）",
    }

    async def send(self, title: str, content: str, content_type: str = "text") -> str:
        server_url = self.config.get("server_url", "").rstrip("/")
        app_token = self.config.get("app_token", "")

        if not server_url or not app_token:
            return "错误: 未配置 server_url 或 app_token"

        endpoint = f"{server_url}/message?token={app_token}"

        body: dict = {
            "title": title or "Notification",
            "message": content,
            "priority": 5,
        }

        # Gotify 支持通过 extras 指定 content type
        if content_type == "markdown":
            body["extras"] = {"client::display": {"contentType": "text/markdown"}}
        elif content_type == "html":
            body["extras"] = {"client::display": {"contentType": "text/html"}}

        try:
            async with httpx.AsyncClient(timeout=10) as client:
                resp = await client.post(endpoint, json=body)
                if resp.status_code == 200:
                    return "ok"
                return f"Gotify 返回 {resp.status_code}: {resp.text[:200]}"
        except Exception as e:
            return f"Gotify 发送失败: {e}"
