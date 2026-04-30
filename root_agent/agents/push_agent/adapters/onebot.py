"""OneBot v11 HTTP API 适配器（兼容 go-cqhttp / NapCat / LLOneBot 等）。"""

from __future__ import annotations

from typing import ClassVar

import httpx

from . import PushAdapter, register_adapter


@register_adapter
class OneBotAdapter(PushAdapter):
    name = "onebot"
    display_name = "OneBot v11 (QQ 机器人)"
    config_schema: ClassVar[dict[str, str]] = {
        "api_url": "OneBot HTTP API 地址（如 http://127.0.0.1:5700）",
        "target_type": "消息类型: private（私聊）或 group（群聊）",
        "target_id": "目标 QQ 号（私聊）或群号（群聊）",
        "access_token": "（可选）HTTP API 的 access_token，未设置则留空",
    }

    async def send(self, title: str, content: str, content_type: str = "text") -> str:
        api_url = self.config.get("api_url", "").rstrip("/")
        target_type = self.config.get("target_type", "private")
        target_id = self.config.get("target_id", "")
        access_token = self.config.get("access_token", "")

        if not api_url or not target_id:
            return "错误: 未配置 api_url 或 target_id"

        # 组装消息文本
        message = f"【{title}】\n{content}" if title else content

        # 构建请求
        endpoint = f"{api_url}/send_msg"
        body: dict = {
            "message_type": target_type,
            "message": message,
        }
        if target_type == "private":
            body["user_id"] = int(target_id)
        else:
            body["group_id"] = int(target_id)

        headers: dict[str, str] = {"Content-Type": "application/json"}
        if access_token:
            headers["Authorization"] = f"Bearer {access_token}"

        try:
            async with httpx.AsyncClient(timeout=10) as client:
                resp = await client.post(endpoint, json=body, headers=headers)
                data = resp.json()
                if data.get("status") == "ok" or data.get("retcode") == 0:
                    return "ok"
                return f"OneBot 返回错误: {data.get('msg') or data.get('wording') or str(data)}"
        except Exception as e:
            return f"OneBot 发送失败: {e}"
