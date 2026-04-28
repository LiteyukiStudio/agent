"""FastAPI application entry point."""

from __future__ import annotations

from contextlib import asynccontextmanager
from typing import TYPE_CHECKING

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

import server.models  # noqa: F401
from server.config import settings
from server.database import create_all_tables
from server.routers import admin, auth, chat

if TYPE_CHECKING:
    from collections.abc import AsyncGenerator


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncGenerator[None]:
    """Application lifespan: create database tables on startup."""
    await create_all_tables()
    yield


app = FastAPI(
    title="LiteYuki SRE Agent API",
    version="0.1.0",
    lifespan=lifespan,
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routers
app.include_router(auth.router)
app.include_router(chat.router)
app.include_router(admin.router)


@app.get("/api/v1/health")
async def health() -> dict[str, str]:
    """Health check endpoint."""
    return {"status": "ok"}


def cli() -> None:
    """CLI entry point for `uv run server`."""
    uvicorn.run("server.main:app", host="0.0.0.0", port=8000, reload=True)
