"""Prometheus 指标中间件。

为每个请求记录 Counter（总数）、Histogram（延迟）和 Gauge（进行中）。
跳过 ``/metrics`` 端点以避免自我抓取死循环。
"""

from __future__ import annotations

import time

from fastapi import FastAPI, Request, Response
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint

from app.core.metrics import (
    http_request_duration_seconds,
    http_requests_in_progress,
    http_requests_total,
)

_SKIP_PATHS = {"/metrics", "/health"}


class MetricsMiddleware(BaseHTTPMiddleware):
    """记录 http_requests_total / duration / in_progress。"""

    async def dispatch(
        self,
        request: Request,
        call_next: RequestResponseEndpoint,
    ) -> Response:
        path = request.url.path
        if path in _SKIP_PATHS:
            return await call_next(request)

        method = request.method
        http_requests_in_progress.labels(method=method).inc()
        start = time.perf_counter()
        try:
            response = await call_next(request)
            status = str(response.status_code)
            return response
        except Exception:
            status = "500"
            raise
        finally:
            elapsed = time.perf_counter() - start
            http_requests_total.labels(method=method, path=path, status=status).inc()
            http_request_duration_seconds.labels(method=method, path=path).observe(
                elapsed
            )
            http_requests_in_progress.labels(method=method).dec()


def install_metrics_middleware(app: FastAPI) -> None:
    """在 FastAPI 应用上注册指标中间件。"""
    app.add_middleware(MetricsMiddleware)


__all__ = ["MetricsMiddleware", "install_metrics_middleware"]
