"""OAuth 和密码认证路由。"""

from __future__ import annotations

import secrets
from typing import TYPE_CHECKING

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import RedirectResponse
from sqlalchemy import select

from server.config import settings
from server.deps import get_current_user, get_db
from server.models.oauth_provider import OAuthProvider
from server.schemas.auth import (
    ApiTokenCreate,
    ApiTokenCreated,
    ApiTokenResponse,
    LoginRequest,
    ProviderInfo,
    TokenResponse,
    UserResponse,
)
from server.services.auth import (
    build_authorization_url,
    check_access_list,
    create_api_token,
    create_jwt,
    delete_api_token,
    exchange_code,
    find_or_create_user,
    list_api_tokens,
    password_login,
)

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

    from server.models.user import User

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])

# 内存中的 state 存储，用于 CSRF 防护（生产环境应使用 Redis/数据库）
_oauth_states: dict[str, str] = {}


# ---------------------------------------------------------------------------
# OAuth 提供商列表
# ---------------------------------------------------------------------------


@router.get("/providers", response_model=list[ProviderInfo])
async def list_providers(db: AsyncSession = Depends(get_db)) -> list[ProviderInfo]:
    """列出所有已启用的 OAuth 提供商（公开端点）。"""
    result = await db.execute(select(OAuthProvider).where(OAuthProvider.enabled.is_(True)))
    providers = result.scalars().all()
    return [ProviderInfo(id=p.id, name=p.name, issuer_url=p.issuer_url) for p in providers]


# ---------------------------------------------------------------------------
# 密码登录
# ---------------------------------------------------------------------------


@router.post("/login", response_model=TokenResponse)
async def login_with_password(
    body: LoginRequest,
    db: AsyncSession = Depends(get_db),
) -> TokenResponse:
    """使用用户名和密码登录。"""
    user = await password_login(db, body.username, body.password)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password",
        )
    token = create_jwt(user)
    return TokenResponse(access_token=token)


# ---------------------------------------------------------------------------
# OAuth 登录流程
# ---------------------------------------------------------------------------


@router.get("/oauth/login/{provider_id}")
async def oauth_login(provider_id: str, db: AsyncSession = Depends(get_db)) -> RedirectResponse:
    """重定向到 OAuth 提供商的授权页面。"""
    result = await db.execute(
        select(OAuthProvider).where(OAuthProvider.id == provider_id, OAuthProvider.enabled.is_(True)),
    )
    provider = result.scalar_one_or_none()
    if provider is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Provider not found")
    if not provider.authorization_endpoint:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Provider has no authorization endpoint configured",
        )

    state = secrets.token_urlsafe(32)
    _oauth_states[state] = provider_id
    redirect_uri = f"{settings.server_host}/api/v1/auth/oauth/callback/{provider_id}"
    url = build_authorization_url(provider, redirect_uri, state)
    return RedirectResponse(url=url)


@router.get("/oauth/callback/{provider_id}")
async def oauth_callback(
    provider_id: str,
    code: str,
    state: str = "",
    db: AsyncSession = Depends(get_db),
) -> TokenResponse:
    """处理 OAuth 回调：交换授权码、创建/查找用户、返回 JWT。"""
    # 验证 state
    if state and _oauth_states.pop(state, None) != provider_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid OAuth state")

    result = await db.execute(select(OAuthProvider).where(OAuthProvider.id == provider_id))
    provider = result.scalar_one_or_none()
    if provider is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Provider not found")

    redirect_uri = f"{settings.server_host}/api/v1/auth/oauth/callback/{provider_id}"

    try:
        userinfo = await exchange_code(provider, code, redirect_uri)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"OAuth code exchange failed: {e}",
        ) from e

    # 检查访问名单
    allowed = await check_access_list(db, provider, userinfo)
    if not allowed:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied: you are not allowed to login via this provider",
        )

    user = await find_or_create_user(db, provider_id, userinfo)
    token = create_jwt(user)
    return TokenResponse(access_token=token)


# ---------------------------------------------------------------------------
# 当前用户
# ---------------------------------------------------------------------------


@router.get("/me", response_model=UserResponse)
async def me(user: User = Depends(get_current_user)) -> UserResponse:
    """获取当前已认证用户的信息。"""
    return UserResponse.model_validate(user)


# ---------------------------------------------------------------------------
# API 访问令牌管理
# ---------------------------------------------------------------------------


@router.get("/tokens", response_model=list[ApiTokenResponse])
async def list_tokens(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[ApiTokenResponse]:
    """列出当前用户的所有 API 令牌。"""
    tokens = await list_api_tokens(db, user.id)
    return [ApiTokenResponse.model_validate(t) for t in tokens]


@router.post("/tokens", response_model=ApiTokenCreated, status_code=status.HTTP_201_CREATED)
async def create_token(
    body: ApiTokenCreate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ApiTokenCreated:
    """创建新的 API 令牌。明文 token 仅在此响应中返回一次。"""
    token_obj, plaintext = await create_api_token(db, user.id, body)
    return ApiTokenCreated(
        id=token_obj.id,
        name=token_obj.name,
        token=plaintext,
        scopes=token_obj.scopes,
        expires_at=token_obj.expires_at,
        created_at=token_obj.created_at,
    )


@router.delete("/tokens/{token_id}", status_code=status.HTTP_204_NO_CONTENT)
async def revoke_token(
    token_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> None:
    """吊销（删除）一个 API 令牌。"""
    deleted = await delete_api_token(db, user.id, token_id)
    if not deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Token not found")
