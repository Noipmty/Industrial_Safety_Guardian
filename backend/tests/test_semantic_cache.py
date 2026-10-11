"""使用 fakeredis + 字符重叠 embedder 的语义缓存测试。

该 fake embedder 将文本的字符集映射为归一化的 1024 维向量，
因此同义改写共享大部分字符（余弦相似度高），而无关查询则相距很远。
"""

from __future__ import annotations

import hashlib

import fakeredis.aioredis
import pytest

from app.tools.semantic_cache import SEMANTIC_THRESHOLD, CacheEntry, SemanticCache


class CharOverlapEmbedder:
    def encode_dense(self, texts: list[str]) -> list[list[float]]:
        vectors = []
        for text in texts:
            vec = [0.0] * 1024
            for ch in set(text.replace(" ", "")):
                slot = int(
                    hashlib.md5(ch.encode(), usedforsecurity=False).hexdigest(), 16
                ) % 1024
                vec[slot] += 1.0
            norm = sum(x * x for x in vec) ** 0.5 or 1.0
            vectors.append([x / norm for x in vec])
        return vectors


@pytest.fixture
def redis_client():
    return fakeredis.aioredis.FakeRedis(decode_responses=True)


@pytest.fixture
def cache(redis_client):
    return SemanticCache(CharOverlapEmbedder(), redis=redis_client)


@pytest.mark.asyncio
async def test_exact_hit(cache):
    await cache.put("防喷器安装要求是什么？", "依据规程：先装环形防喷器。", [{"doc_type": "规程"}])
    hit = await cache.get("防喷器安装要求是什么？")
    assert hit is not None
    assert hit.level == "exact"
    assert "环形防喷器" in hit.response


@pytest.mark.asyncio
async def test_semantic_hit_for_paraphrase(cache):
    await cache.put(
        "动火作业审批流程是什么？", "填写许可证→安全监督审核→领导审批。", []
    )
    hit = await cache.get("动火作业许可审批流程是什么？")
    assert hit is not None
    assert hit.level == "semantic"
    assert "审批" in hit.response


@pytest.mark.asyncio
async def test_miss_for_unrelated_query(cache):
    await cache.put("动火作业审批流程是什么？", "答案A", [])
    hit = await cache.get("明天食堂供应什么饭菜？")
    assert hit is None


@pytest.mark.asyncio
async def test_clear(cache):
    await cache.put("问题", "回答", [])
    await cache.clear()
    assert await cache.get("问题") is None


@pytest.mark.asyncio
async def test_entry_shape(cache, redis_client):
    await cache.put("q", "a", [{"doc_type": "t", "score": 0.5, "text": "x"}])
    entry = await cache.get("q")
    assert isinstance(entry, CacheEntry)
    assert entry.sources[0]["score"] == 0.5
    assert SEMANTIC_THRESHOLD == 0.90
