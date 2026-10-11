"""Gunicorn 配置（通过 ``-c gunicorn_conf.py`` 加载）。

针对 FastAPI + 异步 SQLAlchemy + BGE-M3 预加载调优：
- 4 个 worker（按 CPU 核数横向扩展；可通过 ``GUNICORN_WORKERS`` 环境变量调整）
- UvicornWorker（每个 worker 独立异步事件循环）
- 120 秒超时（足够覆盖 RAG 检索与考试判分）
- 预加载应用以在多个 worker 间共享 BGE-M3 模型（节省约 2GB 内存）
"""

from __future__ import annotations

import multiprocessing
import os

# Gunicorn 会将这些读取为模块级全局变量。
bind = os.environ.get("GUNICORN_BIND", "0.0.0.0:8000")
workers = int(os.environ.get("GUNICORN_WORKERS", multiprocessing.cpu_count() * 2 + 1))
worker_class = "uvicorn.workers.UvicornWorker"
timeout = int(os.environ.get("GUNICORN_TIMEOUT", 120))
keepalive = int(os.environ.get("GUNICORN_KEEPALIVE", 5))
preload_app = True
accesslog = "-"
errorlog = "-"
loglevel = os.environ.get("GUNICORN_LOG_LEVEL", "info")
graceful_timeout = int(os.environ.get("GUNICORN_GRACEFUL_TIMEOUT", 30))
max_requests = int(os.environ.get("GUNICORN_MAX_REQUESTS", 1000))
max_requests_jitter = int(os.environ.get("GUNICORN_MAX_REQUESTS_JITTER", 50))
