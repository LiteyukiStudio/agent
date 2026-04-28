"""应用配置，从环境变量加载。"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

# 加载项目根目录 .env（开发环境用，容器化部署直接注入环境变量）
_env_path = Path(__file__).resolve().parent.parent / ".env"
if _env_path.exists():
    for line in _env_path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        key, _, value = line.partition("=")
        key, value = key.strip(), value.strip()
        if key and key not in os.environ:
            os.environ[key] = value


@dataclass
class Settings:
    """从环境变量解析的服务器配置。"""

    database_url: str = field(
        default_factory=lambda: os.getenv("DATABASE_URL", "sqlite+aiosqlite:///./data.db"),
    )
    secret_key: str = field(
        default_factory=lambda: os.getenv("SECRET_KEY", "change-me-to-a-random-string"),
    )
    server_host: str = field(
        default_factory=lambda: os.getenv("SERVER_HOST", "http://localhost:8000"),
    )
    cors_origins: list[str] = field(
        default_factory=lambda: os.getenv("CORS_ORIGINS", "http://localhost:5173").split(","),
    )
    jwt_algorithm: str = "HS256"
    jwt_expire_hours: int = 24

    # 初始超级用户账号（首次启动自动创建）
    initial_username: str = field(
        default_factory=lambda: os.getenv("INITIAL_USERNAME", "admin"),
    )
    initial_password: str = field(
        default_factory=lambda: os.getenv("INITIAL_PASSWORD", "admin"),
    )


settings = Settings()
