"""长期记忆：情景记忆（30 天）+ 语义记忆（永久）存储。

所有查询方法都接受一个 ``EmbeddingProvider``，便于测试注入假的
embedder，而生产环境使用本地 BGE-M3 服务。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Protocol

from sqlalchemy import text

from app.services.memory.pg_store import (
    bind_user,
    get_memory_session_factory,
    to_vector_literal,
)


class EmbeddingProvider(Protocol):
    """最小化的稠密 embedding 接口。"""

    def encode(self, texts: list[str]) -> list[list[float]]:
        """将文本编码为稠密向量。"""
        ...


@dataclass(slots=True)
class MemoryHit:
    """一条检索到的长期记忆条目。"""

    source: str  # 来源："episodic" | "semantic"
    id: int
    user_id: int
    content: str
    memory_type: str | None
    importance: float
    score: float
    metadata: dict[str, Any] = field(default_factory=dict)


EPISODIC_COLUMNS = (
    "id, user_id, summary AS content, NULL AS memory_type, "
    "importance, session_id, created_at, last_accessed_at"
)
SEMANTIC_COLUMNS = (
    "id, user_id, content, memory_type, "
    "importance, source_session_id, created_at, last_accessed_at"
)


def _effective_importance(importance: float, decay_factor: float) -> float:
    return round(importance * decay_factor, 6)


class LongTermMemory:
    """Read/write/search access over the two memory tables."""

    def __init__(self, embedder: EmbeddingProvider) -> None:
        self._embedder = embedder

    # ------------------------------------------------------------------ #
    # 情景记忆（episodic）
    # ------------------------------------------------------------------ #

    async def add_episodic(
        self,
        user_id: int,
        session_id: str,
        summary: str,
        keywords: list[str] | None = None,
        importance: float = 0.5,
    ) -> int:
        """插入一条压缩后的会话摘要（embedding 在此计算）。"""
        embedding = self._embedder.encode([summary])[0]
        import json as _json

        async with get_memory_session_factory()() as session:
            await bind_user(session, user_id)
            result = await session.execute(
                text(
                    """
                    INSERT INTO episodic_memory
                        (user_id, session_id, summary, keywords, importance, embedding)
                    VALUES
                        (:user_id, :session_id, :summary, :keywords, :importance,
                         CAST(:embedding AS vector))
                    RETURNING id
                    """
                ),
                {
                    "user_id": user_id,
                    "session_id": session_id,
                    "summary": summary,
                    "keywords": _json.dumps(keywords or [], ensure_ascii=False),
                    "importance": importance,
                    "embedding": to_vector_literal(embedding),
                },
            )
            row = result.scalar_one()
            await session.commit()
            return int(row)

    async def search_episodic(
        self,
        user_id: int,
        query: str,
        top_k: int = 5,
        as_of: datetime | None = None,
    ) -> list[MemoryHit]:
        """对未过期的情景摘要做余弦相似度检索。"""
        query_vec = to_vector_literal(self._embedder.encode([query])[0])
        async with get_memory_session_factory()() as session:
            await bind_user(session, user_id)
            result = await session.execute(
                text(
                    f"""
                    SELECT {EPISODIC_COLUMNS},
                           1 - (embedding <=> CAST(:qvec AS vector)) AS score
                    FROM episodic_memory
                    WHERE user_id = :user_id
                      AND expires_at > COALESCE(:as_of, now())
                      AND embedding IS NOT NULL
                    ORDER BY embedding <=> CAST(:qvec AS vector)
                    LIMIT :top_k
                    """  # noqa: S608 — 列名是代码内常量
                ),
                {"qvec": query_vec, "user_id": user_id, "as_of": as_of, "top_k": top_k},
            )
            rows = result.all()
        return [
            self._row_to_hit("episodic", row, user_id) for row in rows
        ]

    # ------------------------------------------------------------------ #
    # 语义记忆（semantic）
    # ------------------------------------------------------------------ #

    async def add_semantic(
        self,
        user_id: int,
        memory_type: str,
        content: str,
        source_session_id: str | None = None,
        importance: float = 0.5,
    ) -> int | None:
        """插入一条事实/偏好/薄弱点；重复时返回 None。

        去重由 UNIQUE(user_id, memory_type, content) 约束保证 ——
        重复插入会保留原行（同时强化 importance）。
        """
        embedding = self._embedder.encode([content])[0]
        async with get_memory_session_factory()() as session:
            await bind_user(session, user_id)
            result = await session.execute(
                text(
                    """
                    INSERT INTO semantic_memory
                        (user_id, memory_type, content, source_session_id,
                         importance, embedding)
                    VALUES
                        (:user_id, :memory_type, :content, :source_session_id,
                         :importance, CAST(:embedding AS vector))
                    ON CONFLICT (user_id, memory_type, content) DO UPDATE
                        SET importance = LEAST(
                            semantic_memory.importance + 0.05, 1.0
                        ),
                        last_accessed_at = now()
                    RETURNING id
                    """
                ),
                {
                    "user_id": user_id,
                    "memory_type": memory_type,
                    "content": content,
                    "source_session_id": source_session_id,
                    "importance": importance,
                    "embedding": to_vector_literal(embedding),
                },
            )
            row = result.scalar_one_or_none()
            await session.commit()
            return int(row) if row is not None else None

    async def search_semantic(
        self,
        user_id: int,
        query: str,
        top_k: int = 5,
        memory_types: list[str] | None = None,
    ) -> list[MemoryHit]:
        """对事实/偏好/薄弱点做余弦相似度检索。"""
        query_vec = to_vector_literal(self._embedder.encode([query])[0])
        type_filter = ""
        params: dict[str, Any] = {
            "qvec": query_vec,
            "user_id": user_id,
            "top_k": top_k,
        }
        if memory_types:
            type_filter = "AND memory_type = ANY(:types)"
            params["types"] = memory_types
        async with get_memory_session_factory()() as session:
            await bind_user(session, user_id)
            result = await session.execute(
                text(
                    f"""
                    SELECT {SEMANTIC_COLUMNS},
                           1 - (embedding <=> CAST(:qvec AS vector)) AS score
                    FROM semantic_memory
                    WHERE user_id = :user_id
                      AND embedding IS NOT NULL
                      {type_filter}
                    ORDER BY embedding <=> CAST(:qvec AS vector)
                    LIMIT :top_k
                    """  # noqa: S608 — 列名/过滤条件均为代码内常量
                ),
                params,
            )
            rows = result.all()
        return [
            self._row_to_hit("semantic", row, user_id) for row in rows
        ]

    # ------------------------------------------------------------------ #
    # 维护操作（衰减/清理）—— 后台任务上下文，绕过 RLS
    # ------------------------------------------------------------------ #

    async def decay_all(self, factor: float = 0.98) -> int:
        """将两张表的 importance/decay 统一乘以 ``factor``。"""
        async with get_memory_session_factory()() as session:
            result = await session.execute(
                text(
                    """
                    UPDATE episodic_memory
                       SET decay_factor = decay_factor * :f,
                           importance   = importance * :f
                    """
                ),
                {"f": factor},
            )
            n_episodic = result.rowcount  # type: ignore[attr-defined]
            result = await session.execute(
                text(
                    """
                    UPDATE semantic_memory
                       SET decay_factor = decay_factor * :f,
                           importance   = importance * :f
                    """
                ),
                {"f": factor},
            )
            n_semantic = result.rowcount  # type: ignore[attr-defined]
            await session.commit()
        return n_episodic + n_semantic

    async def purge_forgotten(self, min_importance: float = 0.1, days: int = 90) -> int:
        """删除 importance 低于阈值且 ``days`` 天未访问的行。"""
        async with get_memory_session_factory()() as session:
            result = await session.execute(
                text(
                    """
                    DELETE FROM episodic_memory
                    WHERE importance < :mi
                      AND last_accessed_at < now() - (:days || ' days')::interval
                    """
                ),
                {"mi": min_importance, "days": str(days)},
            )
            n_episodic = result.rowcount  # type: ignore[attr-defined]
            result = await session.execute(
                text(
                    """
                    DELETE FROM semantic_memory
                    WHERE importance < :mi
                      AND last_accessed_at < now() - (:days || ' days')::interval
                    """
                ),
                {"mi": min_importance, "days": str(days)},
            )
            n_semantic = result.rowcount  # type: ignore[attr-defined]
            await session.commit()
        return n_episodic + n_semantic

    async def touch(self, source: str, memory_id: int) -> None:
        """记忆被用于回答后刷新其访问统计。"""
        table = source if source in ("episodic", "semantic") else None
        if table is None:
            raise ValueError(f"unknown memory source: {source}")
        async with get_memory_session_factory()() as session:
            await session.execute(
                text(
                    f"""
                    UPDATE {table}_memory
                       SET access_count = access_count + 1,
                           last_accessed_at = now()
                    WHERE id = :mid
                    """  # noqa: S608 — 表名是经过校验的白名单字面量
                ),
                {"mid": memory_id},
            )
            await session.commit()

    # ------------------------------------------------------------------ #

    @staticmethod
    def _row_to_hit(source: str, row: Any, user_id: int) -> MemoryHit:
        (
            memory_id,
            row_user_id,
            content,
            memory_type,
            importance,
            session_ref,
            created_at,
            last_accessed_at,
            score,
        ) = row
        return MemoryHit(
            source=source,
            id=int(memory_id),
            user_id=int(user_id),
            content=content,
            memory_type=memory_type,
            importance=_effective_importance(float(importance), 1.0),
            score=float(score),
            metadata={
                "session_ref": session_ref,
                "created_at": (
                    created_at.isoformat() if isinstance(created_at, datetime) else created_at
                ),
                "last_accessed_at": (
                    last_accessed_at.isoformat()
                    if isinstance(last_accessed_at, datetime)
                    else last_accessed_at
                ),
            },
        )
