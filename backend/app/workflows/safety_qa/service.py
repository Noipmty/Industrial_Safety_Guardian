"""QAService —— 组装带生产依赖的安全问答 graph。"""

from __future__ import annotations

from functools import lru_cache
from typing import Any

from app.services.faq import get_faq_service
from app.services.indexing.embedding import get_dense_embedder
from app.services.memory.working_memory import WorkingMemory


def _make_summarizer(llm: Any):
    """构造工作记忆压缩器：把一批消息压成 ≤200 字摘要（LLM）。"""

    async def summarize(messages: list[dict[str, str]]) -> str:
        transcript = "\n".join(
            f"{'用户' if m.get('role') == 'user' else '助手'}: "
            f"{str(m.get('content', ''))[:200]}"
            for m in messages
        )[-6000:]
        resp = await llm.chat(
            [
                {
                    "role": "system",
                    "content": (
                        "你是工业安全问答系统的会话记忆压缩器。"
                        "把对话压缩为不超过 200 字的摘要，必须保留："
                        "用户的关注点与岗位背景、已给出的关键结论、未决事项。"
                        "只输出摘要正文。"
                    ),
                },
                {"role": "user", "content": transcript},
            ],
            max_tokens=512,
        )
        return str(resp.json()).strip()

    return summarize
from app.services.llm.client import get_llm_client
from app.services.memory.long_term import LongTermMemory
from app.tools.graph_rag import GraphRagTool
from app.tools.hybrid_search import HybridSearchTool
from app.tools.memory_retrieval import MemoryRetrievalTool
from app.tools.multimodal_rag import MultimodalRagTool
from app.tools.semantic_cache import SemanticCache
from app.workflows.safety_qa.graph import build_safety_qa_graph
from app.workflows.safety_qa.nodes import QAContext


class QAService:
    """持有编译后的 graph + 会话簿记辅助。"""

    def __init__(self) -> None:
        embedder = get_dense_embedder()
        self.llm = get_llm_client()
        self.working_memory = WorkingMemory(summarizer=_make_summarizer(self.llm))
        self.long_term_memory = LongTermMemory(embedder)
        self.cache = SemanticCache(embedder)
        self.memory_tool = MemoryRetrievalTool(self.working_memory, self.long_term_memory)
        self.search_tool = HybridSearchTool()
        self.graph_rag_tool = GraphRagTool()
        self.multimodal_rag_tool = MultimodalRagTool()
        try:
            faq_service: Any | None = get_faq_service()
        except Exception:  # noqa: BLE001 —— FAQ 层故障不阻断 QA 服务
            faq_service = None
        ctx = QAContext(
            llm=self.llm,
            memory_tool=self.memory_tool,
            search_tool=self.search_tool,
            cache=self.cache,
            graph_rag_tool=self.graph_rag_tool,
            multimodal_rag_tool=self.multimodal_rag_tool,
            faq_service=faq_service,
        )
        self.graph = build_safety_qa_graph(ctx)


@lru_cache
def get_qa_service() -> QAService:
    """共享的 QA 服务单例。"""
    return QAService()
