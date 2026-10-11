"""FAQ 永久缓存服务 —— 缓存层级：Redis 语义缓存 → MySQL FAQ → 完整 RAG。

设计要点：
- 向量表常驻内存（FAQ 量级为数百条），60 秒自动刷新，增删改后立即失效；
- 查询路径完全不依赖数据库往返（一次编码 + 一次 numpy 矩阵乘）；
- 挖掘：扫描 Redis 工作记忆中的近期会话，由 LLM 提炼优质问答候选，
  管理员确认后入库（source="mined"）。
"""

from __future__ import annotations

import json
import time
from dataclasses import dataclass
from typing import Any

import numpy as np
from sqlalchemy import create_engine, text
from sqlalchemy.ext.asyncio import create_async_engine

from app.core.logger import get_logger
from app.services.indexing.embedding import get_embedding_service
from app.config import get_settings

logger = get_logger(__name__)

FAQ_SIM_THRESHOLD = 0.86  # FAQ 命中阈值（精校答案，略严于语义缓存）
REFRESH_INTERVAL = 60.0  # 内存向量表刷新间隔（秒）


@dataclass(slots=True)
class FaqHit:
    """一次 FAQ 命中。"""

    id: int
    question: str
    answer: str
    score: float


class FaqService:
    """FAQ 的检索 / CRUD / 挖掘（内存向量表加速）。"""

    def __init__(self) -> None:
        settings = get_settings()
        self._engine = create_async_engine(
            settings.mysql.url, pool_pre_ping=True, pool_size=3, max_overflow=2
        )
        self._embedder = get_embedding_service()
        self._rows: list[dict[str, Any]] = []
        self._matrix: np.ndarray | None = None
        self._loaded_at: float = 0.0

    # ------------------------------------------------------------------
    # 内存向量表
    # ------------------------------------------------------------------
    async def _ensure_fresh(self, force: bool = False) -> None:
        if not force and (time.time() - self._loaded_at) < REFRESH_INTERVAL:
            return
        async with self._engine.connect() as conn:
            result = await conn.execute(
                text(
                    "SELECT id, question, answer, embedding FROM faqs "
                    "WHERE enabled = 1"
                )
            )
            rows = result.mappings().all()
        rows_out: list[dict[str, Any]] = []
        vecs: list[list[float]] = []
        for row in rows:
            try:
                vec = json.loads(row["embedding"])
            except (TypeError, ValueError):
                continue
            rows_out.append(
                {"id": int(row["id"]), "question": row["question"], "answer": row["answer"]}
            )
            vecs.append([float(x) for x in vec])
        self._rows = rows_out
        if vecs:
            matrix = np.asarray(vecs, dtype=np.float32)
            norms = np.linalg.norm(matrix, axis=1, keepdims=True)
            norms[norms == 0.0] = 1.0
            self._matrix = matrix / norms
        else:
            self._matrix = None
        self._loaded_at = time.time()
        logger.info("FAQ vector table refreshed: %s entries", len(rows_out))

    # ------------------------------------------------------------------
    # 检索（问答链路第 2.5 级缓存）
    # ------------------------------------------------------------------
    async def search(self, query: str) -> FaqHit | None:
        """向量匹配最相似的 FAQ；相似度不足返回 None（继续走 RAG）。"""
        if not query.strip():
            return None
        await self._ensure_fresh()
        if self._matrix is None or not self._rows:
            return None
        try:
            query_vec = np.asarray(
                self._embedder.encode_dense([query])[0], dtype=np.float32
            )
        except Exception:  # noqa: BLE001 —— 编码器不可用直接放行
            logger.warning("FAQ search skipped: embedder unavailable")
            return None
        norm = float(np.linalg.norm(query_vec))
        if norm == 0.0:
            return None
        sims = self._matrix @ (query_vec / norm)
        best_idx = int(np.argmax(sims))
        best_score = float(sims[best_idx])
        if best_score < FAQ_SIM_THRESHOLD:
            return None
        row = self._rows[best_idx]
        return FaqHit(
            id=row["id"], question=row["question"], answer=row["answer"], score=best_score
        )

    async def incr_hit(self, faq_id: int) -> None:
        """命中计数（尽力而为，不阻塞主流程）。"""
        try:
            async with self._engine.begin() as conn:
                await conn.execute(
                    text("UPDATE faqs SET hit_count = hit_count + 1 WHERE id = :id"),
                    {"id": faq_id},
                )
        except Exception:  # noqa: BLE001
            logger.warning("FAQ hit_count increment failed: id=%s", faq_id)

    # ------------------------------------------------------------------
    # CRUD（管理端）
    # ------------------------------------------------------------------
    async def create(
        self, question: str, answer: str, source: str = "manual"
    ) -> int:
        vec = self._embedder.encode_dense([question])[0]
        async with self._engine.begin() as conn:
            result = await conn.execute(
                text(
                    "INSERT INTO faqs (question, answer, embedding, source) "
                    "VALUES (:q, :a, :e, :s)"
                ),
                {"q": question, "a": answer, "e": json.dumps(vec), "s": source},
            )
        await self._ensure_fresh(force=True)
        return int(result.lastrowid or 0)

    async def update(self, faq_id: int, question: str, answer: str) -> None:
        vec = self._embedder.encode_dense([question])[0]
        async with self._engine.begin() as conn:
            await conn.execute(
                text(
                    "UPDATE faqs SET question = :q, answer = :a, embedding = :e "
                    "WHERE id = :id"
                ),
                {"q": question, "a": answer, "e": json.dumps(vec), "id": faq_id},
            )
        await self._ensure_fresh(force=True)

    async def delete(self, faq_id: int) -> None:
        async with self._engine.begin() as conn:
            await conn.execute(text("DELETE FROM faqs WHERE id = :id"), {"id": faq_id})
        await self._ensure_fresh(force=True)

    async def list_all(self) -> list[dict[str, Any]]:
        async with self._engine.connect() as conn:
            result = await conn.execute(
                text(
                    "SELECT id, question, answer, source, hit_count, enabled, "
                    "created_at FROM faqs ORDER BY id DESC"
                )
            )
            rows = result.mappings().all()
        return [
            {
                "id": int(r["id"]),
                "question": r["question"],
                "answer": r["answer"],
                "source": r["source"],
                "hit_count": int(r["hit_count"]),
                "enabled": bool(r["enabled"]),
                "created_at": str(r["created_at"]),
            }
            for r in rows
        ]

    async def toggle(self, faq_id: int, enabled: bool) -> None:
        async with self._engine.begin() as conn:
            await conn.execute(
                text("UPDATE faqs SET enabled = :e WHERE id = :id"),
                {"e": enabled, "id": faq_id},
            )
        await self._ensure_fresh(force=True)

    # ------------------------------------------------------------------
    # 挖掘：从 Redis 工作记忆的近期会话提炼 FAQ 候选
    # ------------------------------------------------------------------
    async def mine_from_sessions(
        self, redis_client: Any, llm_client: Any, limit: int = 5
    ) -> list[dict[str, str]]:
        """扫描近期会话消息 → LLM 提炼优质问答候选（不入库，返回待审核列表）。"""
        keys = [key async for key in redis_client.scan_iter("wm:messages:*")]
        transcripts: list[str] = []
        for key in keys[:20]:
            raw = await redis_client.lrange(key, -40, -1)
            messages = []
            for item in raw:
                try:
                    messages.append(json.loads(item))
                except (TypeError, ValueError):
                    continue
            qa_pairs = [
                (m["role"], m["content"])
                for m in messages
                if m.get("role") in ("user", "assistant") and m.get("content")
            ]
            if len(qa_pairs) >= 2:
                transcripts.append("\n".join(f"{r}: {c}" for r, c in qa_pairs))
        if not transcripts:
            return []

        corpus = "\n\n---\n\n".join(transcripts)[-12000:]
        prompt = (
            "以下是从工业安全问答系统的近期对话中截取的内容。"
            f"请提炼出最多 {limit} 条最值得沉淀为标准 FAQ 的问答对："
            "问题应通用化（去掉个人信息），答案准确、自包含、不超过 300 字。"
            '只输出 JSON 数组，格式：[{"question": "...", "answer": "..."}]，'
            "没有合适内容则输出 []。\n\n" + corpus
        )
        try:
            resp = await llm_client.chat(
                [
                    {"role": "system", "content": "你是知识库运营专家，只输出 JSON。"},
                    {"role": "user", "content": prompt},
                ],
                max_tokens=2048,
            )
            data = resp.json()
        except Exception:  # noqa: BLE001 —— LLM 失败返回空候选
            logger.warning("FAQ mining failed (LLM error)")
            return []
        if isinstance(data, list):
            return [
                {"question": str(item["question"]), "answer": str(item["answer"])}
                for item in data
                if isinstance(item, dict) and item.get("question") and item.get("answer")
            ][:limit]
        return []


_faq_service: FaqService | None = None


def get_faq_service() -> FaqService:
    """模块级单例。"""
    global _faq_service
    if _faq_service is None:
        _faq_service = FaqService()
    return _faq_service
