"""本地 Agent WebSocket 连接管理：支持每用户多 Agent（按主机名区分）。"""

from __future__ import annotations

import asyncio
import contextlib
import json
import logging
from uuid import uuid4

from fastapi import APIRouter, Query, WebSocket, WebSocketDisconnect

from server.config import settings
from server.database import async_session_factory
from server.services.auth import resolve_api_token, verify_jwt

logger = logging.getLogger(__name__)

router = APIRouter(tags=["local-agent"])


# ---------------------------------------------------------------------------
# 连接池：user_id → {hostname → WebSocket}
# ---------------------------------------------------------------------------

_connections: dict[str, dict[str, WebSocket]] = {}
_pending: dict[str, dict[str, asyncio.Future[dict]]] = {}


async def _resolve_user_id(token: str) -> str | None:
    """从 JWT 或 API Token 解析 user_id。"""
    if token.startswith("lys_"):
        async with async_session_factory() as db:
            user = await resolve_api_token(db, token)
            return user.id if user else None
    payload = verify_jwt(token, settings.secret_key, settings.jwt_algorithm)
    if payload:
        return payload.get("sub")
    return None


def get_connected_hosts(user_id: str) -> list[str]:
    """获取用户所有已连接的主机名列表。"""
    return list(_connections.get(user_id, {}).keys())


def is_connected(user_id: str, hostname: str | None = None) -> bool:
    """检查用户的 local_agent 是否在线。hostname 为空则检查是否有任意连接。"""
    hosts = _connections.get(user_id, {})
    if hostname:
        return hostname in hosts
    return len(hosts) > 0


async def call_local_agent(
    user_id: str,
    tool: str,
    args: dict,
    hostname: str | None = None,
    timeout: float = 60.0,
) -> dict:
    """向用户的 local_agent 下发指令并等待结果。

    Args:
        user_id: 用户 ID。
        tool: 工具名。
        args: 工具参数。
        hostname: 目标主机名。None 则自动选第一个在线的。
        timeout: 超时秒数。

    Returns:
        {"result": "..."} 或 {"error": "..."}。
    """
    hosts = _connections.get(user_id, {})
    if not hosts:
        return {"error": "没有本地 Agent 在线。请在电脑上运行 liteyuki-agent 并连接。"}

    # 选择目标主机
    if hostname:
        ws = hosts.get(hostname)
        if not ws:
            available = ", ".join(hosts.keys())
            return {"error": f"主机 {hostname} 未连接。在线主机: {available}"}
    else:
        # 默认选第一个
        hostname = next(iter(hosts))
        ws = hosts[hostname]

    request_id = str(uuid4())
    request = {"id": request_id, "tool": tool, "args": args}

    # 创建 Future 等待响应
    if user_id not in _pending:
        _pending[user_id] = {}
    future: asyncio.Future[dict] = asyncio.get_event_loop().create_future()
    _pending[user_id][request_id] = future

    try:
        await ws.send_json(request)
        return await asyncio.wait_for(future, timeout=timeout)
    except TimeoutError:
        return {"error": f"本地 Agent ({hostname}) 执行超时（{timeout}s）"}
    except Exception as e:
        return {"error": f"通信失败 ({hostname}): {e}"}
    finally:
        _pending.get(user_id, {}).pop(request_id, None)


# ---------------------------------------------------------------------------
# WebSocket 端点
# ---------------------------------------------------------------------------


@router.websocket("/ws/local-agent")
async def local_agent_websocket(
    ws: WebSocket,
    token: str = Query(...),
    hostname: str = Query(default="default"),
) -> None:
    """本地 Agent 的 WebSocket 连接端点。

    每个用户可以注册多个 local_agent，通过 hostname 区分。
    支持 JWT 或 API Token（lys_ 前缀）认证。
    """
    user_id = await _resolve_user_id(token)
    if not user_id:
        await ws.close(code=4001, reason="Invalid token")
        return

    await ws.accept()
    logger.info("Local agent connected: user=%s host=%s", user_id, hostname)

    # 初始化用户的连接 dict
    if user_id not in _connections:
        _connections[user_id] = {}

    # 踢掉同一主机名的旧连接
    old_ws = _connections[user_id].get(hostname)
    if old_ws:
        with contextlib.suppress(Exception):
            await old_ws.close(code=4002, reason="New connection from same host")

    _connections[user_id][hostname] = ws

    try:
        while True:
            data = await ws.receive_text()
            try:
                response = json.loads(data)
                request_id = response.get("id")
                if request_id and user_id in _pending and request_id in _pending[user_id]:
                    _pending[user_id][request_id].set_result(response)
            except json.JSONDecodeError:
                pass
    except WebSocketDisconnect:
        logger.info("Local agent disconnected: user=%s host=%s", user_id, hostname)
    except Exception as e:
        logger.warning("Local agent error: user=%s host=%s err=%s", user_id, hostname, e)
    finally:
        if _connections.get(user_id, {}).get(hostname) is ws:
            _connections[user_id].pop(hostname, None)
            if not _connections[user_id]:
                del _connections[user_id]
        # Cancel pending futures
        for future in _pending.pop(user_id, {}).values():
            if not future.done():
                future.cancel()


# ---------------------------------------------------------------------------
# REST 端点
# ---------------------------------------------------------------------------


@router.get("/api/v1/local-agent/status")
async def local_agent_status(
    token: str = Query(...),
) -> dict:
    """检查当前用户的 local_agent 连接状态。"""
    user_id = await _resolve_user_id(token)
    if not user_id:
        return {"connected": False, "hosts": [], "error": "Invalid token"}
    hosts = get_connected_hosts(user_id)
    return {"connected": len(hosts) > 0, "hosts": hosts}
