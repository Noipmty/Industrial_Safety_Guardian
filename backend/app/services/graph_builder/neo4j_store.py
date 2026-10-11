"""GraphRAG 实体/关系图谱的幂等 Neo4j 存储。

所有写入均使用 ``MERGE``，因此重复运行构建器不会产生重复的
节点或边。单例 ``AsyncDriver`` 惰性创建（与 ``pg_store`` /
``deps`` 的 engine 模式一致）。Neo4j 不可达时，所有方法优雅
降级（空列表 / 空操作 / 计数为 0），让流水线其余部分 ——
向量检索、记忆、对话 —— 继续运行。

Cypher 说明：
    - 实体节点带 ``Entity`` 标签，以 ``name`` 为键。
    - 关系统一为单一 ``REL`` 边类型 + ``type`` 属性，这样无论
      出现多少种关系名称，schema 都保持稳定。
    - N 跳遍历将（已校验的）深度内联进查询，因为 Cypher 不
      接受变长路径边界使用参数。
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from neo4j import AsyncGraphDatabase

from app.config import get_settings
from app.core.logger import get_logger
from app.services.graph_builder.extractor import Triple

if TYPE_CHECKING:
    from neo4j import AsyncDriver

logger = get_logger(__name__)

_driver: AsyncDriver | None = None


def get_neo4j_driver() -> AsyncDriver | None:
    """惰性创建并返回单例的异步 Neo4j driver。

    无法创建时返回 ``None``，让调用方优雅降级而不是抛异常。
    """
    global _driver
    if _driver is not None:
        return _driver
    settings = get_settings().neo4j
    try:
        _driver = AsyncGraphDatabase.driver(
            settings.uri, auth=(settings.user, settings.password)
        )
        logger.info("Neo4j async driver created for %s", settings.uri)
    except Exception as exc:  # noqa: BLE001 — 优雅降级
        logger.warning("Neo4j driver creation failed: %s", exc)
        _driver = None
    return _driver


async def _execute_write(cypher: str, params: dict[str, Any]) -> bool:
    """执行写查询；成功返回 ``True``，失败返回 ``False``。"""
    driver = get_neo4j_driver()
    if driver is None:
        logger.warning("Neo4j unreachable, skipping write")
        return False
    try:
        async with driver.session() as session:
            result = await session.run(cypher, params)
            await result.consume()
        return True
    except Exception as exc:  # noqa: BLE001 — 优雅降级
        logger.warning("Neo4j write failed: %s", exc)
        return False


async def _execute_read(
    cypher: str, params: dict[str, Any] | None = None
) -> list[dict[str, Any]]:
    """执行读查询；返回 dict 列表（失败时为空）。"""
    driver = get_neo4j_driver()
    if driver is None:
        logger.warning("Neo4j unreachable, returning empty read result")
        return []
    try:
        async with driver.session() as session:
            result = await session.run(cypher, params or {})
            return await result.data()
    except Exception as exc:  # noqa: BLE001 — 优雅降级
        logger.warning("Neo4j read failed: %s", exc)
        return []


async def upsert_entity(
    name: str,
    entity_type: str,
    aliases: list[str],
    doc_ids: list[int],
    chunk_ids: list[str],
) -> None:
    """MERGE 单个实体节点并写入完整元数据（幂等）。"""
    cypher = (
        "MERGE (e:Entity {name: $name}) "
        "SET e.entity_type = $entity_type, "
        "e.aliases = $aliases, "
        "e.doc_ids = $doc_ids, "
        "e.chunk_ids = $chunk_ids"
    )
    await _execute_write(
        cypher,
        {
            "name": name,
            "entity_type": entity_type,
            "aliases": aliases,
            "doc_ids": doc_ids,
            "chunk_ids": chunk_ids,
        },
    )


async def upsert_relation(
    subject: str,
    relation: str,
    object: str,
    confidence: float,
    chunk_id: str,
    doc_id: int,
) -> None:
    """MERGE 两个实体之间的关系边（幂等）。"""
    cypher = (
        "MERGE (a:Entity {name: $subject}) "
        "MERGE (b:Entity {name: $object}) "
        "MERGE (a)-[r:REL {type: $relation}]->(b) "
        "SET r.confidence = $confidence, "
        "r.chunk_id = $chunk_id, r.doc_id = $doc_id"
    )
    await _execute_write(
        cypher,
        {
            "subject": subject,
            "object": object,
            "relation": relation,
            "confidence": confidence,
            "chunk_id": chunk_id,
            "doc_id": doc_id,
        },
    )


async def upsert_triples(
    triples: list[Triple],
    canonical_map: dict[str, str],
) -> dict[str, int]:
    """批量 upsert 抽取出的实体 + 关系。

    在 MERGE 之前先应用 resolver 的 ``canonical_map``
    （原始名 -> 规范名），使别名合并到同一节点。实体先聚合，
    让每个节点携带完整的别名 / 文档 / chunk 集合。

    返回 ``{"entities": N, "relations": M}``。
    """
    driver = get_neo4j_driver()
    if driver is None:
        logger.warning("Neo4j unreachable, skipping triple upsert")
        return {"entities": 0, "relations": 0}

    entities: dict[str, dict[str, Any]] = {}
    for t in triples:
        cs = canonical_map.get(t.subject, t.subject)
        co = canonical_map.get(t.object, t.object)
        for canonical, raw, etype in (
            (cs, t.subject, t.subject_type),
            (co, t.object, t.object_type),
        ):
            rec = entities.setdefault(
                canonical,
                {
                    "entity_type": etype,
                    "aliases": set(),
                    "doc_ids": set(),
                    "chunk_ids": set(),
                },
            )
            rec["aliases"].add(raw)
            if t.doc_id:
                rec["doc_ids"].add(t.doc_id)
            if t.chunk_id:
                rec["chunk_ids"].add(t.chunk_id)
            if rec["entity_type"] in ("", "unknown") and etype not in ("", "unknown"):
                rec["entity_type"] = etype

    entity_cypher = (
        "MERGE (e:Entity {name: $name}) "
        "SET e.entity_type = $entity_type, "
        "e.aliases = $aliases, "
        "e.doc_ids = $doc_ids, "
        "e.chunk_ids = $chunk_ids"
    )
    rel_cypher = (
        "MERGE (a:Entity {name: $subject}) "
        "MERGE (b:Entity {name: $object}) "
        "MERGE (a)-[r:REL {type: $relation}]->(b) "
        "SET r.confidence = $confidence, "
        "r.chunk_id = $chunk_id, r.doc_id = $doc_id"
    )
    try:
        async with driver.session() as session:
            for name, info in entities.items():
                result = await session.run(
                    entity_cypher,
                    {
                        "name": name,
                        "entity_type": info["entity_type"],
                        "aliases": sorted(info["aliases"]),
                        "doc_ids": sorted(info["doc_ids"]),
                        "chunk_ids": sorted(info["chunk_ids"]),
                    },
                )
                await result.consume()
            for t in triples:
                cs = canonical_map.get(t.subject, t.subject)
                co = canonical_map.get(t.object, t.object)
                result = await session.run(
                    rel_cypher,
                    {
                        "subject": cs,
                        "object": co,
                        "relation": t.relation,
                        "confidence": t.confidence,
                        "chunk_id": t.chunk_id,
                        "doc_id": t.doc_id,
                    },
                )
                await result.consume()
    except Exception as exc:  # noqa: BLE001 — 优雅降级
        logger.warning("Neo4j triple upsert failed: %s", exc)
        return {"entities": 0, "relations": 0}
    logger.info(
        "Upserted %d entities, %d relations", len(entities), len(triples)
    )
    return {"entities": len(entities), "relations": len(triples)}


async def n_hop_traverse(
    anchor: str,
    max_hops: int = 2,
    limit: int = 50,
) -> list[dict[str, Any]]:
    """从锚点实体出发遍历至多 ``max_hops`` 跳。

    Cypher 不接受变长路径边界使用参数，因此 ``max_hops``
    经校验后内联进查询字符串。

    返回邻居 dict 列表，每项带有最短跳数。
    """
    if not isinstance(max_hops, int) or not 1 <= max_hops <= 5:
        raise ValueError(f"max_hops must be an int in [1, 5], got {max_hops!r}")
    cypher = (
        f"MATCH path = (e:Entity {{name: $anchor}})-[:REL*1..{max_hops}]-(neighbor) "
        "WITH neighbor, min(length(path)) AS hops "
        "RETURN neighbor.name AS name, "
        "neighbor.entity_type AS entity_type, "
        "neighbor.aliases AS aliases, hops "
        "ORDER BY hops LIMIT $limit"
    )
    return await _execute_read(cypher, {"anchor": anchor, "limit": limit})


async def get_all_entities() -> list[dict[str, Any]]:
    """返回全部实体节点（供社区检测使用）。"""
    cypher = (
        "MATCH (e:Entity) "
        "RETURN e.name AS name, e.entity_type AS entity_type, "
        "e.aliases AS aliases, e.doc_ids AS doc_ids, "
        "e.chunk_ids AS chunk_ids"
    )
    return await _execute_read(cypher)


async def get_all_relations() -> list[dict[str, Any]]:
    """返回全部关系边（供社区检测使用）。"""
    cypher = (
        "MATCH (a:Entity)-[r:REL]->(b:Entity) "
        "RETURN a.name AS subject, r.type AS relation, "
        "b.name AS object, r.confidence AS confidence, "
        "r.chunk_id AS chunk_id, r.doc_id AS doc_id"
    )
    return await _execute_read(cypher)


async def clear_all() -> None:
    """删除所有 Entity 和 Community 节点（全量重跑前使用）。"""
    await _execute_write("MATCH (e:Entity) DETACH DELETE e", {})
    await _execute_write("MATCH (c:Community) DETACH DELETE c", {})
    logger.info("Cleared all Entity and Community nodes")


async def close() -> None:
    """关闭并丢弃单例 driver。"""
    global _driver
    if _driver is None:
        return
    try:
        await _driver.close()
    except Exception as exc:  # noqa: BLE001 — 尽力关闭
        logger.warning("Neo4j driver close failed: %s", exc)
    _driver = None
