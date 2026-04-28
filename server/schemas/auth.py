"""认证相关的 Pydantic 数据模型。"""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel


class ProviderInfo(BaseModel):
    """公开的 OAuth 提供商信息（不含密钥）。"""

    id: str
    name: str
    issuer_url: str


class UserResponse(BaseModel):
    """返回给前端的用户信息。"""

    id: str
    username: str
    email: str | None = None
    avatar_url: str | None = None
    role: str

    model_config = {"from_attributes": True}


class TokenResponse(BaseModel):
    """登录成功后返回的 JWT 令牌。"""

    access_token: str
    token_type: str = "bearer"


# ---------------------------------------------------------------------------
# 密码登录
# ---------------------------------------------------------------------------


class LoginRequest(BaseModel):
    """密码登录请求体。"""

    username: str
    password: str


# ---------------------------------------------------------------------------
# API 访问令牌
# ---------------------------------------------------------------------------


class ApiTokenCreate(BaseModel):
    """创建 API 令牌的请求体。"""

    name: str
    scopes: str = "*"  # 逗号分隔的权限范围，默认全部
    expires_at: datetime | None = None  # 可选过期时间


class ApiTokenResponse(BaseModel):
    """API 令牌信息（不含完整 token）。"""

    id: str
    name: str
    token_last_eight: str
    scopes: str
    expires_at: datetime | None = None
    last_used_at: datetime | None = None
    created_at: datetime

    model_config = {"from_attributes": True}


class ApiTokenCreated(BaseModel):
    """创建 API 令牌后的响应（包含明文 token，仅展示一次）。"""

    id: str
    name: str
    token: str  # 明文 token，只在创建时返回
    scopes: str
    expires_at: datetime | None = None
    created_at: datetime
