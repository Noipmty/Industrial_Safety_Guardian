"""记忆衰减任务：每日 0.98 衰减系数 + 清理已遗忘的记录。

三种运行方式：
    1. celery beat（调度配置见 celery_app.py）
    2. 手动 celery 派发：  decay_memories.delay()
    3. CLI 一次性执行：    python -m app.tasks.memory_decay
"""

from __future__ import annotations

import asyncio

from app.core.logger import get_logger
from app.tasks.celery_app import celery_app

logger = get_logger(__name__)

DECAY_FACTOR = 0.98
PURGE_BELOW = 0.1
PURGE_AFTER_DAYS = 90


def run_decay_once() -> dict[str, int]:
    """同步执行一轮衰减 + 清理。"""
    from app.services.memory.long_term import LongTermMemory

    async def _run() -> tuple[int, int]:
        ltm = LongTermMemory(embedder=_NullEmbedder())
        decayed = await ltm.decay_all(factor=DECAY_FACTOR)
        purged = await ltm.purge_forgotten(min_importance=PURGE_BELOW, days=PURGE_AFTER_DAYS)
        return decayed, purged

    decayed, purged = asyncio.run(_run())
    logger.info(
        "memory decay done: decayed_rows=%s purged_rows=%s", decayed, purged
    )
    return {"decayed": decayed, "purged": purged}


class _NullEmbedder:
    """衰减/清理不做向量化；占位实现用于满足协议。"""

    def encode(self, texts: list[str]) -> list[list[float]]:
        """空操作编码器。"""
        return [[] for _ in texts]


@celery_app.task(name="app.tasks.memory_decay.decay_memories")
def decay_memories() -> dict[str, int]:
    """每日衰减的 Celery 入口。"""
    return run_decay_once()


if __name__ == "__main__":  # pragma: no cover - 手动 CLI 使用
    print(run_decay_once())
