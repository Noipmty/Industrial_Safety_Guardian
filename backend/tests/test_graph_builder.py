"""GraphRAG 构建器测试——离线（mock LLM + Neo4j 降级）。

测试覆盖：
    1. 规则抽取器（正则模式 + 置信度阈值）
    2. 消解器（基于规则的别名合并）
    3. Neo4j 存储（不可达时降级）
    4. 社区发现（基于内存图的 networkx Louvain）
    5. GraphRagTool（锚点抽取 + 降级）
    6. 增量/全量重建（降级路径）
    7. Reconcile（降级路径）
"""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest

from app.services.graph_builder.extractor import (
    CONFIDENCE_THRESHOLD,
    Triple,
    _expand_few_shot,
    _rule_extract,
    extract_from_chunks,
    extract_triples,
)
from app.services.graph_builder.incremental import full_rebuild, incremental_update
from app.services.graph_builder.neo4j_store import (
    n_hop_traverse,
    upsert_entity,
    upsert_relation,
    upsert_triples,
)
from app.services.graph_builder.reconcile import reconcile
from app.services.graph_builder.resolver import (
    _KNOWN_ALIASES,
    ALIAS_SIMILARITY_THRESHOLD,
    resolve_rule_based,
)
from app.services.llm.client import LLMClient
from app.tools.graph_rag import GraphRagTool, _extract_anchors

# ---------------------------------------------------------------------------
# 1. 抽取器
# ---------------------------------------------------------------------------


class TestExtractor:
    """基于规则的抽取 + few-shot 扩充。"""

    def test_rule_extract_finds_operation_needs(self):
        text = "动火作业需要气体检测。动火作业需要通风。"
        triples = _rule_extract(text, "c1", 1)
        subs = {(t.subject, t.relation, t.object) for t in triples}
        assert ("动火作业", "配套", "气体检测") in subs
        assert ("动火作业", "配套", "通风") in subs

    def test_rule_extract_finds_causation(self):
        text = "高处作业可能导致坠落。"
        triples = _rule_extract(text, "c2", 2)
        causals = [t for t in triples if t.relation == "导致"]
        assert any(t.object == "坠落" for t in causals)

    def test_rule_extract_finds_duty(self):
        text = "司钻的职责包括巡回检查。"
        triples = _rule_extract(text, "c3", 3)
        duties = [t for t in triples if t.relation == "责任于"]
        assert any(t.object == "巡回检查" for t in duties)

    def test_rule_extract_deduplicates(self):
        text = "动火作业需要监护。动火作业需要监护。"
        triples = _rule_extract(text, "c4", 4)
        keys = {(t.subject, t.relation, t.object) for t in triples}
        assert len(keys) == len(triples)  # 无重复

    @pytest.mark.asyncio
    async def test_extract_triples_mock_mode(self):
        """LLM mock 模式应走规则抽取。"""
        llm = LLMClient()
        assert llm.mock_mode is True
        result = await extract_triples(
            "动火作业需要灭火器。", chunk_id="c5", doc_id=5, llm=llm
        )
        assert isinstance(result.triples, list)
        assert len(result.triples) > 0
        assert all(t.confidence >= CONFIDENCE_THRESHOLD for t in result.triples)

    @pytest.mark.asyncio
    async def test_extract_from_chunks_multiple(self):
        chunks = [
            {"text": "动火作业需要气体检测。", "chunk_id": "c1", "doc_id": 1},
            {"text": "高处作业需要安全带。", "chunk_id": "c2", "doc_id": 2},
        ]
        results = await extract_from_chunks(chunks)
        assert len(results) == 2
        total = sum(len(r.triples) for r in results)
        assert total >= 2

    def test_few_shot_examples_count(self):
        examples = _expand_few_shot()
        assert len(examples) >= 200

    def test_few_shot_examples_structure(self):
        examples = _expand_few_shot()
        for ex in examples[:5]:
            assert "text" in ex
            assert "triples" in ex
            assert len(ex["triples"]) >= 1
            t = ex["triples"][0]
            assert "subject" in t and "relation" in t and "object" in t


# ---------------------------------------------------------------------------
# 2. 消解器
# ---------------------------------------------------------------------------


class TestResolver:
    """基于规则的实体消解 + 别名合并。"""

    def test_rule_based_merges_known_aliases(self):
        triples = [
            {"subject": "动火", "subject_type": "作业类型",
             "object": "气体检测", "object_type": "安全措施",
             "doc_id": 1, "chunk_id": "c1"},
            {"subject": "动火作业", "subject_type": "作业类型",
             "object": "通风", "object_type": "安全措施",
             "doc_id": 2, "chunk_id": "c2"},
        ]
        result = resolve_rule_based(triples)
        # “动火”应映射到规范名“动火作业”
        assert result.canonical_map.get("动火") == "动火作业"
        # 两个主语实体应合并为一个实体
        entity_names = {e.name for e in result.entities}
        assert "动火作业" in entity_names
        assert result.merge_count >= 1

    def test_rule_based_case_insensitive(self):
        triples = [
            {"subject": "SafetyBelt", "subject_type": "防护用品",
             "object": "坠落", "object_type": "风险因素"},
            {"subject": "safetybelt", "subject_type": "防护用品",
             "object": "冲击", "object_type": "风险因素"},
        ]
        result = resolve_rule_based(triples)
        # 大小写不敏感匹配应将 "safetybelt" 合并为 "SafetyBelt"
        assert result.canonical_map.get("safetybelt") == "SafetyBelt"
        assert result.merge_count >= 1

    def test_alias_threshold_is_0_88(self):
        assert ALIAS_SIMILARITY_THRESHOLD == 0.88

    def test_known_aliases_non_empty(self):
        assert len(_KNOWN_ALIASES) >= 10
        assert _KNOWN_ALIASES.get("动火") == "动火作业"
        assert _KNOWN_ALIASES.get("受限空间") == "受限空间作业"


# ---------------------------------------------------------------------------
# 3. Neo4j 存储（降级路径——CI 中无真实 Neo4j）
# ---------------------------------------------------------------------------


class TestNeo4jStore:
    """Neo4j 不可达时，所有操作应优雅降级。"""

    @pytest.mark.asyncio
    async def test_upsert_entity_returns_without_error(self):
        """driver 为 None 时 upsert_entity 不应抛异常。"""
        with patch(
            "app.services.graph_builder.neo4j_store.get_neo4j_driver",
            return_value=None,
        ):
            await upsert_entity("test_entity", "作业类型", [], [], [])

    @pytest.mark.asyncio
    async def test_upsert_relation_returns_without_error(self):
        with patch(
            "app.services.graph_builder.neo4j_store.get_neo4j_driver",
            return_value=None,
        ):
            await upsert_relation("A", "导致", "B", 0.9, "c1", 1)

    @pytest.mark.asyncio
    async def test_upsert_triples_returns_zeros(self):
        triples = [Triple("A", "作业类型", "导致", "B", "风险因素")]
        with patch(
            "app.services.graph_builder.neo4j_store.get_neo4j_driver",
            return_value=None,
        ):
            counts = await upsert_triples(triples, {})
        assert counts == {"entities": 0, "relations": 0}

    @pytest.mark.asyncio
    async def test_n_hop_traverse_returns_empty_when_unreachable(self):
        with patch(
            "app.services.graph_builder.neo4j_store.get_neo4j_driver",
            return_value=None,
        ):
            result = await n_hop_traverse("动火作业", max_hops=2, limit=10)
        assert result == []

    @pytest.mark.asyncio
    async def test_n_hop_traverse_invalid_hops_raises(self):
        with pytest.raises(ValueError, match="max_hops"):
            await n_hop_traverse("动火作业", max_hops=0)
        with pytest.raises(ValueError, match="max_hops"):
            await n_hop_traverse("动火作业", max_hops=10)


# ---------------------------------------------------------------------------
# 4. 社区发现（networkx 内存图）
# ---------------------------------------------------------------------------


class TestCommunity:
    """基于内存图使用 networkx Louvain 进行社区发现。"""

    @pytest.mark.asyncio
    async def test_detect_communities_unreachable_returns_empty(self):
        from app.services.graph_builder.community import detect_communities

        result = await detect_communities(driver=None)
        assert result == []

    @pytest.mark.asyncio
    async def test_summarize_community_mock_mode(self):
        from app.services.graph_builder.community import summarize_community

        llm = LLMClient()
        assert llm.mock_mode
        summary = await summarize_community(
            ["动火作业", "气体检测"], [], llm
        )
        assert "动火作业" in summary or "实体" in summary

    @pytest.mark.asyncio
    async def test_summarize_community_no_llm(self):
        from app.services.graph_builder.community import summarize_community

        summary = await summarize_community(["高处作业", "安全带"], [], None)
        assert len(summary) > 0

    @pytest.mark.asyncio
    async def test_build_and_summarize_unreachable(self):
        from app.services.graph_builder.community import build_and_summarize

        result = await build_and_summarize(driver=None, llm=None)
        assert result == []


# ---------------------------------------------------------------------------
# 5. GraphRagTool（锚点抽取 + 工具降级）
# ---------------------------------------------------------------------------


class TestGraphRagTool:
    """锚点抽取 + 工具降级。"""

    def test_extract_anchors_finds_known_entities(self):
        anchors = _extract_anchors("动火作业需要什么安全措施？")
        assert "动火作业" in anchors

    def test_extract_anchors_no_match(self):
        anchors = _extract_anchors("今天天气怎么样？")
        assert anchors == []

    def test_extract_anchors_multiple(self):
        anchors = _extract_anchors("动火作业和受限空间作业的区别")
        assert "动火作业" in anchors
        assert "受限空间作业" in anchors

    @pytest.mark.asyncio
    async def test_run_returns_empty_when_neo4j_unreachable(self):
        tool = GraphRagTool()
        with patch(
            "app.services.graph_builder.neo4j_store.get_neo4j_driver",
            return_value=None,
        ):
            result = await tool.run("动火作业需要什么？")
        assert result == []

    @pytest.mark.asyncio
    async def test_run_no_anchors_returns_empty(self):
        tool = GraphRagTool()
        with patch(
            "app.services.graph_builder.neo4j_store.get_neo4j_driver",
            return_value=AsyncMock(),
        ):
            result = await tool.run("今天天气怎么样？")
        assert result == []


# ---------------------------------------------------------------------------
# 6. 增量/全量重建（降级路径）
# ---------------------------------------------------------------------------


class TestRebuild:
    """Neo4j 不可达时，重建应返回零计数。"""

    @pytest.mark.asyncio
    async def test_full_rebuild_unreachable(self):
        chunks = [{"text": "动火作业需要气体检测。", "chunk_id": "c1", "doc_id": 1}]
        with patch(
            "app.services.graph_builder.incremental.get_neo4j_driver",
            return_value=None,
        ):
            result = await full_rebuild(chunks, llm=LLMClient())
        assert result["entities"] == 0
        assert result["relations"] == 0
        assert result["communities"] == 0
        assert result["mode"] == "full"

    @pytest.mark.asyncio
    async def test_incremental_update_unreachable(self):
        chunks = [{"text": "高处作业需要安全带。", "chunk_id": "c2", "doc_id": 2}]
        with patch(
            "app.services.graph_builder.incremental.get_neo4j_driver",
            return_value=None,
        ):
            result = await incremental_update(chunks, llm=LLMClient())
        assert result["entities"] == 0
        assert result["mode"] == "incremental"

    @pytest.mark.asyncio
    async def test_reconcile_check_delegates(self):
        # Neo4j 不可达时 reconcile 应降级
        with patch(
            "app.services.graph_builder.reconcile.get_neo4j_driver",
            return_value=None,
        ):
            result = await reconcile()
        assert result.get("ok") is False


# ---------------------------------------------------------------------------
# 7. 集成：融合上下文包含 graph_rag 结果
# ---------------------------------------------------------------------------


class TestFusedContext:
    """build_fused_context 应包含 graph_rag 块。"""

    def test_fused_context_includes_graph_results(self):
        from app.workflows.safety_qa.nodes import build_fused_context

        state = {
            "tool_results": {
                "hybrid_search": [
                    {"text": "动火作业规程", "score": 0.8, "doc_type": "操作规程"},
                ],
                "graph_rag": [
                    {
                        "entity": "动火作业",
                        "type": "作业类型",
                        "community_summary": "动火安全社区",
                        "hops": 1,
                        "score": 1.0,
                    },
                ],
            },
            "retrieved_memories": [],
        }
        fused, sources = build_fused_context(state)
        assert "[图知识]" in fused
        assert "动火作业" in fused

    def test_fused_context_no_graph_results(self):
        from app.workflows.safety_qa.nodes import build_fused_context

        state = {
            "tool_results": {
                "hybrid_search": [
                    {"text": "安全规程", "score": 0.7, "doc_type": "规程"},
                ],
            },
            "retrieved_memories": [],
        }
        fused, _ = build_fused_context(state)
        assert "[图知识]" not in fused
