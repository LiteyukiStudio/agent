# ---- 后端 Dockerfile ----
ARG BASE_PYTHON=python:3.13-slim
ARG BASE_UV=ghcr.io/astral-sh/uv:latest

FROM ${BASE_UV} AS uv
FROM ${BASE_PYTHON} AS base

# 安装 uv
COPY --from=uv /uv /usr/local/bin/uv

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

# 启动后端（Hypercorn ASGI server）
CMD ["uv", "run", "hypercorn", "server.main:app", "--bind", "0.0.0.0:8000", "--access-log", "-"]
