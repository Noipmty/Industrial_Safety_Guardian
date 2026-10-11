"""FastAPI 应用入口。"""

from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, PlainTextResponse

from app.api.v1.admin import router as admin_router
from app.api.v1.auth import router as auth_router
from app.api.v1.chat import router as chat_router
from app.api.v1.documents import router as documents_router
from app.api.v1.exam import router as exam_router
from app.api.v1.faq import router as faq_router
from app.api.v1.graph import router as graph_router
from app.api.v1.health import router as health_router
from app.config import get_settings
from app.core.exceptions import AppError
from app.core.logger import configure_logging, get_logger, get_trace_id
from app.core.metrics import render_metrics
from app.core.metrics_middleware import install_metrics_middleware
from app.core.observability import install_trace_middleware
from app.core.redis import close_redis
from app.services.indexing.embedding import get_embedding_service

logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """应用启动 / 关闭钩子。"""
    settings = get_settings()
    configure_logging()
    logger.info(
        "Starting %s v%s (env=%s)",
        settings.app_name,
        settings.app_version,
        settings.env,
    )
    # 在服务请求前先在工作线程中预热 BGE-M3：若在请求处理中途才懒加载
    # torch 模型，uvicorn 下会导致进程崩溃（0xC0000005），而在启动阶段
    # 的同一上下文中预热则是稳定的。
    try:
        await asyncio.to_thread(
            get_embedding_service().encode_dense, ["模型预热"]
        )
        logger.info("BGE-M3 preloaded")
    except Exception:  # noqa: BLE001 — 预热失败不得阻塞启动
        logger.warning("BGE-M3 preload failed; will lazy-load on demand", exc_info=True)
    yield
    logger.info("Shutting down %s", settings.app_name)
    await close_redis()


def create_app() -> FastAPI:
    """应用工厂。"""
    settings = get_settings()
    app = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        lifespan=lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors.origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
        allow_private_network=True,
    )
    install_trace_middleware(app)
    install_metrics_middleware(app)

    @app.get("/metrics", include_in_schema=False)
    async def metrics() -> PlainTextResponse:
        """Prometheus 指标暴露端点。"""
        return PlainTextResponse(
            render_metrics(),
            media_type="text/plain; version=0.0.4; charset=utf-8",
        )

    @app.exception_handler(AppError)
    async def app_error_handler(request: Request, exc: AppError) -> JSONResponse:
        """将领域错误映射为结构化 JSON 响应。"""
        logger.warning("AppError code=%s: %s", exc.code, exc.message)
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "code": exc.code,
                "message": exc.message,
                "trace_id": get_trace_id(),
            },
        )

    @app.exception_handler(Exception)
    async def unhandled_error_handler(request: Request, exc: Exception) -> JSONResponse:
        """兜底异常处理器 — 绝不向客户端泄露堆栈信息。"""
        logger.exception("Unhandled exception")
        return JSONResponse(
            status_code=500,
            content={
                "code": "INTERNAL_ERROR",
                "message": "Internal server error",
                "trace_id": get_trace_id(),
            },
        )

    app.include_router(auth_router, prefix="/api/v1")
    app.include_router(admin_router, prefix="/api/v1")
    app.include_router(chat_router, prefix="/api/v1")
    app.include_router(documents_router, prefix="/api/v1")
    app.include_router(exam_router, prefix="/api/v1")
    app.include_router(faq_router, prefix="/api/v1")
    app.include_router(graph_router, prefix="/api/v1")
    app.include_router(health_router, prefix="/api/v1")

    # /health 不带版本前缀，供容器探针使用。
    app.include_router(health_router)

    return app


app = create_app()
