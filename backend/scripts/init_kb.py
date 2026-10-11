"""幂等的生产知识库初始化脚本。

从 ``backend/knowledge/`` 读取 markdown 文档（文件名前缀决定 doc_type），
登记到 ``documents`` 表（跳过已存在的标题），执行标准入库流水线
（解析 -> 分块 -> 向量化 -> Milvus 同步 -> 状态翻转），最后用样例查询
验证混合检索的召回效果。

用法（在 backend/ 目录下执行）：
    python scripts/init_kb.py                 # 入库 + 验证
    python scripts/init_kb.py --verify-only   # 仅召回检查
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

# 使脚本可直接以 `python scripts/init_kb.py` 运行（将 backend/ 加入导入路径）。
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlalchemy import create_engine, text  # noqa: E402

from app.config import get_settings  # noqa: E402
from app.core.logger import get_logger  # noqa: E402

logger = get_logger(__name__)

KB_DIR = Path(__file__).resolve().parents[1] / "knowledge"

# 文件名前缀 -> documents.doc_type（KnowledgeDocument.DocType 的取值）。
PREFIX_TO_TYPE = {
    "操作规程_": "操作规程",
    "事故案例_": "事故案例",
    "安全制度_": "法规",
}

DOC_VERSION = "v1.0"
VERIFY_TOP_SCORE = 0.35

VERIFY_QUERIES = [
    "动火作业前需要办理哪些审批手续",
    "进入受限空间作业氧含量合格标准是多少",
    "高处作业安全带的挂点有什么要求",
    "有限空间中毒窒息事故暴露了哪些问题",
    "承包商入厂安全教育培训有什么要求",
    "临时用电线路架设的规范要求",
    "吊装作业指挥人员的资质要求",
    "隐患排查治理闭环管理流程",
]


def _sync_engine():
    """登记簿记用的同步引擎（aiomysql 自带 pymysql 依赖）。"""
    url = get_settings().mysql.url.replace("+aiomysql", "+pymysql")
    return create_engine(url, pool_pre_ping=True)


def _ensure_doc(
    engine, title: str, doc_type: str, source_path: Path, version: str
) -> int | None:
    """登记文档；返回其 id，若已存在则返回 None。"""
    with engine.begin() as conn:
        row = conn.execute(
            text("SELECT id FROM documents WHERE title = :title"), {"title": title}
        ).first()
        if row is not None:
            return None
        result = conn.execute(
            text(
                "INSERT INTO documents (title, doc_type, source_path, version, status) "
                "VALUES (:title, :doc_type, :source_path, :version, 'draft')"
            ),
            {
                "title": title,
                "doc_type": doc_type,
                "source_path": str(source_path),
                "version": version,
            },
        )
        return int(result.lastrowid)


def ingest_all() -> tuple[int, int, int]:
    """入库所有知识 markdown 文件。返回（已入库数、跳过数、分块数）。"""
    from app.tasks.ingest import ingest_document_now

    files = sorted(KB_DIR.glob("*.md"))
    if not files:
        logger.error("no markdown documents found in %s", KB_DIR)
        return 0, 0, 0

    engine = _sync_engine()
    ingested = skipped = total_chunks = 0
    for path in files:
        title = path.stem
        doc_type = next(
            (v for prefix, v in PREFIX_TO_TYPE.items() if title.startswith(prefix)),
            None,
        )
        if doc_type is None:
            logger.warning("skip %s — unknown doc_type prefix", path.name)
            continue
        doc_id = _ensure_doc(engine, title, doc_type, path.resolve(), DOC_VERSION)
        if doc_id is None:
            skipped += 1
            logger.info("doc already registered: %s", title)
            continue
        report = ingest_document_now(doc_id)
        total_chunks += int(report["total_chunks"])
        ingested += 1
        logger.info(
            "ingested %s -> +%s chunks (total %s)",
            title, report["inserted"], report["total_chunks"],
        )
    return ingested, skipped, total_chunks


def verify_recall() -> bool:
    """每个样例查询都必须从知识库检索到置信度达标的结果。"""
    from app.services.indexing.embedding import get_embedding_service
    from app.services.indexing.milvus_store import ensure_collection, hybrid_search

    service = get_embedding_service()
    collection = ensure_collection()
    all_ok = True
    for query in VERIFY_QUERIES:
        dense, sparse = service.encode([query])
        hits = hybrid_search(collection, dense[0], sparse[0], 5, None)
        top_score = float(hits[0]["score"]) if hits else 0.0
        ok = top_score >= VERIFY_TOP_SCORE
        all_ok = all_ok and ok
        snippet = str(hits[0]["text"])[:50] if hits else "（无结果）"
        logger.info(
            "[verify %s] %s -> top_score=%.4f | %s",
            "OK" if ok else "MISS", query, top_score, snippet,
        )
    return all_ok


def main() -> int:
    parser = argparse.ArgumentParser(description="知识库批量初始化（幂等）")
    parser.add_argument("--verify-only", action="store_true", help="仅验证召回")
    args = parser.parse_args()

    if not args.verify_only:
        ingested, skipped, total_chunks = ingest_all()
        logger.info(
            "ingest summary: ingested=%s skipped=%s total_chunks=%s",
            ingested, skipped, total_chunks,
        )

    ok = verify_recall()
    logger.info("recall verification: %s", "PASSED" if ok else "FAILED")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
