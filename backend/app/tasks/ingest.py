"""文档摄取流水线（PDF / Markdown / 纯文本）。

阶段：读取文件 -> 提取文本 -> 分块（Markdown 走结构感知分块）
-> 向量化 -> Milvus 同步 -> MySQL 状态翻转。以 Celery 任务执行，或
通过 ``ingest_document_now`` 同步执行（供测试以及无 worker 的开发
环境管理端 API 使用）。
"""

from __future__ import annotations

import asyncio
from pathlib import Path

import fitz  # PyMuPDF
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

from app.config import get_settings
from app.core.logger import get_logger
from app.services.indexing.markdown_chunker import markdown_chunk
from app.services.indexing.plaintext_chunker import recursive_chunk
from app.services.indexing.unified_sync import UnifiedSync
from app.tasks.celery_app import celery_app

logger = get_logger(__name__)

PDF_CHUNK_SIZE = 512


def extract_pdf_text(path: Path) -> str:
    """按页提取文本；扫描页会被标记出来（OCR 桩实现）。"""
    doc = fitz.open(path)
    parts: list[str] = []
    scanned_pages = 0
    for page in doc:
        page_text = page.get_text("text").strip()
        if page_text:
            parts.append(page_text)
        else:
            scanned_pages += 1
            parts.append(f"[SCANNED_PAGE_{page.number + 1}]")
    doc.close()
    if scanned_pages:
        # PP-StructureV3 OCR 流水线将在后续阶段接入；此标记可在此
        # 之前保持分块位置稳定。
        logger.warning("PDF %s has %s scanned page(s) awaiting OCR", path.name, scanned_pages)
    return "\n\n".join(parts)


def load_document_text(path: Path) -> str:
    """按扩展名读取源文档。"""
    suffix = path.suffix.lower()
    if suffix == ".pdf":
        return extract_pdf_text(path)
    return path.read_text(encoding="utf-8")


def chunk_document(path: Path, content: str) -> list:
    """Markdown 使用结构感知分块器，其余用递归分块。

    两个分块器返回的对象都带 ``.text`` 属性，``UnifiedSync`` 只消费
    该属性。
    """
    if path.suffix.lower() in {".md", ".markdown"}:
        return markdown_chunk(content, chunk_size=PDF_CHUNK_SIZE)
    return recursive_chunk(content, chunk_size=PDF_CHUNK_SIZE, overlap=64)


async def _ingest(doc_id: int) -> dict[str, int | str]:
    engine = create_async_engine(get_settings().mysql.url, pool_pre_ping=True)
    try:
        async with engine.begin() as conn:
            row = (
                await conn.execute(
                    text(
                        "SELECT id, title, doc_type, source_path, version "
                        "FROM documents WHERE id = :doc_id"
                    ),
                    {"doc_id": doc_id},
                )
            ).mappings().first()
        if row is None:
            raise ValueError(f"document {doc_id} not found")

        source = Path(row["source_path"])
        if not source.exists():
            raise FileNotFoundError(f"source file missing: {source}")

        content = load_document_text(source)
        chunks = chunk_document(source, content)

        sync = UnifiedSync()
        report = await sync.sync_document(
            doc_id=doc_id,
            doc_type=str(row["doc_type"]),
            position="通用",
            version=str(row["version"]),
            chunks=chunks,
        )

        async with engine.begin() as conn:
            await conn.execute(
                text(
                    "UPDATE documents SET status = 'published' "
                    "WHERE id = :doc_id AND status = 'draft'"
                ),
                {"doc_id": doc_id},
            )
        return {
            "doc_id": doc_id,
            "inserted": report.inserted,
            "deleted": report.deleted,
            "total_chunks": report.total_chunks,
        }
    finally:
        await engine.dispose()


def ingest_document_now(doc_id: int) -> dict[str, int | str]:
    """同步入口（开发 / 测试 / 无 worker 部署）。"""
    return asyncio.run(_ingest(doc_id))


@celery_app.task(name="app.tasks.ingest.ingest_document", bind=True, max_retries=2)
def ingest_document(self, doc_id: int) -> dict[str, int | str]:  # noqa: ANN001
    """异步摄取的 Celery 入口。"""
    try:
        return ingest_document_now(doc_id)
    except Exception as exc:  # noqa: BLE001
        logger.exception("ingest failed for doc=%s", doc_id)
        raise self.retry(exc=exc, countdown=30) from exc
