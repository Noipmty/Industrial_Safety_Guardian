"""健康检查与就绪探针接口。"""

from __future__ import annotations

from fastapi import APIRouter
from redis.asyncio import Redis
from sqlalchemy import text

from app.config import get_settings
from app.core.deps import get_engine
from app.schemas.health import HealthResponse

router = APIRouter(tags=["health"])


@router.get("/health", response_model=HealthResponse)
async def health() -> HealthResponse:
    """存活探针 — 始终轻量，不调用下游。"""
    settings = get_settings()
    return HealthResponse(status="ok", version=settings.app_version, checks={})


@router.get("/health/ready", response_model=HealthResponse)
async def readiness() -> HealthResponse:
    """就绪探针 — 检查 MySQL 与 Redis 连通性。"""
    settings = get_settings()
    checks: dict[str, str] = {}

    try:
        engine = get_engine()
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        checks["mysql"] = "up"
    except Exception:
        checks["mysql"] = "down"

    try:
        redis = Redis.from_url(settings.redis.url, socket_timeout=2.0)
        await redis.ping()
        await redis.aclose()
        checks["redis"] = "up"
    except Exception:
        checks["redis"] = "down"

    all_up = all(v == "up" for v in checks.values())
    return HealthResponse(
        status="ok" if all_up else "degraded",
        version=settings.app_version,
        checks=checks,
    )
