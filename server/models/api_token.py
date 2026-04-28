"""API 访问令牌 ORM 模型。

用于外部 API 调用认证，区别于网页端的 JWT。
令牌格式: lys_ + 40位随机十六进制字符。
"""

from __future__ import annotations

from datetime import datetime
from uuid import uuid4

from sqlalchemy import DateTime, ForeignKey, String, func
from sqlalchemy.orm import Mapped, mapped_column

from server.database import Base


class ApiToken(Base):
    """用户的 API 访问令牌。"""

    __tablename__ = "api_tokens"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), nullable=False)
    name: Mapped[str] = mapped_column(String(200), nullable=False)  # 用户给令牌起的名字
    token_hash: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)  # sha256 哈希
    token_last_eight: Mapped[str] = mapped_column(String(8), nullable=False)  # 最后 8 位，用于识别
    scopes: Mapped[str] = mapped_column(String(500), default="*")  # 逗号分隔的权限范围
    expires_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)  # 可选过期时间
    last_used_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)  # 最后使用时间

    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
