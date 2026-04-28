"""用户配置相关的 Pydantic 数据模型。"""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel


class UserConfigSet(BaseModel):
    """创建或更新用户配置。"""

    namespace: str
    key: str
    value: str
    is_secret: bool = False


class UserConfigResponse(BaseModel):
    """用户配置响应（敏感值脱敏）。"""

    namespace: str
    key: str
    value: str  # 如果 is_secret 则显示为 "******"
    is_secret: bool
    updated_at: datetime

    model_config = {"from_attributes": True}
