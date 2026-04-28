"""CLI entry points for uv run <command>."""

import subprocess
import sys


def dev() -> None:
    """Run the root agent interactively (adk run root_agent)."""
    sys.exit(subprocess.call(["adk", "run", "root_agent"]))


def web() -> None:
    """Run the root agent with web UI (adk web root_agent)."""
    sys.exit(subprocess.call(["adk", "web", "root_agent"]))


def lint() -> None:
    """Run ruff linter on the project."""
    sys.exit(subprocess.call(["ruff", "check", "."]))


def fmt() -> None:
    """Run ruff formatter on the project."""
    sys.exit(subprocess.call(["ruff", "format", "."]))


def fix() -> None:
    """Run ruff with auto-fix (lint + format)."""
    ret = subprocess.call(["ruff", "check", "--fix", "."])
    ret2 = subprocess.call(["ruff", "format", "."])
    sys.exit(ret or ret2)


def check() -> None:
    """Run all checks: lint + format check."""
    ret = subprocess.call(["ruff", "check", "."])
    ret2 = subprocess.call(["ruff", "format", "--check", "."])
    sys.exit(ret or ret2)
