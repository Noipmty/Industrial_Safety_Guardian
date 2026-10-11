"""trace id 中间件：在请求链路中生成 / 透传 X-Trace-Id。"""

from __future__ import annotations

import uuid

from fastapi import FastAPI, Request, Response
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint

from app.core.logger import get_trace_id, set_trace_id

TRACE_HEADER = "X-Trace-Id"


class TraceIdMiddleware(BaseHTTPMiddleware):
    """确保每个请求（及其中的每条日志）都有 trace id。"""

    async def dispatch(
        self,
        request: Request,
        call_next: RequestResponseEndpoint,
    ) -> Response:
        incoming = request.headers.get(TRACE_HEADER)
        trace_id = incoming if incoming else uuid.uuid4().hex
        set_trace_id(trace_id)
        response = await call_next(request)
        response.headers[TRACE_HEADER] = trace_id
        return response


def install_trace_middleware(app: FastAPI) -> None:
    """在 FastAPI 应用上注册 trace 中间件。"""
    app.add_middleware(TraceIdMiddleware)


__all__ = ["TRACE_HEADER", "TraceIdMiddleware", "install_trace_middleware", "get_trace_id"]
