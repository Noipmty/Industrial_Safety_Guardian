"""判卷工作流的 LangGraph 组装（2 个 node）。"""

from __future__ import annotations

from langgraph.graph import END, START, StateGraph

from app.workflows.exam_grade.nodes import (
    ExamGradeContext,
    make_grade_objective_node,
    make_grade_subjective_node,
)
from app.workflows.exam_grade.state import ExamGradeState


def build_exam_grade_graph(ctx: ExamGradeContext):
    """编译：grade_objective -> grade_subjective -> END。"""
    builder = StateGraph(ExamGradeState)
    builder.add_node("grade_objective", make_grade_objective_node(ctx))
    builder.add_node("grade_subjective", make_grade_subjective_node(ctx))
    builder.add_edge(START, "grade_objective")
    builder.add_edge("grade_objective", "grade_subjective")
    builder.add_edge("grade_subjective", END)
    return builder.compile()
