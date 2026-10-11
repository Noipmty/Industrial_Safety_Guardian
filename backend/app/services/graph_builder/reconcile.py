"""MySQL <-> Neo4j 数据一致性对账。

按 ``doc_id`` 比较 MySQL 的 ``document_chunks`` 台账表与
Neo4j 实体/关系图谱。用于在构建后或同步失败后检测数据漂移，
以便运维触发全量重建。

返回 ``{mysql_docs, neo4j_entities, neo4j_relations, orphan_docs,
missing_docs, ok}``，其中：
    - ``orphan_docs``  ：存在于 Neo4j 但不在 MySQL 中的 doc id。
    - ``missing_docs`` ：存在于 MySQL 但不在 Neo4j 中的 doc id。
    - 仅当无数据漂移时 ``ok`` 为 True。

任一数据库不可达时，函数返回 ``{"ok": False}`` 并附带错误信息，
让调用方无需抛异常即可降级。
"""

from __future__ import annotations

from typing import Any

from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy.pool import NullPool

from app.config import get_settings
from app.core.logger import get_logger
from app.services.graph_builder.neo4j_store import get_neo4j_driver

logger = get_logger(__name__)


async def reconcile() -> dict[str, Any]:
    """比较 MySQL document_chunks 与 Neo4j 实体/关系。"""
    # --- MySQL 侧 ---------------------------------------------------------- #
    mysql_doc_ids: set[int] = set()
    try:
        settings = get_settings()
        engine = create_async_engine(
            settings.mysql.url, pool_pre_ping=True, poolclass=NullPool
        )
        try:
            async with engine.connect() as conn:
                rows = await conn.execute(
                    text("SELECT DISTINCT doc_id FROM document_chunks")
                )
                mysql_doc_ids = {int(row[0]) for row in rows}
        finally:
            await engine.dispose()
    except Exception as exc:  # noqa: BLE001 — 优雅降级
        logger.warning("MySQL reconcile query failed: %s", exc)
        return {"ok": False, "error": f"mysql: {exc}"}

    # --- Neo4j 侧 ---------------------------------------------------------- #
    driver = get_neo4j_driver()
    if driver is None:
        logger.warning("Neo4j unreachable during reconcile")
        return {"ok": False, "error": "neo4j driver unavailable"}
    try:
        async with driver.session() as session:
            r1 = await session.run("MATCH (e:Entity) RETURN count(e) AS n")
            rec1 = await r1.single()
            neo4j_entity_count = int(rec1["n"]) if rec1 else 0

            r2 = await session.run(
                "MATCH ()-[rel:REL]->() RETURN count(rel) AS n"
            )
            rec2 = await r2.single()
            neo4j_rel_count = int(rec2["n"]) if rec2 else 0

            r3 = await session.run(
                "MATCH (e:Entity) "
                "WHERE e.doc_ids IS NOT NULL "
                "UNWIND e.doc_ids AS d "
                "RETURN DISTINCT d AS doc_id"
            )
            records = await r3.data()
            neo4j_doc_ids = {
                int(r["doc_id"])
                for r in records
                if r.get("doc_id") is not None
            }
    except Exception as exc:  # noqa: BLE001 — 优雅降级
        logger.warning("Neo4j reconcile query failed: %s", exc)
        return {"ok": False, "error": f"neo4j: {exc}"}

    orphan_docs = sorted(neo4j_doc_ids - mysql_doc_ids)
    missing_docs = sorted(mysql_doc_ids - neo4j_doc_ids)
    ok = not orphan_docs and not missing_docs
    return {
        "mysql_docs": len(mysql_doc_ids),
        "neo4j_entities": neo4j_entity_count,
        "neo4j_relations": neo4j_rel_count,
        "orphan_docs": orphan_docs,
        "missing_docs": missing_docs,
        "ok": ok,
    }
