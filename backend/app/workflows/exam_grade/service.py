"""ExamGradeService —— 组装带依赖的判卷 graph。"""

from __future__ import annotations

from functools import lru_cache

from app.services.llm.client import get_llm_client
from app.tools.hybrid_search import HybridSearchTool
from app.workflows.exam_grade.graph import build_exam_grade_graph
from app.workflows.exam_grade.nodes import ExamGradeContext


class ExamGradeService:
    """持有编译后的判卷 graph。"""

    def __init__(self) -> None:
        self.llm = get_llm_client()
        self.search_tool = HybridSearchTool()
        ctx = ExamGradeContext(llm=self.llm, search_tool=self.search_tool)
        self.graph = build_exam_grade_graph(ctx)


@lru_cache
def get_exam_grade_service() -> ExamGradeService:
    return ExamGradeService()
