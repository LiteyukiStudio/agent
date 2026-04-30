"""FastAPI 应用入口。"""

from __future__ import annotations

import logging
import sys
from contextlib import asynccontextmanager
from typing import TYPE_CHECKING

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

import server.models  # noqa: F401 — 确保所有模型被注册
from server.config import settings
from server.database import async_session_factory
from server.routers import admin, auth, chat, device_auth, local_agent, usage, user_config
from server.services.auth import init_superuser
from server.services.usage import init_default_plan

if TYPE_CHECKING:
    from collections.abc import AsyncGenerator

# ---------------------------------------------------------------------------
# 日志配置：确保应用日志输出到 stdout，即使在 uvicorn --reload 模式下
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    stream=sys.stdout,
    force=True,  # 强制覆盖 uvicorn 预设的 handler
)
# 降低第三方库的日志级别，避免刷屏
logging.getLogger("httpcore").setLevel(logging.WARNING)
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("hpack").setLevel(logging.WARNING)

logger = logging.getLogger(__name__)


def _run_alembic_upgrade() -> None:
    """同步执行 Alembic 数据库迁移到最新版本。"""
    from pathlib import Path

    from alembic import command
    from alembic.config import Config

    # 确保 SQLite data 目录存在
    db_url = settings.database_url
    if "sqlite" in db_url:
        db_path = db_url.split("///")[-1]
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)

    try:
        alembic_cfg = Config("alembic.ini")
        command.upgrade(alembic_cfg, "head")
        logger.info("Database migration completed (alembic upgrade head)")
    except Exception:
        logger.exception("Database migration FAILED")
        raise


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncGenerator[None]:
    """应用生命周期：启动时执行数据库迁移并初始化超级用户。"""
    # 自动迁移数据库到最新 schema
    _run_alembic_upgrade()
    # 首次启动自动创建初始超级用户和默认配额方案
    async with async_session_factory() as db:
        await init_superuser(db)
        await init_default_plan(db)
    yield


app = FastAPI(
    title="Liteyuki Flow Agent API",
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
app.include_router(local_agent.router)
app.include_router(device_auth.router)


@app.get("/api/v1/health")
async def health() -> dict[str, str]:
    """健康检查端点。"""
    return {"status": "ok"}


def cli() -> None:
    """`uv run server` 的 CLI 入口点。"""
    # 开发环境仍用 uvicorn（支持 reload），生产用 hypercorn
    uvicorn.run(
        "server.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        reload_includes=["*.env"],
        log_level="info",
    )
