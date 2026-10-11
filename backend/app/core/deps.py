"""异步 SQLAlchemy engine/session 工厂与 FastAPI 依赖项。"""

from __future__ import annotations

from collections.abc import AsyncGenerator
from typing import Annotated, Any

from fastapi import Depends, Header
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.config import get_settings
from app.core.exceptions import AuthError, PermissionError_
from app.core.logger import get_logger
from app.core.redis import get_redis
from app.core.security import decode_token

logger = get_logger(__name__)

_engine: AsyncEngine | None = None
_session_factory: async_sessionmaker[AsyncSession] | None = None


def get_engine() -> AsyncEngine:
    """创建（仅一次）并返回全局异步 engine。"""
    global _engine, _session_factory
    if _engine is None:
        settings = get_settings()
        _engine = create_async_engine(
            settings.mysql.url,
            pool_pre_ping=True,
            pool_size=10,
            max_overflow=20,
            echo=False,
        )
        _session_factory = async_sessionmaker(_engine, expire_on_commit=False)
        logger.info("Async database engine initialized")
    return _engine


def get_session_factory() -> async_sessionmaker[AsyncSession]:
    """返回全局 session 工厂（必要时先初始化 engine）。"""
    get_engine()
    assert _session_factory is not None
    return _session_factory


async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """为每个请求提供一个作用域内的数据库 session。"""
    factory = get_session_factory()
    async with factory() as session:
        yield session


DbSession = Annotated[AsyncSession, Depends(get_db_session)]


async def get_current_user(
    authorization: Annotated[str | None, Header(alias="Authorization")] = None,
) -> dict[str, Any]:
    """解析 Bearer JWT 并返回用户 claims。

    示例：``{"sub": "1", "position": "司钻", "role": "worker", "jti": "..."}``

    若 token 的 ``jti`` 已在 Redis 黑名单中（轮换后）则拒绝该 token。
    """
    if not authorization or not authorization.startswith("Bearer "):
        raise AuthError("Missing bearer token")
    token = authorization.removeprefix("Bearer ").strip()
    settings = get_settings()
    payload = decode_token(
        token,
        secret=settings.jwt.secret,
        algorithm=settings.jwt.algorithm,
    )
    jti = payload.get("jti")
    if jti:
        redis = get_redis()
        if await redis.exists(f"jwt:blacklist:{jti}"):
            raise AuthError("Token has been rotated")
    return {
        "user_id": int(payload["sub"]),
        "position": payload.get("position", ""),
        "role": payload.get("role", "worker"),
        "jti": jti,
    }


CurrentUser = Annotated[dict[str, Any], Depends(get_current_user)]


async def require_admin(user: CurrentUser) -> dict[str, Any]:
    """仅允许管理员通过的依赖项。"""
    if user.get("role") != "admin":
        raise PermissionError_("Admin role required")
    return user


AdminUser = Annotated[dict[str, Any], Depends(require_admin)]
