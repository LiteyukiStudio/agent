"""SQLAlchemy 异步引擎和会话工厂。"""

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from server.config import settings

engine = create_async_engine(
    settings.database_url,
    echo=False,
    # SQLite 需要 check_same_thread=False
    connect_args={"check_same_thread": False} if settings.database_url.startswith("sqlite") else {},
)

async_session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


class Base(DeclarativeBase):
    """所有 ORM 模型的声明式基类。"""


async def create_all_tables() -> None:
    """创建 Base 子类定义的所有数据库表。"""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
