"""出题工作流的 LangGraph 组装（3 个 node）。"""

from __future__ import annotations

from langgraph.graph import END, START, StateGraph

from app.workflows.exam_generate.nodes import (
    ExamGenContext,
    make_generate_questions_node,
    make_intent_detect_node,
    make_quality_check_node,
    route_after_intent,
)
from app.workflows.exam_generate.state import ExamGenState


def build_exam_generate_graph(ctx: ExamGenContext):
    """编译出题 graph：

    intent_detect --no--> END
          |
         yes
          v
    generate_questions -> quality_check -> END
    """
    builder = StateGraph(ExamGenState)
    builder.add_node("intent_detect", make_intent_detect_node(ctx))
    builder.add_node("generate_questions", make_generate_questions_node(ctx))
    builder.add_node("quality_check", make_quality_check_node(ctx))

    builder.add_edge(START, "intent_detect")
    builder.add_conditional_edges(
        "intent_detect",
        route_after_intent,
        {"generate_questions": "generate_questions", END: END},
    )
    builder.add_edge("generate_questions", "quality_check")
    builder.add_edge("quality_check", END)
    return builder.compile()
