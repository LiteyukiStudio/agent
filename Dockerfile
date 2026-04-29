# ---- 后端 Dockerfile ----
FROM python:3.13-slim AS base

# 安装 uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

WORKDIR /app

# 复制依赖声明（利用缓存层）
COPY pyproject.toml uv.lock README.md ./

# 安装依赖（不安装项目本身，只装依赖）
RUN uv sync --no-install-project --frozen

# 复制项目代码
COPY model_config.py credential_provider.py alembic.ini ./
COPY alembic/ ./alembic/
COPY root_agent/ ./root_agent/
COPY server/ ./server/

# 安装项目
RUN uv sync --frozen

EXPOSE 8000

# 启动后端
CMD ["uv", "run", "uvicorn", "server.main:app", "--host", "0.0.0.0", "--port", "8000"]
