"""Chat API 契约测试（fake graph，不依赖真实服务）。"""

from __future__ import annotations

import time
from types import SimpleNamespace

import fakeredis.aioredis
import pytest

import app.api.v1.chat as chat_mod
from app.config import get_settings
from app.core.security import create_access_token
from app.services.memory.working_memory import WorkingMemory

FAKE_RESULT = {
    "session_id": "api-test-session",
    "user_id": 7,
    "raw_query": "动火作业审批流程是什么？",
    "query_type": "structural",
    "generated_response": "动火审批需填写许可证、安全监督审核、主管审批。[1]",
    "sources": [
        {"doc_type": "操作规程", "score": 0.76, "text": "动火作业许可证…", "doc_id": 3}
    ],
    "messages": [],
    "cache_hit": False,
}


class FakeGraph:
    async def ainvoke(self, state):
        return {**FAKE_RESULT, **state}


class WorkingMemoryStub(WorkingMemory):
    """基于 fakeredis 的真实 WorkingMemory；历史始终为空。"""

    def __init__(self, redis) -> None:
        super().__init__(redis=redis)

    async def get_messages(self, session_id, limit=20):
        return []


@pytest.fixture
def patched_service(monkeypatch):
    redis = fakeredis.aioredis.FakeRedis(decode_responses=True)
    fake = SimpleNamespace(graph=FakeGraph(), working_memory=WorkingMemoryStub(redis))
    monkeypatch.setattr(chat_mod, "get_qa_service", lambda: fake)
    return fake


def _auth_header(user_id: int) -> dict:
    settings = get_settings()
    token = create_access_token(
        user_id,
        "司钻",
        "worker",
        secret=settings.jwt.secret,
        algorithm=settings.jwt.algorithm,
        expire_minutes=settings.jwt.expire_minutes,
    )
    return {"Authorization": f"Bearer {token}"}


@pytest.mark.asyncio
async def test_chat_json_response(async_client, patched_service):
    resp = await async_client.post(
        "/api/v1/chat",
        json={"message": "动火作业审批流程是什么？", "user_id": 7},
        headers=_auth_header(7),
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["response"].startswith("动火审批")
    assert body["intent"] == "structural"
    assert body["sources"][0]["doc_type"] == "操作规程"
    assert body["session_id"]
    assert body["trace_id"]


@pytest.mark.asyncio
async def test_chat_sse_stream(async_client, patched_service):
    resp = await async_client.post(
        "/api/v1/chat",
        json={"message": "动火作业审批流程是什么？", "user_id": 7, "stream": True},
        headers=_auth_header(7),
    )
    assert resp.status_code == 200
    assert "text/event-stream" in resp.headers["content-type"]
    raw = resp.text
    assert '"type": "token"' in raw
    assert '"type": "sources"' in raw
    assert '"type": "done"' in raw
    assert "[DONE]" in raw
    assert "操作规程" in raw


@pytest.mark.asyncio
async def test_sessions_require_auth(async_client, patched_service):
    resp = await async_client.get("/api/v1/chat/sessions", params={"user_id": 7})
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_sessions_list_and_delete(async_client, patched_service):
    redis_client = patched_service.working_memory.redis
    await redis_client.zadd("chat:sessions:7", {"sess-1": time.time()})
    await redis_client.hset(
        "wm:context:sess-1",
        mapping={"last_message": '"你好"', "created_at": "2026-01-01T00:00:00+00:00"},
    )

    headers = _auth_header(7)
    resp = await async_client.get(
        "/api/v1/chat/sessions", params={"user_id": 7}, headers=headers
    )
    assert resp.status_code == 200
    sessions = resp.json()
    assert sessions[0]["session_id"] == "sess-1"
    assert sessions[0]["last_message"] == "你好"

    resp = await async_client.delete("/api/v1/chat/sessions/sess-1", headers=headers)
    assert resp.status_code == 200
    assert await redis_client.zrange("chat:sessions:7", 0, -1) == []


@pytest.mark.asyncio
async def test_sessions_forbidden_for_other_user(async_client, patched_service):
    headers = _auth_header(8)
    resp = await async_client.get(
        "/api/v1/chat/sessions", params={"user_id": 7}, headers=headers
    )
    assert resp.status_code == 403
