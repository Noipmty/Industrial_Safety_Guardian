"""unified_sync 集成测试（Milvus + MySQL 簿记）。

需要本地 Docker 服务。使用确定性的 fake embedder。
"""

from __future__ import annotations

import asyncio
import uuid

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

from app.config import get_settings
from app.services.indexing.plaintext_chunker import Chunk
from app.services.indexing.unified_sync import UnifiedSync, sha1_hash


class FakeEmbedder:
    def encode(self, texts: list[str]) -> tuple[list[list[float]], list[dict[int, float]]]:
        dense = [[float(len(t) % 97) / 97.0] * 1024 for t in texts]
        sparse = [
            {(i * 7 + 3) % 30000: 1.0 + i * 0.01 for i in range(min(len(t), 64))}
            for t in texts
        ]
        return dense, sparse


@pytest.fixture(scope="module")
def event_loop():
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


def _chunks(texts: list[str]) -> list[Chunk]:
    return [Chunk(text=t, start=0, end=len(t)) for t in texts]


@pytest.mark.asyncio
async def test_sync_idempotent_and_diff():
    doc_id = int(uuid.uuid4().int % 1_000_000) + 10_000_000
    engine = create_async_engine(get_settings().mysql.url)
    try:
        sync = UnifiedSync(embedder=FakeEmbedder())

        first = await sync.sync_document(
            doc_id=doc_id, doc_type="法规", position="通用", version="v1",
            chunks=_chunks(["第一条 安全生产人人有责。", "第二条 隐患排查制度。"]),
        )
        assert first.inserted == 2 and first.deleted == 0

        # 相同内容重复执行：零写入（幂等契约）。
        second = await sync.sync_document(
            doc_id=doc_id, doc_type="法规", position="通用", version="v1",
            chunks=_chunks(["第一条 安全生产人人有责。", "第二条 隐患排查制度。"]),
        )
        assert second.inserted == 0 and second.deleted == 0

        # 修改一个分块 + 追加一个：1 次删除 + 2 次插入。
        third = await sync.sync_document(
            doc_id=doc_id, doc_type="法规", position="通用", version="v1",
            chunks=_chunks([
                "第一条 安全生产人人有责。",
                "第二条 隐患排查治理制度（修订）。",
                "第三条 应急预案。",
            ]),
        )
        assert third.inserted == 2
        assert third.deleted == 1

        # Milvus 中被修改的分块必须携带新哈希。
        rows = await sync._load_chunk_hashes(doc_id)
        by_index = {r["chunk_index"]: r for r in rows}
        assert by_index[1]["content_hash"] == sha1_hash("第二条 隐患排查治理制度（修订）。")

        # 清理 Milvus + MySQL。
        from app.services.indexing.milvus_store import delete_by_doc, ensure_collection

        delete_by_doc(ensure_collection(), doc_id)
        async with engine.begin() as conn:
            await conn.execute(text("DELETE FROM document_chunks WHERE doc_id = :d"), {"d": doc_id})
    finally:
        await engine.dispose()
