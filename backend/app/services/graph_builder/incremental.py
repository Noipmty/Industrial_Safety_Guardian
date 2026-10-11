"""GraphRAG 增量 + 全量构建编排。

- ``full_rebuild``：清空 -> 抽取 -> 消歧 -> upsert -> 社区。
  首次运行和内容大改后始终使用全量重建。
- ``incremental_update``：仅抽取变化的 chunk（与 Neo4j 已有
  chunk id 做差集），幂等地 MERGE 写入，然后基于当前全图
  重建社区摘要。
- ``reconcile_check``：MySQL 文档数与 Neo4j 实体/关系数的
  一致性校验（委托给 ``reconcile.reconcile``）。

注意：当语料超过约 5000 篇文档时，建议用 HIT-Leiden 替代
进程内 Louvain 以获得更好的社区质量；构建仍会继续执行，
并记录警告日志供运维决策。
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from app.core.logger import get_logger
from app.services.graph_builder.community import build_and_summarize
from app.services.graph_builder.extractor import Triple, extract_from_chunks
from app.services.graph_builder.neo4j_store import (
    clear_all,
    get_neo4j_driver,
    upsert_triples,
)
from app.services.graph_builder.resolver import resolve_with_embeddings

if TYPE_CHECKING:
    from neo4j import AsyncDriver

    from app.services.llm.client import LLMClient

logger = get_logger(__name__)

_LARGE_CORPUS_THRESHOLD = 5000


async def full_rebuild(
    chunks: list[dict[str, Any]],
    llm: LLMClient | None = None,
) -> dict[str, Any]:
    """全量 GraphRAG 构建：清空 -> 抽取 -> 消歧 -> upsert -> 社区。"""
    driver = get_neo4j_driver()
    if driver is None:
        logger.warning("Full rebuild skipped (Neo4j unreachable)")
        return {"entities": 0, "relations": 0, "communities": 0, "mode": "full"}
    distinct_docs = {c.get("doc_id") for c in chunks}
    if len(distinct_docs) > _LARGE_CORPUS_THRESHOLD:
        logger.warning(
            "Corpus has %d docs; HIT-Leiden recommended for community quality",
            len(distinct_docs),
        )
    await clear_all()
    extraction_results = await extract_from_chunks(chunks, llm=llm)
    triples = [t for r in extraction_results for t in r.triples]
    if not triples:
        logger.info("Full rebuild: no triples extracted from %d chunks", len(chunks))
        return {"entities": 0, "relations": 0, "communities": 0, "mode": "full"}
    triple_dicts = [_triple_to_dict(t) for t in triples]
    resolution = await resolve_with_embeddings(triple_dicts)
    counts = await upsert_triples(triples, resolution.canonical_map)
    communities = await build_and_summarize(driver, llm)
    result = {
        "entities": counts.get("entities", 0),
        "relations": counts.get("relations", 0),
        "communities": len(communities),
        "mode": "full",
    }
    logger.info("Full rebuild done: %s", result)
    return result


async def incremental_update(
    chunks: list[dict[str, Any]],
    llm: LLMClient | None = None,
) -> dict[str, Any]:
    """增量构建：仅对变化的 chunk 做抽取 + 消歧 + upsert。

    ``chunk_id`` 在 Neo4j 中已有三元组的 chunk 会被跳过，
    避免对未变化内容重复运行 LLM 抽取。MERGE 写入保持幂等，
    因此重复处理同一 chunk 是安全的。之后基于当前全图
    重建社区摘要。

    局限：内容变化但 ``chunk_id`` 不变的 chunk 不会被重新抽取；
    如需完全重同步请运行 ``full_rebuild``。
    """
    driver = get_neo4j_driver()
    if driver is None:
        logger.warning("Incremental update skipped (Neo4j unreachable)")
        return {
            "entities": 0,
            "relations": 0,
            "communities": 0,
            "mode": "incremental",
        }
    existing_ids = await _existing_chunk_ids(driver)
    changed = [
        c for c in chunks
        if str(c.get("chunk_id", "")) not in existing_ids
    ]
    if not changed:
        logger.info("Incremental: no changed chunks (%d total)", len(chunks))
        communities = await build_and_summarize(driver, llm)
        return {
            "entities": 0,
            "relations": 0,
            "communities": len(communities),
            "mode": "incremental",
        }
    extraction_results = await extract_from_chunks(changed, llm=llm)
    triples = [t for r in extraction_results for t in r.triples]
    if not triples:
        logger.info("Incremental: no triples from %d changed chunks", len(changed))
        communities = await build_and_summarize(driver, llm)
        return {
            "entities": 0,
            "relations": 0,
            "communities": len(communities),
            "mode": "incremental",
        }
    triple_dicts = [_triple_to_dict(t) for t in triples]
    resolution = await resolve_with_embeddings(triple_dicts)
    counts = await upsert_triples(triples, resolution.canonical_map)
    communities = await build_and_summarize(driver, llm)
    result = {
        "entities": counts.get("entities", 0),
        "relations": counts.get("relations", 0),
        "communities": len(communities),
        "mode": "incremental",
    }
    logger.info("Incremental update done: %s", result)
    return result


async def reconcile_check() -> dict[str, Any]:
    """一致性校验：MySQL 文档数 vs Neo4j 实体/关系数。"""
    from app.services.graph_builder.reconcile import reconcile

    return await reconcile()


async def _existing_chunk_ids(driver: AsyncDriver) -> set[str]:
    """返回在 Neo4j 中已有关系边的 chunk id 集合。"""
    cypher = "MATCH ()-[r:REL]->() RETURN DISTINCT r.chunk_id AS cid"
    try:
        async with driver.session() as session:
            result = await session.run(cypher)
            records = await result.data()
            return {
                str(r["cid"]) for r in records if r.get("cid") is not None
            }
    except Exception as exc:  # noqa: BLE001 — 优雅降级
        logger.warning("load existing chunk_ids failed: %s", exc)
        return set()


def _triple_to_dict(t: Triple) -> dict[str, Any]:
    """将 Triple dataclass 转换为 dict，供 resolver 使用。"""
    return {
        "subject": t.subject,
        "subject_type": t.subject_type,
        "relation": t.relation,
        "object": t.object,
        "object_type": t.object_type,
        "confidence": t.confidence,
        "chunk_id": t.chunk_id,
        "doc_id": t.doc_id,
    }
