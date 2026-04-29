"""本地 Agent WebSocket 连接管理：支持每用户多设备（按 device_id 区分）。"""

from __future__ import annotations

import asyncio
import contextlib
import json
import logging
from typing import TYPE_CHECKING
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, Query, WebSocket, WebSocketDisconnect

from server.config import settings
from server.database import async_session_factory
from server.deps import get_current_user, get_db
from server.services.auth import resolve_api_token, verify_jwt

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

    from server.models.user import User

logger = logging.getLogger(__name__)

router = APIRouter(tags=["local-agent"])


# ---------------------------------------------------------------------------
# 设备信息
# ---------------------------------------------------------------------------


class DeviceInfo:
    """一个已连接的设备。"""

    def __init__(self, device_id: str, device_name: str, ws: WebSocket, token_id: str = "") -> None:
        self.device_id = device_id
        self.device_name = device_name
        self.ws = ws
        self.token_id = token_id  # 关联的 API Token ID，用于联动删除


# ---------------------------------------------------------------------------
# 连接池：user_id → {device_id → DeviceInfo}
# ---------------------------------------------------------------------------

_connections: dict[str, dict[str, DeviceInfo]] = {}
_pending: dict[str, dict[str, asyncio.Future[dict]]] = {}


async def _resolve_user_id(token: str) -> tuple[str | None, str]:
    """从 JWT 或 API Token 解析 (user_id, token_id)。

    Returns:
        (user_id, token_id)。JWT 认证时 token_id 为空字符串。
    """
    if token.startswith("lys_"):
        async with async_session_factory() as db:
            from sqlalchemy import select as sa_select

            from server.models.api_token import ApiToken
            from server.services.auth import hash_api_token

            token_hashed = hash_api_token(token)
            result = await db.execute(
                sa_select(ApiToken).where(ApiToken.token_hash == token_hashed),
            )
            token_obj = result.scalar_one_or_none()
            if not token_obj:
                return (None, "")
            user = await resolve_api_token(db, token)
            return (user.id if user else None, token_obj.id)
    payload = verify_jwt(token, settings.secret_key, settings.jwt_algorithm)
    if payload:
        return (payload.get("sub"), "")
    return (None, "")


def get_connected_devices(user_id: str) -> list[dict]:
    """获取用户所有已连接设备的信息。"""
    devices = _connections.get(user_id, {})
    return [{"device_id": d.device_id, "device_name": d.device_name, "token_id": d.token_id} for d in devices.values()]


async def disconnect_by_token(user_id: str, token_id: str) -> int:
    """踢掉使用指定 token 连接的所有设备。返回踢掉的数量。"""
    devices = _connections.get(user_id, {})
    to_kick = [d for d in devices.values() if d.token_id == token_id]
    for d in to_kick:
        with contextlib.suppress(Exception):
            await d.ws.close(code=4003, reason="Token revoked")
        devices.pop(d.device_id, None)
    if not devices and user_id in _connections:
        del _connections[user_id]
    return len(to_kick)


def is_connected(user_id: str, device_id: str | None = None) -> bool:
    """检查用户的设备是否在线。"""
    devices = _connections.get(user_id, {})
    if device_id:
        return device_id in devices
    return len(devices) > 0


async def call_local_agent(
    user_id: str,
    tool: str,
    args: dict,
    device_id: str | None = None,
    timeout: float = 60.0,
) -> dict:
    """向用户的 local_agent 下发指令并等待结果。

    Args:
        user_id: 用户 ID。
        tool: 工具名。
        args: 工具参数。
        device_id: 目标设备 ID。None 则自动选第一个在线的。
        timeout: 超时秒数。

    Returns:
        {"result": "..."} 或 {"error": "..."}。
    """
    devices = _connections.get(user_id, {})
    if not devices:
        return {"error": "没有本地 Agent 在线。请在电脑上运行 liteyuki-agent 并连接。"}

    if device_id:
        device = devices.get(device_id)
        if not device:
            names = ", ".join(f"{d.device_name}({d.device_id[:8]})" for d in devices.values())
            return {"error": f"设备 {device_id[:8]} 未连接。在线设备: {names}"}
    else:
        device = next(iter(devices.values()))

    request_id = str(uuid4())
    request = {"id": request_id, "tool": tool, "args": args}

    if user_id not in _pending:
        _pending[user_id] = {}
    future: asyncio.Future[dict] = asyncio.get_event_loop().create_future()
    _pending[user_id][request_id] = future

    try:
        await device.ws.send_json(request)
        return await asyncio.wait_for(future, timeout=timeout)
    except TimeoutError:
        return {"error": f"本地 Agent ({device.device_name}) 执行超时（{timeout}s）"}
    except Exception as e:
        return {"error": f"通信失败 ({device.device_name}): {e}"}
    finally:
        _pending.get(user_id, {}).pop(request_id, None)


# ---------------------------------------------------------------------------
# WebSocket 端点
# ---------------------------------------------------------------------------


@router.websocket("/ws/local-agent")
async def local_agent_websocket(
    ws: WebSocket,
    token: str = Query(...),
    device_id: str = Query(default=""),
    device_name: str = Query(default="unknown"),
) -> None:
    """本地 Agent 的 WebSocket 连接端点。

    每个设备通过唯一的 device_id 标识，device_name 用于展示。
    支持 JWT 或 API Token 认证。
    """
    user_id, token_id = await _resolve_user_id(token)
    if not user_id:
        await ws.close(code=4001, reason="Invalid token")
        return

    if not device_id:
        device_id = str(uuid4())

    await ws.accept()
    logger.info("Local agent connected: user=%s device=%s (%s)", user_id, device_name, device_id[:8])

    # 持久化设备信息到数据库（upsert）
    async with async_session_factory() as db:
        from sqlalchemy import select as sa_select

        from server.models.device import Device

        result = await db.execute(sa_select(Device).where(Device.device_id == device_id))
        dev = result.scalar_one_or_none()
        if dev:
            dev.device_name = device_name
            dev.token_id = token_id or dev.token_id
            dev.last_seen_at = __import__("datetime").datetime.now(__import__("datetime").UTC)
        else:
            dev = Device(
                user_id=user_id,
                device_id=device_id,
                device_name=device_name,
                token_id=token_id or None,
            )
            db.add(dev)
        await db.commit()

    if user_id not in _connections:
        _connections[user_id] = {}

    # 踢掉同一 device_id 的旧连接
    old = _connections[user_id].get(device_id)
    if old:
        with contextlib.suppress(Exception):
            await old.ws.close(code=4002, reason="New connection from same device")

    _connections[user_id][device_id] = DeviceInfo(device_id, device_name, ws, token_id)

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
        logger.info("Local agent disconnected: user=%s device=%s", user_id, device_id[:8])
    except Exception as e:
        logger.warning("Local agent error: user=%s device=%s err=%s", user_id, device_id[:8], e)
    finally:
        if _connections.get(user_id, {}).get(device_id) and _connections[user_id][device_id].ws is ws:
            del _connections[user_id][device_id]
            if not _connections[user_id]:
                del _connections[user_id]
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
    """检查当前用户的 local_agent 连接状态（CLI 用，token 传参）。"""
    user_id, _ = await _resolve_user_id(token)
    if not user_id:
        return {"connected": False, "devices": [], "error": "Invalid token"}
    devices = get_connected_devices(user_id)
    return {"connected": len(devices) > 0, "devices": devices}


@router.get("/api/v1/local-agent/devices")
async def list_devices(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """列出当前用户所有设备（含在线/离线状态）。"""
    from sqlalchemy import select as sa_select

    from server.models.device import Device

    result = await db.execute(
        sa_select(Device).where(Device.user_id == user.id).order_by(Device.created_at.desc()),
    )
    all_devices = result.scalars().all()
    online_ids = set(_connections.get(user.id, {}).keys())

    devices = [
        {
            "id": d.id,
            "device_id": d.device_id,
            "device_name": d.device_name,
            "online": d.device_id in online_ids,
            "last_seen_at": d.last_seen_at.isoformat() if d.last_seen_at else None,
            "created_at": d.created_at.isoformat() if d.created_at else None,
        }
        for d in all_devices
    ]
    return {"devices": devices, "count": len(devices)}


@router.delete("/api/v1/local-agent/devices/{device_id}", status_code=204)
async def remove_device(
    device_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> None:
    """删除设备：断开连接 + 吊销 Token + 从数据库移除。"""
    from sqlalchemy import select as sa_select

    from server.models.device import Device

    # 从数据库查找
    result = await db.execute(
        sa_select(Device).where(Device.device_id == device_id, Device.user_id == user.id),
    )
    dev = result.scalar_one_or_none()
    if not dev:
        raise HTTPException(status_code=404, detail="Device not found")

    # 踢掉在线连接
    online_device = _connections.get(user.id, {}).get(device_id)
    if online_device:
        with contextlib.suppress(Exception):
            await online_device.ws.close(code=4003, reason="Device removed")
        _connections.get(user.id, {}).pop(device_id, None)

    # 删除关联 token
    if dev.token_id:
        from server.services.auth import delete_api_token

        await delete_api_token(db, user.id, dev.token_id)

    # 从数据库删除设备记录
    await db.delete(dev)
    await db.commit()
