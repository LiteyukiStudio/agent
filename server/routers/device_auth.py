"""设备授权流程：CLI 工具通过浏览器完成认证。

流程：
1. CLI 请求 device code
2. 用户在浏览器打开验证页面，登录并确认
3. CLI 轮询获取 token
"""

from __future__ import annotations

import logging
import secrets
import string
from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from server.deps import get_current_user, get_db
from server.schemas.auth import ApiTokenCreate
from server.services.auth import create_api_token

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

    from server.models.user import User

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/auth/device", tags=["device-auth"])

# ---------------------------------------------------------------------------
# 内存存储（设备码 → 状态）
# ---------------------------------------------------------------------------

_EXPIRY_MINUTES = 10
_CODE_LENGTH = 8


class DeviceSession:
    """一次设备授权会话。"""

    def __init__(self, device_code: str, user_code: str, server_url: str) -> None:
        self.device_code = device_code
        self.user_code = user_code
        self.server_url = server_url
        self.created_at = datetime.now(tz=UTC)
        self.expires_at = self.created_at + timedelta(minutes=_EXPIRY_MINUTES)
        self.approved = False
        self.user_id: str | None = None
        self.token: str | None = None  # 授权后生成的 API Token

    @property
    def expired(self) -> bool:
        return datetime.now(tz=UTC) > self.expires_at


# device_code → DeviceSession
_sessions: dict[str, DeviceSession] = {}
# user_code → device_code（方便通过 user_code 查找）
_user_code_index: dict[str, str] = {}


def _generate_user_code() -> str:
    """生成易读的用户验证码，格式: ABCD-1234"""
    letters = "".join(secrets.choice(string.ascii_uppercase) for _ in range(4))
    digits = "".join(secrets.choice(string.digits) for _ in range(4))
    return f"{letters}-{digits}"


def _cleanup_expired() -> None:
    """清理过期的会话。"""
    expired = [k for k, v in _sessions.items() if v.expired]
    for k in expired:
        session = _sessions.pop(k)
        _user_code_index.pop(session.user_code, None)


# ---------------------------------------------------------------------------
# API 模型
# ---------------------------------------------------------------------------


class DeviceCodeRequest(BaseModel):
    server_url: str = "https://flow.liteyuki.org"


class DeviceCodeResponse(BaseModel):
    device_code: str
    user_code: str
    verification_url: str
    expires_in: int  # 秒


class DeviceTokenRequest(BaseModel):
    device_code: str


class DeviceTokenResponse(BaseModel):
    status: str  # "pending" | "approved" | "expired"
    token: str | None = None


class DeviceApproveRequest(BaseModel):
    user_code: str


# ---------------------------------------------------------------------------
# 端点
# ---------------------------------------------------------------------------


@router.post("/code", response_model=DeviceCodeResponse)
async def request_device_code(
    body: DeviceCodeRequest,
) -> DeviceCodeResponse:
    """CLI 请求设备码。返回 device_code（轮询用）和 user_code（给用户看）。"""
    _cleanup_expired()

    device_code = secrets.token_urlsafe(32)
    user_code = _generate_user_code()

    # 确保 user_code 唯一
    while user_code in _user_code_index:
        user_code = _generate_user_code()

    session = DeviceSession(device_code, user_code, body.server_url)
    _sessions[device_code] = session
    _user_code_index[user_code] = device_code

    verification_url = f"{body.server_url}/device?code={user_code}"

    return DeviceCodeResponse(
        device_code=device_code,
        user_code=user_code,
        verification_url=verification_url,
        expires_in=_EXPIRY_MINUTES * 60,
    )


@router.post("/token", response_model=DeviceTokenResponse)
async def poll_device_token(
    body: DeviceTokenRequest,
) -> DeviceTokenResponse:
    """CLI 轮询检查用户是否已授权。"""
    session = _sessions.get(body.device_code)
    if not session:
        return DeviceTokenResponse(status="expired")

    if session.expired:
        _sessions.pop(body.device_code, None)
        _user_code_index.pop(session.user_code, None)
        return DeviceTokenResponse(status="expired")

    if session.approved and session.token:
        # 授权成功，清理会话，返回 token
        _sessions.pop(body.device_code, None)
        _user_code_index.pop(session.user_code, None)
        return DeviceTokenResponse(status="approved", token=session.token)

    return DeviceTokenResponse(status="pending")


@router.post("/approve")
async def approve_device(
    body: DeviceApproveRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """用户在浏览器中确认授权。需要已登录。"""
    device_code = _user_code_index.get(body.user_code)
    if not device_code:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Invalid or expired code",
        )

    session = _sessions.get(device_code)
    if not session or session.expired:
        raise HTTPException(
            status_code=status.HTTP_410_GONE,
            detail="Code expired",
        )

    # 为用户创建一个 API Token
    token_name = f"local-agent-{session.user_code}"
    token_data = ApiTokenCreate(name=token_name, scopes="local-agent")
    _, api_token = await create_api_token(db, user_id=user.id, data=token_data)

    session.approved = True
    session.user_id = user.id
    session.token = api_token

    logger.info("Device auth approved: user=%s code=%s", user.username, session.user_code)

    return {"message": "Authorized", "user_code": session.user_code}


# ---------------------------------------------------------------------------
# 快速浏览器认证（CLI 启动本地 HTTP server，浏览器回调传 token）
# ---------------------------------------------------------------------------


class CliTokenRequest(BaseModel):
    """CLI 请求为 local-agent 创建 API Token。需要已登录。"""

    hostname: str = "default"


@router.post("/cli-token")
async def create_cli_token(
    body: CliTokenRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """为已登录用户的 CLI 创建 API Token（快速认证模式）。

    前端 /auth/cli 页面调用此接口，将生成的 token 通过 redirect 传给 CLI 本地 server。
    """
    token_name = f"local-agent-{body.hostname}"
    token_data = ApiTokenCreate(name=token_name, scopes="local-agent")
    _, api_token = await create_api_token(db, user_id=user.id, data=token_data)

    logger.info(
        "CLI token created: user=%s hostname=%s",
        user.username,
        body.hostname,
    )

    return {"token": api_token}
