"""多模态 RAG 流水线测试（P4）。

覆盖：
    - 页面图像化 + 页面哈希（page_image.py）
    - 编码器两阶段检索：MaxSim + 余弦（multimodal_encoder.py）
    - 使用 fake 编码器的 MultimodalRagTool（multimodal_rag.py）
    - QA 图集成：visual 查询路由到 multimodal_rag
    - build_fused_context 包含视觉上下文块
"""

from __future__ import annotations

import hashlib
from typing import Any

import fakeredis.aioredis
import pytest

from app.services.indexing.page_image import (
    page_hash_from_text,
)
from app.services.rag.multimodal_encoder import (
    TextDescriptionEncoder,
    cosine_sim,
    maxsim_score,
    two_stage_retrieve,
)
from app.tools.multimodal_rag import MultimodalRagTool
from app.workflows.safety_qa.nodes import (
    TOOL_ROUTE_TABLE,
    QAContext,
    build_fused_context,
)

# ---------------------------------------------------------------------------
# 页面图像 / 哈希测试
# ---------------------------------------------------------------------------


def test_page_hash_deterministic():
    """相同文本 -> 相同哈希。"""
    h1 = page_hash_from_text("动火作业许可证审批流程")
    h2 = page_hash_from_text("动火作业许可证审批流程")
    assert h1 == h2
    assert len(h1) == 32


def test_page_hash_differs_on_content():
    """不同文本 -> 不同哈希。"""
    h1 = page_hash_from_text("动火作业许可证审批流程")
    h2 = page_hash_from_text("受限空间作业审批流程")
    assert h1 != h2


def test_page_hash_uses_sha256():
    """验证哈希与 sha256 实现一致。"""
    text = "测试页面内容"
    expected = hashlib.sha256(text.encode("utf-8")).hexdigest()[:32]
    assert page_hash_from_text(text) == expected


# ---------------------------------------------------------------------------
# 编码器检索函数测试
# ---------------------------------------------------------------------------


def test_cosine_sim_identical():
    v = [1.0, 0.0, 0.0]
    assert cosine_sim(v, v) == pytest.approx(1.0)


def test_cosine_sim_orthogonal():
    assert cosine_sim([1.0, 0.0], [0.0, 1.0]) == pytest.approx(0.0)


def test_cosine_sim_zero_vector():
    assert cosine_sim([0.0, 0.0], [1.0, 0.0]) == 0.0


def test_maxsim_score_basic():
    """token 重叠时应得到非零分数。"""
    query_tokens = {1: 0.5, 2: 0.3}
    page_tokens = {1: 0.8, 3: 0.1}
    score = maxsim_score(query_tokens, page_tokens)
    # 仅 token 1 重叠：0.5 * 0.8 = 0.4
    assert score == pytest.approx(0.4)


def test_maxsim_score_no_overlap():
    query_tokens = {1: 0.5}
    page_tokens = {2: 0.5}
    assert maxsim_score(query_tokens, page_tokens) == 0.0


def test_maxsim_score_empty():
    assert maxsim_score({}, {1: 0.5}) == 0.0
    assert maxsim_score({1: 0.5}, {}) == 0.0


def test_two_stage_retrieve_basic():
    """两阶段检索按融合分数对页面排序返回。"""
    # 3 个页面，dense + sparse 特征各不相同
    query_dense = [1.0, 0.0]
    query_sparse = {0: 1.0}

    pages = [
        # 页面 0：dense 相似度高，sparse 无重叠
        ([1.0, 0.0], {}),
        # 页面 1：dense 中等，sparse 重叠高
        ([0.5, 0.5], {0: 1.0}),
        # 页面 2：dense 低，sparse 无重叠
        ([0.0, 1.0], {}),
    ]

    results = two_stage_retrieve(
        query_dense, query_sparse, pages,
        prefilter_k=3, final_k=2,
    )
    assert len(results) == 2
    # 页面 0 应排第一（cosine=1.0, maxsim=0.0, fused=0.6）
    # 页面 1 应排第二（cosine=0.707, maxsim=1.0, fused=0.424+0.4=0.824）
    # 实际上页面 1 fused = 0.6*0.707 + 0.4*1.0 = 0.424+0.4 = 0.824
    # 页面 0 fused = 0.6*1.0 + 0.4*0.0 = 0.6
    # 所以页面 1 > 页面 0
    assert results[0][0] == 1  # 页面 1 第一
    assert results[1][0] == 0  # 页面 0 第二


def test_two_stage_retrieve_empty():
    results = two_stage_retrieve([1.0], {}, [], prefilter_k=5, final_k=3)
    assert results == []


def test_two_stage_retrieve_prefilter_cutoff():
    """预筛阶段在 MaxSim 之前限制候选数量。"""
    query_dense = [1.0, 0.0]
    query_sparse = {0: 1.0}

    pages = [
        ([1.0, 0.0], {0: 1.0}),  # 最优
        ([0.9, 0.1], {}),
        ([0.8, 0.2], {}),
        ([0.7, 0.3], {}),
        ([0.6, 0.4], {}),
    ]

    # prefilter_k=2 表示仅 dense 前 2 的候选参与重排
    results = two_stage_retrieve(
        query_dense, query_sparse, pages,
        prefilter_k=2, final_k=2,
    )
    assert len(results) == 2
    assert results[0][0] == 0  # 最优页面
    assert results[1][0] == 1  # dense 排名第二


# ---------------------------------------------------------------------------
# TextDescriptionEncoder 测试
# ---------------------------------------------------------------------------


class FakeEmbedder:
    """用于测试的确定性 fake embedder。"""

    def encode(self, texts: list[str]) -> tuple[list[list[float]], list[dict[int, float]]]:
        dense_list: list[list[float]] = []
        sparse_list: list[dict[int, float]] = []
        for text in texts:
            vec = [0.0] * 1024
            for ch in set(text.replace(" ", "")):
                slot = int(
                    hashlib.md5(ch.encode(), usedforsecurity=False).hexdigest(), 16
                ) % 1024
                vec[slot] += 1.0
            norm = sum(x * x for x in vec) ** 0.5 or 1.0
            dense_list.append([x / norm for x in vec])
            # Sparse：同样的 token 作为权重
            sparse: dict[int, float] = {}
            for ch in set(text.replace(" ", "")):
                token_id = int(
                    hashlib.md5(ch.encode(), usedforsecurity=False).hexdigest(), 16
                ) % 10000
                sparse[token_id] = sparse.get(token_id, 0.0) + 1.0
            sparse_list.append(sparse)
        return dense_list, sparse_list


    def encode_dense(self, texts: list[str]) -> list[list[float]]:
        dense, _ = self.encode(texts)
        return dense


def test_text_encoder_degraded(monkeypatch):
    """ColQwen2 不可用时 TextDescriptionEncoder 走 BGE-M3 代理。"""
    fake = FakeEmbedder()

    import app.services.indexing.embedding as emb_mod

    class FakeEmbeddingService:
        def encode(self, texts, batch_size=8):
            return fake.encode(texts)

    monkeypatch.setattr(emb_mod, "get_embedding_service", lambda: FakeEmbeddingService())

    encoder = TextDescriptionEncoder()
    assert not encoder.is_colqwen2
    assert encoder.dim == 1024

    dense, sparse = encoder.encode_query("动火作业示意图")
    assert len(dense) == 1024
    assert len(sparse) > 0

    pages = encoder.encode_pages(["动火作业流程图", "安全疏散路线图"])
    assert len(pages) == 2
    for d, s in pages:
        assert len(d) == 1024
        assert len(s) > 0


# ---------------------------------------------------------------------------
# MultimodalRagTool 测试（使用 fake 编码器）
# ---------------------------------------------------------------------------


class FakeMultimodalEncoder:
    """返回确定性向量的 fake 编码器。"""

    def __init__(self) -> None:
        self._fake = FakeEmbedder()

    def encode_pages(self, descriptions: list[str]):
        return self._fake.encode(descriptions)

    def encode_query(self, query: str):
        d, s = self._fake.encode([query])
        return d[0], s[0]

    @property
    def dim(self) -> int:
        return 1024

    @property
    def is_colqwen2(self) -> bool:
        return False


@pytest.mark.asyncio
async def test_multimodal_tool_degrades_on_failure():
    """Milvus 不可达时工具应返回空列表。"""
    tool = MultimodalRagTool(encoder=FakeMultimodalEncoder())
    # 测试中无 Milvus 运行 -> 应降级为 []
    results = await tool.run("动火作业示意图")
    assert results == []


@pytest.mark.asyncio
async def test_multimodal_tool_index_degrades_on_failure():
    """Milvus 不可达时索引应返回 0。"""
    tool = MultimodalRagTool(encoder=FakeMultimodalEncoder())
    inserted = await tool.index_pages(
        doc_id=1,
        descriptions=["动火作业流程图", "疏散路线图"],
        image_paths=["data/p1.png", "data/p2.png"],
        page_hashes=["hash1", "hash2"],
    )
    assert inserted == 0


# ---------------------------------------------------------------------------
# QA 图集成测试
# ---------------------------------------------------------------------------


class CharEmbedder:
    """语义缓存用的字符集 embedder。"""

    def encode(self, texts: list[str]) -> list[list[float]]:
        return self.encode_dense(texts)

    def encode_dense(self, texts: list[str]) -> list[list[float]]:
        vectors = []
        for text in texts:
            vec = [0.0] * 1024
            for ch in set(text.replace(" ", "")):
                slot = int(
                    hashlib.md5(ch.encode(), usedforsecurity=False).hexdigest(), 16
                ) % 1024
                vec[slot] += 1.0
            norm = sum(x * x for x in vec) ** 0.5 or 1.0
            vectors.append([x / norm for x in vec])
        return vectors


FAKE_VISUAL_HITS = [
    {
        "score": 0.82,
        "page_id": "5:0",
        "doc_id": 5,
        "page_num": 0,
        "page_hash": "abc123",
        "description": "井场布局示意图：标注动火区、受限空间、疏散路线。",
        "image_path": "/data/pages/5/page_0000.png",
        "version": "v1",
        "doc_type": "visual",
    },
]


class FakeMultimodalTool:
    """返回页面级视觉命中的 fake 多模态工具。"""

    async def run(self, query: str, doc_id: int | None = None) -> list[dict[str, Any]]:
        return [dict(h) for h in FAKE_VISUAL_HITS]


class FakeSearchTool:
    async def run(self, query, doc_types=None):
        return []


class FakeLTM:
    async def search_episodic(self, user_id, query, top_k=5, as_of=None):
        return []

    async def search_semantic(self, user_id, query, top_k=5, memory_types=None):
        return []


def test_visual_route_includes_multimodal():
    """visual 查询应同时路由到 hybrid_search 和 multimodal_rag。"""
    assert "multimodal_rag" in TOOL_ROUTE_TABLE["visual"]
    assert "hybrid_search" in TOOL_ROUTE_TABLE["visual"]


@pytest.mark.asyncio
async def test_visual_query_uses_multimodal_tool():
    """visual 查询应触发 multimodal_rag 工具并包含其结果。"""
    from app.services.llm.client import LLMClient
    from app.services.memory.working_memory import WorkingMemory
    from app.tools.memory_retrieval import MemoryRetrievalTool
    from app.tools.semantic_cache import SemanticCache
    from app.workflows.safety_qa.graph import build_safety_qa_graph

    redis = fakeredis.aioredis.FakeRedis(decode_responses=True)
    wm = WorkingMemory(redis=redis)
    ctx = QAContext(
        llm=LLMClient(),  # mock 模式
        memory_tool=MemoryRetrievalTool(wm, FakeLTM()),
        search_tool=FakeSearchTool(),
        cache=SemanticCache(CharEmbedder(), redis=redis),
        multimodal_rag_tool=FakeMultimodalTool(),
    )
    graph = build_safety_qa_graph(ctx)
    result = await graph.ainvoke({
        "session_id": "mm-test-1",
        "user_id": 1,
        "user_position": "司钻",
        "raw_query": "井场发生火灾时的应急疏散路线如何确定？",
        "messages": [],
    })
    assert result["query_type"] == "visual"
    assert "multimodal_rag" in result["planned_tools"]
    # 视觉命中应出现在融合上下文中
    assert "图表" in result["fused_context"] or "页面0" in result["fused_context"]


def test_build_fused_context_with_visual_hits():
    """multimodal_rag 有命中时 build_fused_context 应包含 [图表/图纸] 块。"""
    state = {
        "tool_results": {
            "hybrid_search": [],
            "multimodal_rag": FAKE_VISUAL_HITS,
        },
        "retrieved_memories": [],
    }
    fused, sources = build_fused_context(state)
    assert "[图表/图纸]" in fused
    assert "井场布局" in fused
    assert "页面0" in fused
    # 无 hybrid_search 命中 -> 无文本来源
    assert sources == []


def test_build_fused_context_without_visual_hits():
    """multimodal_rag 无结果时不添加 [图表/图纸] 块。"""
    state = {
        "tool_results": {
            "hybrid_search": [
                {"text": "动火作业流程", "score": 0.8, "doc_type": "规程"},
            ],
            "multimodal_rag": [],
        },
        "retrieved_memories": [],
    }
    fused, _ = build_fused_context(state)
    assert "[图表/图纸]" not in fused
    assert "[1]" in fused  # hybrid_search 命中


def test_build_fused_context_both_text_and_visual():
    """文本与视觉命中应在融合上下文中共存。"""
    state = {
        "tool_results": {
            "hybrid_search": [
                {"text": "安全规程", "score": 0.7, "doc_type": "规程"},
            ],
            "multimodal_rag": FAKE_VISUAL_HITS,
        },
        "retrieved_memories": [],
    }
    fused, sources = build_fused_context(state)
    assert "[1]" in fused  # 文本命中
    assert "[图表/图纸]" in fused  # 视觉块
    assert len(sources) == 1  # 仅统计文本来源
