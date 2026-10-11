"""Prometheus 指标注册表。

暴露：
- ``http_requests_total``：Counter（method、path、status）
- ``http_request_duration_seconds``：Histogram（method、path）
- ``http_requests_in_progress``：Gauge（method）

使用 ``prometheus_client.generate_latest()`` 供 ``/metrics`` 抓取。
"""

from __future__ import annotations

from prometheus_client import Counter, Gauge, Histogram, generate_latest

http_requests_total = Counter(
    "gongan_http_requests_total",
    "Total HTTP requests by method/path/status",
    labelnames=("method", "path", "status"),
)

http_request_duration_seconds = Histogram(
    "gongan_http_request_duration_seconds",
    "Request latency in seconds",
    labelnames=("method", "path"),
    buckets=(0.05, 0.1, 0.25, 0.5, 1, 2.5, 5, 10, 30),
)

http_requests_in_progress = Gauge(
    "gongan_http_requests_in_progress",
    "In-flight HTTP requests",
    labelnames=("method",),
)


def render_metrics() -> bytes:
    """返回 Prometheus 暴露格式（text/plain，0.0.4）。"""
    return generate_latest()


__all__ = [
    "http_requests_in_progress",
    "http_requests_total",
    "http_request_duration_seconds",
    "render_metrics",
]
