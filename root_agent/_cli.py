"""uv run <command> 的 CLI 入口点。"""

import subprocess
import sys


def dev() -> None:
    """以交互模式启动 root agent（adk run root_agent）。"""
    sys.exit(subprocess.call(["adk", "run", "root_agent"]))


def web() -> None:
    """以 Web UI 模式启动 root agent（adk web root_agent）。"""
    sys.exit(subprocess.call(["adk", "web", "root_agent"]))


def lint() -> None:
    """运行 Ruff 代码检查。"""
    sys.exit(subprocess.call(["ruff", "check", "."]))


def fmt() -> None:
    """运行 Ruff 代码格式化。"""
    sys.exit(subprocess.call(["ruff", "format", "."]))


def fix() -> None:
    """自动修复 lint 问题并格式化。"""
    ret = subprocess.call(["ruff", "check", "--fix", "."])
    ret2 = subprocess.call(["ruff", "format", "."])
    sys.exit(ret or ret2)


def check() -> None:
    """运行所有检查：lint + 格式检查（不修改文件）。"""
    ret = subprocess.call(["ruff", "check", "."])
    ret2 = subprocess.call(["ruff", "format", "--check", "."])
    sys.exit(ret or ret2)


def server() -> None:
    """启动 FastAPI 后端服务器（开发模式，代码和 .env 变更自动重载）。"""
    sys.exit(
        subprocess.call(
            [
                "uvicorn",
                "server.main:app",
                "--reload",
                "--reload-include",
                "*.env",
                "--port",
                "8000",
            ]
        )
    )
