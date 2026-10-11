"""健康检查端点测试。"""

import pytest
from httpx import ASGITransport, AsyncClient


@pytest.mark.asyncio
async def test_health_returns_ok() -> None:
    """GET /health 返回 200 且 status 为 ok。"""
    from app.main import app

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ok"


@pytest.mark.asyncio
async def test_health_has_version() -> None:
    """健康检查响应包含 version 字段。"""
    from app.main import app

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/health")
    assert resp.status_code == 200
    data = resp.json()
    assert "version" in data
    assert data["version"] == "0.1.0"


@pytest.mark.asyncio
async def test_trace_id_propagation() -> None:
    """X-Trace-Id 请求头应原样回显到响应。"""
    from app.main import app

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/health", headers={"X-Trace-Id": "test-trace-123"})
    assert resp.status_code == 200
    assert resp.headers.get("X-Trace-Id") == "test-trace-123"


@pytest.mark.asyncio
async def test_trace_id_auto_generated() -> None:
    """请求未携带 X-Trace-Id 时，响应应自动生成一个。"""
    from app.main import app

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/health")
    assert resp.status_code == 200
    trace_id = resp.headers.get("X-Trace-Id")
    assert trace_id is not None
    assert len(trace_id) > 0
