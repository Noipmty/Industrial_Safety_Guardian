"""Pytest 配置与共享 fixture。"""

from __future__ import annotations

import asyncio
from collections.abc import AsyncGenerator

import fakeredis.aioredis
import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.pool import StaticPool

import app.core.deps as deps_mod
import app.core.redis as redis_mod

TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"

engine = create_async_engine(
    TEST_DATABASE_URL,
    poolclass=StaticPool,
    connect_args={"check_same_thread": False},
)
TestingSessionLocal = async_sessionmaker(
    engine, class_=AsyncSession, expire_on_commit=False
)

# 所有测试共享的 fakeredis 客户端（jti 黑名单、上传进度等）。
_fake_redis = fakeredis.aioredis.FakeRedis(decode_responses=True)


@pytest.fixture(scope="session")
def event_loop() -> asyncio.AbstractEventLoop:
    """为测试会话强制使用全新的事件循环。"""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(autouse=True)
def _stub_redis(monkeypatch) -> None:
    """用共享的 fakeredis 实例替换全局 Redis 客户端。

    确保 ``get_current_user`` 的 jti 黑名单检查和管理端上传进度
    在测试期间不会尝试连接真实 Redis。
    """
    monkeypatch.setattr(redis_mod, "_redis", _fake_redis)
    monkeypatch.setattr(deps_mod, "get_redis", lambda: _fake_redis)


@pytest_asyncio.fixture(scope="function")
async def db_session() -> AsyncGenerator[AsyncSession, None]:
    """提供用于数据库 mock 的异步 SQLite 内存会话。"""
    async with TestingSessionLocal() as session:
        yield session
        await session.rollback()


@pytest_asyncio.fixture(scope="function")
async def async_client() -> AsyncGenerator[AsyncClient, None]:
    """提供连接到 FastAPI ASGI 应用的异步 HTTP 客户端。"""
    from app.main import app

    transport = ASGITransport(app=app)
    async with AsyncClient(
        transport=transport, base_url="http://testserver"
    ) as client:
        yield client
