"""SQLAlchemy async engine and session factory."""

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from server.config import settings

engine = create_async_engine(
    settings.database_url,
    echo=False,
    # SQLite requires check_same_thread=False
    connect_args={"check_same_thread": False} if settings.database_url.startswith("sqlite") else {},
)

async_session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


class Base(DeclarativeBase):
    """Declarative base for all ORM models."""


async def create_all_tables() -> None:
    """Create all tables defined by Base subclasses."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
