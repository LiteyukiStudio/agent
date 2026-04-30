"""企业微信群机器人 Webhook 适配器。"""

from __future__ import annotations

from typing import ClassVar

import httpx

from . import PushAdapter, register_adapter


@register_adapter
class WecomAdapter(PushAdapter):
    name = "wecom"
    display_name = "企业微信 (WeCom Webhook)"
    config_schema: ClassVar[dict[str, str]] = {
        "webhook_url": "企业微信群机器人的 Webhook 地址（格式: https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=xxx）",
    }

    async def send(self, title: str, content: str, content_type: str = "text") -> str:
        url = self.config.get("webhook_url", "")
        if not url:
            return "错误: 未配置 webhook_url"

        if content_type in ("markdown", "html"):
            # 企业微信 markdown 格式
            md_content = f"## {title}\n{content}" if title else content
            body = {"msgtype": "markdown", "markdown": {"content": md_content}}
        else:
            # 纯文本
            text = f"{title}\n{content}" if title else content
            body = {"msgtype": "text", "text": {"content": text}}

        try:
            async with httpx.AsyncClient(timeout=10) as client:
                resp = await client.post(url, json=body)
                data = resp.json()
                if data.get("errcode") == 0:
                    return "ok"
                return f"企业微信返回错误: {data.get('errmsg', str(data))}"
        except Exception as e:
            return f"企业微信发送失败: {e}"
