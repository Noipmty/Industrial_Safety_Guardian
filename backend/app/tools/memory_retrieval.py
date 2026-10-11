"""记忆检索工具 —— 工作记忆 + 情景/语义长期记忆。"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from app.core.logger import get_logger
from app.services.memory.long_term import LongTermMemory
from app.services.memory.working_memory import WorkingMemory

logger = get_logger(__name__)


@dataclass(slots=True)
class MemoryToolResult:
    """为单次查询聚合的记忆上下文。"""

    history: list[dict[str, str]] = field(default_factory=list)
    hits: list[dict[str, Any]] = field(default_factory=list)


class MemoryRetrievalTool:
    """获取近期会话历史 + 相关的长期记忆。"""

    def __init__(
        self,
        working_memory: WorkingMemory,
        long_term_memory: LongTermMemory,
        history_turns: int = 6,
        top_k: int = 5,
    ) -> None:
        self._wm = working_memory
        self._ltm = long_term_memory
        self._history_turns = history_turns
        self._top_k = top_k

    async def run(
        self, user_id: int, session_id: str, query: str
    ) -> MemoryToolResult:
        """返回近期历史（用于改写）+ 打分排序后的记忆命中。"""
        result = MemoryToolResult()
        try:
            result.history = await self._wm.get_messages(
                session_id, limit=self._history_turns
            )
        except Exception as exc:  # noqa: BLE001 —— 降级为空历史
            logger.warning("Working memory read failed: %s", exc)

        import asyncio

        try:
            episodic, semantic = await asyncio.gather(
                self._ltm.search_episodic(user_id, query, top_k=self._top_k),
                self._ltm.search_semantic(user_id, query, top_k=self._top_k),
            )
        except Exception as exc:  # noqa: BLE001 —— 降级为无记忆
            logger.warning("Long-term memory search failed: %s", exc)
            return result

        for hit in episodic + semantic:
            result.hits.append(
                {
                    "source": hit.source,
                    "content": hit.content,
                    "memory_type": hit.memory_type,
                    "importance": hit.importance,
                    "score": hit.score,
                    "id": hit.id,
                }
            )
        result.hits.sort(key=lambda h: h["score"], reverse=True)
        return result
