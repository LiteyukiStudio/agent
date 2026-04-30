"""SMTP 邮件推送适配器（支持 HTML）。"""

from __future__ import annotations

import asyncio
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import ClassVar

from . import PushAdapter, register_adapter


@register_adapter
class SmtpAdapter(PushAdapter):
    name = "smtp"
    display_name = "邮件 (SMTP)"
    config_schema: ClassVar[dict[str, str]] = {
        "host": "SMTP 服务器地址（如 smtp.qq.com、smtp.gmail.com）",
        "port": "SMTP 端口（TLS 通常是 587，SSL 通常是 465）",
        "username": "登录用户名（通常是邮箱地址）",
        "password": "登录密码或授权码（QQ 邮箱需要用授权码）",
        "from_addr": "发件人地址（如 noreply@example.com）",
        "to_addr": "收件人地址（多个用逗号分隔）",
        "use_tls": "（可选）是否使用 TLS，默认 true。设为 ssl 则使用 SSL",
    }

    async def send(self, title: str, content: str, content_type: str = "text") -> str:
        host = self.config.get("host", "")
        port = int(self.config.get("port", 587))
        username = self.config.get("username", "")
        password = self.config.get("password", "")
        from_addr = self.config.get("from_addr", username)
        to_addr = self.config.get("to_addr", "")
        use_tls = str(self.config.get("use_tls", "true")).lower()

        if not all([host, username, password, to_addr]):
            return "错误: SMTP 配置不完整（需要 host/username/password/to_addr）"

        # 构建邮件
        msg = MIMEMultipart("alternative")
        msg["Subject"] = title or "Notification"
        msg["From"] = from_addr
        msg["To"] = to_addr

        if content_type == "html":
            msg.attach(MIMEText(content, "html", "utf-8"))
        elif content_type == "markdown":
            # markdown 作为纯文本发送（或后续可接 markdown→html 转换）
            msg.attach(MIMEText(content, "plain", "utf-8"))
        else:
            msg.attach(MIMEText(content, "plain", "utf-8"))

        recipients = [addr.strip() for addr in to_addr.split(",")]

        # 在线程池中执行同步 SMTP 操作
        def _send() -> str:
            try:
                if use_tls == "ssl":
                    server = smtplib.SMTP_SSL(host, port, timeout=15)
                else:
                    server = smtplib.SMTP(host, port, timeout=15)
                    if use_tls != "false":
                        server.starttls()
                server.login(username, password)
                server.sendmail(from_addr, recipients, msg.as_string())
                server.quit()
                return "ok"
            except Exception as e:
                return f"SMTP 发送失败: {e}"

        return await asyncio.get_event_loop().run_in_executor(None, _send)
