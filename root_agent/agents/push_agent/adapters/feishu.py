"""飞书自定义机器人 Webhook 适配器。"""

from __future__ import annotations

from typing import ClassVar

import httpx

from . import PushAdapter, register_adapter


@register_adapter
class FeishuAdapter(PushAdapter):
    name = "feishu"
    display_name = "飞书 (Feishu Webhook)"
    config_schema: ClassVar[dict[str, str]] = {
        "webhook_url": "飞书群机器人的 Webhook 地址（格式: https://open.feishu.cn/open-apis/bot/v2/hook/xxx）",
    }

    async def send(self, title: str, content: str, content_type: str = "text") -> str:
        url = self.config.get("webhook_url", "")
        if not url:
            return "错误: 未配置 webhook_url"

        # 飞书支持：text / interactive (卡片)
        if content_type == "markdown":
            # 用富文本卡片发送 markdown
            body = {
                "msg_type": "interactive",
                "card": {
                    "header": {"title": {"tag": "plain_text", "content": title}},
                    "elements": [{"tag": "markdown", "content": content}],
                },
            }
        else:
            # 纯文本
            text = f"**{title}**\n{content}" if title else content
            body = {"msg_type": "text", "content": {"text": text}}

        try:
            async with httpx.AsyncClient(timeout=10) as client:
                resp = await client.post(url, json=body)
                data = resp.json()
                if data.get("code") == 0 or data.get("StatusCode") == 0:
                    return "ok"
                return f"飞书返回错误: {data.get('msg', str(data))}"
        except Exception as e:
            return f"飞书发送失败: {e}"
