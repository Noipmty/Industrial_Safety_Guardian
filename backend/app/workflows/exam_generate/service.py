"""ExamGenService —— 组装带依赖的出题 graph。"""

from __future__ import annotations

from functools import lru_cache

from app.core.deps import get_session_factory
from app.services.llm.client import get_llm_client
from app.tools.hybrid_search import HybridSearchTool
from app.workflows.exam_generate.graph import build_exam_generate_graph
from app.workflows.exam_generate.nodes import ExamGenContext


class ExamGenService:
    """持有编译后的出题 graph。"""

    def __init__(self) -> None:
        self.llm = get_llm_client()
        self.search_tool = HybridSearchTool()
        self.session_factory = get_session_factory()
        ctx = ExamGenContext(
            llm=self.llm,
            search_tool=self.search_tool,
            session_factory=self.session_factory,
        )
        self.graph = build_exam_generate_graph(ctx)


@lru_cache
def get_exam_gen_service() -> ExamGenService:
    """共享的出题服务单例。"""
    return ExamGenService()
