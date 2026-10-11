"""知识图谱接口：概览子图 / 实体搜索 / 全量重建。

数据源为 GraphRAG 流水线写入 Neo4j 的 ``Entity`` / ``REL`` /
``Community``（见 ``app.services.graph_builder``）。Neo4j 不可达时
所有查询优雅降级为空结果，前端展示"暂无数据"而不是报错。
"""

from __future__ import annotations

import json
from typing import Any

from fastapi import APIRouter, BackgroundTasks, Query

from app.core.deps import AdminUser
from app.core.logger import get_logger
from app.core.redis import get_redis
from app.services.graph_builder.neo4j_store import (
    get_neo4j_driver,
)
from app.services.indexing.milvus_store import fetch_all_chunks

logger = get_logger(__name__)
router = APIRouter(prefix="/admin/graph", tags=["知识图谱"])

REBUILD_STATUS_KEY = "graph:rebuild:status"  # Redis: 重建状态 JSON，TTL 1h
REBUILD_STATUS_TTL = 3600


async def _read(cypher: str, params: dict[str, Any] | None = None) -> list[dict[str, Any]]:
    """执行只读 Cypher；Neo4j 不可达或查询失败时返回空列表。"""
    driver = get_neo4j_driver()
    if driver is None:
        logger.warning("Neo4j unreachable, graph query degraded to empty")
        return []
    try:
        async with driver.session() as session:
            result = await session.run(cypher, params or {})
            return await result.data()
    except Exception as exc:  # noqa: BLE001 — 优雅降级
        logger.warning("Neo4j graph query failed: %s", exc)
        return []


# ---------------------------------------------------------------------------
# 响应模型（简单 dict 组装，避免多余 schema 文件）
# ---------------------------------------------------------------------------

def _empty_graph() -> dict[str, Any]:
    return {
        "stats": {"entities": 0, "relations": 0, "communities": 0},
        "nodes": [],
        "edges": [],
        "anchors": [],
    }


def _node(name: Any, entity_type: Any, degree: int) -> dict[str, Any]:
    return {"id": str(name), "name": str(name), "entity_type": entity_type or "unknown", "degree": degree}


# ---------------------------------------------------------------------------
# 查询端点
# ---------------------------------------------------------------------------

@router.get("/overview")
async def graph_overview(
    user: AdminUser,
    limit: int = Query(150, ge=10, le=500),
) -> dict[str, Any]:
    """返回图谱统计 + 度数最高的 ``limit`` 个实体构成的子图。"""
    stats_rows = await _read("MATCH (e:Entity) RETURN count(e) AS c")
    rel_rows = await _read("MATCH ()-[r:REL]->() RETURN count(r) AS c")
    com_rows = await _read("MATCH (c:Community) RETURN count(c) AS c")
    stats = {
        "entities": stats_rows[0]["c"] if stats_rows else 0,
        "relations": rel_rows[0]["c"] if rel_rows else 0,
        "communities": com_rows[0]["c"] if com_rows else 0,
    }
    if not stats["entities"]:
        return _empty_graph() | {"stats": stats}

    top = await _read(
        "MATCH (e:Entity) "
        "WITH e, COUNT {(e)-[:REL]-()} AS degree "
        "ORDER BY degree DESC LIMIT $limit "
        "RETURN e.name AS name, e.entity_type AS entity_type, degree",
        {"limit": limit},
    )
    names = [r["name"] for r in top]
    edges_raw = await _read(
        "MATCH (a:Entity)-[r:REL]->(b:Entity) "
        "WHERE a.name IN $names AND b.name IN $names "
        "RETURN a.name AS source, r.type AS relation, b.name AS target, "
        "r.confidence AS confidence",
        {"names": names},
    )
    edges: list[dict[str, Any]] = []
    seen: set[tuple[str, str, str]] = set()
    for e in edges_raw:
        key = (str(e["source"]), str(e["relation"]), str(e["target"]))
        if key in seen:
            continue
        seen.add(key)
        edges.append(
            {
                "source": str(e["source"]),
                "target": str(e["target"]),
                "relation": str(e["relation"]),
                "confidence": float(e.get("confidence") or 0.0),
            }
        )
    nodes = [
        _node(r["name"], r["entity_type"], int(r["degree"]))
        for r in top
    ]
    return {"stats": stats, "nodes": nodes, "edges": edges, "anchors": []}


@router.get("/search")
async def graph_search(
    user: AdminUser,
    q: str = Query(..., min_length=1),
    limit: int = Query(5, ge=1, le=20),
) -> dict[str, Any]:
    """按名称/别名模糊搜索实体，返回锚点及其一跳邻域子图。"""
    matched = await _read(
        "MATCH (e:Entity) "
        "WHERE toLower(e.name) CONTAINS toLower($q) "
        "   OR any(a IN coalesce(e.aliases, []) WHERE toLower(a) CONTAINS toLower($q)) "
        "WITH e, COUNT {(e)-[:REL]-()} AS degree "
        "ORDER BY degree DESC LIMIT $limit "
        "RETURN e.name AS name, e.entity_type AS entity_type, degree",
        {"q": q, "limit": limit},
    )
    if not matched:
        return _empty_graph()

    anchors = [r["name"] for r in matched]
    rows = await _read(
        "MATCH (e:Entity)-[r:REL]-(n:Entity) "
        "WHERE e.name IN $anchors "
        "RETURN e.name AS anchor, r.type AS relation, r.confidence AS confidence, "
        "startNode(r).name AS source, endNode(r).name AS target, "
        "n.name AS neighbor, n.entity_type AS neighbor_type",
        {"anchors": anchors},
    )
    node_map: dict[str, dict[str, Any]] = {}
    edge_map: dict[tuple[str, str, str], dict[str, Any]] = {}
    for m in matched:
        node_map[str(m["name"])] = _node(m["name"], m["entity_type"], int(m["degree"]))
    for r in rows:
        neighbor = str(r["neighbor"])
        if neighbor not in node_map:
            node_map[neighbor] = _node(neighbor, r["neighbor_type"], 1)
        key = (str(r["source"]), str(r["relation"]), str(r["target"]))
        edge_map.setdefault(
            key,
            {
                "source": str(r["source"]),
                "target": str(r["target"]),
                "relation": str(r["relation"]),
                "confidence": float(r.get("confidence") or 0.0),
            },
        )
    return {
        "stats": {"entities": len(node_map), "relations": len(edge_map), "communities": 0},
        "nodes": list(node_map.values()),
        "edges": list(edge_map.values()),
        "anchors": [str(a) for a in anchors],
    }


@router.get("/status")
async def rebuild_status(user: AdminUser) -> dict[str, Any]:
    """查询后台重建任务状态。"""
    redis = get_redis()
    raw = await redis.get(REBUILD_STATUS_KEY)
    if not raw:
        return {"state": "idle"}
    return json.loads(raw)


# ---------------------------------------------------------------------------
# 重建端点
# ---------------------------------------------------------------------------

async def _run_rebuild() -> None:
    """后台执行全量图谱重建并更新 Redis 状态。"""
    redis = get_redis()
    try:
        chunks = fetch_all_chunks()
        if not chunks:
            await redis.set(
                REBUILD_STATUS_KEY,
                json.dumps({"state": "error", "message": "知识库为空，无 chunk 可构建"}, ensure_ascii=False),
                ex=REBUILD_STATUS_TTL,
            )
            return
        from app.services.graph_builder.incremental import full_rebuild
        from app.services.llm.client import get_llm_client

        result = await full_rebuild(chunks, llm=get_llm_client())
        await redis.set(
            REBUILD_STATUS_KEY,
            json.dumps({"state": "done", "result": result}, ensure_ascii=False, default=str),
            ex=REBUILD_STATUS_TTL,
        )
        logger.info("Graph rebuild finished: %s", result)
    except Exception as exc:  # noqa: BLE001 — 状态落库便于前端提示
        logger.exception("Graph rebuild failed")
        try:
            await redis.set(
                REBUILD_STATUS_KEY,
                json.dumps({"state": "error", "message": str(exc)}, ensure_ascii=False),
                ex=REBUILD_STATUS_TTL,
            )
        except Exception:  # noqa: BLE001
            pass


@router.post("/rebuild", status_code=202)
async def rebuild_graph(
    user: AdminUser,
    background: BackgroundTasks,
) -> dict[str, str]:
    """触发后台全量重建（抽取 -> 消歧 -> upsert -> 社区），立即返回。"""
    redis = get_redis()
    raw = await redis.get(REBUILD_STATUS_KEY)
    if raw and json.loads(raw).get("state") == "running":
        return {"status": "already_running"}
    await redis.set(
        REBUILD_STATUS_KEY,
        json.dumps({"state": "running"}, ensure_ascii=False),
        ex=REBUILD_STATUS_TTL,
    )
    background.add_task(_run_rebuild)
    return {"status": "started"}
