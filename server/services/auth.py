"""认证服务：密码登录、OAuth、JWT、API Token、用户管理。"""

from __future__ import annotations

import hashlib
import secrets
from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING

import bcrypt
import httpx
from jose import JWTError, jwt
from sqlalchemy import func, select

from server.config import settings
from server.models.access_list import AccessListEntry
from server.models.api_token import ApiToken
from server.models.user import User

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

    from server.models.oauth_provider import OAuthProvider
    from server.schemas.auth import ApiTokenCreate

# ---------------------------------------------------------------------------
# 角色常量
# ---------------------------------------------------------------------------

ROLE_SUPERUSER = "superuser"
ROLE_ADMIN = "admin"
ROLE_USER = "user"
VALID_ROLES = {ROLE_SUPERUSER, ROLE_ADMIN, ROLE_USER}

# 角色权重，用于权限比较
ROLE_WEIGHT = {ROLE_SUPERUSER: 3, ROLE_ADMIN: 2, ROLE_USER: 1}


def is_at_least(role: str, minimum: str) -> bool:
    """检查角色是否达到最低要求。"""
    return ROLE_WEIGHT.get(role, 0) >= ROLE_WEIGHT.get(minimum, 0)


# ---------------------------------------------------------------------------
# 密码工具
# ---------------------------------------------------------------------------


def hash_password(password: str) -> str:
    """使用 bcrypt 哈希密码。"""
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()


def verify_password(password: str, hashed: str) -> bool:
    """验证密码是否匹配 bcrypt 哈希。"""
    return bcrypt.checkpw(password.encode(), hashed.encode())


async def password_login(db: AsyncSession, username: str, password: str) -> User | None:
    """通过用户名和密码登录。

    Args:
        db: 异步数据库会话。
        username: 用户名。
        password: 明文密码。

    Returns:
        验证成功返回 User，否则返回 None。
    """
    result = await db.execute(select(User).where(User.username == username))
    user = result.scalar_one_or_none()
    if user is None or not user.password_hash:
        return None
    if not verify_password(password, user.password_hash):
        return None
    return user


# ---------------------------------------------------------------------------
# 初始超级用户
# ---------------------------------------------------------------------------


async def init_superuser(db: AsyncSession) -> None:
    """首次启动时创建初始超级用户（如果没有任何用户）。

    Args:
        db: 异步数据库会话。
    """
    count_result = await db.execute(select(func.count()).select_from(User))
    total = count_result.scalar() or 0
    if total > 0:
        return

    user = User(
        username=settings.initial_username,
        role=ROLE_SUPERUSER,
        password_hash=hash_password(settings.initial_password),
    )
    db.add(user)
    await db.commit()


# ---------------------------------------------------------------------------
# OIDC 发现
# ---------------------------------------------------------------------------


async def discover_oidc(issuer_url: str) -> dict[str, str]:
    """从 issuer 的 well-known 端点获取 OIDC 发现文档。"""
    url = issuer_url.rstrip("/") + "/.well-known/openid-configuration"
    async with httpx.AsyncClient(timeout=15) as client:
        resp = await client.get(url)
        resp.raise_for_status()
        data = resp.json()
    return {
        "authorization_endpoint": data.get("authorization_endpoint", ""),
        "token_endpoint": data.get("token_endpoint", ""),
        "userinfo_endpoint": data.get("userinfo_endpoint", ""),
    }


# ---------------------------------------------------------------------------
# OAuth 授权码交换
# ---------------------------------------------------------------------------


async def exchange_code(
    provider: OAuthProvider,
    code: str,
    redirect_uri: str,
) -> dict:
    """用授权码交换访问令牌，然后获取用户信息。"""
    async with httpx.AsyncClient(timeout=15) as client:
        # 用授权码交换令牌
        token_resp = await client.post(
            provider.token_endpoint or "",
            data={
                "grant_type": "authorization_code",
                "code": code,
                "redirect_uri": redirect_uri,
                "client_id": provider.client_id,
                "client_secret": provider.client_secret,
            },
            headers={"Accept": "application/json"},
        )
        token_resp.raise_for_status()
        token_data = token_resp.json()
        access_token = token_data.get("access_token", "")

        # 获取用户信息
        userinfo_resp = await client.get(
            provider.userinfo_endpoint or "",
            headers={"Authorization": f"Bearer {access_token}"},
        )
        userinfo_resp.raise_for_status()
        return userinfo_resp.json()


# ---------------------------------------------------------------------------
# OAuth 用户查找/创建
# ---------------------------------------------------------------------------


async def find_or_create_user(
    db: AsyncSession,
    provider_id: str,
    userinfo: dict,
) -> User:
    """查找现有用户或根据 OAuth 用户信息创建新用户。

    如果系统中没有任何用户，首个 OAuth 用户获得 superuser。
    如果已有初始账号（密码用户），首个 OAuth 用户获得 admin。
    """
    # 尝试提取稳定的用户 ID
    oauth_user_id = str(
        userinfo.get("sub") or userinfo.get("id") or userinfo.get("login") or secrets.token_hex(16),
    )

    result = await db.execute(
        select(User).where(User.oauth_provider_id == provider_id, User.oauth_user_id == oauth_user_id),
    )
    user = result.scalar_one_or_none()

    if user is not None:
        # 更新可变字段
        user.email = userinfo.get("email") or user.email
        user.avatar_url = userinfo.get("avatar_url") or userinfo.get("picture") or user.avatar_url
        await db.commit()
        await db.refresh(user)
        return user

    # 确定新用户角色：系统空白时为 superuser，否则为普通用户
    count_result = await db.execute(select(func.count()).select_from(User))
    total_users = count_result.scalar() or 0
    role = ROLE_SUPERUSER if total_users == 0 else ROLE_USER

    # 处理用户名冲突
    desired_username = userinfo.get("login") or userinfo.get("preferred_username") or "user"
    username = await _ensure_unique_username(db, desired_username)

    user = User(
        username=username,
        email=userinfo.get("email"),
        avatar_url=userinfo.get("avatar_url") or userinfo.get("picture"),
        role=role,
        oauth_provider_id=provider_id,
        oauth_user_id=oauth_user_id,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user


async def _ensure_unique_username(db: AsyncSession, desired: str) -> str:
    """确保用户名唯一，冲突时追加数字后缀。"""
    result = await db.execute(select(User).where(User.username == desired))
    if result.scalar_one_or_none() is None:
        return desired
    # 追加数字后缀
    for i in range(1, 1000):
        candidate = f"{desired}_{i}"
        result = await db.execute(select(User).where(User.username == candidate))
        if result.scalar_one_or_none() is None:
            return candidate
    return f"{desired}_{secrets.token_hex(4)}"


# ---------------------------------------------------------------------------
# JWT
# ---------------------------------------------------------------------------


def create_jwt(user: User) -> str:
    """签发包含用户 ID 和角色的 JWT。"""
    now = datetime.now(tz=UTC)
    payload = {
        "sub": user.id,
        "role": user.role,
        "iat": now,
        "exp": now + timedelta(hours=settings.jwt_expire_hours),
    }
    return jwt.encode(payload, settings.secret_key, algorithm=settings.jwt_algorithm)


def verify_jwt(token: str, secret_key: str, algorithm: str) -> dict | None:
    """解码并验证 JWT 令牌。"""
    try:
        return jwt.decode(token, secret_key, algorithms=[algorithm])
    except JWTError:
        return None


# ---------------------------------------------------------------------------
# OAuth 授权 URL
# ---------------------------------------------------------------------------


def build_authorization_url(provider: OAuthProvider, redirect_uri: str, state: str) -> str:
    """构建 OAuth 授权 URL，用于重定向用户。"""
    params = {
        "response_type": "code",
        "client_id": provider.client_id,
        "redirect_uri": redirect_uri,
        "scope": "openid profile email groups",
        "state": state,
    }
    query = "&".join(f"{k}={v}" for k, v in params.items())
    return f"{provider.authorization_endpoint}?{query}"


# ---------------------------------------------------------------------------
# 访问名单检查
# ---------------------------------------------------------------------------


async def check_access_list(
    db: AsyncSession,
    provider: OAuthProvider,
    userinfo: dict,
) -> bool:
    """检查用户是否通过提供商的 Group 访问名单验证。

    基于 OIDC userinfo 中的 groups claim 做匹配（如 Casdoor 的组名）。
    白名单模式：名单为空时允许所有人，名单不为空时仅属于指定 group 的用户允许。
    黑名单模式：属于指定 group 的用户禁止登录。
    """
    # 提取用户的 groups（OIDC groups claim，Casdoor 等支持）
    raw_groups = userinfo.get("groups", [])
    if isinstance(raw_groups, str):
        # 有些 provider 返回逗号分隔字符串
        raw_groups = [g.strip() for g in raw_groups.split(",") if g.strip()]
    user_groups = {str(g).lower() for g in raw_groups if g}

    result = await db.execute(
        select(AccessListEntry).where(AccessListEntry.provider_id == provider.id),
    )
    entries = list(result.scalars().all())

    if provider.access_mode == "blacklist":
        # 用户属于任何一个黑名单 group 就禁止
        return all(entry.group_name.lower() not in user_groups for entry in entries)

    # 白名单（默认）
    if not entries:
        return True
    # 用户属于任何一个白名单 group 就允许
    return any(entry.group_name.lower() in user_groups for entry in entries)


# ---------------------------------------------------------------------------
# API 访问令牌
# ---------------------------------------------------------------------------

_TOKEN_PREFIX = "lys_"


def generate_api_token() -> str:
    """生成 API 令牌：lys_ + 40位随机十六进制。"""
    return f"{_TOKEN_PREFIX}{secrets.token_hex(20)}"


def hash_api_token(token: str) -> str:
    """用 SHA-256 哈希 API 令牌。"""
    return hashlib.sha256(token.encode()).hexdigest()


async def create_api_token(
    db: AsyncSession,
    user_id: str,
    data: ApiTokenCreate,
) -> tuple[ApiToken, str]:
    """创建 API 令牌。

    Returns:
        (ApiToken 记录, 明文 token)。明文 token 仅此一次返回。
    """
    plaintext = generate_api_token()
    token_obj = ApiToken(
        user_id=user_id,
        name=data.name,
        token_hash=hash_api_token(plaintext),
        token_last_eight=plaintext[-8:],
        scopes=data.scopes,
        expires_at=data.expires_at,
    )
    db.add(token_obj)
    await db.commit()
    await db.refresh(token_obj)
    return token_obj, plaintext


async def list_api_tokens(db: AsyncSession, user_id: str) -> list[ApiToken]:
    """列出用户的所有 API 令牌。"""
    result = await db.execute(
        select(ApiToken).where(ApiToken.user_id == user_id).order_by(ApiToken.created_at.desc()),
    )
    return list(result.scalars().all())


async def delete_api_token(db: AsyncSession, user_id: str, token_id: str) -> bool:
    """删除用户的 API 令牌。"""
    result = await db.execute(
        select(ApiToken).where(ApiToken.id == token_id, ApiToken.user_id == user_id),
    )
    token_obj = result.scalar_one_or_none()
    if token_obj is None:
        return False
    await db.delete(token_obj)
    await db.commit()
    return True


async def resolve_api_token(db: AsyncSession, token: str) -> User | None:
    """通过 API 令牌查找用户。同时更新 last_used_at。"""
    token_hashed = hash_api_token(token)
    result = await db.execute(
        select(ApiToken).where(ApiToken.token_hash == token_hashed),
    )
    token_obj = result.scalar_one_or_none()
    if token_obj is None:
        return None

    # 检查过期
    if token_obj.expires_at and token_obj.expires_at < datetime.now(tz=UTC):
        return None

    # 更新最后使用时间
    token_obj.last_used_at = datetime.now(tz=UTC)
    await db.commit()

    # 查找关联用户
    user_result = await db.execute(select(User).where(User.id == token_obj.user_id))
    return user_result.scalar_one_or_none()
