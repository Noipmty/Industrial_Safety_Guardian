"""基于 Redis 的两级语义缓存（精确哈希 -> 语义余弦）。

第一级（精确）：对归一化查询取 SHA-256 -> ``GET sc:exact:{hash}``。
第二级（语义）：在最近 ``MAX_ENTRIES`` 条记录上做应用侧余弦扫描
（以紧凑的 float32 blob 存储在 Redis Hash 中）。原生 Redis 7.2 不带
RediSearch 模块，因此向量扫描在 Python 中对有界条目集执行 ——
约 500 次点积，亚毫秒级。

所有失败均降级为"未命中"，缓存永远不会阻塞聊天流程。
"""

from __future__ import annotations

import base64
import hashlib
import json
import struct
import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Protocol

from redis.asyncio import Redis, from_url

from app.config import get_settings
from app.core.logger import get_logger

logger = get_logger(__name__)

EXACT_TTL = 3600  # 精确命中缓存 1 小时
SEMANTIC_TTL = 86400  # 语义条目缓存 1 天
MAX_ENTRIES = 500
SEMANTIC_THRESHOLD = 0.90
INDEX_KEY = "sc:semantic:index"  # ZSET member=entry_id score=created_ts
DATA_KEY = "sc:semantic:data"  # HASH field=entry_id value=packed JSON


class Embedder(Protocol):
    """最小化的 dense embedding 接口（异步安全包装器内部同步调用）。"""

    def encode_dense(self, texts: list[str]) -> list[list[float]]: ...


@dataclass(slots=True)
class CacheEntry:
    """一条缓存的问答结果。"""

    response: str
    sources: list[dict[str, Any]] = field(default_factory=list)
    level: str = "exact"  # "exact" | "semantic"


def _normalize(query: str) -> str:
    return "".join(query.split()).strip().lower()


def _pack_vec(vec: list[float]) -> str:
    return base64.b64encode(struct.pack(f"<{len(vec)}f", *vec)).decode("ascii")


def _unpack_vec(blob: str) -> list[float]:
    raw = base64.b64decode(blob)
    return list(struct.unpack(f"<{len(raw) // 4}f", raw))


def _cosine(a: list[float], b: list[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b, strict=False))
    na = sum(x * x for x in a) ** 0.5
    nb = sum(x * x for x in b) ** 0.5
    if na == 0 or nb == 0:
        return 0.0
    return dot / (na * nb)


class SemanticCache:
    """基于 Redis 的两级答案缓存。"""

    def __init__(self, embedder: Embedder, redis: Redis | None = None) -> None:
        self._embedder = embedder
        self._redis = redis if redis is not None else from_url(
            get_settings().redis.url, decode_responses=True
        )

    # ------------------------------------------------------------------ #
    # 第一级：精确缓存
    # ------------------------------------------------------------------ #

    @staticmethod
    def _exact_key(query: str, scope: str = "default") -> str:
        digest = hashlib.sha256(_normalize(query).encode("utf-8")).hexdigest()
        return f"sc:exact:{scope}:{digest}"

    async def _get_exact(self, query: str, scope: str = "default") -> CacheEntry | None:
        raw = await self._redis.get(self._exact_key(query, scope))
        if raw is None:
            return None
        data = json.loads(raw)
        return CacheEntry(
            response=data["response"],
            sources=data.get("sources", []),
            level="exact",
        )

    async def _put_exact(
        self, query: str, response: str, sources: list[dict[str, Any]], scope: str = "default"
    ) -> None:
        payload = json.dumps(
            {"response": response, "sources": sources}, ensure_ascii=False
        )
        await self._redis.set(self._exact_key(query, scope), payload, ex=EXACT_TTL)

    # ------------------------------------------------------------------ #
    # 第二级：语义缓存
    # ------------------------------------------------------------------ #

    async def _get_semantic(self, query: str, scope: str = "default") -> CacheEntry | None:
        try:
            query_vec = self._embedder.encode_dense([query])[0]
        except Exception:  # noqa: BLE001 —— 编码器离线 -> 跳过第二级
            logger.warning("Semantic cache: embedder unavailable, level-2 skipped")
            return None
        index_key = f"{INDEX_KEY}:{scope}"
        raw_ids = await self._redis.zrevrange(index_key, 0, MAX_ENTRIES - 1)
        entry_ids = [str(e) for e in raw_ids]
        if not entry_ids:
            return None
        data_key = f"{DATA_KEY}:{scope}"
        entries = await self._redis.hmget(data_key, entry_ids)
        best_id: str | None = None
        best_score = 0.0
        for entry_id, blob in zip(entry_ids, entries, strict=False):
            if blob is None:
                continue
            data = json.loads(blob)
            score = _cosine(query_vec, _unpack_vec(data["vec"]))
            if score > best_score:
                best_id = entry_id
                best_score = score
        if best_id is None or best_score < SEMANTIC_THRESHOLD:
            return None
        blob = await self._redis.hget(data_key, best_id)
        if blob is None:
            return None
        data = json.loads(blob)
        logger.info(
            "Semantic cache HIT (level=semantic score=%.3f)", best_score
        )
        return CacheEntry(
            response=data["response"],
            sources=data.get("sources", []),
            level="semantic",
        )

    async def _put_semantic(
        self, query: str, response: str, sources: list[dict[str, Any]], scope: str = "default"
    ) -> None:
        try:
            vec = self._embedder.encode_dense([query])[0]
        except Exception:  # noqa: BLE001
            return
        entry_id = uuid.uuid4().hex
        now = time.time()
        payload = json.dumps(
            {
                "vec": _pack_vec(vec),
                "response": response,
                "sources": sources,
                "created": now,
            },
            ensure_ascii=False,
        )
        index_key = f"{INDEX_KEY}:{scope}"
        data_key = f"{DATA_KEY}:{scope}"
        async with self._redis.pipeline(transaction=True) as pipe:
            pipe.hset(data_key, entry_id, payload)
            pipe.zadd(index_key, {entry_id: now})
            pipe.zremrangebyrank(index_key, 0, -MAX_ENTRIES - 1)
            pipe.expire(data_key, SEMANTIC_TTL)
            pipe.expire(index_key, SEMANTIC_TTL)
            await pipe.execute()

    # ------------------------------------------------------------------ #
    # 对外 API
    # ------------------------------------------------------------------ #

    async def get(self, query: str, scope: str = "default") -> CacheEntry | None:
        """两级查找：先精确，后语义余弦（scope 隔离不同权限视图）。"""
        try:
            hit = await self._get_exact(query, scope)
            if hit is not None:
                logger.info("Semantic cache HIT (level=exact)")
                return hit
            return await self._get_semantic(query, scope)
        except Exception:  # noqa: BLE001 —— 缓存绝不阻塞主流程
            logger.warning("Semantic cache lookup failed, treating as miss")
            return None

    async def put(
        self, query: str, response: str, sources: list[dict[str, Any]], scope: str = "default"
    ) -> None:
        """两级同时写入（尽力而为）。"""
        try:
            await self._put_exact(query, response, sources, scope)
            await self._put_semantic(query, response, sources, scope)
        except Exception:  # noqa: BLE001
            logger.warning("Semantic cache write failed (non-fatal)")

    async def clear(self) -> None:
        """清空两级缓存（测试 / 失效处理用）。"""
        exact_keys = [key async for key in self._redis.scan_iter("sc:exact:*")]
        if exact_keys:
            await self._redis.delete(*exact_keys)
        data_keys = [key async for key in self._redis.scan_iter(f"{DATA_KEY}:*")]
        index_keys = [key async for key in self._redis.scan_iter(f"{INDEX_KEY}:*")]
        stale = [*data_keys, *index_keys]
        if stale:
            await self._redis.delete(*stale)
