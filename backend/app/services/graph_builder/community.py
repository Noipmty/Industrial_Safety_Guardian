"""社区检测（Louvain）+ LLM 社区摘要。

从 Neo4j 的实体/关系构建 NetworkX 图，用 Louvain 划分社区，
再让 LLM 为每个社区生成 1-2 句摘要。摘要以 ``:Community`` 节点
写回 Neo4j，供 GraphRAG 检索器在查询时获取。

降级策略：
    - 未安装 NetworkX 时，所有实体合并为单一社区（摘要仍会生成）。
    - LLM 缺失或处于 mock 模式时，摘要使用确定性模板，
      保证流水线离线可运行。
    - Neo4j 不可达时，所有函数返回空 / 空操作。
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from app.core.logger import get_logger
from app.services.graph_builder.neo4j_store import (
    get_all_entities,
    get_all_relations,
    get_neo4j_driver,
)
from app.services.llm.client import LLMClient

if TYPE_CHECKING:
    from neo4j import AsyncDriver

try:  # networkx 是可选依赖 —— 缺失时降级
    import networkx as nx  # type: ignore[import-untyped]
    from networkx.algorithms.community import louvain_communities  # type: ignore[import-untyped]

    _HAS_NETWORKX = True
except ImportError:  # pragma: no cover — networkx 可选
    nx = None  # type: ignore[assignment]
    louvain_communities = None  # type: ignore[assignment]
    _HAS_NETWORKX = False

logger = get_logger(__name__)


async def detect_communities(
    driver: AsyncDriver | None,
) -> list[list[str]]:
    """用 Louvain 将 Neo4j 实体划分为社区。

    返回实体名称列表的列表。NetworkX 缺失时降级为单一社区
    （包含全部实体）；Neo4j 不可用或实体集为空时返回 ``[]``。
    """
    if driver is None:
        logger.warning("Neo4j driver unavailable, skipping community detection")
        return []
    entities = await get_all_entities()
    if not entities:
        return []
    relations = await get_all_relations()
    if not _HAS_NETWORKX:
        logger.info("networkx unavailable, falling back to single community")
        return [[e["name"] for e in entities if e.get("name")]]

    graph = nx.Graph()
    for e in entities:
        name = e.get("name")
        if name:
            graph.add_node(name)
    for r in relations:
        s = r.get("subject")
        o = r.get("object")
        if s and o:
            graph.add_edge(s, o)

    communities_raw = louvain_communities(graph)
    communities = [sorted(c) for c in communities_raw]
    logger.info("Louvain detected %d communities", len(communities))
    return communities


async def summarize_community(
    entities: list[str],
    relations: list[dict[str, Any]],
    llm: LLMClient | None,
) -> str:
    """为一个社区生成 1-2 句摘要。

    当 LLM 缺失、处于 mock 模式或调用失败时，
    退回确定性模板。
    """
    head = ", ".join(entities[:5])
    template = f"包含{len(entities)}个实体的社区，主要涉及{head}"
    if llm is None or llm.mock_mode:
        return template
    rel_lines = [
        f"{r.get('subject', '')} -[{r.get('relation', '')}]-> "
        f"{r.get('object', '')}"
        for r in relations[:20]
    ]
    messages = [
        {
            "role": "system",
            "content": "你是工业安全知识图谱的社区摘要助手。"
            "请用1-2句中文概括以下实体及其关系构成的社区主题。",
        },
        {
            "role": "user",
            "content": (
                f"实体：{head}"
                f"{'...' if len(entities) > 5 else ''}\n"
                f"关系示例：\n" + "\n".join(rel_lines)
            ),
        },
    ]
    try:
        resp = await llm.chat(messages, temperature=0.2, max_tokens=256)
        text = resp.content.strip()
        return text or template
    except Exception as exc:  # noqa: BLE001 — 降级为模板
        logger.warning("Community LLM summary failed: %s", exc)
        return template


async def build_and_summarize(
    driver: AsyncDriver | None,
    llm: LLMClient | None,
) -> list[dict[str, Any]]:
    """完整社区流水线：检测 -> 摘要 -> 持久化到 Neo4j。

    返回 ``[{"community_id": int, "entities": [...], "summary": str}]``。
    社区摘要写入 ``:Community`` 节点，并为每个实体打上
    ``community_id`` 标签以便后续查询。
    """
    communities = await detect_communities(driver)
    if not communities:
        return []
    relations = await get_all_relations()
    results: list[dict[str, Any]] = []
    for cid, members in enumerate(communities):
        member_set = set(members)
        rels = [
            r
            for r in relations
            if r.get("subject") in member_set or r.get("object") in member_set
        ]
        summary = await summarize_community(members, rels, llm)
        results.append(
            {
                "community_id": cid,
                "entities": members,
                "summary": summary,
            }
        )
        await _store_community(driver, cid, members, summary)
    logger.info("Built and stored %d community summaries", len(results))
    return results


async def _store_community(
    driver: AsyncDriver | None,
    cid: int,
    entities: list[str],
    summary: str,
) -> None:
    """将社区摘要与实体归属关系持久化到 Neo4j。"""
    if driver is None:
        return
    set_cypher = (
        "UNWIND $entities AS name "
        "MATCH (e:Entity {name: name}) "
        "SET e.community_id = $cid"
    )
    merge_cypher = (
        "MERGE (c:Community {id: $cid}) "
        "SET c.summary = $summary, c.entities = $entities"
    )
    try:
        async with driver.session() as session:
            r1 = await session.run(set_cypher, {"entities": entities, "cid": cid})
            await r1.consume()
            r2 = await session.run(
                merge_cypher,
                {"cid": cid, "summary": summary, "entities": entities},
            )
            await r2.consume()
    except Exception as exc:  # noqa: BLE001 — 优雅降级
        logger.warning("Failed to store community %d: %s", cid, exc)


async def get_community_for_entity(entity_name: str) -> str | None:
    """返回实体所属社区的摘要，不存在时返回 ``None``。"""
    driver = get_neo4j_driver()
    if driver is None:
        return None
    cypher = (
        "MATCH (e:Entity {name: $name}) "
        "WHERE e.community_id IS NOT NULL "
        "MATCH (c:Community {id: e.community_id}) "
        "RETURN c.summary AS summary"
    )
    try:
        async with driver.session() as session:
            result = await session.run(cypher, {"name": entity_name})
            record = await result.single()
            return record["summary"] if record else None
    except Exception as exc:  # noqa: BLE001 — 优雅降级
        logger.warning("get_community_for_entity failed: %s", exc)
        return None
