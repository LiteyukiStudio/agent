"""Application configuration loaded from environment variables."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

# Load .env from root_agent/.env if dotenv is available
_env_path = Path(__file__).resolve().parent.parent / "root_agent" / ".env"
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
    """Server settings resolved from environment variables."""

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


settings = Settings()
