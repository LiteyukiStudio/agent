"""管理相关的 Pydantic 数据模型。"""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel

# ---------------------------------------------------------------------------
# OAuth 提供商
# ---------------------------------------------------------------------------


class OAuthProviderCreate(BaseModel):
    """创建新 OAuth 提供商的请求体。"""

    name: str
    issuer_url: str
    client_id: str
    client_secret: str
    access_mode: str = "whitelist"  # whitelist 或 blacklist


class OAuthProviderUpdate(BaseModel):
    """更新 OAuth 提供商的请求体（所有字段可选）。"""

    name: str | None = None
    issuer_url: str | None = None
    client_id: str | None = None
    client_secret: str | None = None
    enabled: bool | None = None
    access_mode: str | None = None


class OAuthProviderResponse(BaseModel):
    """OAuth 提供商信息（不含 client_secret）。"""

    id: str
    name: str
    issuer_url: str
    client_id: str
    enabled: bool
    access_mode: str
    authorization_endpoint: str | None = None
    token_endpoint: str | None = None
    userinfo_endpoint: str | None = None
    callback_url: str | None = None  # 由 router 层填充
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


# ---------------------------------------------------------------------------
# 访问名单
# ---------------------------------------------------------------------------


class AccessListEntryCreate(BaseModel):
    """添加 Group 名单条目。"""

    group_name: str  # OIDC group 名称
    note: str | None = None


class AccessListEntryResponse(BaseModel):
    """Group 名单条目响应。"""

    id: str
    provider_id: str
    group_name: str
    note: str | None = None
    created_at: datetime

    model_config = {"from_attributes": True}


# ---------------------------------------------------------------------------
# 用户
# ---------------------------------------------------------------------------


class UserUpdate(BaseModel):
    """更新用户角色的请求体。

    可用角色: user, admin（仅 superuser 可设置 admin）。
    superuser 角色不可通过 API 分配。
    """

    role: str  # user 或 admin
