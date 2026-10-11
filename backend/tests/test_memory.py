"""三层记忆系统的集成测试。

需要通过 ``infra/docker-compose.yml`` 启动本地 Docker 服务
（postgres / redis）。向量化使用确定性的 fake 实现，保证测试
快速且离线运行。
"""

from __future__ import annotations

import asyncio

import pytest

from app.services.llm.client import LLMResponse
from app.services.memory.consolidate import SessionConsolidator, transcript_from_messages
from app.services.memory.long_term import LongTermMemory
from app.services.memory.working_memory import WorkingMemory


class FakeEmbedder:
    """基于哈希的确定性 dense embedder（1024 维，单位范数）。"""

    def encode(self, texts: list[str]) -> list[list[float]]:
        vectors = []
        for text in texts:
            vec = [0.0] * 1024
            for i, byte in enumerate(text.encode("utf-8")):
                vec[(byte * 31 + i) % 1024] += 1.0
            norm = sum(x * x for x in vec) ** 0.5 or 1.0
            vectors.append([x / norm for x in vec])
        return vectors


class FakeLLM:
    """返回固定内容的整合 LLM（结构化 JSON）。"""

    async def chat(self, messages, temperature: float = 0.3, max_tokens: int = 1024):
        return LLMResponse(
            content=(
                '{"summary": "用户复习了动火作业审批流程，确认了分级要求。",'
                ' "facts": ["用户是车间安全员，负责动火审批", "用户不熟悉有限空间作业"]}'
            ),
            route="mock",
            model="fake",
        )


@pytest.fixture(scope="module")
def event_loop():
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest.mark.asyncio
async def test_working_memory_window_and_ttl():
    wm = WorkingMemory()
    await wm.clear_session("test-wm-1")
    for i in range(25):
        await wm.add_message("test-wm-1", "user", f"msg-{i}")
    messages = await wm.get_messages("test-wm-1")
    assert len(messages) == 20
    assert messages[-1]["content"] == "msg-24"
    assert messages[0]["content"] == "msg-5"

    await wm.set_context("test-wm-1", {"user_position": "钻工", "query_type": "factual"})
    ctx = await wm.get_context("test-wm-1")
    assert ctx["user_position"] == "钻工"
    assert ctx["query_type"] == "factual"
    await wm.clear_session("test-wm-1")
    assert await wm.get_messages("test-wm-1") == []


@pytest.mark.asyncio
async def test_episodic_and_semantic_roundtrip():
    await _init_db()
    ltm = LongTermMemory(embedder=FakeEmbedder())
    user_id = 900001

    epi_id = await ltm.add_episodic(
        user_id=user_id,
        session_id="sess-mem-test",
        summary="用户咨询了动火作业分级审批流程。",
        keywords=["动火", "审批"],
        importance=0.8,
    )
    assert epi_id > 0

    hits = await ltm.search_episodic(user_id, "动火作业审批", top_k=3)
    assert hits
    assert hits[0].source == "episodic"
    assert hits[0].user_id == user_id

    first = await ltm.add_semantic(
        user_id=user_id, memory_type="preference", content="用户是车间安全员", importance=0.6
    )
    dup = await ltm.add_semantic(
        user_id=user_id, memory_type="preference", content="用户是车间安全员", importance=0.6
    )
    assert first is not None and dup is not None  # 冲突路径仍会返回 id
    assert dup == first  # UNIQUE 去重保留原始行

    sem_hits = await ltm.search_semantic(user_id, "车间安全员", top_k=3)
    assert any("车间安全员" in h.content for h in sem_hits)


@pytest.mark.asyncio
async def test_rls_isolates_users():
    await _init_db()
    ltm = LongTermMemory(embedder=FakeEmbedder())
    await ltm.add_episodic(user_id=900002, session_id="s-a", summary="甲用户的秘密摘要。")
    await ltm.add_episodic(user_id=900003, session_id="s-b", summary="乙用户的摘要。")

    hits_a = await ltm.search_episodic(900002, "用户的摘要", top_k=10)
    assert hits_a
    assert all(h.user_id == 900002 for h in hits_a)


@pytest.mark.asyncio
async def test_decay_and_purge():
    await _init_db()
    ltm = LongTermMemory(embedder=FakeEmbedder())
    decayed = await ltm.decay_all(factor=0.5)
    assert decayed >= 0
    purged = await ltm.purge_forgotten(min_importance=0.1, days=90)
    assert purged >= 0


@pytest.mark.asyncio
async def test_consolidation_dual_write():
    await _init_db()
    ltm = LongTermMemory(embedder=FakeEmbedder())
    consolidator = SessionConsolidator(long_term_memory=ltm, llm=FakeLLM())
    messages = [
        {"role": "user", "content": "动火作业审批流程是什么？"},
        {"role": "assistant", "content": "动火作业实行分级审批。"},
    ]
    result = await consolidator.consolidate_session(
        user_id=900004, session_id="sess-consolidate", transcript=transcript_from_messages(messages)
    )
    assert "动火作业" in result.summary
    assert len(result.facts) == 2
    assert result.episodic_id is not None

    # 薄弱点事实写入语义记忆。
    hits = await ltm.search_semantic(900004, "有限空间作业", top_k=5)
    assert any("有限空间" in h.content for h in hits)


_init_done = False


async def _init_db() -> None:
    global _init_done
    if not _init_done:
        from app.services.memory.pg_store import init_memory_db

        await init_memory_db()
        _init_done = True
