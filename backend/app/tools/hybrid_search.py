"""混合检索工具 —— 封装 P1 的 embedding + Milvus 混合检索。"""

from __future__ import annotations

import asyncio
from typing import Any

from app.core.logger import get_logger
from app.services.indexing.embedding import get_embedding_service
from app.services.indexing.milvus_store import hybrid_search

logger = get_logger(__name__)


class HybridSearchTool:
    """对安全知识库执行 dense(0.7) + sparse(0.3) 混合检索。"""

    def __init__(self, top_k: int = 8) -> None:
        self._top_k = top_k

    async def run(
        self,
        query: str,
        doc_types: list[str] | None = None,
    ) -> list[dict[str, Any]]:
        """编码查询并执行一次混合检索（线程池卸载执行）。

        当 Milvus 或编码器失败时降级为空命中列表，QA 工作流仍可依靠
        记忆 / 缓存作答。
        """
        try:
            service = get_embedding_service()
            dense, sparse = await asyncio.to_thread(service.encode, [query])
            from app.services.indexing.milvus_store import (
                ensure_collection,
            )

            collection = await asyncio.to_thread(ensure_collection)
            hits = await asyncio.to_thread(
                hybrid_search,
                collection,
                dense[0],
                sparse[0],
                self._top_k,
                doc_types,
            )
            logger.info("Hybrid search '%s' -> %d hits", query[:30], len(hits))
            return hits
        except Exception as exc:  # noqa: BLE001 —— 检索失败时降级放行
            logger.warning("Hybrid search failed: %s", exc)
            return []
