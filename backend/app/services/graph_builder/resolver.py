"""实体消歧：合并同名实体 + 别名映射。

双策略 resolver：
1. **规则法**：名称精确匹配（忽略大小写）→ 立即合并。
2. **embedding 相似度**：余弦 ≥ 0.88 → 候选别名对，由人工或
   规则确认后再合并。mock 模式下仅运行规则法。

resolver 返回规范映射 {raw_name → canonical_name}，由
Neo4j 存储在 MERGE 写入时应用。
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from typing import Any

import numpy as np

from app.core.logger import get_logger
from app.services.indexing.embedding import get_embedding_service

logger = get_logger(__name__)

ALIAS_SIMILARITY_THRESHOLD = 0.88

# 硬编码的别名词典（安全领域知识）
_KNOWN_ALIASES: dict[str, str] = {
    "动火": "动火作业",
    "动火工作": "动火作业",
    "受限空间": "受限空间作业",
    "密闭空间": "受限空间作业",
    "高处": "高处作业",
    "高空": "高处作业",
    "临时用电": "临时用电作业",
    "吊装": "吊装作业",
    "动土": "动土作业",
    "挖掘": "动土作业",
    "断路": "断路作业",
    "检维修": "设备检维修",
    "维修": "设备检维修",
    "安全帽": "头部防护用品",
    "安全带": "防坠落用品",
    "呼吸器": "呼吸防护用品",
    "防毒面具": "呼吸防护用品",
    "灭火器": "消防器材",
    "可燃气体检测仪": "气体检测仪",
    "气体报警器": "气体检测仪",
    "作业许可": "作业许可证",
    "动火证": "动火许可证",
    "停电": "停电挂牌",
    "挂牌": "停电挂牌",
}


@dataclass(slots=True)
class EntityRecord:
    """一条从抽取结果中收集到的实体。"""

    name: str
    entity_type: str
    aliases: set[str] = field(default_factory=set)
    doc_ids: set[int] = field(default_factory=set)
    chunk_ids: set[str] = field(default_factory=set)


@dataclass(slots=True)
class ResolutionResult:
    """实体消歧的输出。"""

    canonical_map: dict[str, str]
    entities: list[EntityRecord]
    merge_count: int


def _normalize(name: str) -> str:
    """规范化实体名称以便比较。"""
    return name.strip().lower().replace(" ", "")


def resolve_rule_based(triples: list[dict[str, Any]]) -> ResolutionResult:
    """基于精确匹配 + 已知别名词典进行实体消歧。

    Args:
        triples: 带 subject/object 字段的三元组 dict 列表。

    Returns:
        canonical_map: {raw_name → canonical_name}
        entities: 消歧后的 EntityRecord 列表
        merge_count: 合并的别名数量
    """
    entities: dict[str, EntityRecord] = {}
    canonical_map: dict[str, str] = {}

    def _register(raw_name: str, entity_type: str, doc_id: int = 0, chunk_id: str = "") -> None:
        raw_name = raw_name.strip()
        if not raw_name:
            return
        # 先查已知别名
        canonical = _KNOWN_ALIASES.get(raw_name, raw_name)
        # 再查已消歧的规范化名称
        norm = _normalize(raw_name)
        for existing_canonical, existing_norm in [
            (c, _normalize(c)) for c in entities
        ]:
            if norm == existing_norm:
                canonical = existing_canonical
                break

        canonical_map[raw_name] = canonical
        if canonical not in entities:
            entities[canonical] = EntityRecord(name=canonical, entity_type=entity_type)
        rec = entities[canonical]
        rec.aliases.add(raw_name)
        if doc_id:
            rec.doc_ids.add(doc_id)
        if chunk_id:
            rec.chunk_ids.add(chunk_id)
        # 当原类型为 "unknown" 时采用更宽泛的类型
        if rec.entity_type in ("unknown", "") and entity_type not in ("unknown", ""):
            rec.entity_type = entity_type

    for t in triples:
        _register(t.get("subject", ""), t.get("subject_type", "unknown"),
                  t.get("doc_id", 0), t.get("chunk_id", ""))
        _register(t.get("object", ""), t.get("object_type", "unknown"),
                  t.get("doc_id", 0), t.get("chunk_id", ""))

    merge_count = sum(len(e.aliases) - 1 for e in entities.values())
    logger.info("Rule resolution: %d entities, %d aliases merged",
                len(entities), merge_count)
    return ResolutionResult(
        canonical_map=canonical_map,
        entities=list(entities.values()),
        merge_count=merge_count,
    )


async def resolve_with_embeddings(
    triples: list[dict[str, Any]],
    *,
    similarity_threshold: float = ALIAS_SIMILARITY_THRESHOLD,
) -> ResolutionResult:
    """两阶段消歧：先规则法，再用 embedding 相似度合并。

    mock 模式（无可用编码器）下仅退回规则法。
    """
    # 阶段 1：规则法
    result = resolve_rule_based(triples)
    if not result.entities:
        return result

    # 阶段 2：对尚未合并的实体做 embedding 相似度匹配
    # 编码与矩阵运算均放入线程池执行，避免同步 torch 计算阻塞事件循环。
    try:
        svc = get_embedding_service()
        names = [e.name for e in result.entities]
        vecs = await asyncio.to_thread(svc.encode_dense, names)
    except Exception as exc:  # noqa: BLE001 — 编码器不可用
        logger.info("Embedding resolver skipped (no encoder): %s", exc)
        return result

    # 对未被合并的候选做两两余弦相似度
    canonical_map = dict(result.canonical_map)
    entities_by_name = {e.name: e for e in result.entities}
    merged: set[str] = set()
    new_merges = 0

    # 矩阵化余弦相似度：一次 matmul 得到 N×N 相似度表，
    # 替代纯 Python 的 O(N²)×D 点积循环（数千实体会耗时数十分钟）。
    matrix = np.asarray(vecs, dtype=np.float32)
    norms = np.linalg.norm(matrix, axis=1, keepdims=True)
    norms[norms == 0.0] = 1.0
    matrix = matrix / norms
    sim = await asyncio.to_thread(lambda: matrix @ matrix.T)

    for i, (name_i, _vec_i) in enumerate(zip(names, vecs, strict=False)):
        if name_i in merged:
            continue
        for j in range(i + 1, len(names)):
            name_j = names[j]
            if name_j in merged or name_j == name_i:
                continue
            if float(sim[i, j]) < similarity_threshold:
                continue
            sim_ij = float(sim[i, j])
            logger.info("Embedding merge: '%s' -> '%s' (sim=%.3f)",
                        name_j, name_i, sim_ij)
            for raw, canonical in canonical_map.items():
                if canonical == name_j:
                    canonical_map[raw] = name_i
            if name_j in entities_by_name:
                entities_by_name[name_i].aliases |= entities_by_name[name_j].aliases
                entities_by_name[name_i].doc_ids |= entities_by_name[name_j].doc_ids
                entities_by_name[name_i].chunk_ids |= entities_by_name[name_j].chunk_ids
                del entities_by_name[name_j]
                merged.add(name_j)
                new_merges += 1

    logger.info("Embedding resolution: %d additional merges", new_merges)
    return ResolutionResult(
        canonical_map=canonical_map,
        entities=list(entities_by_name.values()),
        merge_count=result.merge_count + new_merges,
    )


def _cosine(a: list[float], b: list[float]) -> float:
    """两个稠密向量之间的余弦相似度。"""
    import math

    dot = sum(x * y for x, y in zip(a, b, strict=False))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(y * y for y in b))
    if na == 0 or nb == 0:
        return 0.0
    return dot / (na * nb)
