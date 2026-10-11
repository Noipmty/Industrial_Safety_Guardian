"""多模态 RAG 工具 —— 面向图纸 / 蓝图的页级视觉检索。

两阶段检索流程（prompt §P4）：
    1. 池化预过滤：在 ``safety_visual`` 集合上做 dense cosine ANN
    2. MaxSim 重排：稀疏词权重的 late-interaction 匹配

封装多模态编码器 + Milvus 视觉库。当 Milvus 或编码器失败时降级为
空命中列表，QA 工作流仍可依靠文本检索 / 记忆作答。

当 ColQwen2 权重不可用时，编码器会透明地回退到 BGE-M3 文本描述
编码（见 ``multimodal_encoder.py``）。
"""

from __future__ import annotations

import asyncio
from typing import Any

from app.core.logger import get_logger
from app.services.rag.multimodal_encoder import (
    MultimodalEncoder,
    get_multimodal_encoder,
)

logger = get_logger(__name__)


class MultimodalRagTool:
    """页级视觉检索：池化预过滤 -> MaxSim 两阶段流程。"""

    def __init__(
        self,
        top_k: int = 5,
        encoder: MultimodalEncoder | None = None,
    ) -> None:
        self._top_k = top_k
        self._encoder = encoder or get_multimodal_encoder()

    async def run(
        self,
        query: str,
        doc_id: int | None = None,
    ) -> list[dict[str, Any]]:
        """为查询检索页级视觉命中。

        返回 ``[{"page_id", "doc_id", "page_num", "description",
        "image_path", "score", "doc_type": "visual"}]``。
        """
        try:
            q_dense, q_sparse = await asyncio.to_thread(
                self._encoder.encode_query, query
            )
            from app.services.indexing.multimodal_store import (
                ensure_visual_collection,
                visual_search,
            )

            collection = await asyncio.to_thread(ensure_visual_collection)
            hits = await asyncio.to_thread(
                visual_search,
                collection,
                q_dense,
                q_sparse,
                self._top_k,
            )
            if doc_id is not None:
                hits = [h for h in hits if h.get("doc_id") == doc_id]
            for hit in hits:
                hit["doc_type"] = "visual"
            logger.info(
                "Multimodal RAG '%s' -> %d page hits", query[:30], len(hits)
            )
            return hits
        except Exception as exc:  # noqa: BLE001 —— 检索失败时降级放行
            logger.warning("Multimodal RAG failed: %s", exc)
            return []

    async def index_pages(
        self,
        doc_id: int,
        descriptions: list[str],
        image_paths: list[str],
        page_hashes: list[str],
        version: str = "v1",
    ) -> int:
        """将页级视觉内容增量写入 Milvus 索引。

        已存在相同 ``page_hash`` 的页会被跳过（幂等）。
        """
        try:
            encodings = await asyncio.to_thread(
                self._encoder.encode_pages, descriptions
            )
            from app.services.indexing.multimodal_store import (
                PageRecord,
                ensure_visual_collection,
                has_page_hash,
                insert_pages,
            )

            collection = await asyncio.to_thread(ensure_visual_collection)
            records: list[PageRecord] = []
            for i, (dense, sparse) in enumerate(encodings):
                if await asyncio.to_thread(
                    has_page_hash, collection, page_hashes[i]
                ):
                    logger.debug("Skipping page %d (hash exists)", i)
                    continue
                records.append(
                    PageRecord(
                        page_id=f"{doc_id}:{i}",
                        doc_id=doc_id,
                        page_num=i,
                        page_hash=page_hashes[i],
                        description=descriptions[i][:2048],
                        image_path=image_paths[i],
                        version=version,
                        dense=dense,
                        sparse=sparse,
                    )
                )
            inserted = await asyncio.to_thread(insert_pages, collection, records)
            logger.info(
                "Indexed %d visual pages for doc_id=%d (skipped %d)",
                inserted,
                doc_id,
                len(descriptions) - inserted,
            )
            return inserted
        except Exception as exc:  # noqa: BLE001 —— 索引失败时降级放行
            logger.warning("Visual indexing failed: %s", exc)
            return 0
