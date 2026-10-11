"""带 trace_id 透传的结构化 JSON 日志。

代码库中禁止使用 ``print``，一律使用 ``get_logger``。
内置自包含的 JSON formatter（无第三方依赖），保证 Windows 下可安全启动。
"""

from __future__ import annotations

import json
import logging
import sys
from contextvars import ContextVar
from datetime import datetime, timezone
from typing import Any

# 由 TraceIdMiddleware 在每个请求中写入。
trace_id_ctx: ContextVar[str] = ContextVar("trace_id", default="-")


def get_trace_id() -> str:
    """返回当前异步上下文的 trace id。"""
    return trace_id_ctx.get()


def set_trace_id(value: str) -> None:
    """将 trace id 绑定到当前异步上下文。"""
    trace_id_ctx.set(value)


class TraceIdFilter(logging.Filter):
    """将当前 trace_id 注入每条日志记录。"""

    def filter(self, record: logging.LogRecord) -> bool:
        record.trace_id = trace_id_ctx.get()  # type: ignore[attr-defined]
        return True


class JsonFormatter(logging.Formatter):
    """精简 JSON formatter：ts / level / logger / message / 额外字段。"""

    def format(self, record: logging.LogRecord) -> str:
        entry: dict[str, Any] = {
            "ts": datetime.now(timezone.utc).isoformat(timespec="milliseconds"),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "trace_id": getattr(record, "trace_id", "-"),
        }
        for key, value in record.__dict__.items():
            if key not in {
                "name",
                "msg",
                "args",
                "levelname",
                "levelno",
                "pathname",
                "filename",
                "module",
                "exc_info",
                "exc_text",
                "stack_info",
                "lineno",
                "funcName",
                "created",
                "msecs",
                "relativeCreated",
                "thread",
                "threadName",
                "processName",
                "process",
                "taskName",
                "trace_id",
                "message",
            }:
                entry[key] = value
        if record.exc_info:
            entry["exc_info"] = self.formatException(record.exc_info)
        return json.dumps(entry, ensure_ascii=False, default=str)


def configure_logging(level: int = logging.INFO) -> None:
    """一次性配置 root logger，以 JSON 格式输出到 stdout。"""
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JsonFormatter())
    handler.addFilter(TraceIdFilter())
    root = logging.getLogger()
    root.handlers = [handler]
    root.setLevel(level)


def get_logger(name: str) -> logging.Logger:
    """返回指定模块名对应的 logger。"""
    return logging.getLogger(name)
