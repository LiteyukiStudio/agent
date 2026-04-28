"""FastAPI 应用入口。"""

from __future__ import annotations

from contextlib import asynccontextmanager
from typing import TYPE_CHECKING

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

import server.models  # noqa: F401 — 确保所有模型被注册
from server.config import settings
from server.database import async_session_factory, create_all_tables
from server.routers import admin, auth, chat, usage, user_config
from server.services.auth import init_superuser
from server.services.usage import init_default_plan

if TYPE_CHECKING:
    from collections.abc import AsyncGenerator


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncGenerator[None]:
    """应用生命周期：启动时创建数据库表并初始化超级用户。"""
    await create_all_tables()
    # 首次启动自动创建初始超级用户和默认配额方案
    async with async_session_factory() as db:
        await init_superuser(db)
        await init_default_plan(db)
    yield


app = FastAPI(
    title="LiteYuki SRE Agent API",
    version="0.1.0",
    lifespan=lifespan,
)

# 跨域中间件
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 路由注册
app.include_router(auth.router)
app.include_router(chat.router)
app.include_router(admin.router)
app.include_router(usage.router)
app.include_router(user_config.router)


@app.get("/api/v1/health")
async def health() -> dict[str, str]:
    """健康检查端点。"""
    return {"status": "ok"}


def cli() -> None:
    """`uv run server` 的 CLI 入口点。"""
    uvicorn.run("server.main:app", host="0.0.0.0", port=8000, reload=True)
