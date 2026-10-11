"""情景记忆 / 语义记忆的 PostgreSQL + pgvector 存储。

使用独立的异步 engine（与 MySQL 业务库分开）。``init_memory_db``
是幂等的：创建 pgvector 扩展、两张记忆表、HNSW 索引以及
行级安全（RLS）策略。

隐私隔离（提示词 §P1）：
    每个请求级连接必须调用 ``bind_user``，使
    ``SET LOCAL app.current_user_id`` 在事务内生效；
    RLS 策略随即将读写限制到该用户自己的行。
    维护连接（衰减任务、迁移）不设置该 GUC，策略将其视为
    仅限后台工作的旁路。
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pgvector.sqlalchemy import Vector
from sqlalchemy import (
    BigInteger,
    DateTime,
    Float,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy.pool import NullPool

from app.config import get_settings

EMBEDDING_DIM = 1024


class MemoryBase(DeclarativeBase):
    """记忆库（PostgreSQL）schema 独立的 declarative base。"""


class EpisodicMemory(MemoryBase):
    """压缩后的会话摘要（TTL 30 天）。"""

    __tablename__ = "episodic_memory"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    session_id: Mapped[str] = mapped_column(String(64), nullable=False)
    summary: Mapped[str] = mapped_column(Text, nullable=False)
    keywords: Mapped[str] = mapped_column(Text, nullable=False, server_default="[]")
    importance: Mapped[float] = mapped_column(Float, nullable=False, server_default="0.5")
    decay_factor: Mapped[float] = mapped_column(Float, nullable=False, server_default="1.0")
    access_count: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")
    embedding: Mapped[list[float] | None] = mapped_column(
        Vector(EMBEDDING_DIM), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.current_timestamp(), nullable=False
    )
    last_accessed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.current_timestamp(), nullable=False
    )
    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=text("now() + interval '30 days'"),
    )


class SemanticMemory(MemoryBase):
    """长期保存的偏好 / 事实 / 薄弱点记忆（无 TTL）。"""

    __tablename__ = "semantic_memory"
    __table_args__ = (
        # 提示词要求：UNIQUE(user_id, memory_type, content) 去重。
        UniqueConstraint(
            "user_id", "memory_type", "content", name="uq_semantic_memory_content"
        ),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    memory_type: Mapped[str] = mapped_column(String(32), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    source_session_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    importance: Mapped[float] = mapped_column(Float, nullable=False, server_default="0.5")
    decay_factor: Mapped[float] = mapped_column(Float, nullable=False, server_default="1.0")
    access_count: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")
    embedding: Mapped[list[float] | None] = mapped_column(
        Vector(EMBEDDING_DIM), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.current_timestamp(), nullable=False
    )
    last_accessed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.current_timestamp(), nullable=False
    )


_hnsw_episodic = Index(
    "ix_episodic_memory_embedding",
    EpisodicMemory.embedding,
    postgresql_using="hnsw",
    postgresql_ops={"embedding": "vector_cosine_ops"},
)
_hnsw_semantic = Index(
    "ix_semantic_memory_embedding",
    SemanticMemory.embedding,
    postgresql_using="hnsw",
    postgresql_ops={"embedding": "vector_cosine_ops"},
)

# 两条策略共用的旁路子句：维护连接未绑定请求级用户，
# 因此 current_setting(..., true) 返回 NULL。
_RLS_BYPASS = "current_setting('app.current_user_id', true) IS NULL"
_RLS_BIND = "user_id = current_setting('app.current_user_id')::bigint"

_engine: AsyncEngine | None = None
_session_factory: async_sessionmaker[AsyncSession] | None = None


def get_memory_engine() -> AsyncEngine:
    """惰性创建记忆库共享的异步 engine。"""
    global _engine, _session_factory
    if _engine is None:
        # NullPool：记忆层 QPS 很低；每次新建连接可避免
        # 跨事件循环的连接失效问题（测试会为每个用例新建事件循环）。
        _engine = create_async_engine(
            get_settings().postgres.url, pool_pre_ping=True, poolclass=NullPool
        )
        _session_factory = async_sessionmaker(_engine, expire_on_commit=False)
    return _engine


def get_memory_session_factory() -> async_sessionmaker[AsyncSession]:
    """返回共享的 session factory（必要时先创建 engine）。"""
    get_memory_engine()
    assert _session_factory is not None
    return _session_factory


async def init_memory_db() -> None:
    """幂等地创建扩展、表、索引和 RLS 策略。"""
    engine = get_memory_engine()
    async with engine.begin() as conn:
        await conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
        await conn.run_sync(MemoryBase.metadata.create_all)
        # FORCE 使 RLS 同样对表所有者生效；策略内的旁路子句
        # 仍允许维护连接通过。
        for table in ("episodic_memory", "semantic_memory"):
            await conn.execute(
                text(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY")
            )
            await conn.execute(
                text(f"ALTER TABLE {table} FORCE ROW LEVEL SECURITY")
            )
            await conn.execute(
                text(
                    f"""
                    DROP POLICY IF EXISTS memory_user_isolation ON {table}
                    """
                )
            )
            await conn.execute(
                text(
                    f"""
                    CREATE POLICY memory_user_isolation ON {table}
                    USING ({_RLS_BYPASS} OR {_RLS_BIND})
                    WITH CHECK ({_RLS_BYPASS} OR {_RLS_BIND})
                    """
                )
            )


async def bind_user(session: AsyncSession, user_id: int) -> None:
    """将请求用户绑定到会话事务，供 RLS 使用。

    asyncpg 无法在 SET 语句中绑定参数，因此将（已校验的）
    整数内联到字面量 SQL 中。
    """
    if not isinstance(user_id, int) or user_id < 0:
        raise ValueError(f"user_id must be a non-negative int, got {user_id!r}")
    await session.execute(text(f"SET LOCAL app.current_user_id = '{int(user_id)}'"))


def to_vector_literal(embedding: list[float]) -> str:
    """将稠密向量序列化为 pgvector 的文本字面量。"""
    return "[" + ",".join(f"{x:.7f}" for x in embedding) + "]"


def rows_to_dicts(rows: list[Any], entity_names: tuple[str, ...]) -> list[dict[str, Any]]:
    """按给定列顺序将 Row 元组转换为 dict。"""
    return [dict(zip(entity_names, row, strict=False)) for row in rows]
