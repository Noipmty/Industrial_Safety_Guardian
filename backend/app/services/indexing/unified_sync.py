"""文档 → Milvus 的统一同步，基于内容 hash 做差异比对。

幂等契约：内容不变时重复执行 sync 不会产生任何 Milvus 写入。
chunk 级 ``content_hash`` 驱动差异计算：
    - 新出现的 hash   -> 插入
    - 消失的 hash     -> 删除（按 chunk_id）
    - 变化的 hash     -> 先删后插
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from typing import Any

from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy.pool import NullPool

from app.config import get_settings
from app.core.logger import get_logger
from app.services.indexing.embedding import EmbeddingService
from app.services.indexing.milvus_store import (
    ChunkRecord,
    delete_by_doc,
    ensure_collection,
    insert_chunks,
)
from app.services.indexing.plaintext_chunker import Chunk as TextChunk

logger = get_logger(__name__)


def sha1_hash(content: str) -> str:
    """chunk 的稳定内容 hash。"""
    return hashlib.sha1(content.encode("utf-8"), usedforsecurity=False).hexdigest()


@dataclass(slots=True)
class SyncReport:
    """一次 unified_sync 运行的汇总。"""

    doc_id: int
    inserted: int
    deleted: int
    total_chunks: int


class UnifiedSync:
    """MySQL 台账与 Milvus 之间基于差异的文档同步。"""

    def __init__(self, embedder: EmbeddingService | None = None) -> None:
        self._embedder = embedder
        self._engine = create_async_engine(
            get_settings().mysql.url, pool_pre_ping=True, poolclass=NullPool
        )

    async def sync_document(
        self,
        doc_id: int,
        doc_type: str,
        position: str,
        version: str,
        chunks: list[TextChunk],
    ) -> SyncReport:
        """将一个文档的 chunk 同步进 Milvus（幂等）。"""
        if self._embedder is None:
            from app.services.indexing.embedding import get_embedding_service

            self._embedder = get_embedding_service()

        new_hashes = [sha1_hash(chunk.text) for chunk in chunks]
        existing = await self._load_chunk_hashes(doc_id)
        existing_by_index = {row["chunk_index"]: row for row in existing}

        to_insert_idx = [
            i for i, h in enumerate(new_hashes)
            if i not in existing_by_index or existing_by_index[i]["content_hash"] != h
        ]
        new_max = len(chunks)
        to_delete_ids = [
            row["pk"] for row in existing if row["chunk_index"] >= new_max
        ]
        changed_indexes = {
            i for i in to_insert_idx
            if i in existing_by_index and existing_by_index[i]["content_hash"] != new_hashes[i]
        }

        report = SyncReport(
            doc_id=doc_id, inserted=0, deleted=0, total_chunks=len(chunks)
        )
        collection = ensure_collection()

        # 1) 删除消失 / 变化的行
        stale_pks = list(to_delete_ids)
        if changed_indexes:
            for row in existing:
                if row["chunk_index"] in changed_indexes and row["pk"] not in stale_pks:
                    stale_pks.append(row["pk"])
        if stale_pks:
            id_list = ", ".join(str(pk) for pk in stale_pks)
            collection.delete(f"pk in [{id_list}]")
            collection.flush()
            report.deleted = len(stale_pks)

        # 2) 对差异做 embedding 并插入
        if to_insert_idx:
            texts = [chunks[i].text for i in to_insert_idx]
            dense_list, sparse_list = self._embedder.encode(texts)
            records = [
                ChunkRecord(
                    chunk_id=f"{doc_id}:{i}",
                    doc_id=doc_id,
                    chunk_index=i,
                    text=chunks[i].text,
                    content_hash=new_hashes[i],
                    doc_type=doc_type,
                    position=position,
                    version=version,
                    dense=dense_list[k],
                    sparse=sparse_list[k],
                )
                for k, i in enumerate(to_insert_idx)
            ]
            report.inserted = insert_chunks(collection, records)

        # 3) 刷新 MySQL 台账
        await self._upsert_chunk_rows(doc_id, new_hashes)
        logger.info(
            "sync doc=%s inserted=%s deleted=%s total=%s",
            doc_id, report.inserted, report.deleted, report.total_chunks,
        )
        return report

    async def resync_full_document(
        self,
        doc_id: int,
        doc_type: str,
        position: str,
        version: str,
        chunks: list[TextChunk],
    ) -> SyncReport:
        """将文档从 Milvus 中删除后重新同步（版本升级时使用）。"""
        collection = ensure_collection()
        delete_by_doc(collection, doc_id)
        async with self._engine.begin() as conn:
            await conn.execute(
                text("DELETE FROM document_chunks WHERE doc_id = :doc_id"),
                {"doc_id": doc_id},
            )
        return await self.sync_document(doc_id, doc_type, position, version, chunks)

    async def _load_chunk_hashes(self, doc_id: int) -> list[dict[str, Any]]:
        """加载 chunk 台账并关联 Milvus 主键（PK）。

        MySQL 行中保存内容 hash；Milvus PK 通过确定性的
        chunk_id（``{doc_id}:{index}``）反推，因此删除时无需
        额外一次 Milvus 查询往返即可命中正确的行。
        """
        collection = ensure_collection()
        rows = collection.query(
            expr=f"doc_id == {doc_id}",
            output_fields=["pk", "chunk_id", "content_hash"],
            limit=16384,
        )
        return [
            {
                "pk": int(row["pk"]),
                "chunk_index": int(str(row["chunk_id"]).rsplit(":", 1)[1]),
                "content_hash": row["content_hash"],
            }
            for row in rows
        ]

    async def _upsert_chunk_rows(self, doc_id: int, hashes: list[str]) -> None:
        """替换某文档在 MySQL 中的台账行。"""
        async with self._engine.begin() as conn:
            await conn.execute(
                text("DELETE FROM document_chunks WHERE doc_id = :doc_id"),
                {"doc_id": doc_id},
            )
            if hashes:
                values = [
                    {"doc_id": doc_id, "chunk_index": i, "content_hash": h}
                    for i, h in enumerate(hashes)
                ]
                await conn.execute(
                    text(
                        """
                        INSERT INTO document_chunks (doc_id, chunk_index, content_hash)
                        VALUES (:doc_id, :chunk_index, :content_hash)
                        """
                    ),
                    values,
                )
