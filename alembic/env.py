"""Alembic 迁移环境配置。

从项目的 server.config 和 server.database 读取配置，
支持 async SQLAlchemy（SQLite + PostgreSQL）。
"""

from __future__ import annotations

from logging.config import fileConfig
from typing import Any

from sqlalchemy import pool

# 导入所有模型（确保 Base.metadata 包含全部表）
import server.models  # noqa: F401
from alembic import context

# 加载项目配置（触发 .env 读取）
from server.config import settings
from server.database import Base

# Alembic Config 对象
config = context.config

# 日志配置
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# 设置 SQLAlchemy URL（从项目配置获取，转为同步驱动用于 autogenerate）
db_url = settings.database_url
# Alembic 的 autogenerate 需要同步驱动
sync_url = db_url.replace("+aiosqlite", "").replace("+asyncpg", "+psycopg2") if "+" in db_url else db_url

config.set_main_option("sqlalchemy.url", sync_url)

# 目标 metadata
target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """以 'offline' 模式运行迁移——只生成 SQL，不连接数据库。"""
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        include_object=_include_object,
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """以 'online' 模式运行迁移——连接数据库并执行。"""
    from sqlalchemy import create_engine

    connectable = create_engine(sync_url, poolclass=pool.NullPool)

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            include_object=_include_object,
        )
        with context.begin_transaction():
            context.run_migrations()


# ADK 内部表，autogenerate 时忽略
_ADK_TABLES = {"sessions", "events", "app_states", "user_states", "adk_internal_metadata"}


def _include_object(
    object: Any,  # noqa: A002
    name: str | None,
    type_: str,
    reflected: bool,
    compare_to: Any,
) -> bool:
    """排除 ADK 自动创建的内部表。"""
    return not (type_ == "table" and name in _ADK_TABLES)


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
