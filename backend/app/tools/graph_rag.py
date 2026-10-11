"""GraphRAG 检索工具 —— 锚点实体抽取 + N 跳图遍历。

流程：从查询中抽取锚点实体（基于规则，与已知安全领域实体名做子串
匹配）-> 在 Neo4j 中进行 N 跳图遍历 -> 附加社区摘要 -> 融合为扁平
结果列表。

当 Neo4j 不可达时降级为空列表，QA 工作流仍可依靠向量 / 记忆检索
作答。
"""

from __future__ import annotations

from typing import Any

from app.core.logger import get_logger
from app.services.graph_builder.community import get_community_for_entity
from app.services.graph_builder.neo4j_store import (
    get_neo4j_driver,
    n_hop_traverse,
)

logger = get_logger(__name__)

# 规则式锚点抽取所用的已知实体类型锚点。随安全领域词表扩充可继续
# 追加。
_ANCHOR_ENTITIES: list[str] = [
    "动火作业", "受限空间作业", "高处作业", "临时用电作业",
    "吊装作业", "动土作业", "断路作业", "设备检维修", "粉尘作业",
    "动火许可证", "气体检测", "通风", "监护", "停电挂牌",
    "安全带", "呼吸器", "灭火器", "安全阀", "可燃气体报警器",
]


class GraphRagTool:
    """GraphRAG 检索：锚点抽取 -> 图遍历 -> 社区摘要。"""

    def __init__(self, limit: int = 50) -> None:
        self._limit = limit

    async def run(
        self,
        query: str,
        max_hops: int = 2,
    ) -> list[dict[str, Any]]:
        """为查询检索图上下文实体。

        返回 ``[{"entity", "type", "community_summary", "hops", "score"}]``。
        score 恒为 1.0（图命中是二值的），由下游重排器与向量分数融合。
        """
        driver = get_neo4j_driver()
        if driver is None:
            logger.info("GraphRAG skipped (Neo4j unreachable)")
            return []
        anchors = _extract_anchors(query)
        if not anchors:
            logger.info("GraphRAG: no anchor entities in query '%s'", query[:30])
            return []
        results: list[dict[str, Any]] = []
        seen: set[str] = set()
        for anchor in anchors:
            neighbors = await n_hop_traverse(anchor, max_hops, self._limit)
            for nb in neighbors:
                name = nb.get("name")
                if not name or name in seen:
                    continue
                seen.add(name)
                summary = await get_community_for_entity(name)
                results.append(
                    {
                        "entity": name,
                        "type": nb.get("entity_type", ""),
                        "community_summary": summary or "",
                        "hops": nb.get("hops", 0),
                        "score": 1.0,
                    }
                )
        logger.info("GraphRAG '%s' -> %d entities", query[:30], len(results))
        return results


def _extract_anchors(query: str) -> list[str]:
    """规则式锚点抽取：与已知实体名做子串匹配。"""
    return [entity for entity in _ANCHOR_ENTITIES if entity in query]
