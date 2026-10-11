"""全局异步 Redis 客户端（单例）。

用于跨请求状态（上传进度、限流计数器、JWT refresh 相关等）。
工作记忆与语义缓存目前仍使用各自的客户端。
"""

from __future__ import annotations

from redis.asyncio import Redis, from_url

from app.config import get_settings
from app.core.logger import get_logger

logger = get_logger(__name__)

_redis: Redis | None = None


def get_redis() -> Redis:
    """返回全局异步 Redis 客户端（首次调用时创建）。"""
    global _redis
    if _redis is None:
        _redis = from_url(get_settings().redis.url, decode_responses=True)
        logger.info("Global Redis client initialized")
    return _redis


async def close_redis() -> None:
    """关闭全局 Redis 客户端（应用关闭时调用）。"""
    global _redis
    if _redis is not None:
        await _redis.aclose()
        _redis = None
        logger.info("Global Redis client closed")


__all__ = ["close_redis", "get_redis"]
